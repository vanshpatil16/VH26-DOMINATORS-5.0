/**
 * The files to fix first — a ranked meter list rather than a chart, because
 * the reader wants the names and the magnitude, and paths never fit an axis.
 */
import React from "react";
import type { RiskRow } from "@/lib/leakMonitor";
import { SEVERITY, SURFACE } from "../chartTheme";

interface Props {
  rows: RiskRow[];
  query: string;
  onSelect: (path: string) => void;
  empty?: React.ReactNode;
}

export default function HotFiles({ rows, query, onSelect, empty }: Props) {
  const max = rows.reduce((m, r) => Math.max(m, r.total), 0) || 1;

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-zinc-100">Fix these first</h3>
        <p className="mt-0.5 text-xs text-zinc-500">Files carrying the most findings</p>
      </div>

      {rows.length === 0 ? (
        <div className="flex flex-1 items-center justify-center">{empty}</div>
      ) : (
        <ol className="flex flex-1 flex-col justify-center gap-3">
          {rows.map((row, i) => {
            const active = query === row.key;
            const errorPct = (row.error / max) * 100;
            const warnPct = (row.warning / max) * 100;

            return (
              <li key={row.key}>
                <button
                  onClick={() => onSelect(active ? "" : row.key)}
                  className="group w-full text-left"
                  title={row.key}
                >
                  <div className="mb-1.5 flex items-baseline gap-2">
                    <span className="w-3 shrink-0 text-[10px] tabular-nums text-zinc-600">
                      {i + 1}
                    </span>
                    <span
                      className={`truncate font-mono text-[11px] transition-colors ${
                        active ? "text-white" : "text-zinc-300 group-hover:text-white"
                      }`}
                    >
                      {row.label}
                    </span>
                    <span className="ml-auto shrink-0 text-[11px] font-semibold tabular-nums text-zinc-300">
                      {row.total}
                    </span>
                  </div>

                  {/* meter: fill carries severity, track is a lighter step of the same ramp */}
                  <div
                    className="ml-5 flex h-1.5 overflow-hidden rounded-full"
                    style={{ background: "rgba(208,59,59,0.14)" }}
                  >
                    {row.error > 0 && (
                      <span
                        style={{
                          width: `${errorPct}%`,
                          background: SEVERITY.error,
                          opacity: active || query === "" ? 1 : 0.45,
                        }}
                      />
                    )}
                    {row.warning > 0 && (
                      <span
                        style={{
                          width: `${warnPct}%`,
                          background: SEVERITY.warning,
                          borderLeft: row.error > 0 ? `2px solid ${SURFACE}` : undefined,
                          opacity: active || query === "" ? 1 : 0.45,
                        }}
                      />
                    )}
                  </div>

                  <p className="ml-5 mt-1 truncate text-[10px] text-zinc-600">
                    {row.error} confirmed · {row.warning} risk
                    {row.repo ? ` · ${row.repo.split("/")[1] ?? row.repo}` : ""}
                  </p>
                </button>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
