/**
 * Hot Files Component — Priority files carrying security findings.
 * Editorial, minimalist design featuring clean file path typography, subtle micro-badges,
 * and sleek progress indicators.
 */
import React from "react";
import { FileCode, ArrowRight, ShieldAlert } from "lucide-react";
import type { RiskRow } from "@/lib/leakMonitor";

interface Props {
  rows: RiskRow[];
  query: string;
  onSelect: (path: string) => void;
  empty?: React.ReactNode;
}

export default function HotFiles({ rows, query, onSelect, empty }: Props) {
  const maxTotal = Math.max(...rows.map((r) => r.total || 0), 1);

  return (
    <div className="flex h-full flex-col font-poppins">
      {/* Header */}
      <div className="mb-3.5 flex items-center justify-between border-b border-[#181a24] pb-3">
        <div>
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2 font-mono">
            <FileCode className="w-3.5 h-3.5 text-rose-400" />
            <span>Critical Files to Fix</span>
          </h3>
          <p className="mt-0.5 text-[11px] text-zinc-400">Files carrying the highest findings</p>
        </div>
        <span className="px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[10px] font-mono font-semibold">
          {rows.length} {rows.length === 1 ? "File" : "Files"}
        </span>
      </div>

      {/* List Content */}
      {rows.length === 0 ? (
        <div className="flex flex-1 items-center justify-center p-6 text-center">
          {empty || (
            <div className="flex flex-col items-center gap-2">
              <ShieldAlert className="w-6 h-6 text-zinc-700" />
              <span className="font-mono text-zinc-500 text-[11px]">No critical files needing attention</span>
            </div>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-2 flex-1 overflow-y-auto pr-1">
          {rows.map((row, idx) => {
            const isSelected = query === row.key;
            const total = row.total || row.error + row.warning;
            const pct = Math.min(100, Math.max(6, (total / maxTotal) * 100));

            return (
              <button
                key={row.key}
                onClick={() => onSelect(isSelected ? "" : row.key)}
                className={`group relative flex flex-col gap-2 rounded-lg p-2.5 text-left transition-all duration-150 border ${
                  isSelected
                    ? "bg-[#161115] border-rose-500/50 shadow-md shadow-rose-950/30"
                    : "bg-[#0b0c13] border-[#181b26] hover:border-[#2a2f44] hover:bg-[#0f1019]"
                }`}
              >
                {/* Upper line */}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-mono text-[10px] font-bold text-zinc-500 w-4">
                      #{idx + 1}
                    </span>
                    <FileCode className="w-3.5 h-3.5 text-zinc-500 shrink-0 group-hover:text-rose-400 transition-colors" />
                    <span className="font-mono text-xs font-semibold text-zinc-200 group-hover:text-white transition-colors truncate">
                      {row.label || row.key}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0 font-mono text-[10px]">
                    {row.error > 0 && (
                      <span className="px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold">
                        {row.error} path
                      </span>
                    )}
                    {row.warning > 0 && (
                      <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 font-semibold">
                        {row.warning} risk
                      </span>
                    )}
                    <span className="text-zinc-400 font-semibold ml-1">
                      {total}
                    </span>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="w-full bg-[#12141d] rounded-full h-1 overflow-hidden flex">
                  <div
                    className="h-full bg-gradient-to-r from-rose-500 via-amber-400 to-rose-400 rounded-full transition-all duration-300"
                    style={{ width: `${pct}%` }}
                  />
                </div>

                {/* Subtext info */}
                <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500 pt-0.5">
                  <span>
                    {row.error} confirmed · {row.warning} risk
                    {row.repo ? ` · ${row.repo.split("/")[1] ?? row.repo}` : ""}
                  </span>
                  <span className="opacity-0 group-hover:opacity-100 transition-opacity text-rose-400 flex items-center gap-1 font-medium">
                    Filter feed <ArrowRight className="w-3 h-3" />
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
