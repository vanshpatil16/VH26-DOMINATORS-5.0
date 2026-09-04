/**
 * CFG tab — renders per-function control-flow graphs as node/edge SVG,
 * fed by the backend's CFG JSON (Scalpel CFG + CodeGate patches).
 * Leak blocks glow red, safe blocks green, TRUE/FALSE branch labels shown.
 */
import { useMemo, useState } from "react";
import { Network } from "lucide-react";
import type { CfgFunction } from "@/lib/codegate";

const NODE_W = 168;
const NODE_H = 62;
const H_GAP = 44;
const V_GAP = 88;

interface Pos { x: number; y: number; }

function layout(fn: CfgFunction): { pos: Record<number, Pos>; width: number; height: number } {
  // BFS levels from entry
  const childrenOf = new Map<number, number[]>();
  const indeg = new Map<number, number>();
  fn.blocks.forEach((b) => { indeg.set(b.id, 0); });
  fn.edges.forEach((e) => {
    const arr = childrenOf.get(e.from) ?? [];
    arr.push(e.to);
    childrenOf.set(e.from, arr);
    indeg.set(e.to, (indeg.get(e.to) ?? 0) + 1);
  });
  const entry = fn.blocks.find((b) => b.isEntry) ?? fn.blocks[0];
  const levels: number[][] = [];
  const seen = new Set<number>([entry.id]);
  let frontier = [entry.id];
  while (frontier.length) {
    levels.push(frontier);
    const next: number[] = [];
    frontier.forEach((id) => {
      (childrenOf.get(id) ?? []).forEach((c) => {
        if (!seen.has(c)) { seen.add(c); next.push(c); }
      });
    });
    frontier = next;
  }
  // orphans (unreachable after dedupe/filtering) get appended to last level
  const placed = new Set(levels.flat());
  const orphans = fn.blocks.map((b) => b.id).filter((id) => !placed.has(id));
  if (orphans.length) levels.push(orphans);

  const pos: Record<number, Pos> = {};
  const canvasW = Math.max(560, levels.reduce((m, row) => Math.max(m, row.length), 0) * (NODE_W + H_GAP));
  levels.forEach((row, li) => {
    const totalW = row.length * NODE_W + (row.length - 1) * H_GAP;
    let sx = (canvasW - totalW) / 2;
    row.forEach((id) => {
      pos[id] = { x: sx, y: 28 + li * (NODE_H + V_GAP) };
      sx += NODE_W + H_GAP;
    });
  });
  const height = 28 + levels.length * (NODE_H + V_GAP);
  return { pos, width: canvasW, height };
}

function blockColor(tag: "leak" | "safe" | null): { fill: string; stroke: string; text: string } {
  if (tag === "leak") return { fill: "#1d0d10", stroke: "#ef4444", text: "#fca5a5" };
  if (tag === "safe") return { fill: "#0b1a12", stroke: "#10b981", text: "#6ee7b7" };
  return { fill: "#0d0e12", stroke: "#2a2d36", text: "#a1a1aa" };
}

function FunctionGraph({ fn }: { fn: CfgFunction }) {
  const { pos, width, height } = useMemo(() => layout(fn), [fn]);
  const [selected, setSelected] = useState<number | null>(null);

  const byId = useMemo(
    () => Object.fromEntries(fn.blocks.map((b) => [b.id, b])) as Record<number, CfgFunction["blocks"][number]>,
    [fn],
  );
  const sel = selected != null ? byId[selected] : null;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <h3 className="text-xs font-mono text-zinc-300">{fn.name}()</h3>
        {fn.hasLeak ? (
          <span className="px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/30 text-red-400 text-[10px] font-medium">
            LEAK DETECTED
          </span>
        ) : (
          <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[10px] font-medium">
            CLEAN
          </span>
        )}
        <span className="text-[10px] font-mono text-zinc-600">
          {fn.blocks.length} blocks · {fn.edges.length} edges
        </span>
      </div>
      <div className="rounded-2xl border border-[#1c1f28] bg-[#0a0b0e] overflow-x-auto">
        <svg width={width} height={height} className="min-w-full">
          <defs>
            <marker id="cg-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
              <path d="M0,0 L7,3.5 L0,7 z" fill="#52525b" />
            </marker>
            <marker id="cg-arrow-leak" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
              <path d="M0,0 L7,3.5 L0,7 z" fill="#ef4444" />
            </marker>
            <marker id="cg-arrow-safe" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
              <path d="M0,0 L7,3.5 L0,7 z" fill="#10b981" />
            </marker>
          </defs>

          {/* edges */}
          {fn.edges.map((e, i) => {
            const a = pos[e.from];
            const b = pos[e.to];
            if (!a || !b) return null;
            const sx = a.x + NODE_W / 2;
            const sy = a.y + NODE_H;
            const tx = b.x + NODE_W / 2;
            const ty = b.y;
            const target = byId[e.to];
            const stroke = target?.tag === "leak" ? "#ef4444" : target?.tag === "safe" ? "#10b981" : "#52525b";
            const marker = target?.tag === "leak" ? "cg-arrow-leak" : target?.tag === "safe" ? "cg-arrow-safe" : "cg-arrow";
            const midY = (sy + ty) / 2;
            const sameColumn = Math.abs(sx - tx) < 4;
            const d = sameColumn
              ? `M ${sx} ${sy} C ${sx} ${midY}, ${tx} ${midY}, ${tx} ${ty}`
              : `M ${sx} ${sy} C ${sx} ${midY}, ${tx} ${midY}, ${tx} ${ty}`;
            return (
              <g key={i}>
                <path d={d} fill="none" stroke={stroke} strokeWidth={1.2} markerEnd={`url(#${marker})`} opacity={0.75} />
                {e.label && (
                  <text
                    x={(sx + tx) / 2}
                    y={midY - 4}
                    textAnchor="middle"
                    className="font-mono"
                    fontSize={9}
                    fill={e.label === "TRUE" ? "#fbbf24" : e.label === "FALSE" ? "#71717a" : "#a78bfa"}
                  >
                    {e.label}
                  </text>
                )}
              </g>
            );
          })}

          {/* nodes */}
          {fn.blocks.map((b) => {
            const p = pos[b.id];
            if (!p) return null;
            const col = blockColor(b.tag);
            const isSel = selected === b.id;
            return (
              <g
                key={b.id}
                onClick={() => setSelected(isSel ? null : b.id)}
                className="cursor-pointer"
                style={{ filter: b.tag === "leak" ? "drop-shadow(0 0 6px rgba(239,68,68,.35))" : undefined }}
              >
                <rect
                  x={p.x} y={p.y} width={NODE_W} height={NODE_H} rx={10}
                  fill={col.fill} stroke={isSel ? "#a78bfa" : col.stroke}
                  strokeWidth={isSel ? 1.8 : 1.1}
                />
                <text x={p.x + 10} y={p.y + 16} className="font-mono" fontSize={9}
                  fill={b.isEntry ? "#67e8f9" : "#71717a"}>
                  {b.isEntry ? "▶ ENTRY " : ""}#{b.id}
                  {b.lineStart ? ` · L${b.lineStart}${b.lineEnd && b.lineEnd !== b.lineStart ? `–${b.lineEnd}` : ""}` : ""}
                </text>
                {b.statements.slice(0, 2).map((s, i) => (
                  <text key={i} x={p.x + 10} y={p.y + 32 + i * 13} className="font-mono" fontSize={9.5} fill={col.text}>
                    {s.length > 24 ? s.slice(0, 23) + "…" : s}
                  </text>
                ))}
                {b.statements.length > 2 && (
                  <text x={p.x + 10} y={p.y + 32 + 2 * 13} className="font-mono" fontSize={9} fill="#52525b">
                    +{b.statements.length - 2} more
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {sel && (
        <div className="rounded-xl border border-[#1c1f28] bg-[#0d0e12] p-3">
          <p className="text-[10px] font-mono text-zinc-500 mb-1">BLOCK #{sel.id} — FULL STATEMENTS</p>
          {sel.statements.length ? (
            <pre className="text-[11px] font-mono text-zinc-300 whitespace-pre-wrap">
              {sel.statements.map((s, i) => `${i + 1}. ${s}`).join("\n")}
            </pre>
          ) : (
            <p className="text-[11px] text-zinc-600">(empty block)</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function CfgGraphTab({ functions }: { functions: CfgFunction[] }) {
  if (!functions.length) {
    return (
      <div className="flex items-center gap-2 text-xs text-zinc-500 p-6">
        <Network className="w-4 h-4" /> Run an analysis to see control-flow graphs.
      </div>
    );
  }
  return (
    <div className="space-y-6">
      <p className="text-xs text-zinc-500 px-1">
        Control-flow graph per function — click a block to inspect its statements.
        <span className="text-red-400"> Red</span> = leaking path, <span className="text-emerald-400">green</span> = safe path.
      </p>
      {functions.map((fn) => (
        <FunctionGraph key={fn.name} fn={fn} />
      ))}
    </div>
  );
}
