/**
 * Repository picker + per-branch CI health + Graphical Commit Log Stream.
 *
 * Each row is a branch: what the last LeakGuard run was (push or PR), how it
 * concluded, who triggered it, and how many leaks the analyzer annotated.
 * Clicking a branch opens its graphical Git commit timeline graph & commit log.
 */
import React, { useState, useCallback, useMemo } from "react";
import {
  GitBranch,
  RefreshCw,
  Loader2,
  ExternalLink,
  Play,
  Lock,
  GitPullRequest,
  GitCommitHorizontal,
  AlertOctagon,
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronUp,
  Search,
  Copy,
  Users,
  Calendar,
  Sparkles,
  GitCommit,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { toast } from "sonner";

import {
  fetchRepoCommits,
  processCommitTimeline,
  type GitHubRepo,
  type GitHubCommit,
} from "@/lib/github";
import type { BranchHealth } from "@/lib/leakMonitor";
import type { GhError } from "@/lib/githubActions";
import { conclusionLabel, conclusionStyle, timeAgo } from "./format";
import { SEVERITY } from "./chartTheme";

export interface LiveScanState {
  repo: string;
  branch: string;
  done: number;
  total: number;
}

interface Props {
  repos: GitHubRepo[];
  selectedRepo: string | null;
  onSelectRepo: (fullName: string) => void;

  branches: BranchHealth[];
  runsInspected: number;
  loading: boolean;
  error: string | null;
  notes: GhError[];

  activeBranch: string | "all";
  onFocusBranch: (branch: string | "all") => void;
  onRescanRepo: () => void;
  onLiveScan: (branch: string) => void;
  liveScan: LiveScanState | null;
}

export default function RepoBranchPanel({
  repos,
  selectedRepo,
  onSelectRepo,
  branches,
  runsInspected,
  loading,
  error,
  notes,
  activeBranch,
  onFocusBranch,
  onRescanRepo,
  onLiveScan,
  liveScan,
}: Props) {
  const [expandedBranch, setExpandedBranch] = useState<string | null>(null);
  const [branchCommits, setBranchCommits] = useState<Record<string, GitHubCommit[]>>({});
  const [loadingCommits, setLoadingCommits] = useState<Record<string, boolean>>({});
  const [searchCommitQuery, setSearchCommitQuery] = useState("");

  const loadCommitsForBranch = useCallback(
    async (branchName: string) => {
      if (!selectedRepo) return;
      const [owner, name] = selectedRepo.split("/");
      if (!owner || !name) return;

      setLoadingCommits(prev => ({ ...prev, [branchName]: true }));
      const commits = await fetchRepoCommits(owner, name, branchName);
      setBranchCommits(prev => ({ ...prev, [branchName]: commits }));
      setLoadingCommits(prev => ({ ...prev, [branchName]: false }));
    },
    [selectedRepo]
  );

  const toggleBranchExpand = (branchName: string) => {
    if (expandedBranch === branchName) {
      setExpandedBranch(null);
    } else {
      setExpandedBranch(branchName);
      if (!branchCommits[branchName]) {
        void loadCommitsForBranch(branchName);
      }
    }
  };

  const handleCopySha = (sha: string) => {
    navigator.clipboard.writeText(sha);
    toast.success(`Copied commit SHA: ${sha}`);
  };

  return (
    <section className="overflow-hidden rounded-2xl border border-[#1e2230] bg-[#13151b] shadow-xl">
      {/* header */}
      <div className="flex flex-col gap-3 border-b border-[#1e2230] p-5 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-zinc-100">
            <GitBranch className="h-4 w-4 text-purple-400" />
            Branches & Commit History Graph
          </h2>
          <p className="mt-0.5 text-xs text-zinc-500">
            {selectedRepo ? (
              <>
                <span className="font-mono text-purple-300 font-medium">{selectedRepo}</span> ·{" "}
                {runsInspected} CI run{runsInspected === 1 ? "" : "s"} inspected · Click any branch to expand commit timeline
              </>
            ) : (
              "Pick a repository below to inspect branches and commit history"
            )}
          </p>
        </div>

        <button
          onClick={onRescanRepo}
          disabled={!selectedRepo || loading}
          className="flex items-center gap-1.5 self-start rounded-lg border border-[#242938] bg-[#0f1117] px-3 py-1.5 text-xs text-zinc-300 transition-colors hover:border-purple-500/50 hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-purple-400" : ""}`} />
          Re-read CI
        </button>
      </div>

      {/* repo chips */}
      <div className="flex items-center gap-2 overflow-x-auto border-b border-[#1e2230] px-5 py-3 scrollbar-purple">
        {repos.length === 0 && (
          <span className="text-xs text-zinc-600">No repositories loaded</span>
        )}
        {repos.map(r => {
          const active = selectedRepo === r.full_name;
          return (
            <button
              key={r.id}
              onClick={() => {
                onSelectRepo(r.full_name);
                setExpandedBranch(null);
              }}
              className={`flex flex-shrink-0 items-center gap-2 rounded-xl border px-3 py-1.5 text-xs transition-all ${
                active
                  ? "border-purple-500/50 bg-purple-500/15 text-white font-medium shadow-md shadow-purple-950/40"
                  : "border-[#242938] bg-[#0f1117] text-zinc-400 hover:border-purple-500/30 hover:text-white"
              }`}
            >
              <span>{r.name}</span>
              {r.language && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-purple-300">
                  {r.language}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* API notes and errors */}
      {(notes.length > 0 || error) && (
        <div className="space-y-1.5 border-b border-[#1e2230] px-5 py-3">
          {error && (
            <p className="flex items-start gap-2 text-[11px]" style={{ color: "#f0a3a3" }}>
              <AlertOctagon className="mt-px h-3 w-3 flex-shrink-0" />
              {error}
            </p>
          )}
          {notes.map((n, i) => (
            <p
              key={`${n.status}-${i}`}
              className="flex items-start gap-2 text-[11px] text-amber-200/80"
            >
              <Lock className="mt-px h-3 w-3 flex-shrink-0" />
              <span>
                {n.message}
                {n.needsAuth ? " — add a token with checks:read to read this repository." : ""}
              </span>
            </p>
          ))}
        </div>
      )}

      {/* branch table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-[#1e2230] text-[10px] uppercase tracking-wider text-zinc-500">
              <th className="py-2.5 pl-5 pr-3 font-medium">Branch</th>
              <th className="px-3 py-2.5 font-medium">Last run</th>
              <th className="px-3 py-2.5 font-medium">Trigger</th>
              <th className="px-3 py-2.5 font-medium">When</th>
              <th className="px-3 py-2.5 text-right font-medium">Findings</th>
              <th className="py-2.5 pl-3 pr-5 text-right font-medium">Commit Logs & Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && branches.length === 0 && (
              <tr>
                <td colSpan={6} className="py-8 text-center">
                  <span className="inline-flex items-center gap-2 text-xs text-zinc-500">
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-purple-400" />
                    Reading workflow runs and check annotations…
                  </span>
                </td>
              </tr>
            )}

            {!loading && branches.length === 0 && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-xs text-zinc-600">
                  {selectedRepo
                    ? "No branches or LeakGuard runs found for this repository."
                    : "Select a repository above."}
                </td>
              </tr>
            )}

            {branches.map(b => {
              const focused = activeBranch === b.branch;
              const isExpanded = expandedBranch === b.branch;
              const scanning = liveScan?.branch === b.branch && liveScan?.repo === selectedRepo;
              const run = b.lastRun;
              const commits = branchCommits[b.branch] || [];
              const isLoadingCommits = loadingCommits[b.branch];

              const filteredCommits = searchCommitQuery.trim()
                ? commits.filter(
                    c =>
                      c.message.toLowerCase().includes(searchCommitQuery.toLowerCase()) ||
                      c.sha.toLowerCase().includes(searchCommitQuery.toLowerCase()) ||
                      c.authorName.toLowerCase().includes(searchCommitQuery.toLowerCase())
                  )
                : commits;

              const timelinePoints = processCommitTimeline(commits);

              return (
                <React.Fragment key={b.branch}>
                  <tr
                    className={`border-b border-[#181b25] transition-colors ${
                      focused || isExpanded ? "bg-purple-500/[0.07]" : "hover:bg-white/[0.02]"
                    }`}
                  >
                    {/* Branch Name & Expand Button */}
                    <td className="py-2.5 pl-5 pr-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => toggleBranchExpand(b.branch)}
                          className="p-1 rounded-md bg-white/5 hover:bg-purple-500/20 text-zinc-400 hover:text-purple-300 transition-colors"
                          title={isExpanded ? "Collapse commit log" : "Expand branch commit log graph"}
                        >
                          {isExpanded ? (
                            <ChevronUp className="h-3.5 w-3.5 text-purple-400" />
                          ) : (
                            <ChevronDown className="h-3.5 w-3.5" />
                          )}
                        </button>

                        <button
                          onClick={() => onFocusBranch(focused ? "all" : b.branch)}
                          className="group flex items-center gap-2 text-left"
                          title="Filter findings to this branch"
                        >
                          <span
                            className={`h-4 w-0.5 rounded-full ${
                              focused ? "bg-purple-400" : "bg-transparent"
                            }`}
                          />
                          <span
                            className={`max-w-[14rem] truncate font-mono text-[11px] ${
                              focused ? "text-white font-semibold" : "text-zinc-300 group-hover:text-white"
                            }`}
                          >
                            {b.branch}
                          </span>
                        </button>
                      </div>
                    </td>

                    {/* Last Run */}
                    <td className="px-3 py-2.5">
                      {run ? (
                        <span
                          className={`inline-block rounded border px-2 py-0.5 text-[10px] ${conclusionStyle(
                            run.status,
                            run.conclusion
                          )}`}
                        >
                          {conclusionLabel(run.status, run.conclusion)}
                        </span>
                      ) : (
                        <span className="text-[11px] text-zinc-600">no CI run</span>
                      )}
                    </td>

                    {/* Trigger */}
                    <td className="px-3 py-2.5">
                      {run ? (
                        <span className="inline-flex items-center gap-1.5 text-[11px] text-zinc-400">
                          {run.event === "pull_request" ? (
                            <GitPullRequest className="h-3 w-3 text-[#199e70]" />
                          ) : (
                            <GitCommitHorizontal className="h-3 w-3 text-[#3987e5]" />
                          )}
                          {run.event === "pull_request" && run.prNumbers.length
                            ? `PR #${run.prNumbers[0]}`
                            : run.event.replace("_", " ")}
                          <span className="max-w-[8rem] truncate text-zinc-600">@{run.actor}</span>
                        </span>
                      ) : (
                        <span className="text-[11px] text-zinc-600">—</span>
                      )}
                    </td>

                    {/* When */}
                    <td className="px-3 py-2.5 text-[11px] tabular-nums text-zinc-500">
                      {timeAgo(run?.createdAt)}
                    </td>

                    {/* Findings */}
                    <td className="whitespace-nowrap px-3 py-2.5 text-right">
                      {b.counts.total === 0 ? (
                        <span className="inline-flex items-center gap-1 text-[11px] text-emerald-500/80">
                          <Check className="h-3 w-3" />
                          clear
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-2">
                          {b.counts.error > 0 && (
                            <span
                              className="inline-flex items-center gap-1 text-[11px] tabular-nums"
                              style={{ color: "#f0a3a3" }}
                              title={`${b.counts.error} confirmed leaks`}
                            >
                              <AlertOctagon className="h-3 w-3" style={{ color: SEVERITY.error }} />
                              {b.counts.error}
                            </span>
                          )}
                          {b.counts.warning > 0 && (
                            <span
                              className="inline-flex items-center gap-1 text-[11px] tabular-nums text-amber-200/90"
                              title={`${b.counts.warning} exception risks`}
                            >
                              <AlertTriangle className="h-3 w-3" style={{ color: SEVERITY.warning }} />
                              {b.counts.warning}
                            </span>
                          )}
                        </span>
                      )}
                    </td>

                    {/* Actions & Commit Toggle Button */}
                    <td className="py-2.5 pl-3 pr-5">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => toggleBranchExpand(b.branch)}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 text-purple-300 text-[11px] font-mono transition-all"
                        >
                          <GitCommit className="w-3.5 h-3.5 text-purple-400" />
                          <span>{isExpanded ? "Hide Commits" : "Commits & Graph"}</span>
                        </button>

                        <button
                          onClick={() => onLiveScan(b.branch)}
                          disabled={!!liveScan}
                          title="Analyse this branch now with CodeGate"
                          className="rounded-lg border border-transparent p-1.5 text-zinc-500 transition-colors hover:border-[#242938] hover:bg-[#0f1117] hover:text-cyan-300 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {scanning ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin text-cyan-400" />
                          ) : (
                            <Play className="h-3.5 w-3.5" />
                          )}
                        </button>

                        {run && (
                          <a
                            href={run.htmlUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            title="Open the workflow run on GitHub"
                            className="inline-block rounded-lg border border-transparent p-1.5 text-zinc-500 transition-colors hover:border-[#242938] hover:bg-[#0f1117] hover:text-white"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        )}
                      </div>
                    </td>
                  </tr>

                  {/* ── EXPANDED GRAPH & COMMIT STREAM DRAWER ── */}
                  {isExpanded && (
                    <tr className="bg-[#0b0c10] border-b border-[#1e2230]">
                      <td colSpan={6} className="p-4 md:p-6 space-y-5">
                        <div className="rounded-2xl bg-[#0f1117] border border-[#1f2434] p-4 md:p-5 space-y-4 shadow-2xl">
                          
                          {/* Top Controls & Search Bar */}
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1c2030] pb-4">
                            <div>
                              <div className="flex items-center gap-2">
                                <GitBranch className="w-4 h-4 text-purple-400" />
                                <h4 className="text-sm font-bold text-white font-poppins">
                                  Branch Commit Timeline — <span className="font-mono text-purple-300">{b.branch}</span>
                                </h4>
                                <span className="text-[10px] font-mono bg-purple-500/20 border border-purple-500/30 text-purple-300 px-2 py-0.5 rounded-full">
                                  {commits.length} commits
                                </span>
                              </div>
                              <p className="text-xs text-zinc-400 mt-0.5">
                                Interactive commit graph stream parsed from GitHub REST API
                              </p>
                            </div>

                            <div className="relative w-full sm:w-64">
                              <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                              <input
                                type="text"
                                value={searchCommitQuery}
                                onChange={e => setSearchCommitQuery(e.target.value)}
                                placeholder="Filter commits by SHA or message..."
                                className="w-full bg-[#151722] border border-[#272d40] focus:border-purple-500 text-white placeholder-zinc-500 pl-8 pr-3 py-1.5 rounded-xl text-xs font-mono outline-none transition-colors"
                              />
                            </div>
                          </div>

                          {/* Graphical Commit Activity Chart */}
                          {commits.length > 0 && (
                            <div className="bg-[#141620] border border-[#202536] rounded-xl p-4 space-y-2">
                              <div className="flex items-center justify-between text-xs font-mono text-zinc-400">
                                <span className="flex items-center gap-1.5">
                                  <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                                  <span>COMMIT ACTIVITY TIMELINE</span>
                                </span>
                                <span>Density over time</span>
                              </div>

                              <div className="h-28 w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                  <AreaChart data={timelinePoints} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                                    <defs>
                                      <linearGradient id={`grad-${b.branch}`} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.4} />
                                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.0} />
                                      </linearGradient>
                                    </defs>
                                    <XAxis dataKey="date" stroke="#3f4760" tick={{ fontSize: 10, fill: '#8e99b0' }} />
                                    <YAxis stroke="#3f4760" tick={{ fontSize: 10, fill: '#8e99b0' }} allowDecimals={false} />
                                    <Tooltip
                                      contentStyle={{
                                        background: '#0d0e12',
                                        border: '1px solid #8b5cf6',
                                        borderRadius: '10px',
                                        fontSize: '11px',
                                        color: '#fff',
                                      }}
                                    />
                                    <Area
                                      type="monotone"
                                      dataKey="count"
                                      stroke="#8b5cf6"
                                      strokeWidth={2}
                                      fillOpacity={1}
                                      fill={`url(#grad-${b.branch})`}
                                    />
                                  </AreaChart>
                                </ResponsiveContainer>
                              </div>
                            </div>
                          )}

                          {/* Loading State */}
                          {isLoadingCommits && (
                            <div className="py-8 flex items-center justify-center space-x-2 text-xs text-zinc-400 font-mono">
                              <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                              <span>Fetching branch commit logs from GitHub...</span>
                            </div>
                          )}

                          {/* Commit List Stream with Git Graph Line */}
                          {!isLoadingCommits && (
                            <div className="relative pl-6 space-y-3 max-h-[360px] overflow-y-auto pr-2 custom-scrollbar">
                              {/* Vertical Git Branch Line */}
                              <div className="absolute left-2.5 top-2 bottom-2 w-0.5 bg-gradient-to-b from-purple-500 via-purple-500/40 to-transparent pointer-events-none" />

                              {filteredCommits.map((c, idx) => (
                                <div
                                  key={c.sha + idx}
                                  className="relative group bg-[#141722] hover:bg-[#191d2b] border border-[#222738] hover:border-purple-500/40 rounded-xl p-3 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md"
                                >
                                  {/* Git Node Bullet */}
                                  <div className="absolute -left-6 top-4 w-3.5 h-3.5 rounded-full bg-[#0d0e12] border-2 border-purple-400 group-hover:scale-125 transition-transform" />

                                  {/* Commit Info */}
                                  <div className="flex items-start gap-3 min-w-0 flex-1">
                                    <img
                                      src={c.authorAvatar || "https://avatars.githubusercontent.com/u/9919?v=4"}
                                      alt={c.authorName}
                                      className="w-8 h-8 rounded-full border border-purple-500/40 object-cover shrink-0 mt-0.5"
                                    />

                                    <div className="min-w-0 flex-1 space-y-1">
                                      <p className="text-xs font-semibold text-white truncate font-poppins group-hover:text-purple-200 transition-colors">
                                        {c.message}
                                      </p>
                                      <div className="flex items-center gap-2 text-[10px] font-mono text-zinc-400 flex-wrap">
                                        <span className="text-purple-300 font-medium">@{c.authorName}</span>
                                        <span>•</span>
                                        <span className="flex items-center gap-1 text-zinc-500">
                                          <Calendar className="w-3 h-3" />
                                          {timeAgo(c.date)}
                                        </span>
                                      </div>
                                    </div>
                                  </div>

                                  {/* SHA Badge & Link */}
                                  <div className="flex items-center gap-2 shrink-0">
                                    <button
                                      onClick={() => handleCopySha(c.sha)}
                                      className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#1c202e] hover:bg-[#252a3d] border border-[#2c3348] text-purple-300 font-mono text-[11px] hover:border-purple-400 transition-all group/sha"
                                      title="Click to copy commit SHA"
                                    >
                                      <GitCommit className="w-3 h-3 text-purple-400" />
                                      <span>{c.sha}</span>
                                      <Copy className="w-3 h-3 opacity-0 group-hover/sha:opacity-100 transition-opacity" />
                                    </button>

                                    <a
                                      href={c.htmlUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="p-1.5 rounded-lg bg-[#1c202e] hover:bg-[#252a3d] border border-[#2c3348] text-zinc-400 hover:text-white transition-colors"
                                      title="View commit on GitHub"
                                    >
                                      <ExternalLink className="w-3.5 h-3.5" />
                                    </a>
                                  </div>
                                </div>
                              ))}

                              {filteredCommits.length === 0 && !isLoadingCommits && (
                                <div className="text-center py-6 text-xs text-zinc-500 font-mono">
                                  No commits found for {b.branch}.
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {liveScan && liveScan.repo === selectedRepo && (
        <div className="flex items-center gap-3 border-t border-[#1e2230] px-5 py-3 text-[11px] text-cyan-300">
          <Loader2 className="h-3.5 w-3.5 flex-shrink-0 animate-spin" />
          <span className="flex-shrink-0 font-mono">
            {liveScan.branch} — {liveScan.done}/{liveScan.total} files
          </span>
          <span className="h-1 flex-1 overflow-hidden rounded-full bg-[#1b1f29]">
            <span
              className="block h-full bg-cyan-400 transition-all duration-300"
              style={{ width: `${liveScan.total ? (liveScan.done / liveScan.total) * 100 : 0}%` }}
            />
          </span>
        </div>
      )}
    </section>
  );
}
