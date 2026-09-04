/**
 * LeakGuard admin panel — one screen to watch every connected GitHub account,
 * what the LeakGuard Action found on their pushes and pull requests, and how
 * each branch of each repository is doing.
 *
 * All data comes from the GitHub REST API (workflow runs → check runs →
 * annotations) plus, for branches CI has not covered, on-demand analysis
 * through the local CodeGate endpoint.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "wouter";
import {
  ArrowLeft,
  ShieldCheck,
  Activity,
  Users,
  FolderGit2,
  AlertOctagon,
  AlertTriangle,
  Gauge,
  ScanLine,
  Loader2,
  Database,
  DatabaseZap,
} from "lucide-react";
import { toast } from "sonner";

import AccountsStrip, { type AccountSummary } from "../components/admin/AccountsStrip";
import OverviewBand from "../components/admin/OverviewBand";
import BranchRisk from "../components/admin/charts/BranchRisk";
import HotFiles from "../components/admin/charts/HotFiles";
import RepoBranchPanel, { type LiveScanState } from "../components/admin/RepoBranchPanel";
import FindingsPanel from "../components/admin/FindingsPanel";

import {
  fetchGitHubUser,
  fetchUserRepos,
  type GitHubRepo,
  type GitHubUser,
} from "../lib/github";
import {
  fetchBranches,
  fetchViewer,
  fetchWorkflowRuns,
  getRateSnapshot,
  getToken,
  mapLimit,
  setToken,
  type BranchInfo,
  type GhError,
  type RateSnapshot,
  type WorkflowRunInfo,
} from "../lib/githubActions";
import {
  branchHealth,
  collectCiFindings,
  countLevels,
  dailyBuckets,
  EMPTY_FILTERS,
  eventSplit,
  loadWatchlist,
  mergeFindings,
  saveWatchlist,
  scanBranchLive,
  topBranches,
  topFiles,
  trendDelta,
  type BranchHealth,
  type Finding,
  type FindingFilters,
} from "../lib/leakMonitor";
import {
  dbHealth,
  deleteAccount as dbDeleteAccount,
  listAccounts,
  listFindings,
  saveAccount as dbSaveAccount,
  saveFindings,
  type DbHealth,
} from "../lib/adminApi";

interface AccountState {
  login: string;
  user: GitHubUser | null;
  repos: GitHubRepo[];
  loading: boolean;
  error: string | null;
}

interface RepoState {
  runs: WorkflowRunInfo[];
  branches: BranchInfo[];
  findings: Finding[];
  runsInspected: number;
  loading: boolean;
  error: string | null;
  notes: GhError[];
  scannedAt: string | null;
}

const EMPTY_REPO_STATE: RepoState = {
  runs: [],
  branches: [],
  findings: [],
  runsInspected: 0,
  loading: false,
  error: null,
  notes: [],
  scannedAt: null,
};

/** How many repos "Scan account" walks, newest first. */
const ACCOUNT_SCAN_REPOS = 6;

export default function Admin() {
  const [order, setOrder] = useState<string[]>(() =>
    loadWatchlist([localStorage.getItem("connected_github_user") || "OmkarKudalkar23"])
  );
  const [accounts, setAccounts] = useState<Record<string, AccountState>>({});
  const [repoStates, setRepoStates] = useState<Record<string, RepoState>>({});

  const [selectedLogin, setSelectedLogin] = useState<string | null>(order[0] ?? null);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [filters, setFilters] = useState<FindingFilters>(EMPTY_FILTERS);

  const [liveScan, setLiveScan] = useState<LiveScanState | null>(null);
  const [accountScanning, setAccountScanning] = useState<string | null>(null);
  const [rate, setRate] = useState<RateSnapshot | null>(getRateSnapshot());

  const [db, setDb] = useState<DbHealth | null>(null);
  const [storedFindings, setStoredFindings] = useState<Record<string, Finding[]>>({});

  const [tokenOwner, setTokenOwner] = useState<string | null>(null);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [tokenChecking, setTokenChecking] = useState(false);

  const syncRate = useCallback(() => setRate(getRateSnapshot()), []);

  /** Pulls an account's remembered findings out of MongoDB, if it is up. */
  const loadStored = useCallback(async (login: string) => {
    const stored = await listFindings(login.toLowerCase());
    if (stored) setStoredFindings(prev => ({ ...prev, [login.toLowerCase()]: stored }));
  }, []);

  /* ── accounts ──────────────────────────────────────────────────────────── */

  const loadAccount = useCallback(async (login: string) => {
    setAccounts(prev => ({
      ...prev,
      [login]: { login, user: prev[login]?.user ?? null, repos: prev[login]?.repos ?? [], loading: true, error: null },
    }));

    const [user, repos] = await Promise.all([fetchGitHubUser(login), fetchUserRepos(login)]);
    syncRate();

    setAccounts(prev => ({
      ...prev,
      [login]: {
        login,
        user,
        repos,
        loading: false,
        error: user ? (repos.length === 0 ? "no public repos visible" : null) : "account not found / rate limited",
      },
    }));
    return repos;
  }, [syncRate]);

  /* ── one repository: workflow runs + branches + CI annotations ─────────── */

  const scanRepo = useCallback(async (fullName: string) => {
    const [owner, name] = fullName.split("/");
    if (!owner || !name) return;

    setRepoStates(prev => ({
      ...prev,
      [fullName]: { ...(prev[fullName] ?? EMPTY_REPO_STATE), loading: true, error: null },
    }));

    const [runsRes, branchesRes] = await Promise.all([
      fetchWorkflowRuns(owner, name, { perPage: 20 }),
      fetchBranches(owner, name),
    ]);

    const notes: GhError[] = [];
    const runs = runsRes.ok ? runsRes.data : [];
    if (!runsRes.ok) notes.push(runsRes.error);
    const branches = branchesRes.ok ? branchesRes.data : [];
    if (!branchesRes.ok) notes.push(branchesRes.error);

    const ci = await collectCiFindings(owner, name, runs, { maxRuns: 8, onlyLeakGuard: true });
    syncRate();

    // remember this scan (no-op when MongoDB is unreachable)
    void saveFindings(owner, fullName, ci.findings, {
      runsInspected: ci.runsInspected,
      source: "ci",
      replaceScope: { source: "ci" },
    }).then(saved => { if (saved) void loadStored(owner); });

    setRepoStates(prev => {
      const previous = prev[fullName] ?? EMPTY_REPO_STATE;
      // keep on-demand scan results, replace the CI half
      const live = previous.findings.filter(f => f.source === "live");
      return {
        ...prev,
        [fullName]: {
          runs,
          branches,
          findings: [...ci.findings, ...live],
          runsInspected: ci.runsInspected,
          loading: false,
          error: runs.length === 0 && !runsRes.ok ? runsRes.error.message : null,
          notes: [...notes, ...ci.errors],
          scannedAt: new Date().toISOString(),
        },
      };
    });
  }, [syncRate, loadStored]);

  const scanAccount = useCallback(async (login: string) => {
    const repos = accounts[login]?.repos ?? (await loadAccount(login));
    const targets = repos.slice(0, ACCOUNT_SCAN_REPOS).map(r => r.full_name);
    if (targets.length === 0) return;

    setAccountScanning(login);
    await mapLimit(targets, 2, async (fullName) => { await scanRepo(fullName); });
    setAccountScanning(null);
    toast.success(`Scanned ${targets.length} repositories for @${login}`);
  }, [accounts, loadAccount, scanRepo]);

  /* ── first paint: load every watched account, open the first repo ──────── */

  useEffect(() => {
    let cancelled = false;
    (async () => {
      // 1. database: health, remembered accounts, remembered findings
      const health = await dbHealth();
      if (cancelled) return;
      setDb(health);

      let watchlist = order;
      if (health.ok) {
        const remembered = await listAccounts();
        if (cancelled) return;
        if (remembered) {
          const merged = Array.from(
            new Map(
              [...remembered.map(a => a.login), ...order].map(l => [l.toLowerCase(), l])
            ).values()
          );
          watchlist = merged;
          if (merged.length !== order.length) {
            setOrder(merged);
            saveWatchlist(merged);
          }
          // push any browser-only account into the database
          const known = new Set(remembered.map(a => a.login.toLowerCase()));
          order.filter(l => !known.has(l.toLowerCase())).forEach(l => void dbSaveAccount(l));
        }
        watchlist.forEach(l => void loadStored(l));
      }

      // 2. github: profiles, repos, and the first repo's CI trail
      for (const login of watchlist) {
        const repos = await loadAccount(login);
        if (cancelled) return;
        void dbSaveAccount(login, { repoCount: repos.length });
        if (login === (selectedLogin ?? watchlist[0]) && repos.length > 0) {
          const first = repos[0].full_name;
          setSelectedRepo(prev => prev ?? first);
          void scanRepo(first);
        }
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── watchlist mutations ───────────────────────────────────────────────── */

  const addAccount = useCallback(async (login: string) => {
    if (order.some(l => l.toLowerCase() === login.toLowerCase())) {
      toast.info(`@${login} is already being watched`);
      return;
    }
    const next = [...order, login];
    setOrder(next);
    saveWatchlist(next);
    setSelectedLogin(login);
    void dbSaveAccount(login);
    void loadStored(login);
    const repos = await loadAccount(login);
    if (repos.length > 0) {
      const first = repos[0].full_name;
      setSelectedRepo(first);
      setFilters(prev => ({ ...prev, branch: "all" }));
      void scanRepo(first);
    }
  }, [order, loadAccount, scanRepo]);

  const removeAccount = useCallback((login: string) => {
    const next = order.filter(l => l !== login);
    setOrder(next);
    saveWatchlist(next);
    void dbDeleteAccount(login);
    setStoredFindings(prev => {
      const copy = { ...prev };
      delete copy[login.toLowerCase()];
      return copy;
    });
    setAccounts(prev => {
      const copy = { ...prev };
      delete copy[login];
      return copy;
    });
    if (selectedLogin === login) {
      const fallback = next[0] ?? null;
      setSelectedLogin(fallback);
      setSelectedRepo(null);
      setFilters(EMPTY_FILTERS);
    }
  }, [order, selectedLogin]);

  /* ── token ─────────────────────────────────────────────────────────────── */

  const verifyToken = useCallback(async () => {
    if (!getToken()) {
      setTokenOwner(null);
      setTokenError(null);
      return;
    }
    setTokenChecking(true);
    const res = await fetchViewer();
    setTokenChecking(false);
    syncRate();
    if (res.ok) {
      setTokenOwner(res.data.login);
      setTokenError(null);
    } else {
      setTokenOwner(null);
      setTokenError(res.error.message);
    }
  }, [syncRate]);

  useEffect(() => { void verifyToken(); }, [verifyToken]);

  const saveTokenAndReload = useCallback(async (token: string) => {
    setToken(token);
    await verifyToken();
    toast.success("Token saved — re-reading GitHub data");
    for (const login of order) void loadAccount(login);
    if (selectedRepo) void scanRepo(selectedRepo);
  }, [verifyToken, order, loadAccount, selectedRepo, scanRepo]);

  const clearToken = useCallback(() => {
    setToken(null);
    setTokenOwner(null);
    setTokenError(null);
    toast.info("Token removed — public data only");
  }, []);

  /* ── on-demand branch scan ─────────────────────────────────────────────── */

  const runLiveScan = useCallback(async (branch: string) => {
    if (!selectedRepo) return;
    const [owner, name] = selectedRepo.split("/");
    setLiveScan({ repo: selectedRepo, branch, done: 0, total: 0 });

    const result = await scanBranchLive(owner, name, branch, 12, p =>
      setLiveScan({ repo: selectedRepo, branch, done: p.done, total: p.total })
    );
    setLiveScan(null);
    syncRate();

    if (result.error) {
      toast.error(result.error);
      return;
    }
    setRepoStates(prev => {
      const previous = prev[selectedRepo] ?? EMPTY_REPO_STATE;
      const kept = previous.findings.filter(f => !(f.source === "live" && f.branch === branch));
      return { ...prev, [selectedRepo]: { ...previous, findings: [...kept, ...result.findings] } };
    });

    void saveFindings(owner, selectedRepo, result.findings, {
      source: "live",
      branch,
      replaceScope: { source: "live", branch },
    }).then(saved => { if (saved) void loadStored(owner); });
    toast.success(
      `${branch}: ${result.findings.length} leak${result.findings.length === 1 ? "" : "s"} in ` +
      `${result.filesScanned} file${result.filesScanned === 1 ? "" : "s"}` +
      (result.skipped > 0 ? ` (${result.skipped} more not scanned)` : "")
    );
  }, [selectedRepo, syncRate, loadStored]);

  /* ── derived data ──────────────────────────────────────────────────────── */

  const activeAccount = selectedLogin ? accounts[selectedLogin] : undefined;
  const accountRepos = activeAccount?.repos ?? [];

  const accountFindings = useMemo(() => {
    const names = new Set(accountRepos.map(r => r.full_name));
    const live = Object.entries(repoStates)
      .filter(([fullName]) => names.has(fullName))
      .flatMap(([, st]) => st.findings);
    const remembered = selectedLogin ? storedFindings[selectedLogin.toLowerCase()] ?? [] : [];
    return mergeFindings(remembered, live);
  }, [accountRepos, repoStates, storedFindings, selectedLogin]);

  const allFindings = useMemo(
    () => Object.values(repoStates).flatMap(st => st.findings),
    [repoStates]
  );

  const repoState = selectedRepo ? repoStates[selectedRepo] ?? EMPTY_REPO_STATE : EMPTY_REPO_STATE;

  /** Branch rows: CI history first, then branches CI has never run on. */
  const branchRows: BranchHealth[] = useMemo(() => {
    const rows = branchHealth(repoState.runs, repoState.findings);
    const seen = new Set(rows.map(r => r.branch));
    repoState.branches.forEach(b => {
      if (!seen.has(b.name)) {
        rows.push({
          branch: b.name,
          lastRun: null,
          runs: 0,
          counts: { error: 0, warning: 0, notice: 0, total: 0 },
        });
      }
    });
    return rows;
  }, [repoState]);

  const accountSummaries: AccountSummary[] = useMemo(
    () =>
      order.map(login => {
        const acc = accounts[login];
        const repoNames = new Set((acc?.repos ?? []).map(r => r.full_name));
        const scanned = Object.keys(repoStates).filter(n => repoNames.has(n));
        const findings = mergeFindings(
          storedFindings[login.toLowerCase()] ?? [],
          scanned.flatMap(n => repoStates[n].findings)
        );
        return {
          login,
          user: acc?.user ?? null,
          repoCount: acc?.repos.length ?? 0,
          scannedRepos: scanned.length,
          counts: countLevels(findings),
          loading: acc?.loading ?? false,
          error: acc?.error ?? null,
        };
      }),
    [order, accounts, repoStates, storedFindings]
  );

  const globalCounts = useMemo(() => countLevels(allFindings), [allFindings]);
  const reposScanned = Object.values(repoStates).filter(s => s.scannedAt).length;
  const runsInspected = Object.values(repoStates).reduce((a, s) => a + s.runsInspected, 0);

  const branchNames = useMemo(
    () => Array.from(new Set(accountFindings.map(f => f.branch))).sort(),
    [accountFindings]
  );
  const repoNames = useMemo(
    () => Array.from(new Set(accountFindings.map(f => f.repo))).sort(),
    [accountFindings]
  );

  const ratePct = rate && rate.limit ? Math.round((rate.remaining / rate.limit) * 100) : null;

  /* chart inputs — all scoped to the selected account */
  const accountCounts = useMemo(() => countLevels(accountFindings), [accountFindings]);
  const buckets = useMemo(() => dailyBuckets(accountFindings, 14), [accountFindings]);
  const delta = useMemo(() => trendDelta(accountFindings, 7), [accountFindings]);
  const events = useMemo(() => eventSplit(accountFindings), [accountFindings]);
  const branchRisk = useMemo(() => topBranches(accountFindings, 7), [accountFindings]);
  const fileRisk = useMemo(() => topFiles(accountFindings, 6), [accountFindings]);

  const accountRepoStates = useMemo(
    () =>
      accountRepos
        .map(r => repoStates[r.full_name])
        .filter((s): s is RepoState => !!s),
    [accountRepos, repoStates]
  );
  const accountReposScanned = accountRepoStates.filter(s => s.scannedAt).length;
  const accountReposWithCi = accountRepoStates.filter(s => s.runs.length > 0).length;
  const lastScanAt = accountRepoStates.reduce<string | null>(
    (latest, s) => (s.scannedAt && (!latest || s.scannedAt > latest) ? s.scannedAt : latest),
    null
  );

  const busy = repoState.loading || !!accountScanning;

  /* ── render ────────────────────────────────────────────────────────────── */

  const emptyHint = (
    <div className="max-w-[15rem] text-center">
      <p className="text-xs text-zinc-400">Nothing recorded yet</p>
      <p className="mt-1 text-[11px] leading-relaxed text-zinc-600">
        Scan a repository to read its LeakGuard runs, or analyse a branch on demand
        from the table below.
      </p>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#08090c] font-poppins text-zinc-100 selection:bg-purple-500/30 selection:text-purple-200">
      {/* ── top bar ── */}
      <header className="sticky top-0 z-30 border-b border-[#171a24] bg-[#08090c]/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-4 px-4 py-3 md:px-8">
          <Link
            to="/dashboard"
            className="group flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-zinc-400 transition-colors hover:bg-white/5 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
            Dashboard
          </Link>

          <span className="h-5 w-px bg-[#1e2230]" />

          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <h1 className="text-sm font-semibold tracking-tight text-white">LeakGuard Admin</h1>
            <span className="hidden text-xs text-zinc-500 sm:inline">
              CI leak monitoring across watched accounts
            </span>
          </div>

          {/* status cluster — plain text with hairline separators, not a card row */}
          <div className="ml-auto flex items-center gap-4 text-[11px]">
            <span
              className="flex items-center gap-1.5"
              title={db?.error || (db?.ok ? `MongoDB ${db.db} · ${db.ms}ms` : "checking database…")}
            >
              {db?.ok ? (
                <DatabaseZap className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <Database className={`h-3.5 w-3.5 ${db ? "text-rose-400" : "text-zinc-600"}`} />
              )}
              <span className={db?.ok ? "text-zinc-400" : db ? "text-rose-300" : "text-zinc-500"}>
                {db?.ok ? db.db : db ? (db.configured ? "db unreachable" : "db off") : "checking"}
              </span>
            </span>

            <span className="hidden h-4 w-px bg-[#1e2230] sm:block" />

            <span className="hidden items-center gap-1.5 sm:flex" title="GitHub API budget">
              <Gauge
                className={`h-3.5 w-3.5 ${ratePct !== null && ratePct < 20 ? "text-rose-400" : "text-zinc-500"}`}
              />
              <span className={ratePct !== null && ratePct < 20 ? "text-rose-300" : "text-zinc-400"}>
                {rate ? `${rate.remaining}/${rate.limit}` : "—"}
              </span>
            </span>

            <button
              onClick={() => selectedLogin && void scanAccount(selectedLogin)}
              disabled={!selectedLogin || !!accountScanning}
              className="flex items-center gap-2 rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-medium text-white shadow-lg shadow-purple-950/40 transition-colors hover:bg-purple-500 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-500 disabled:shadow-none"
            >
              {accountScanning ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <ScanLine className="h-3.5 w-3.5" />
              )}
              {accountScanning ? "Scanning…" : "Scan newest repos"}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] space-y-4 px-4 py-6 md:px-8">
        <AccountsStrip
          accounts={accountSummaries}
          selected={selectedLogin}
          onSelect={login => {
            setSelectedLogin(login);
            void loadStored(login);
            const first = accounts[login]?.repos[0]?.full_name ?? null;
            setSelectedRepo(first);
            setFilters(prev => ({ ...prev, repo: "all", branch: "all" }));
            if (first && !repoStates[first]) void scanRepo(first);
          }}
          onAdd={login => void addAccount(login)}
          onRemove={removeAccount}
          onRescan={login => void scanAccount(login)}
          tokenPresent={!!getToken()}
          tokenOwner={tokenOwner}
          tokenError={tokenError}
          tokenChecking={tokenChecking}
          onSaveToken={token => void saveTokenAndReload(token)}
          onClearToken={clearToken}
        />

        <OverviewBand
          errors={accountCounts.error}
          warnings={accountCounts.warning}
          repoCount={repoNames.length || accountRepos.length}
          watchedRepos={accountRepos.length}
          branchCount={branchNames.length}
          reposWithCi={accountReposWithCi}
          reposScanned={accountReposScanned}
          lastScanAt={lastScanAt}
          delta={delta}
          buckets={buckets}
          events={events}
          emptyHint={emptyHint}
        />

        {/* where the leaks are */}
        <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
          <section className="min-w-0 overflow-hidden rounded-2xl border border-[#1e2230] bg-[#13151b] p-5">
            <BranchRisk
              rows={branchRisk}
              activeBranch={filters.branch}
              onSelect={branch =>
                setFilters(prev => ({ ...prev, branch: prev.branch === branch ? "all" : branch }))
              }
              empty={emptyHint}
            />
          </section>

          <section className="min-w-0 overflow-hidden rounded-2xl border border-[#1e2230] bg-[#13151b] p-5">
            <HotFiles
              rows={fileRisk}
              query={filters.query}
              onSelect={path => setFilters(prev => ({ ...prev, query: path }))}
              empty={emptyHint}
            />
          </section>
        </div>

        <RepoBranchPanel
          repos={accountRepos}
          selectedRepo={selectedRepo}
          onSelectRepo={fullName => {
            setSelectedRepo(fullName);
            setFilters(prev => ({ ...prev, branch: "all" }));
            if (!repoStates[fullName]) void scanRepo(fullName);
          }}
          branches={branchRows}
          runsInspected={repoState.runsInspected}
          loading={repoState.loading}
          error={repoState.error}
          notes={repoState.notes}
          activeBranch={filters.branch}
          onFocusBranch={branch => setFilters(prev => ({ ...prev, branch }))}
          onRescanRepo={() => selectedRepo && void scanRepo(selectedRepo)}
          onLiveScan={branch => void runLiveScan(branch)}
          liveScan={liveScan}
        />

        <FindingsPanel
          findings={accountFindings}
          filters={filters}
          onFiltersChange={setFilters}
          branches={branchNames}
          repos={repoNames}
          loading={busy}
        />
      </main>
    </div>
  );
}
