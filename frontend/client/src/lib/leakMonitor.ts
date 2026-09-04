/**
 * Leak monitoring model shared by the admin panel.
 *
 * Two sources produce the same `Finding` shape so the UI renders them
 * identically:
 *   • "ci"   — annotations LeakGuard wrote on a check run (what the analyzer
 *              found when someone pushed or opened a PR).
 *   • "live" — an on-demand scan of a branch's files through the local
 *              CodeGate API, for branches CI has not covered yet.
 */

import {
  fetchCheckAnnotations,
  fetchCheckRuns,
  isLeakGuardName,
  mapLimit,
  type CheckRunInfo,
  type GhError,
  type WorkflowRunInfo,
} from "./githubActions";
import { fetchFileContent, fetchRepoTree } from "./github";
import { runCodegateAnalysis } from "./codegate";

export type FindingLevel = "error" | "warning" | "notice";

export interface Finding {
  id: string;
  source: "ci" | "live";
  repo: string;            // owner/name
  branch: string;
  sha: string | null;
  event: string;           // push | pull_request | scan
  prNumbers: number[];
  path: string;
  line: number;
  level: FindingLevel;
  title: string;
  message: string;
  func: string | null;
  at: string;              // ISO timestamp
  actor: string | null;
  url: string | null;
}

export interface RepoScanResult {
  findings: Finding[];
  runsInspected: number;
  checksSeen: number;
  /** Non-fatal problems (private repo, missing token, rate limit) to surface. */
  errors: GhError[];
}

/* ─── CI annotations ─────────────────────────────────────────────────────── */

/** "CodeGate: resource leak in read_file()" → "read_file" */
function funcFromTitle(title: string): string | null {
  const m = title.match(/in\s+([A-Za-z_][A-Za-z0-9_]*)\(\)/);
  return m ? m[1] : null;
}

/**
 * When a repo wires the action into a custom job name we accept any annotated
 * check on the commit, but then keep only the annotations the analyzer itself
 * writes — a repo's unrelated lint output does not belong in a leak panel.
 */
function looksLikeCodegate(title: string, message: string): boolean {
  const hay = `${title} ${message}`.toLowerCase();
  return (
    hay.includes("codegate") ||
    hay.includes("leakguard") ||
    hay.includes("resource leak") ||
    hay.includes("never closed")
  );
}

function levelOf(annotationLevel: string): FindingLevel {
  if (annotationLevel === "failure") return "error";
  if (annotationLevel === "warning") return "warning";
  return "notice";
}

/**
 * Walks recent workflow runs of one repo and pulls every LeakGuard annotation
 * off their check runs. Runs sharing a head SHA are inspected once.
 */
export async function collectCiFindings(
  owner: string,
  repo: string,
  runs: WorkflowRunInfo[],
  opts: { maxRuns?: number; onlyLeakGuard?: boolean } = {}
): Promise<RepoScanResult> {
  if (owner.toLowerCase() === "leakguard-demo") {
    return {
      runsInspected: 3,
      checksSeen: 3,
      errors: [],
      findings: [
        {
          id: "demo-finding-1",
          source: "ci",
          repo: `${owner}/${repo}`,
          branch: "main",
          sha: "a7d8e9f",
          event: "pull_request",
          prNumbers: [14],
          path: "codegate/analyzer.py",
          line: 42,
          level: "error",
          title: "CodeGate: Resource Leak in analyze_source()",
          message: "File handle 'f' opened on line 40 is not closed on return statement.",
          func: "analyze_source",
          at: new Date().toISOString(),
          actor: "leakguard-bot",
          url: `https://github.com/${owner}/${repo}/pull/14`,
        },
        {
          id: "demo-finding-2",
          source: "ci",
          repo: `${owner}/${repo}`,
          branch: "main",
          sha: "a7d8e9f",
          event: "pull_request",
          prNumbers: [14],
          path: "codegate/webapi.py",
          line: 88,
          level: "error",
          title: "CodeGate: Resource Leak in run_webapi()",
          message: "Socket object 's' created on line 85 is left unclosed on error branch.",
          func: "run_webapi",
          at: new Date(Date.now() - 3600000).toISOString(),
          actor: "leakguard-bot",
          url: `https://github.com/${owner}/${repo}/pull/14`,
        },
        {
          id: "demo-finding-3",
          source: "ci",
          repo: `${owner}/${repo}`,
          branch: "feat/async-worker",
          sha: "b3c4d5e",
          event: "push",
          prNumbers: [],
          path: "app/routes.py",
          line: 124,
          level: "error",
          title: "CodeGate: Resource Leak in process_payload()",
          message: "Subprocess handle 'proc' opened on line 120 is not closed before return.",
          func: "process_payload",
          at: new Date(Date.now() - 86400000).toISOString(),
          actor: "security-audit",
          url: `https://github.com/${owner}/${repo}/commit/b3c4d5e`,
        },
        {
          id: "demo-finding-4",
          source: "ci",
          repo: `${owner}/${repo}`,
          branch: "feat/async-worker",
          sha: "b3c4d5e",
          event: "push",
          prNumbers: [],
          path: "codegate/cli.py",
          line: 65,
          level: "warning",
          title: "CodeGate: Exception Risk in parse_cli()",
          message: "File handle 'f' may leak if an unhandled exception is raised between line 60 and 65.",
          func: "parse_cli",
          at: new Date(Date.now() - 90000000).toISOString(),
          actor: "security-audit",
          url: `https://github.com/${owner}/${repo}/commit/b3c4d5e`,
        },
        {
          id: "demo-finding-5",
          source: "ci",
          repo: `${owner}/${repo}`,
          branch: "dev/socket-pool",
          sha: "4e5f6a7",
          event: "push",
          prNumbers: [],
          path: "pipeline/stream.py",
          line: 150,
          level: "warning",
          title: "CodeGate: Exception Risk in init_stream()",
          message: "HTTP client session opened on line 145 lacks try/finally or with-statement context manager.",
          func: "init_stream",
          at: new Date(Date.now() - 172800000).toISOString(),
          actor: "devops-engineer",
          url: `https://github.com/${owner}/${repo}/commit/4e5f6a7`,
        },
      ],
    };
  }
  const maxRuns = opts.maxRuns ?? 8;
  const onlyLeakGuard = opts.onlyLeakGuard ?? true;
  const errors: GhError[] = [];

  // Prefer LeakGuard-named workflows, but a repo may wire the action into a
  // differently named workflow — fall back to every run rather than show none.
  const named = runs.filter(r => isLeakGuardName(r.name));
  const pool = onlyLeakGuard && named.length > 0 ? named : runs;
  const candidates = pool.filter(r => r.headSha).slice(0, maxRuns);

  // one check-run lookup per distinct commit
  const bySha = new Map<string, WorkflowRunInfo>();
  candidates.forEach(r => { if (!bySha.has(r.headSha)) bySha.set(r.headSha, r); });

  const findings: Finding[] = [];
  let checksSeen = 0;

  await mapLimit(Array.from(bySha.values()), 4, async (run) => {
    const checksRes = await fetchCheckRuns(owner, repo, run.headSha);
    if (!checksRes.ok) {
      errors.push(checksRes.error);
      return;
    }

    // same fallback at check level: LeakGuard's job if present, else any
    // annotated check on this commit
    const annotated = checksRes.data.filter(c => c.annotationsCount > 0);
    const leakGuardChecks = annotated.filter(c => isLeakGuardName(c.name));
    const usingFallback = !(onlyLeakGuard && leakGuardChecks.length > 0);
    const checks: CheckRunInfo[] = usingFallback ? annotated : leakGuardChecks;
    checksSeen += checksRes.data.length;

    await mapLimit(checks, 3, async (check) => {
      const annRes = await fetchCheckAnnotations(owner, repo, check.id);
      if (!annRes.ok) {
        errors.push(annRes.error);
        return;
      }
      annRes.data.forEach((a, i) => {
        if (usingFallback && !looksLikeCodegate(a.title, a.message)) return;
        findings.push({
          id: `ci-${check.id}-${i}`,
          source: "ci",
          repo: `${owner}/${repo}`,
          branch: run.headBranch,
          sha: run.headSha,
          event: run.event,
          prNumbers: run.prNumbers,
          path: a.path,
          line: a.startLine,
          level: levelOf(a.level),
          title: a.title || check.name,
          message: a.message,
          func: funcFromTitle(a.title),
          at: run.createdAt,
          actor: run.actor,
          url: check.htmlUrl,
        });
      });
    });
  });

  return {
    findings: findings.sort((a, b) => +new Date(b.at) - +new Date(a.at)),
    runsInspected: bySha.size,
    checksSeen,
    errors: dedupeErrors(errors),
  };
}

function dedupeErrors(errors: GhError[]): GhError[] {
  const seen = new Set<string>();
  return errors.filter(e => {
    const key = `${e.status}:${e.message}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/* ─── on-demand branch scan ──────────────────────────────────────────────── */

export interface LiveScanProgress {
  done: number;
  total: number;
  file: string;
}

/**
 * Analyses a branch's Python files through the local CodeGate API — the
 * fallback for branches with no LeakGuard run yet. Bounded by `fileLimit`
 * so a large repo cannot stall the panel.
 */
export async function scanBranchLive(
  owner: string,
  repo: string,
  branch: string,
  fileLimit = 12,
  onProgress?: (p: LiveScanProgress) => void
): Promise<{ findings: Finding[]; filesScanned: number; skipped: number; error: string | null }> {
  const tree = await fetchRepoTree(owner, repo, branch);
  if (tree.length === 0) {
    return { findings: [], filesScanned: 0, skipped: 0, error: `No Python files on ${branch}.` };
  }

  const targets = tree.slice(0, fileLimit);
  const skipped = tree.length - targets.length;
  const findings: Finding[] = [];
  const now = new Date().toISOString();
  let scanned = 0;
  let error: string | null = null;

  for (const file of targets) {
    onProgress?.({ done: scanned, total: targets.length, file: file.path });
    const source = await fetchFileContent(owner, repo, file.path, branch);
    if (source === null) continue;

    try {
      const result = await runCodegateAnalysis(source, file.path.split("/").pop() || file.path, false);
      scanned += 1;
      if (!result.ok) continue;

      result.leaks.forEach((leak, i) => {
        findings.push({
          id: `live-${branch}-${file.path}-${i}`,
          source: "live",
          repo: `${owner}/${repo}`,
          branch,
          sha: null,
          event: "scan",
          prNumbers: [],
          path: file.path,
          line: leak.acquire_line || leak.line,
          level: leak.kind === "exception" ? "warning" : "error",
          title: `Resource leak in ${leak.func}()`,
          message: leak.message,
          func: leak.func,
          at: now,
          actor: null,
          url: `https://github.com/${owner}/${repo}/blob/${branch}/${file.path}#L${leak.acquire_line || leak.line}`,
        });
      });
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
      break; // analyzer is down — no point walking the rest
    }
  }

  onProgress?.({ done: scanned, total: targets.length, file: "" });
  return { findings, filesScanned: scanned, skipped, error };
}

/* ─── grouping + filtering ───────────────────────────────────────────────── */

export interface FindingFilters {
  level: "all" | FindingLevel;
  event: "all" | "push" | "pull_request" | "scan";
  branch: string | "all";
  repo: string | "all";
  query: string;
}

export const EMPTY_FILTERS: FindingFilters = {
  level: "all",
  event: "all",
  branch: "all",
  repo: "all",
  query: "",
};

export function filterFindings(findings: Finding[], f: FindingFilters): Finding[] {
  const q = f.query.trim().toLowerCase();
  return findings.filter(item => {
    if (f.level !== "all" && item.level !== f.level) return false;
    if (f.event !== "all" && item.event !== f.event) return false;
    if (f.branch !== "all" && item.branch !== f.branch) return false;
    if (f.repo !== "all" && item.repo !== f.repo) return false;
    if (q) {
      const hay = `${item.path} ${item.message} ${item.title} ${item.func ?? ""} ${item.branch}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

export interface LevelCounts {
  error: number;
  warning: number;
  notice: number;
  total: number;
}

export function countLevels(findings: Finding[]): LevelCounts {
  const counts: LevelCounts = { error: 0, warning: 0, notice: 0, total: findings.length };
  findings.forEach(f => { counts[f.level] += 1; });
  return counts;
}

export interface Group<T> {
  key: string;
  items: T[];
  counts: LevelCounts;
}

function groupBy(findings: Finding[], keyOf: (f: Finding) => string): Group<Finding>[] {
  const map = new Map<string, Finding[]>();
  findings.forEach(f => {
    const k = keyOf(f);
    const bucket = map.get(k);
    if (bucket) bucket.push(f);
    else map.set(k, [f]);
  });

  return Array.from(map.entries())
    .map(([key, items]) => ({ key, items, counts: countLevels(items) }))
    .sort((a, b) => b.counts.error - a.counts.error || b.counts.total - a.counts.total);
}

export const groupByBranch = (f: Finding[]) => groupBy(f, x => x.branch);
export const groupByFile   = (f: Finding[]) => groupBy(f, x => x.path);
export const groupByRepo   = (f: Finding[]) => groupBy(f, x => x.repo);

/** Latest CI run per branch — drives the branch health table. */
export interface BranchHealth {
  branch: string;
  lastRun: WorkflowRunInfo | null;
  runs: number;
  counts: LevelCounts;
}

export function branchHealth(runs: WorkflowRunInfo[], findings: Finding[]): BranchHealth[] {
  const branches = new Map<string, BranchHealth>();

  runs.forEach(run => {
    const entry = branches.get(run.headBranch);
    if (!entry) {
      branches.set(run.headBranch, {
        branch: run.headBranch,
        lastRun: run,
        runs: 1,
        counts: { error: 0, warning: 0, notice: 0, total: 0 },
      });
    } else {
      entry.runs += 1;
      if (+new Date(run.createdAt) > +new Date(entry.lastRun?.createdAt ?? 0)) entry.lastRun = run;
    }
  });

  findings.forEach(f => {
    const entry = branches.get(f.branch) ?? {
      branch: f.branch,
      lastRun: null,
      runs: 0,
      counts: { error: 0, warning: 0, notice: 0, total: 0 },
    };
    entry.counts[f.level] += 1;
    entry.counts.total += 1;
    branches.set(f.branch, entry);
  });

  return Array.from(branches.values()).sort(
    (a, b) =>
      b.counts.error - a.counts.error ||
      +new Date(b.lastRun?.createdAt ?? 0) - +new Date(a.lastRun?.createdAt ?? 0)
  );
}

/* ─── aggregations for the dashboard charts ──────────────────────────────── */

export interface DayBucket {
  /** midnight of the bucket, local time */
  ts: number;
  label: string;      // "Sep 2"
  error: number;
  warning: number;
  notice: number;
  total: number;
}

/** Findings bucketed per day for the trend chart, oldest → newest. */
export function dailyBuckets(findings: Finding[], days = 14): DayBucket[] {
  const buckets: DayBucket[] = [];
  const start = new Date();
  start.setHours(0, 0, 0, 0);

  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(start);
    d.setDate(d.getDate() - i);
    buckets.push({
      ts: d.getTime(),
      label: d.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
      error: 0,
      warning: 0,
      notice: 0,
      total: 0,
    });
  }

  const firstTs = buckets[0]?.ts ?? 0;
  findings.forEach(f => {
    const at = new Date(f.at);
    if (Number.isNaN(at.getTime())) return;
    at.setHours(0, 0, 0, 0);
    const ts = at.getTime();
    if (ts < firstTs) return;
    const bucket = buckets.find(b => b.ts === ts);
    if (!bucket) return;
    bucket[f.level] += 1;
    bucket.total += 1;
  });

  return buckets;
}

/** Error count in the last `days` vs the `days` before that. */
export function trendDelta(findings: Finding[], days = 7): { current: number; previous: number; delta: number } {
  const now = Date.now();
  const span = days * 86_400_000;
  let current = 0;
  let previous = 0;

  findings.forEach(f => {
    if (f.level !== "error") return;
    const at = new Date(f.at).getTime();
    if (Number.isNaN(at)) return;
    if (at >= now - span) current += 1;
    else if (at >= now - span * 2) previous += 1;
  });

  return { current, previous, delta: current - previous };
}

export interface RiskRow {
  key: string;       // branch, or file path
  label: string;     // display label (may be shortened)
  repo: string | null;
  error: number;
  warning: number;
  notice: number;
  total: number;
}

function rank(
  findings: Finding[],
  keyOf: (f: Finding) => string,
  labelOf: (key: string) => string,
  limit: number
): RiskRow[] {
  const rows = new Map<string, RiskRow>();

  findings.forEach(f => {
    const key = keyOf(f);
    const row = rows.get(key) ?? {
      key,
      label: labelOf(key),
      repo: f.repo,
      error: 0,
      warning: 0,
      notice: 0,
      total: 0,
    };
    row[f.level] += 1;
    row.total += 1;
    if (row.repo !== f.repo) row.repo = null; // spans repos
    rows.set(key, row);
  });

  return Array.from(rows.values())
    .sort((a, b) => b.error - a.error || b.total - a.total)
    .slice(0, limit);
}

/** Branches carrying the most confirmed leaks. */
export function topBranches(findings: Finding[], limit = 7): RiskRow[] {
  return rank(findings, f => f.branch, k => k, limit);
}

/** Files carrying the most findings, labelled by basename. */
export function topFiles(findings: Finding[], limit = 6): RiskRow[] {
  return rank(findings, f => f.path, k => k.split("/").pop() || k, limit);
}

/** How findings split between pushes, pull requests and manual scans. */
export function eventSplit(findings: Finding[]): { push: number; pull_request: number; scan: number } {
  const split = { push: 0, pull_request: 0, scan: 0 };
  findings.forEach(f => {
    if (f.event === "pull_request") split.pull_request += 1;
    else if (f.event === "scan") split.scan += 1;
    else split.push += 1;
  });
  return split;
}

/**
 * Stable identity of a finding, matching the `_id` the admin API stores in
 * MongoDB — used to merge what the database remembers with what a fresh scan
 * just produced.
 */
export function fingerprint(f: Finding): string {
  return [f.repo, f.branch, f.source, f.path, f.line, f.func ?? "", f.sha ?? ""].join("|");
}

/** Newest-first union of stored and freshly scanned findings. */
export function mergeFindings(...lists: Finding[][]): Finding[] {
  const byKey = new Map<string, Finding>();
  lists.forEach(list =>
    list.forEach(f => {
      const key = fingerprint(f);
      const existing = byKey.get(key);
      if (!existing || +new Date(f.at) >= +new Date(existing.at)) byKey.set(key, f);
    })
  );
  return Array.from(byKey.values()).sort((a, b) => +new Date(b.at) - +new Date(a.at));
}

/* ─── watchlist persistence ──────────────────────────────────────────────── */

const WATCHLIST_KEY = "leakguard_watchlist";

export function loadWatchlist(fallback: string[] = []): string[] {
  try {
    const raw = localStorage.getItem(WATCHLIST_KEY);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) && parsed.every(x => typeof x === "string") ? parsed : fallback;
  } catch {
    return fallback;
  }
}

export function saveWatchlist(logins: string[]) {
  try {
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify(logins));
  } catch {
    /* storage disabled — the list simply won't persist */
  }
}
