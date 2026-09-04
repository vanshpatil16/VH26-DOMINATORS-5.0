/**
 * GitHub Actions / Checks API client.
 *
 * The LeakGuard workflow (.github/workflows/codegate.yml) runs `codegate.ci`
 * on every push and PR; the analyzer prints `::error`/`::warning` workflow
 * commands, which GitHub stores as *check-run annotations*. This module reads
 * that trail back out: workflow runs → check runs → annotations, plus the
 * branch list, so the admin panel can show what leaked, where, and when.
 *
 * Everything degrades gracefully: private repos and the annotations endpoint
 * need a token (localStorage `github_token`), and callers get a typed error
 * instead of an exception.
 */

export interface WorkflowRunInfo {
  id: number;
  name: string;
  workflowId: number;
  event: string;               // push | pull_request | workflow_dispatch | …
  headBranch: string;
  headSha: string;
  status: string;              // queued | in_progress | completed
  conclusion: string | null;   // success | failure | cancelled | …
  createdAt: string;
  htmlUrl: string;
  actor: string;
  actorAvatar: string;
  runNumber: number;
  prNumbers: number[];
  commitMessage: string;
}

export interface CheckRunInfo {
  id: number;
  name: string;
  status: string;
  conclusion: string | null;
  annotationsCount: number;
  htmlUrl: string;
  summary: string | null;
}

export interface CheckAnnotation {
  path: string;
  startLine: number;
  endLine: number;
  level: "failure" | "warning" | "notice";
  title: string;
  message: string;
  rawDetails: string | null;
}

export interface BranchInfo {
  name: string;
  sha: string;
  isProtected: boolean;
}

export interface RateSnapshot {
  limit: number;
  remaining: number;
  resetAt: number; // epoch seconds
  authenticated: boolean;
}

export interface GhError {
  status: number;
  message: string;
  /** true when the call would work with a token (private repo / rate limit). */
  needsAuth: boolean;
}

export type GhResult<T> = { ok: true; data: T } | { ok: false; error: GhError };

/* ─── token + rate limit ─────────────────────────────────────────────────── */

export const TOKEN_KEY = "github_token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage disabled — calls simply stay unauthenticated */
  }
}

let rateSnapshot: RateSnapshot | null = null;

export function getRateSnapshot(): RateSnapshot | null {
  return rateSnapshot;
}

function headers(): HeadersInit {
  const token = getToken();
  const base: Record<string, string> = { Accept: "application/vnd.github+json" };
  if (token) base.Authorization = `Bearer ${token}`;
  return base;
}

async function ghJson<T>(url: string): Promise<GhResult<T>> {
  let res: Response;
  try {
    res = await fetch(url, { headers: headers() });
  } catch (err) {
    return {
      ok: false,
      error: { status: 0, message: err instanceof Error ? err.message : "network error", needsAuth: false },
    };
  }

  const limit = Number(res.headers.get("x-ratelimit-limit") ?? 0);
  if (limit > 0) {
    rateSnapshot = {
      limit,
      remaining: Number(res.headers.get("x-ratelimit-remaining") ?? 0),
      resetAt: Number(res.headers.get("x-ratelimit-reset") ?? 0),
      authenticated: !!getToken(),
    };
  }

  if (!res.ok) {
    const exhausted = res.status === 403 && rateSnapshot?.remaining === 0;
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.message) message = body.message;
    } catch {
      /* keep the status-code message */
    }
    return {
      ok: false,
      error: {
        status: res.status,
        message: exhausted ? "GitHub rate limit exhausted — add a token to continue." : message,
        needsAuth: exhausted || res.status === 401 || res.status === 404 || res.status === 403,
      },
    };
  }

  return { ok: true, data: (await res.json()) as T };
}

/* ─── endpoints ──────────────────────────────────────────────────────────── */

export async function fetchWorkflowRuns(
  owner: string,
  repo: string,
  opts: { perPage?: number; branch?: string; event?: string } = {}
): Promise<GhResult<WorkflowRunInfo[]>> {
  const params = new URLSearchParams({ per_page: String(opts.perPage ?? 20) });
  if (opts.branch) params.set("branch", opts.branch);
  if (opts.event) params.set("event", opts.event);

  const res = await ghJson<{ workflow_runs?: any[] }>(
    `https://api.github.com/repos/${owner}/${repo}/actions/runs?${params}`
  );
  if (!res.ok) return res;

  const runs = (res.data.workflow_runs ?? []).map(
    (r: any): WorkflowRunInfo => ({
      id: r.id,
      name: r.name ?? "workflow",
      workflowId: r.workflow_id,
      event: r.event,
      headBranch: r.head_branch ?? "(detached)",
      headSha: r.head_sha ?? "",
      status: r.status,
      conclusion: r.conclusion ?? null,
      createdAt: r.created_at,
      htmlUrl: r.html_url,
      actor: r.actor?.login ?? r.triggering_actor?.login ?? "unknown",
      actorAvatar: r.actor?.avatar_url ?? "https://github.com/github.png",
      runNumber: r.run_number ?? 0,
      prNumbers: Array.isArray(r.pull_requests) ? r.pull_requests.map((p: any) => p.number) : [],
      commitMessage: (r.head_commit?.message ?? "").split("\n")[0],
    })
  );
  return { ok: true, data: runs };
}

export async function fetchCheckRuns(
  owner: string,
  repo: string,
  sha: string
): Promise<GhResult<CheckRunInfo[]>> {
  const res = await ghJson<{ check_runs?: any[] }>(
    `https://api.github.com/repos/${owner}/${repo}/commits/${sha}/check-runs?per_page=30`
  );
  if (!res.ok) return res;

  const checks = (res.data.check_runs ?? []).map(
    (c: any): CheckRunInfo => ({
      id: c.id,
      name: c.name ?? "check",
      status: c.status,
      conclusion: c.conclusion ?? null,
      annotationsCount: c.output?.annotations_count ?? 0,
      htmlUrl: c.html_url,
      summary: c.output?.summary ?? null,
    })
  );
  return { ok: true, data: checks };
}

export async function fetchCheckAnnotations(
  owner: string,
  repo: string,
  checkRunId: number
): Promise<GhResult<CheckAnnotation[]>> {
  const res = await ghJson<any[]>(
    `https://api.github.com/repos/${owner}/${repo}/check-runs/${checkRunId}/annotations?per_page=100`
  );
  if (!res.ok) return res;

  const list = Array.isArray(res.data) ? res.data : [];
  return {
    ok: true,
    data: list.map(
      (a: any): CheckAnnotation => ({
        path: a.path ?? "",
        startLine: a.start_line ?? 0,
        endLine: a.end_line ?? a.start_line ?? 0,
        level: (a.annotation_level ?? "notice") as CheckAnnotation["level"],
        title: a.title ?? "",
        message: a.message ?? "",
        rawDetails: a.raw_details ?? null,
      })
    ),
  };
}

export async function fetchBranches(
  owner: string,
  repo: string,
  perPage = 50
): Promise<GhResult<BranchInfo[]>> {
  const res = await ghJson<any[]>(
    `https://api.github.com/repos/${owner}/${repo}/branches?per_page=${perPage}`
  );
  if (!res.ok) return res;

  const list = Array.isArray(res.data) ? res.data : [];
  return {
    ok: true,
    data: list.map((b: any): BranchInfo => ({
      name: b.name,
      sha: b.commit?.sha ?? "",
      isProtected: !!b.protected,
    })),
  };
}

/** Confirms a token works and returns the login it belongs to. */
export async function fetchViewer(): Promise<GhResult<{ login: string; avatar: string }>> {
  const res = await ghJson<any>("https://api.github.com/user");
  if (!res.ok) return res;
  return { ok: true, data: { login: res.data.login, avatar: res.data.avatar_url } };
}

/* ─── helpers ────────────────────────────────────────────────────────────── */

/** Runs `worker` over `items` with a bounded number of in-flight requests. */
export async function mapLimit<T, R>(
  items: T[],
  limit: number,
  worker: (item: T, index: number) => Promise<R>
): Promise<R[]> {
  const out: R[] = new Array(items.length);
  let cursor = 0;

  const runners = Array.from({ length: Math.min(limit, items.length) }, async () => {
    for (;;) {
      const i = cursor++;
      if (i >= items.length) return;
      out[i] = await worker(items[i], i);
    }
  });

  await Promise.all(runners);
  return out;
}

/** The LeakGuard workflow/check names emitted by this repo's CI. */
export function isLeakGuardName(name: string): boolean {
  const n = name.toLowerCase();
  return n.includes("leakguard") || n.includes("codegate");
}
