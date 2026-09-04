/**
 * Branch Risk Profile Component — Editorial, ultra-clean security risk index.
 * Precision micro-typography, monochromatic high-contrast cards, linear status pills.
 */
import React from "react";
import { GitBranch, ChevronRight, ShieldAlert } from "lucide-react";
import type { RiskRow } from "@/lib/leakMonitor";

interface Props {
  rows: RiskRow[];
  activeBranch: string | "all";
  onSelect: (branch: string) => void;
  empty?: React.ReactNode;
}

export default function BranchRisk({ rows, activeBranch, onSelect, empty }: Props) {
  const maxVal = Math.max(...rows.map((r) => r.total || 0), 1);

  return (
    <div className="flex h-full flex-col font-poppins">
      {/* Header */}
      <div className="mb-3.5 flex items-center justify-between border-b border-[#181a24] pb-3">
        <div>
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2 font-mono">
            <GitBranch className="w-3.5 h-3.5 text-purple-400" />
            <span>Branch Risk Profile</span>
          </h3>
          <p className="mt-0.5 text-[11px] text-zinc-400">Branches ranked by security findings</p>
        </div>
        
        {/* Legend */}
        <div className="flex items-center gap-2.5 text-[10px] font-mono">
          <span className="flex items-center gap-1 text-zinc-400">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
            Confirmed
          </span>
          <span className="flex items-center gap-1 text-zinc-400">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            Risk
          </span>
        </div>
      </div>

      {/* Body */}
      {rows.length === 0 ? (
        <div className="flex flex-1 items-center justify-center p-6 text-center">
          {empty || (
            <div className="flex flex-col items-center gap-2">
              <ShieldAlert className="w-6 h-6 text-zinc-700" />
              <span className="font-mono text-zinc-500 text-[11px]">No branch risk findings recorded</span>
            </div>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-2 flex-1 overflow-y-auto pr-1">
          {rows.map((row, idx) => {
            const isSelected = activeBranch === row.key;
            const total = row.total || row.error + row.warning;
            const pct = Math.min(100, Math.max(6, (total / maxVal) * 100));

            return (
              <button
                key={row.key}
                onClick={() => onSelect(isSelected ? "all" : row.key)}
                className={`group relative flex flex-col gap-2 rounded-lg p-2.5 text-left transition-all duration-150 border ${
                  isSelected
                    ? "bg-[#12131d] border-purple-500/50 shadow-md shadow-purple-950/30"
                    : "bg-[#0b0c13] border-[#181b26] hover:border-[#2a2f44] hover:bg-[#0f1019]"
                }`}
              >
                {/* Upper row */}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-mono text-[10px] font-bold text-zinc-500 w-4">
                      #{idx + 1}
                    </span>
                    <span className="font-mono text-xs font-semibold text-zinc-200 group-hover:text-white transition-colors truncate">
                      {row.label || row.key}
                    </span>
                    {row.repo && (
                      <span className="hidden sm:inline-block text-[10px] font-mono text-zinc-500 truncate">
                        · {row.repo.split("/")[1] ?? row.repo}
                      </span>
                    )}
                  </div>

                  {/* Badges */}
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
                    <ChevronRight className="w-3.5 h-3.5 text-zinc-600 group-hover:text-purple-400 transition-colors" />
                  </div>
                </div>

                {/* Meter Bar */}
                <div className="w-full bg-[#12141d] rounded-full h-1 overflow-hidden flex">
                  <div
                    className="h-full bg-gradient-to-r from-rose-500 via-amber-400 to-purple-500 rounded-full transition-all duration-300"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
