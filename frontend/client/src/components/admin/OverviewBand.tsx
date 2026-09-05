/**
 * Vibrant Editorial Analytics Band — styled after high-contrast Alps design:
 * High-vibrancy metric cards (Crimson, Royal Blue, Warm Amber, Emerald Green)
 * with inline sparklines, percentage indicators, and curved activity trend.
 */
import React, { useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  AlertOctagon,
  AlertTriangle,
  FolderGit2,
  CheckCircle2,
  Sparkles,
  Calendar,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { DayBucket } from "@/lib/leakMonitor";

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
  const [timeFilter, setTimeFilter] = useState<"7D" | "14D">("14D");

  const clean = errors === 0 && warnings === 0;
  const trendUp = delta.delta > 0;
  const trendFlat = delta.delta === 0;
  const coverage = reposScanned > 0 ? Math.round((reposWithCi / (reposScanned || 1)) * 100) : 100;

  const displayBuckets = timeFilter === "7D" ? buckets.slice(-7) : buckets;

  return (
    <div className="space-y-5 font-sans select-none">
      {/* ── 4-CARD METRIC BAND (Obsidian Console Style) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* CARD 1: Confirmed Leaks */}
        <div className="relative overflow-hidden rounded-md bg-[#0d0f14] border border-white/[0.08] p-4 text-white shadow-sm transition-all hover:border-white/[0.15]">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 font-mono">
              Confirmed Leaks
            </span>
            <div className="w-7 h-7 rounded-md bg-red-500/10 border border-red-500/25 flex items-center justify-center">
              <AlertOctagon className="w-3.5 h-3.5 text-red-400" />
            </div>
          </div>

          <div className="mt-2.5 flex items-baseline justify-between">
            <span className="text-3xl font-extrabold tracking-tight">
              {errors}
            </span>
            <span className="inline-flex items-center space-x-1 text-[10px] font-mono bg-red-500/10 border border-red-500/25 px-2 py-0.5 rounded text-red-300">
              {trendFlat ? (
                <Minus className="w-3 h-3" />
              ) : trendUp ? (
                <TrendingUp className="w-3 h-3 text-red-400" />
              ) : (
                <TrendingDown className="w-3 h-3 text-emerald-400" />
              )}
              <span>{trendFlat ? "0%" : `${trendUp ? "+" : ""}${delta.delta} vs Wk`}</span>
            </span>
          </div>

          <p className="mt-1.5 text-xs text-zinc-400 font-mono">
            {errors > 0 ? "Requires CST with-block autofix" : "0 leaks confirmed"}
          </p>

          <div className="mt-2.5 flex items-end space-x-1 h-2.5 opacity-40">
            {[40, 70, 30, 90, 50, 80, 100].map((h, i) => (
              <div key={i} className="flex-1 bg-red-400 rounded-t-sm" style={{ height: `${h}%` }} />
            ))}
          </div>
        </div>

        {/* CARD 2: Exception Risks */}
        <div className="relative overflow-hidden rounded-md bg-[#0d0f14] border border-white/[0.08] p-4 text-white shadow-sm transition-all hover:border-white/[0.15]">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 font-mono">
              Exception Risks
            </span>
            <div className="w-7 h-7 rounded-md bg-amber-500/10 border border-amber-500/25 flex items-center justify-center">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            </div>
          </div>

          <div className="mt-2.5 flex items-baseline justify-between">
            <span className="text-3xl font-extrabold tracking-tight">
              {warnings}
            </span>
            <span className="inline-flex items-center space-x-1 text-[10px] font-mono bg-amber-500/10 border border-amber-500/25 px-2 py-0.5 rounded text-amber-300">
              <TrendingUp className="w-3 h-3" />
              <span>{branchCount} Branches</span>
            </span>
          </div>

          <p className="mt-1.5 text-xs text-zinc-400 font-mono">
            {warnings > 0 ? "Potential unhandled path leak" : "0 exception risks"}
          </p>

          <div className="mt-2.5 flex items-end space-x-1 h-2.5 opacity-40">
            {[60, 40, 80, 50, 70, 90, 65].map((h, i) => (
              <div key={i} className="flex-1 bg-amber-400 rounded-t-sm" style={{ height: `${h}%` }} />
            ))}
          </div>
        </div>

        {/* CARD 3: Repositories Monitored */}
        <div className="relative overflow-hidden rounded-md bg-[#0d0f14] border border-white/[0.08] p-4 text-white shadow-sm transition-all hover:border-white/[0.15]">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 font-mono">
              Monitored Repos
            </span>
            <div className="w-7 h-7 rounded-md bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center">
              <FolderGit2 className="w-3.5 h-3.5 text-indigo-400" />
            </div>
          </div>

          <div className="mt-2.5 flex items-baseline justify-between">
            <span className="text-3xl font-extrabold tracking-tight">
              {watchedRepos || repoCount}
            </span>
            <span className="inline-flex items-center space-x-1 text-[10px] font-mono bg-indigo-500/10 border border-indigo-500/25 px-2 py-0.5 rounded text-indigo-300">
              <span>{coverage}% CI Coverage</span>
            </span>
          </div>

          <p className="mt-1.5 text-xs text-zinc-400 font-mono">
            {reposScanned} scanned with LeakGuard
          </p>

          <div className="mt-2.5 flex items-end space-x-1 h-2.5 opacity-40">
            {[30, 50, 70, 80, 60, 90, 85].map((h, i) => (
              <div key={i} className="flex-1 bg-indigo-400 rounded-t-sm" style={{ height: `${h}%` }} />
            ))}
          </div>
        </div>

        {/* CARD 4: Clean Pass Rate */}
        <div className="relative overflow-hidden rounded-md bg-[#0d0f14] border border-white/[0.08] p-4 text-white shadow-sm transition-all hover:border-white/[0.15]">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 font-mono">
              Clean Pass Rate
            </span>
            <div className="w-7 h-7 rounded-md bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-center">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            </div>
          </div>

          <div className="mt-2.5 flex items-baseline justify-between">
            <span className="text-3xl font-extrabold tracking-tight">
              {clean ? "100%" : `${Math.max(10, 100 - (errors * 15 + warnings * 5))}%`}
            </span>
            <span className="inline-flex items-center space-x-1 text-[10px] font-mono bg-emerald-500/10 border border-emerald-500/25 px-2 py-0.5 rounded text-emerald-300">
              <TrendingUp className="w-3 h-3 text-emerald-400" />
              <span>Optimal</span>
            </span>
          </div>

          <p className="mt-1.5 text-xs text-zinc-400 font-mono">
            {clean ? "All branches clear of resource leaks" : `${errors + warnings} issues flagged`}
          </p>

          {/* Mini Sparkline Bar Accent */}
          <div className="mt-3 flex items-end space-x-1 h-3 opacity-60">
            {[80, 85, 90, 95, 90, 98, 100].map((h, i) => (
              <div key={i} className="flex-1 bg-white rounded-t-sm" style={{ height: `${h}%` }} />
            ))}
          </div>
        </div>
      </div>

      {/* ── LARGE DUAL-SERIES ANALYTICS CHART (Alps High-Contrast Dashboard) ── */}
      <div className="rounded-2xl border border-[#1e2230] bg-[#12141c] p-6 space-y-4 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1c2030] pb-4">
          <div>
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-rose-400" />
              <h3 className="text-base font-bold text-white font-poppins tracking-tight">
                Leak Detection & CI Scan Activity
              </h3>
            </div>
            <p className="text-xs text-zinc-400 mt-0.5 font-mono">
              Temporal distribution of confirmed leaks and exception risks across CI runs
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-1 bg-[#1a1d2b] border border-[#272d40] rounded-xl p-1 text-xs font-mono">
              <button
                onClick={() => setTimeFilter("7D")}
                className={`px-3 py-1 rounded-lg transition-colors ${
                  timeFilter === "7D" ? "bg-rose-600 text-white font-bold" : "text-zinc-400 hover:text-white"
                }`}
              >
                7 Days
              </button>
              <button
                onClick={() => setTimeFilter("14D")}
                className={`px-3 py-1 rounded-lg transition-colors ${
                  timeFilter === "14D" ? "bg-rose-600 text-white font-bold" : "text-zinc-400 hover:text-white"
                }`}
              >
                14 Days
              </button>
            </div>
          </div>
        </div>

        {/* Recharts Area Chart */}
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={displayBuckets} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorError" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.5} />
                  <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="colorWarning" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="label" stroke="#3f4760" tick={{ fontSize: 11, fill: "#8e99b0" }} />
              <YAxis stroke="#3f4760" tick={{ fontSize: 11, fill: "#8e99b0" }} allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  background: "#0c0d14",
                  border: "1px solid #f43f5e",
                  borderRadius: "14px",
                  fontSize: "12px",
                  color: "#fff",
                  boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
                }}
              />
              <Area
                type="monotone"
                dataKey="error"
                name="Confirmed Leaks"
                stroke="#f43f5e"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorError)"
                activeDot={{ r: 6, fill: "#f43f5e", stroke: "#ffffff", strokeWidth: 2 }}
              />
              <Area
                type="monotone"
                dataKey="warning"
                name="Exception Risks"
                stroke="#3b82f6"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorWarning)"
                activeDot={{ r: 6, fill: "#3b82f6", stroke: "#ffffff", strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Legend Indicator */}
        <div className="flex items-center justify-between text-xs font-mono text-zinc-400 border-t border-[#1c2030] pt-3">
          <div className="flex items-center space-x-6">
            <span className="flex items-center space-x-2">
              <span className="w-3 h-3 rounded-full bg-rose-500 inline-block shadow-sm shadow-rose-500/50" />
              <span className="text-zinc-200 font-semibold">Confirmed Leaks</span>
            </span>
            <span className="flex items-center space-x-2">
              <span className="w-3 h-3 rounded-full bg-blue-500 inline-block shadow-sm shadow-blue-500/50" />
              <span className="text-zinc-200 font-semibold">Exception Risks</span>
            </span>
          </div>
          <span className="text-zinc-500 hidden sm:inline">
            Updated in real-time from GitHub Check Runs
          </span>
        </div>
      </div>
    </div>
  );
}
