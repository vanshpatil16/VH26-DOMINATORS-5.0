/**
 * The band the dashboard opens with: the one number that matters, the context
 * that makes it mean something, and the 14-day trend beside it.
 */
import React from "react";
import { ArrowDownRight, ArrowUpRight, Minus, GitPullRequest, GitCommitHorizontal, Radar } from "lucide-react";
import LeakTrend from "./charts/LeakTrend";
import type { DayBucket } from "@/lib/leakMonitor";
import { EVENT, SEVERITY, SURFACE } from "./chartTheme";
import { timeAgo } from "./format";

interface Props {
  errors: number;
  warnings: number;
  repoCount: number;
  watchedRepos: number;
  branchCount: number;
  reposWithCi: number;
  reposScanned: number;
  lastScanAt: string | null;
  delta: { current: number; previous: number; delta: number };
  buckets: DayBucket[];
  events: { push: number; pull_request: number; scan: number };
  emptyHint: React.ReactNode;
}

export default function OverviewBand({
  errors,
  warnings,
  repoCount,
  watchedRepos,
  branchCount,
  reposWithCi,
  reposScanned,
  lastScanAt,
  delta,
  buckets,
  events,
  emptyHint,
}: Props) {
  const clean = errors === 0 && warnings === 0;
  const trendUp = delta.delta > 0;
  const trendFlat = delta.delta === 0;
  const eventTotal = events.push + events.pull_request + events.scan || 1;
  const coverage = reposScanned > 0 ? Math.round((reposWithCi / reposScanned) * 100) : 0;

  return (
    <section className="grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-[#1e2230] bg-[#1e2230] lg:grid-cols-12">
      {/* ── the number ── */}
      <div className="min-w-0 bg-[#13151b] p-5 sm:p-6 lg:col-span-5">
        <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
          Open confirmed leaks
        </p>

        <div className="mt-2 flex items-end gap-4">
          <span
            className="text-[56px] font-semibold leading-none tracking-tight"
            style={{ color: clean ? "#0ca30c" : SEVERITY.error }}
          >
            {errors}
          </span>

          <span
            className={`mb-2 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] ${
              trendFlat
                ? "border-zinc-700/60 text-zinc-400"
                : trendUp
                  ? "border-[#d03b3b]/40 bg-[#d03b3b]/10 text-[#f0a3a3]"
                  : "border-[#0ca30c]/40 bg-[#0ca30c]/10 text-[#7fd07f]"
            }`}
            title="Confirmed leaks in the last 7 days vs the 7 days before"
          >
            {trendFlat ? (
              <Minus className="h-3 w-3" />
            ) : trendUp ? (
              <ArrowUpRight className="h-3 w-3" />
            ) : (
              <ArrowDownRight className="h-3 w-3" />
            )}
            {trendFlat ? "no change" : `${trendUp ? "+" : ""}${delta.delta} vs prior week`}
          </span>
        </div>

        <p className="mt-3 max-w-sm text-sm leading-relaxed text-zinc-400">
          {clean ? (
            <>
              Nothing outstanding across{" "}
              <span className="text-zinc-200">
                {watchedRepos} watched {watchedRepos === 1 ? "repository" : "repositories"}
              </span>
              . Scan a branch to check code CI has not covered.
            </>
          ) : (
            <>
              <span className="text-zinc-200">{warnings} exception risks</span> alongside
              them, across{" "}
              <span className="text-zinc-200">
                {branchCount} {branchCount === 1 ? "branch" : "branches"}
              </span>{" "}
              in{" "}
              <span className="text-zinc-200">
                {repoCount} {repoCount === 1 ? "repository" : "repositories"}
              </span>
              .
            </>
          )}
        </p>

        {/* CI coverage meter */}
        <div className="mt-6 space-y-2">
          <div className="flex items-baseline justify-between text-xs">
            <span className="text-zinc-400">Repos with LeakGuard CI</span>
            <span className="tabular-nums text-zinc-300">
              {reposWithCi} of {reposScanned || 0} scanned
            </span>
          </div>
          <div
            className="flex h-1.5 overflow-hidden rounded-full"
            style={{ background: "rgba(57,135,229,0.16)" }}
          >
            <span style={{ width: `${coverage}%`, background: "#3987e5" }} />
          </div>
          <p className="text-[11px] text-zinc-600">
            {lastScanAt ? `Last scan ${timeAgo(lastScanAt)}` : "No scan recorded yet"}
          </p>
        </div>

        {/* where findings come from */}
        <div className="mt-6 space-y-2">
          <p className="text-xs text-zinc-400">Reported on</p>
          <div className="flex h-1.5 overflow-hidden rounded-full bg-[#1b1f29]">
            {(["push", "pull_request", "scan"] as const).map(
              key =>
                events[key] > 0 && (
                  <span
                    key={key}
                    style={{
                      width: `${(events[key] / eventTotal) * 100}%`,
                      background: EVENT[key],
                      borderRight: `2px solid ${SURFACE}`,
                    }}
                  />
                )
            )}
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-zinc-500">
            <span className="flex items-center gap-1.5">
              <GitCommitHorizontal className="h-3 w-3" style={{ color: EVENT.push }} />
              {events.push} on pushes
            </span>
            <span className="flex items-center gap-1.5">
              <GitPullRequest className="h-3 w-3" style={{ color: EVENT.pull_request }} />
              {events.pull_request} on PRs
            </span>
            <span className="flex items-center gap-1.5">
              <Radar className="h-3 w-3" style={{ color: EVENT.scan }} />
              {events.scan} on demand
            </span>
          </div>
        </div>
      </div>

      {/* ── the trend ── */}
      <div className="min-w-0 bg-[#13151b] p-5 sm:p-6 lg:col-span-7">
        <LeakTrend data={buckets} empty={emptyHint} />
      </div>
    </section>
  );
}
