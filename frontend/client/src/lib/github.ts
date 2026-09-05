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

/* ─── Mock Data for Demo Account ("leakguard-demo") ──────────────────────── */

const MOCK_LEAKGUARD_USER: GitHubUser = {
  login: "leakguard-demo",
  name: "LeakGuard Security Demo",
  avatar_url: "https://avatars.githubusercontent.com/u/9919?v=4",
  public_repos: 4,
  followers: 142,
  following: 12,
  bio: "Official LeakGuard Action & CodeGate Static Analyzer Demo Account",
  html_url: "https://github.com/leakguard-demo",
};

const MOCK_LEAKGUARD_REPOS: GitHubRepo[] = [
  {
    id: 991,
    name: "leakguard-action",
    full_name: "leakguard-demo/leakguard-action",
    description: "Automated resource leak detection for GitHub Actions & CI workflows",
    stargazers_count: 142,
    forks_count: 38,
    language: "Python",
    updated_at: new Date().toISOString(),
    html_url: "https://github.com/leakguard-demo/leakguard-action",
    default_branch: "main",
  },
  {
    id: 992,
    name: "secure-flask-api",
    full_name: "leakguard-demo/secure-flask-api",
    description: "High-performance REST API backend with automated leak prevention",
    stargazers_count: 88,
    forks_count: 14,
    language: "Python",
    updated_at: new Date(Date.now() - 86400000).toISOString(),
    html_url: "https://github.com/leakguard-demo/secure-flask-api",
    default_branch: "main",
  },
  {
    id: 993,
    name: "data-pipeline-service",
    full_name: "leakguard-demo/data-pipeline-service",
    description: "ETL stream pipeline with AST control-flow verification",
    stargazers_count: 56,
    forks_count: 9,
    language: "Python",
    updated_at: new Date(Date.now() - 172800000).toISOString(),
    html_url: "https://github.com/leakguard-demo/data-pipeline-service",
    default_branch: "main",
  },
  {
    id: 994,
    name: "cloud-storage-helper",
    full_name: "leakguard-demo/cloud-storage-helper",
    description: "S3 & Blob storage SDK wrapper with exception liveness tracking",
    stargazers_count: 34,
    forks_count: 4,
    language: "Python",
    updated_at: new Date(Date.now() - 259200000).toISOString(),
    html_url: "https://github.com/leakguard-demo/cloud-storage-helper",
    default_branch: "main",
  },
];

const MOCK_LEAKGUARD_COMMITS: GitHubCommit[] = [
  {
    sha: "a7d8e9f",
    message: "fix(core): close file descriptors on exception exit in analyzer.py",
    authorName: "LeakGuard Bot",
    authorAvatar: "https://avatars.githubusercontent.com/u/9919?v=4",
    date: new Date().toISOString(),
    htmlUrl: "https://github.com/leakguard-demo/leakguard-action/commit/a7d8e9f",
  },
  {
    sha: "b3c4d5e",
    message: "feat(scanner): trace control-flow graph for subprocess Popen handles",
    authorName: "LeakGuard Lead",
    authorAvatar: "https://avatars.githubusercontent.com/u/9919?v=4",
    date: new Date(Date.now() - 7200000).toISOString(),
    htmlUrl: "https://github.com/leakguard-demo/leakguard-action/commit/b3c4d5e",
  },
  {
    sha: "f1e2d3c",
    message: "ci(leakguard): configure GitHub Actions PR scanner & annotations",
    authorName: "DevOps Engineer",
    authorAvatar: "https://avatars.githubusercontent.com/u/9919?v=4",
    date: new Date(Date.now() - 86400000).toISOString(),
    htmlUrl: "https://github.com/leakguard-demo/leakguard-action/commit/f1e2d3c",
  },
  {
    sha: "9a8b7c6",
    message: "refactor(api): convert socket creation to context manager with-block",
    authorName: "Security Auditor",
    authorAvatar: "https://avatars.githubusercontent.com/u/9919?v=4",
    date: new Date(Date.now() - 172800000).toISOString(),
    htmlUrl: "https://github.com/leakguard-demo/leakguard-action/commit/9a8b7c6",
  },
  {
    sha: "4e5f6a7",
    message: "test(analyzer): add regression test cases for socket leaks & branch liveness",
    authorName: "QA Lead",
    authorAvatar: "https://avatars.githubusercontent.com/u/9919?v=4",
    date: new Date(Date.now() - 259200000).toISOString(),
    htmlUrl: "https://github.com/leakguard-demo/leakguard-action/commit/4e5f6a7",
  },
];

/**
 * Optional auth header. A PAT stored under `github_token` (same key the
 * dashboard clears on logout) lifts the 60 req/h unauthenticated rate limit.
 */
function ghHeaders(): HeadersInit {
  const token =
    typeof localStorage !== "undefined" ? localStorage.getItem("github_token") : null;
  if (!token) return { Accept: "application/vnd.github+json" };
  const authHeader =
    token.startsWith("ghp_") || token.startsWith("github_pat_") || token.startsWith("gho_")
      ? `token ${token}`
      : `Bearer ${token}`;
  return {
    Authorization: authHeader,
    Accept: "application/vnd.github+json",
  };
}

export async function fetchGitHubUser(username: string): Promise<GitHubUser | null> {
  if (!username) return null;
  if (username.toLowerCase() === "leakguard-demo") {
    return MOCK_LEAKGUARD_USER;
  }
  try {
    const res = await fetch(`https://api.github.com/users/${username}`, {
      headers: ghHeaders(),
    });
    if (!res.ok) {
      if (res.status === 403) {
        console.warn(`GitHub API Rate limit (403) reached fetching user @${username}`);
      }
      return null;
    }
    return await res.json();
  } catch (err) {
    console.error("Error fetching GitHub user:", err);
    return null;
  }
}

export async function fetchUserRepos(username: string): Promise<GitHubRepo[]> {
  if (!username) return [];
  if (username.toLowerCase() === "leakguard-demo") {
    return MOCK_LEAKGUARD_REPOS;
  }
  try {
    const res = await fetch(
      `https://api.github.com/users/${username}/repos?sort=updated&per_page=30`,
      { headers: ghHeaders() }
    );
    if (!res.ok) {
      if (res.status === 403) {
        console.warn(`GitHub API Rate limit (403) reached fetching repos for @${username}`);
      }
      return [];
    }
    return await res.json();
  } catch (err) {
    console.error("Error fetching GitHub repos:", err);
    return [];
  }
}

export async function fetchRepoCommits(
  username: string,
  repo: string,
  branch?: string
): Promise<GitHubCommit[]> {
  if (!username || !repo) return [];
  if (username.toLowerCase() === "leakguard-demo") {
    return MOCK_LEAKGUARD_COMMITS;
  }
  try {
    const url =
      `https://api.github.com/repos/${username}/${repo}/commits?per_page=50` +
      (branch ? `&sha=${encodeURIComponent(branch)}` : "");
    const res = await fetch(url, { headers: ghHeaders() });
    if (!res.ok) {
      if (res.status === 403) {
        console.warn(`GitHub API Rate limit (403) reached fetching commits for ${username}/${repo}`);
      }
      return [];
    }
    const data = await res.json();
    if (!Array.isArray(data)) return [];

    return data.map((item: any) => ({
      sha: item.sha.substring(0, 7),
      message: item.commit?.message || "Commit",
      authorName: item.commit?.author?.name || item.author?.login || username,
      authorAvatar: item.author?.avatar_url || "https://avatars.githubusercontent.com/u/9919?v=4",
      date: item.commit?.author?.date || item.commit?.committer?.date || new Date().toISOString(),
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

export async function fetchRepoMeta(
  owner: string,
  repo: string
): Promise<GitHubRepo | null> {
  if (!owner || !repo) return null;
  if (owner.toLowerCase() === "leakguard-demo") {
    return MOCK_LEAKGUARD_REPOS.find(r => r.name === repo) || MOCK_LEAKGUARD_REPOS[0];
  }
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
  if (!owner || !repo) return [];
  if (owner.toLowerCase() === "leakguard-demo") {
    return [
      { path: "codegate/analyzer.py", size: 4200, sha: "a7d8e9f" },
      { path: "codegate/webapi.py", size: 3100, sha: "b3c4d5e" },
      { path: "codegate/cli.py", size: 2800, sha: "f1e2d3c" },
      { path: "app/routes.py", size: 1900, sha: "9a8b7c6" },
      { path: "pipeline/stream.py", size: 3500, sha: "4e5f6a7" },
    ];
  }
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
  if (!owner || !repo || !path) return null;
  if (owner.toLowerCase() === "leakguard-demo") {
    return `def read_file(path):\n    f = open(path)\n    data = f.read()\n    if not data:\n        return None   # LEAK: f never closed\n    f.close()\n    return data\n`;
  }
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
