/**
 * Client for the MongoDB-backed admin API (/api/admin/*).
 *
 * Every call resolves to a value or null — when the database is unreachable
 * the panel keeps working off the GitHub API and browser storage, it just
 * stops remembering things between sessions.
 */
import type { Finding } from "./leakMonitor";

export interface DbHealth {
  ok: boolean;
  db?: string;
  ms?: number;
  error?: string;
  configured: boolean;
}

export interface StoredAccount {
  login: string;
  name: string | null;
  avatarUrl: string | null;
  addedAt: string;
  lastScanAt: string | null;
  repoCount: number;
}

export interface ScanRecord {
  login: string;
  repo: string;
  at: string;
  runsInspected: number;
  errors: number;
  warnings: number;
  notices: number;
  source: "ci" | "live";
  branch: string | null;
}

async function api<T>(path: string, init?: RequestInit): Promise<T | null> {
  try {
    const res = await fetch(`/api/admin${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function dbHealth(): Promise<DbHealth> {
  try {
    const res = await fetch("/api/admin/health");
    const body = await res.json();
    return {
      ok: !!body.ok,
      db: body.db,
      ms: body.ms,
      error: body.error,
      configured: !!body.configured,
    };
  } catch (err) {
    return {
      ok: false,
      configured: false,
      error: err instanceof Error ? err.message : "admin API unreachable",
    };
  }
}

export async function listAccounts(): Promise<StoredAccount[] | null> {
  const body = await api<{ ok: boolean; accounts: StoredAccount[] }>("/accounts");
  return body?.accounts ?? null;
}

export async function saveAccount(
  login: string,
  meta: { name?: string | null; avatarUrl?: string | null; repoCount?: number } = {}
): Promise<boolean> {
  const body = await api<{ ok: boolean }>("/accounts", {
    method: "POST",
    body: JSON.stringify({ login, ...meta }),
  });
  return !!body?.ok;
}

export async function deleteAccount(login: string): Promise<boolean> {
  const body = await api<{ ok: boolean }>(`/accounts/${encodeURIComponent(login)}`, {
    method: "DELETE",
  });
  return !!body?.ok;
}

/** Stored findings for an account (optionally one repo), newest first. */
export async function listFindings(login: string, repo?: string): Promise<Finding[] | null> {
  const params = new URLSearchParams({ login, limit: "1000" });
  if (repo) params.set("repo", repo);

  const body = await api<{ ok: boolean; findings: any[] }>(`/findings?${params}`);
  if (!body?.findings) return null;

  return body.findings.map((d): Finding => ({
    id: String(d._id),
    source: d.source === "live" ? "live" : "ci",
    repo: d.repo,
    branch: d.branch,
    sha: d.sha ?? null,
    event: d.event ?? "push",
    prNumbers: Array.isArray(d.prNumbers) ? d.prNumbers : [],
    path: d.path,
    line: d.line,
    level: d.level,
    title: d.title,
    message: d.message,
    func: d.func ?? null,
    at: d.at,
    actor: d.actor ?? null,
    url: d.url ?? null,
  }));
}

/**
 * Persists one scan's findings. `replaceScope` prunes findings of the same
 * repo/source (optionally branch) that this scan no longer reports, so fixed
 * leaks disappear instead of lingering.
 */
export async function saveFindings(
  login: string,
  repo: string,
  items: Finding[],
  opts: {
    runsInspected?: number;
    source?: "ci" | "live";
    branch?: string | null;
    replaceScope?: { source: "ci" | "live"; branch?: string } | null;
  } = {}
): Promise<{ stored: number } | null> {
  const body = await api<{ ok: boolean; stored: number }>("/findings", {
    method: "POST",
    body: JSON.stringify({
      login,
      repo,
      findings: items,
      runsInspected: opts.runsInspected ?? 0,
      source: opts.source ?? "ci",
      branch: opts.branch ?? null,
      replaceScope: opts.replaceScope ?? null,
    }),
  });
  return body?.ok ? { stored: body.stored } : null;
}

export async function listScans(login: string, limit = 20): Promise<ScanRecord[] | null> {
  const body = await api<{ ok: boolean; scans: ScanRecord[] }>(
    `/scans?login=${encodeURIComponent(login)}&limit=${limit}`
  );
  return body?.scans ?? null;
}
