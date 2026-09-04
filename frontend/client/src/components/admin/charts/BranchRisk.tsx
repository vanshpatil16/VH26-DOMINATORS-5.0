/**
 * Which branches carry the leaks — horizontal stacked bars, worst first.
 *
 * Horizontal because branch names are long and ranked comparison reads down a
 * column; the value rides the bar end so the reader never counts gridlines.
 */
import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertOctagon, AlertTriangle } from "lucide-react";
import type { RiskRow } from "@/lib/leakMonitor";
import { axisProps, GRID, INK, SEVERITY, SURFACE } from "../chartTheme";

interface Props {
  rows: RiskRow[];
  activeBranch: string | "all";
  onSelect: (branch: string) => void;
  empty?: React.ReactNode;
}

function RiskTooltip({ active, payload }: any) {
  if (!active || !Array.isArray(payload) || payload.length === 0) return null;
  const row: RiskRow | undefined = payload[0]?.payload;
  if (!row) return null;

  return (
    <div className="max-w-xs rounded-lg border border-[#2a2f3d] bg-[#0b0d12]/95 px-3 py-2 shadow-xl shadow-black/60 backdrop-blur-sm">
      <p className="mb-1 truncate font-mono text-[11px] text-zinc-200">{row.key}</p>
      {row.repo && <p className="mb-1.5 truncate text-[10px] text-zinc-500">{row.repo}</p>}
      <p className="flex items-center gap-2 text-[11px] leading-5">
        <span className="inline-block h-0.5 w-3 rounded-full" style={{ background: SEVERITY.error }} />
        <span className="font-semibold tabular-nums text-zinc-100">{row.error}</span>
        <span className="text-zinc-400">confirmed</span>
      </p>
      <p className="flex items-center gap-2 text-[11px] leading-5">
        <span className="inline-block h-0.5 w-3 rounded-full" style={{ background: SEVERITY.warning }} />
        <span className="font-semibold tabular-nums text-zinc-100">{row.warning}</span>
        <span className="text-zinc-400">exception risk</span>
      </p>
      <p className="mt-1.5 text-[10px] text-zinc-500">Click to filter the feed to this branch</p>
    </div>
  );
}

export default function BranchRisk({ rows, activeBranch, onSelect, empty }: Props) {
  const height = Math.max(160, rows.length * 38 + 16);

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-baseline justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-zinc-100">Branch risk</h3>
          <p className="mt-0.5 text-xs text-zinc-500">Branches ranked by confirmed leaks</p>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-zinc-400">
          <span className="flex items-center gap-1.5">
            <AlertOctagon className="h-3 w-3" style={{ color: SEVERITY.error }} />
            Confirmed
          </span>
          <span className="flex items-center gap-1.5">
            <AlertTriangle className="h-3 w-3" style={{ color: SEVERITY.warning }} />
            Risk
          </span>
        </div>
      </div>

      <div className="relative flex min-h-[190px] w-full min-w-0 flex-1 items-center overflow-hidden">
        {rows.length === 0 && empty ? (
          <div className="absolute inset-0 flex items-center justify-center">{empty}</div>
        ) : (
          <ResponsiveContainer width="100%" height={height}>
            <BarChart
              data={rows}
              layout="vertical"
              margin={{ top: 0, right: 34, bottom: 0, left: 0 }}
              barCategoryGap="34%"
            >
              <CartesianGrid stroke={GRID} strokeWidth={1} horizontal={false} />
              <XAxis type="number" {...axisProps} allowDecimals={false} hide />
              <YAxis
                type="category"
                dataKey="label"
                width={116}
                tick={{ fill: INK.secondary, fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip content={<RiskTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
              <Bar
                dataKey="error"
                stackId="sev"
                fill={SEVERITY.error}
                stroke={SURFACE}
                strokeWidth={2}
                maxBarSize={16}
                onClick={(d: any) => d?.payload?.key && onSelect(d.payload.key)}
                className="cursor-pointer"
              >
                {rows.map(r => (
                  <Cell
                    key={r.key}
                    fillOpacity={activeBranch === "all" || activeBranch === r.key ? 1 : 0.35}
                  />
                ))}
              </Bar>
              <Bar
                dataKey="warning"
                stackId="sev"
                fill={SEVERITY.warning}
                stroke={SURFACE}
                strokeWidth={2}
                maxBarSize={16}
                radius={[0, 3, 3, 0]}
                onClick={(d: any) => d?.payload?.key && onSelect(d.payload.key)}
                className="cursor-pointer"
              >
                {rows.map(r => (
                  <Cell
                    key={r.key}
                    fillOpacity={activeBranch === "all" || activeBranch === r.key ? 1 : 0.35}
                  />
                ))}
                <LabelList
                  dataKey="total"
                  position="right"
                  offset={8}
                  fill={INK.secondary}
                  fontSize={11}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
