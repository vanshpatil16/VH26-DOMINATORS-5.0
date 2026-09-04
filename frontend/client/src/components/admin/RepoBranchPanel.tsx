/**
 * Repository picker + per-branch CI health.
 *
 * Each row is a branch: what the last LeakGuard run was (push or PR), how it
 * concluded, who triggered it, and how many leaks the analyzer annotated.
 * Branches CI has not touched can be analysed on demand.
 */
import React from "react";
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
} from "lucide-react";
import type { GitHubRepo } from "@/lib/github";
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
  return (
    <section className="overflow-hidden rounded-2xl border border-[#1e2230] bg-[#13151b]">
      {/* header */}
      <div className="flex flex-col gap-3 border-b border-[#1e2230] p-5 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-zinc-100">
            <GitBranch className="h-4 w-4 text-purple-400" />
            Branches
          </h2>
          <p className="mt-0.5 text-xs text-zinc-500">
            {selectedRepo ? (
              <>
                <span className="font-mono text-zinc-400">{selectedRepo}</span> ·{" "}
                {runsInspected} CI run{runsInspected === 1 ? "" : "s"} inspected
              </>
            ) : (
              "Pick a repository to see its branches"
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
              onClick={() => onSelectRepo(r.full_name)}
              className={`flex flex-shrink-0 items-center gap-2 rounded-xl border px-3 py-1.5 text-xs transition-colors ${
                active
                  ? "border-purple-500/50 bg-purple-500/10 text-white"
                  : "border-[#242938] bg-[#0f1117] text-zinc-400 hover:border-purple-500/30 hover:text-white"
              }`}
            >
              <span className="font-medium">{r.name}</span>
              {r.language && <span className="text-[10px] text-zinc-500">{r.language}</span>}
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
              <th className="py-2.5 pl-3 pr-5 text-right font-medium">Actions</th>
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
              const scanning = liveScan?.branch === b.branch && liveScan?.repo === selectedRepo;
              const run = b.lastRun;

              return (
                <tr
                  key={b.branch}
                  className={`border-b border-[#181b25] transition-colors last:border-0 ${
                    focused ? "bg-purple-500/[0.07]" : "hover:bg-white/[0.02]"
                  }`}
                >
                  <td className="py-2.5 pl-5 pr-3">
                    <button
                      onClick={() => onFocusBranch(focused ? "all" : b.branch)}
                      className="group flex items-center gap-2 text-left"
                      title="Filter findings to this branch"
                    >
                      <span
                        className={`h-4 w-0.5 rounded-full ${focused ? "bg-purple-400" : "bg-transparent"}`}
                      />
                      <span
                        className={`max-w-[16rem] truncate font-mono text-[11px] ${
                          focused ? "text-white" : "text-zinc-300 group-hover:text-white"
                        }`}
                      >
                        {b.branch}
                      </span>
                    </button>
                  </td>

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

                  <td className="px-3 py-2.5 text-[11px] tabular-nums text-zinc-500">
                    {timeAgo(run?.createdAt)}
                  </td>

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

                  <td className="py-2.5 pl-3 pr-5">
                    <div className="flex items-center justify-end gap-1">
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
