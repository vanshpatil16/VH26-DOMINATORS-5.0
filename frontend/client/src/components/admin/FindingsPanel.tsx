/**
 * The findings feed: every leak LeakGuard annotated on a check run, plus any
 * on-demand scan results, grouped so a few hundred of them stay readable.
 */
import React, { useMemo, useState } from "react";
import {
  Search,
  ChevronRight,
  ChevronDown,
  ExternalLink,
  FileCode2,
  GitBranch,
  GitPullRequest,
  GitCommitHorizontal,
  Radar,
  Loader2,
  CheckCircle2,
  AlertOctagon,
  AlertTriangle,
  Info,
  X,
} from "lucide-react";
import {
  countLevels,
  filterFindings,
  groupByBranch,
  groupByFile,
  groupByRepo,
  type Finding,
  type FindingFilters,
} from "@/lib/leakMonitor";
import { eventLabel, timeAgo } from "./format";
import { EVENT, SEVERITY } from "./chartTheme";

type GroupMode = "file" | "branch" | "repo" | "flat";

const PAGE_SIZE = 25;

const LEVEL_ICON = {
  error: AlertOctagon,
  warning: AlertTriangle,
  notice: Info,
} as const;

const LEVEL_TEXT = {
  error: "#f0a3a3",
  warning: "#f5d08a",
  notice: "#a8c9f2",
} as const;

interface Props {
  findings: Finding[];
  filters: FindingFilters;
  onFiltersChange: (f: FindingFilters) => void;
  branches: string[];
  repos: string[];
  loading: boolean;
}

const controlClass =
  "rounded-lg border border-[#242938] bg-[#0f1117] px-2.5 py-1.5 text-[11px] text-zinc-300 outline-none transition-colors focus:border-purple-500";

export default function FindingsPanel({
  findings,
  filters,
  onFiltersChange,
  branches,
  repos,
  loading,
}: Props) {
  const [groupMode, setGroupMode] = useState<GroupMode>("file");
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [visibleGroups, setVisibleGroups] = useState(12);

  const filtered = useMemo(() => filterFindings(findings, filters), [findings, filters]);
  const counts = useMemo(() => countLevels(filtered), [filtered]);

  const groups = useMemo(() => {
    if (groupMode === "flat") return [{ key: "All findings", items: filtered, counts }];
    if (groupMode === "branch") return groupByBranch(filtered);
    if (groupMode === "repo") return groupByRepo(filtered);
    return groupByFile(filtered);
  }, [filtered, groupMode, counts]);

  const set = (patch: Partial<FindingFilters>) => onFiltersChange({ ...filters, ...patch });

  const activeFilters =
    (filters.level !== "all" ? 1 : 0) +
    (filters.event !== "all" ? 1 : 0) +
    (filters.branch !== "all" ? 1 : 0) +
    (filters.query.trim() ? 1 : 0);

  const toggleGroup = (key: string) =>
    setCollapsed(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  return (
    <section className="overflow-hidden rounded-2xl border border-[#1e2230] bg-[#13151b]">
      {/* header */}
      <div className="flex flex-col gap-3 border-b border-[#1e2230] p-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100">Findings</h2>
          <p className="mt-0.5 text-xs text-zinc-500">
            {loading
              ? "Collecting from GitHub…"
              : `${counts.total} shown of ${findings.length} collected`}
          </p>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5" style={{ color: LEVEL_TEXT.error }}>
            <AlertOctagon className="h-3.5 w-3.5" style={{ color: SEVERITY.error }} />
            <span className="tabular-nums">{counts.error}</span> confirmed
          </span>
          <span className="flex items-center gap-1.5" style={{ color: LEVEL_TEXT.warning }}>
            <AlertTriangle className="h-3.5 w-3.5" style={{ color: SEVERITY.warning }} />
            <span className="tabular-nums">{counts.warning}</span> risks
          </span>
          {counts.notice > 0 && (
            <span className="flex items-center gap-1.5" style={{ color: LEVEL_TEXT.notice }}>
              <Info className="h-3.5 w-3.5" style={{ color: SEVERITY.notice }} />
              <span className="tabular-nums">{counts.notice}</span> notices
            </span>
          )}
        </div>
      </div>

      {/* filters — one row, scoping everything below */}
      <div className="flex flex-wrap items-center gap-2 border-b border-[#1e2230] px-5 py-3">
        <div className="relative min-w-[12rem] flex-1">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-500" />
          <input
            type="text"
            value={filters.query}
            onChange={e => set({ query: e.target.value })}
            placeholder="Filter by file, function or message…"
            className="w-full rounded-lg border border-[#242938] bg-[#0f1117] py-1.5 pl-8 pr-8 text-[11px] text-white placeholder-zinc-600 outline-none transition-colors focus:border-purple-500"
          />
          {filters.query && (
            <button
              onClick={() => set({ query: "" })}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-zinc-500 hover:text-white"
              title="Clear search"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>

        <select
          value={filters.level}
          onChange={e => set({ level: e.target.value as FindingFilters["level"] })}
          className={controlClass}
        >
          <option value="all">All severities</option>
          <option value="error">Confirmed leaks</option>
          <option value="warning">Exception risks</option>
          <option value="notice">Notices</option>
        </select>

        <select
          value={filters.event}
          onChange={e => set({ event: e.target.value as FindingFilters["event"] })}
          className={controlClass}
        >
          <option value="all">Pushes & PRs</option>
          <option value="push">Pushes</option>
          <option value="pull_request">Pull requests</option>
          <option value="scan">On-demand scans</option>
        </select>

        <select value={filters.branch} onChange={e => set({ branch: e.target.value })} className={controlClass}>
          <option value="all">All branches</option>
          {branches.map(b => (
            <option key={b} value={b}>{b}</option>
          ))}
        </select>

        {repos.length > 1 && (
          <select value={filters.repo} onChange={e => set({ repo: e.target.value })} className={controlClass}>
            <option value="all">All repos</option>
            {repos.map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        )}

        <span className="mx-1 h-5 w-px bg-[#1e2230]" />

        <select
          value={groupMode}
          onChange={e => setGroupMode(e.target.value as GroupMode)}
          className={controlClass}
        >
          <option value="file">Group by file</option>
          <option value="branch">Group by branch</option>
          <option value="repo">Group by repo</option>
          <option value="flat">No grouping</option>
        </select>

        <button
          onClick={() => setCollapsed(prev => (prev.size ? new Set() : new Set(groups.map(g => g.key))))}
          className="rounded-lg border border-[#242938] bg-[#0f1117] px-2.5 py-1.5 text-[11px] text-zinc-400 transition-colors hover:border-purple-500/50 hover:text-white"
        >
          {collapsed.size ? "Expand all" : "Collapse all"}
        </button>

        {activeFilters > 0 && (
          <button
            onClick={() => onFiltersChange({ ...filters, level: "all", event: "all", branch: "all", query: "" })}
            className="rounded-lg px-2 py-1.5 text-[11px] text-purple-300 transition-colors hover:text-white"
          >
            Clear {activeFilters} filter{activeFilters === 1 ? "" : "s"}
          </button>
        )}
      </div>

      {/* results */}
      {loading && filtered.length === 0 ? (
        <div className="space-y-2 p-5">
          {[0, 1, 2].map(i => (
            <div key={i} className="h-14 animate-pulse rounded-xl bg-[#0f1117]" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-2 px-5 py-12 text-center">
          <CheckCircle2 className="h-6 w-6 text-emerald-500/70" />
          <p className="text-sm font-medium text-zinc-300">
            {findings.length === 0 ? "No findings recorded yet" : "Nothing matches these filters"}
          </p>
          <p className="max-w-sm text-xs leading-relaxed text-zinc-600">
            {findings.length === 0
              ? "Scan a repository to read what LeakGuard reported on its pushes and pull requests, or analyse a branch on demand from the table above."
              : "Clear a filter to widen the feed."}
          </p>
        </div>
      ) : (
        <div className="space-y-2 p-5">
          {groups.slice(0, visibleGroups).map(group => {
            const isCollapsed = collapsed.has(group.key);
            return (
              <div key={group.key} className="overflow-hidden rounded-xl border border-[#1e2230]">
                <button
                  onClick={() => toggleGroup(group.key)}
                  className="flex w-full items-center justify-between gap-3 bg-[#0f1117] px-3 py-2 text-left transition-colors hover:bg-[#12151d]"
                >
                  <span className="flex min-w-0 items-center gap-2">
                    {isCollapsed ? (
                      <ChevronRight className="h-3.5 w-3.5 flex-shrink-0 text-zinc-500" />
                    ) : (
                      <ChevronDown className="h-3.5 w-3.5 flex-shrink-0 text-zinc-500" />
                    )}
                    {groupMode === "branch" ? (
                      <GitBranch className="h-3.5 w-3.5 flex-shrink-0 text-purple-400" />
                    ) : (
                      <FileCode2 className="h-3.5 w-3.5 flex-shrink-0 text-zinc-500" />
                    )}
                    <span className="truncate font-mono text-[11px] text-zinc-300">{group.key}</span>
                  </span>

                  <span className="flex flex-shrink-0 items-center gap-2.5 text-[11px] tabular-nums">
                    {group.counts.error > 0 && (
                      <span className="flex items-center gap-1" style={{ color: LEVEL_TEXT.error }}>
                        <AlertOctagon className="h-3 w-3" style={{ color: SEVERITY.error }} />
                        {group.counts.error}
                      </span>
                    )}
                    {group.counts.warning > 0 && (
                      <span className="flex items-center gap-1" style={{ color: LEVEL_TEXT.warning }}>
                        <AlertTriangle className="h-3 w-3" style={{ color: SEVERITY.warning }} />
                        {group.counts.warning}
                      </span>
                    )}
                  </span>
                </button>

                {!isCollapsed && <FindingRows items={group.items} showPath={groupMode !== "file"} />}
              </div>
            );
          })}

          {groups.length > visibleGroups && (
            <button
              onClick={() => setVisibleGroups(v => v + 12)}
              className="w-full rounded-xl border border-[#1e2230] bg-[#0f1117] py-2 text-[11px] text-zinc-400 transition-colors hover:border-purple-500/40 hover:text-white"
            >
              Show 12 more groups · {groups.length - visibleGroups} hidden
            </button>
          )}
        </div>
      )}
    </section>
  );
}

/* ─── one group's rows, itself paged so a hot file cannot flood the panel ─── */

function FindingRows({ items, showPath }: { items: Finding[]; showPath: boolean }) {
  const [shown, setShown] = useState(PAGE_SIZE);
  const visible = items.slice(0, shown);

  return (
    <div className="divide-y divide-[#181b25]">
      {visible.map(f => {
        const Icon = LEVEL_ICON[f.level];
        return (
          <div key={f.id} className="px-3 py-2.5 transition-colors hover:bg-white/[0.02]">
            <div className="flex items-start gap-2.5">
              <Icon
                className="mt-0.5 h-3.5 w-3.5 flex-shrink-0"
                style={{ color: SEVERITY[f.level] }}
              />

              <div className="min-w-0 flex-1">
                <p className="break-words font-mono text-[11px] text-zinc-300">
                  {showPath && <span className="text-zinc-200">{f.path}</span>}
                  {showPath && <span className="text-zinc-600">:</span>}
                  <span className="text-zinc-500">L{f.line}</span>
                  {f.func && <span className="text-zinc-500"> · {f.func}()</span>}
                </p>
                <p className="mt-0.5 break-words text-xs leading-relaxed text-zinc-400">
                  {f.message || f.title}
                </p>

                <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-zinc-600">
                  <span className="flex items-center gap-1">
                    <GitBranch className="h-2.5 w-2.5" />
                    <span className="font-mono">{f.branch}</span>
                  </span>
                  <span className="flex items-center gap-1">
                    {f.event === "pull_request" ? (
                      <GitPullRequest className="h-2.5 w-2.5" style={{ color: EVENT.pull_request }} />
                    ) : f.event === "scan" ? (
                      <Radar className="h-2.5 w-2.5" style={{ color: EVENT.scan }} />
                    ) : (
                      <GitCommitHorizontal className="h-2.5 w-2.5" style={{ color: EVENT.push }} />
                    )}
                    {eventLabel(f.event, f.prNumbers)}
                  </span>
                  {f.actor && <span>@{f.actor}</span>}
                  {f.sha && <span className="font-mono">{f.sha.slice(0, 7)}</span>}
                  <span>{timeAgo(f.at)}</span>
                  <span className={f.source === "ci" ? "text-emerald-600/80" : "text-purple-400/70"}>
                    {f.source === "ci" ? "GitHub Action" : "local scan"}
                  </span>
                </div>
              </div>

              {f.url && (
                <a
                  href={f.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-shrink-0 rounded p-1 text-zinc-600 transition-colors hover:text-white"
                  title="Open on GitHub"
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
        );
      })}

      {items.length > shown && (
        <button
          onClick={() => setShown(s => s + PAGE_SIZE)}
          className="w-full bg-[#0d0f15] py-1.5 text-[10px] text-zinc-500 transition-colors hover:bg-[#12151d] hover:text-white"
        >
          Show {Math.min(PAGE_SIZE, items.length - shown)} more · {items.length - shown} hidden
        </button>
      )}
    </div>
  );
}
