export interface GitHubRepo {
  id: number;
  name: string;
  full_name: string;
  description: string | null;
  stargazers_count: number;
  forks_count: number;
  language: string | null;
  updated_at: string;
  html_url: string;
  default_branch: string;
}

export interface GitHubCommit {
  sha: string;
  message: string;
  authorName: string;
  authorAvatar: string;
  date: string;
  htmlUrl: string;
}

export interface GitHubUser {
  login: string;
  name: string;
  avatar_url: string;
  public_repos: number;
  followers: number;
  following: number;
  bio: string | null;
  html_url: string;
}

export interface CommitTimelinePoint {
  date: string;
  count: number;
  message?: string;
  sha?: string;
}

export async function fetchGitHubUser(username: string): Promise<GitHubUser | null> {
  try {
    const res = await fetch(`https://api.github.com/users/${username}`);
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error("Error fetching GitHub user:", err);
    return null;
  }
}

export async function fetchUserRepos(username: string): Promise<GitHubRepo[]> {
  try {
    const res = await fetch(
      `https://api.github.com/users/${username}/repos?sort=updated&per_page=30`
    );
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.error("Error fetching GitHub repos:", err);
    return [];
  }
}

export async function fetchRepoCommits(
  username: string,
  repo: string
): Promise<GitHubCommit[]> {
  try {
    const res = await fetch(
      `https://api.github.com/repos/${username}/${repo}/commits?per_page=50`
    );
    if (!res.ok) return [];
    const data = await res.json();
    if (!Array.isArray(data)) return [];

    return data.map((item: any) => ({
      sha: item.sha.substring(0, 7),
      message: item.commit.message,
      authorName: item.commit.author?.name || username,
      authorAvatar: item.author?.avatar_url || "https://github.com/github.png",
      date: item.commit.author?.date || new Date().toISOString(),
      htmlUrl: item.html_url,
    }));
  } catch (err) {
    console.error(`Error fetching commits for ${repo}:`, err);
    return [];
  }
}

export function processCommitTimeline(commits: GitHubCommit[]): CommitTimelinePoint[] {
  if (!commits || commits.length === 0) {
    return [
      { date: "Aug 1", count: 2 },
      { date: "Aug 5", count: 5 },
      { date: "Aug 10", count: 3 },
      { date: "Aug 15", count: 8 },
      { date: "Aug 20", count: 4 },
      { date: "Aug 25", count: 12 },
      { date: "Sep 1", count: 7 },
    ];
  }

  const dateMap: { [dateStr: string]: { count: number; message: string; sha: string } } = {};
  const sorted = [...commits].reverse();

  sorted.forEach((c) => {
    const d = new Date(c.date);
    const dateLabel = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    if (!dateMap[dateLabel]) {
      dateMap[dateLabel] = { count: 1, message: c.message, sha: c.sha };
    } else {
      dateMap[dateLabel].count += 1;
    }
  });

  return Object.entries(dateMap).map(([date, data]) => ({
    date,
    count: data.count,
    message: data.message,
    sha: data.sha,
  }));
}

/* ─── Repository source-code access (used by the /graph AST visualizer) ──── */

export interface RepoFile {
  path: string;
  size: number;
  sha: string;
}

/**
 * Optional auth header. A PAT stored under `github_token` (same key the
 * dashboard clears on logout) lifts the 60 req/h unauthenticated rate limit.
 */
function ghHeaders(): HeadersInit {
  const token =
    typeof localStorage !== "undefined" ? localStorage.getItem("github_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchRepoMeta(
  owner: string,
  repo: string
): Promise<GitHubRepo | null> {
  try {
    const res = await fetch(`https://api.github.com/repos/${owner}/${repo}`, {
      headers: ghHeaders(),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error(`Error fetching repo ${owner}/${repo}:`, err);
    return null;
  }
}

/**
 * Full recursive file tree of a repo branch, filtered to source blobs.
 * `extensions` defaults to Python because that is what the CodeGate
 * analyzer can parse.
 */
export async function fetchRepoTree(
  owner: string,
  repo: string,
  branch = "main",
  extensions: string[] = [".py"]
): Promise<RepoFile[]> {
  const load = async (ref: string) =>
    fetch(
      `https://api.github.com/repos/${owner}/${repo}/git/trees/${ref}?recursive=1`,
      { headers: ghHeaders() }
    );

  try {
    let res = await load(branch);
    if (!res.ok && branch !== "master") res = await load("master");
    if (!res.ok) return [];

    const data = await res.json();
    if (!Array.isArray(data?.tree)) return [];

    return data.tree
      .filter(
        (n: any) =>
          n.type === "blob" &&
          extensions.some((ext) => String(n.path).toLowerCase().endsWith(ext))
      )
      .map((n: any) => ({ path: n.path as string, size: n.size ?? 0, sha: n.sha as string }))
      .sort((a: RepoFile, b: RepoFile) => a.path.localeCompare(b.path));
  } catch (err) {
    console.error(`Error fetching tree for ${owner}/${repo}:`, err);
    return [];
  }
}

/** Raw UTF-8 source of a single file (Contents API, base64-decoded). */
export async function fetchFileContent(
  owner: string,
  repo: string,
  path: string,
  ref?: string
): Promise<string | null> {
  try {
    const url =
      `https://api.github.com/repos/${owner}/${repo}/contents/${path
        .split("/")
        .map(encodeURIComponent)
        .join("/")}` + (ref ? `?ref=${encodeURIComponent(ref)}` : "");

    const res = await fetch(url, { headers: ghHeaders() });
    if (!res.ok) return null;

    const data = await res.json();
    if (typeof data?.content !== "string") return null;

    // atob → bytes → UTF-8 (files with non-ASCII identifiers/comments)
    const binary = atob(data.content.replace(/\n/g, ""));
    const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
    return new TextDecoder("utf-8").decode(bytes);
  } catch (err) {
    console.error(`Error fetching ${path} from ${owner}/${repo}:`, err);
    return null;
  }
}
