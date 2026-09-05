/**
 * Fourteen days of LeakGuard findings, stacked by severity.
 *
 * Columns (not lines) because each day is a discrete batch of CI runs, and the
 * reader's job is "is this getting worse?" — magnitude over time, two series.
 */
import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertOctagon, AlertTriangle } from "lucide-react";
import type { DayBucket } from "@/lib/leakMonitor";
import { axisProps, GRID, INK, SEVERITY, SURFACE } from "../chartTheme";

interface Props {
  data: DayBucket[];
  /** Rendered instead of the plot when there is nothing to show yet. */
  empty?: React.ReactNode;
}

function TrendTooltip({ active, payload, label }: any) {
  if (!active || !Array.isArray(payload) || payload.length === 0) return null;
  const rows = payload.filter((p: any) => p.value > 0);
  if (rows.length === 0) return null;

  return (
    <div className="rounded-lg border border-[#2a2f3d] bg-[#0b0d12]/95 px-3 py-2 shadow-xl shadow-black/60 backdrop-blur-sm">
      <p className="text-[11px] font-medium text-zinc-300 mb-1.5">{label}</p>
      {rows.map((r: any) => (
        <p key={r.dataKey} className="flex items-center gap-2 text-[11px] leading-5">
          <span
            className="inline-block h-0.5 w-3 rounded-full"
            style={{ background: r.color }}
          />
          <span className="font-semibold tabular-nums text-zinc-100">{r.value}</span>
          <span className="text-zinc-400">
            {r.dataKey === "error" ? "confirmed leaks" : "exception risks"}
          </span>
        </p>
      ))}
    </div>
  );
}

export default function LeakTrend({ data, empty }: Props) {
  const hasData = data.some(d => d.total > 0);

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-baseline justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-zinc-100">Findings over time</h3>
          <p className="mt-0.5 text-xs text-zinc-500">
            Every push and pull request LeakGuard checked, last 14 days
          </p>
        </div>

        {/* legend — identity never rides on color alone */}
        <div className="flex items-center gap-3 text-[11px] text-zinc-400">
          <span className="flex items-center gap-1.5">
            <AlertOctagon className="h-3 w-3" style={{ color: SEVERITY.error }} />
            Confirmed
          </span>
          <span className="flex items-center gap-1.5">
            <AlertTriangle className="h-3 w-3" style={{ color: SEVERITY.warning }} />
            Exception risk
          </span>
        </div>
      </div>

      <div className="relative min-h-[190px] w-full min-w-0 flex-1 overflow-hidden">
        {!hasData && empty ? (
          <div className="absolute inset-0 flex items-center justify-center">{empty}</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -18 }} barCategoryGap="28%">
              <CartesianGrid stroke={GRID} strokeWidth={1} vertical={false} />
              <XAxis
                dataKey="label"
                {...axisProps}
                interval="preserveStartEnd"
                minTickGap={24}
              />
              <YAxis {...axisProps} allowDecimals={false} width={44} />
              <Tooltip
                content={<TrendTooltip />}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              {/* stroke in the surface color is the 2px gap between segments */}
              <Bar
                dataKey="warning"
                stackId="sev"
                fill={SEVERITY.warning}
                stroke={SURFACE}
                strokeWidth={2}
                maxBarSize={18}
              />
              <Bar
                dataKey="error"
                stackId="sev"
                fill={SEVERITY.error}
                stroke={SURFACE}
                strokeWidth={2}
                maxBarSize={18}
                radius={[3, 3, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {hasData && (
        <p className="mt-2 text-[11px] text-zinc-600" style={{ color: INK.muted }}>
          Bars stack exception risks under confirmed leaks · hover a day for its counts
        </p>
      )}
    </div>
  );
}
