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
