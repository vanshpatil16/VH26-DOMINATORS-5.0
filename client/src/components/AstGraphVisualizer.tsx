import React, { useState, useRef, useCallback, useEffect } from "react";
import { Network, Cpu, Search, Code2, GitBranch, Zap, Move } from "lucide-react";

/* ─── Types ──────────────────────────────────────────────────────────────── */

interface AstNode {
  id: string;
  label: string;
  type: string;
  detail?: string;
  fill: string;
  stroke: string;
  textColor: string;
  children: string[];
}

interface NodePos {
  x: number;
  y: number;
}

/* ─── Static node definitions ────────────────────────────────────────────── */

const NODE_DEFS: AstNode[] = [
  { id: "program",        label: "Program",             type: "Root",           detail: "index.ts · L1–180",  fill: "#1e1140", stroke: "#7c3aed", textColor: "#c4b5fd", children: ["import-block","func-fetch","func-compute"] },
  { id: "import-block",   label: "ImportDecl",          type: "Import",         detail: "L1–10",              fill: "#0c1f2e", stroke: "#0891b2", textColor: "#67e8f9", children: ["id-react","id-github"] },
  { id: "func-fetch",     label: "fetchTelemetry()",    type: "FunctionDecl",   detail: "L12–48",             fill: "#0c2218", stroke: "#059669", textColor: "#6ee7b7", children: ["if-auth","return-payload"] },
  { id: "func-compute",   label: "computeVelocity()",   type: "FunctionDecl",   detail: "L52–98",             fill: "#1a0f2e", stroke: "#9333ea", textColor: "#d8b4fe", children: ["for-loop"] },
  { id: "id-react",       label: '"react"',             type: "StringLiteral",  detail: "L1",                 fill: "#081520", stroke: "#0e7490", textColor: "#a5f3fc", children: [] },
  { id: "id-github",      label: '"../lib/github"',     type: "StringLiteral",  detail: "L3",                 fill: "#081520", stroke: "#0e7490", textColor: "#a5f3fc", children: [] },
  { id: "if-auth",        label: "IfStatement",         type: "IfStatement",    detail: "L15–22",             fill: "#1e1400", stroke: "#d97706", textColor: "#fde68a", children: ["call-dispatch","else-block"] },
  { id: "return-payload", label: "return payload",      type: "ReturnStatement",detail: "L45",                fill: "#0a1c1c", stroke: "#0d9488", textColor: "#99f6e4", children: [] },
  { id: "for-loop",       label: "for…of commits",      type: "ForOfStatement", detail: "L60–85",             fill: "#160f2e", stroke: "#7c3aed", textColor: "#c4b5fd", children: ["assign-delta","call-push"] },
  { id: "call-dispatch",  label: "dispatchAgent()",     type: "CallExpression", detail: "L18",                fill: "#0d200f", stroke: "#16a34a", textColor: "#86efac", children: [] },
  { id: "else-block",     label: "else { throw }",      type: "ThrowStatement", detail: "L20",                fill: "#200a0a", stroke: "#dc2626", textColor: "#fca5a5", children: [] },
  { id: "assign-delta",   label: "delta = Δcommit",     type: "AssignExpr",     detail: "L68",                fill: "#0c1520", stroke: "#2563eb", textColor: "#93c5fd", children: [] },
  { id: "call-push",      label: "results.push(delta)", type: "CallExpression", detail: "L72",                fill: "#0d200f", stroke: "#16a34a", textColor: "#86efac", children: [] },
];

const NODES: Record<string, AstNode> = Object.fromEntries(NODE_DEFS.map(n => [n.id, n]));
const EDGES = NODE_DEFS.flatMap(n => n.children.map(c => ({ from: n.id, to: c })));

/* ─── Initial BFS layout positions ──────────────────────────────────────── */

const NODE_W = 158;
const NODE_H = 56;
const H_GAP  = 50;
const V_GAP  = 100;

function bfsLayout(): Record<string, NodePos> {
  const levels: string[][] = [];
  const visited = new Set<string>();
  let queue = ["program"];
  while (queue.length) {
    levels.push([...queue]);
    queue.forEach(id => visited.add(id));
    const next: string[] = [];
    queue.forEach(id => NODES[id]?.children.forEach(c => { if (!visited.has(c)) next.push(c); }));
    queue = next;
  }
  const pos: Record<string, NodePos> = {};
  levels.forEach((row, li) => {
    const totalW = row.length * NODE_W + (row.length - 1) * H_GAP;
    let sx = 40 + (800 - totalW) / 2; // centre inside 800px canvas
    row.forEach(id => {
      pos[id] = { x: sx, y: 40 + li * (NODE_H + V_GAP) };
      sx += NODE_W + H_GAP;
    });
  });
  return pos;
}

/* ─── Animated dash CSS ──────────────────────────────────────────────────── */

const ANIM_CSS = `
@keyframes marchIdle {
  from { stroke-dashoffset: 28; }
  to   { stroke-dashoffset: 0;  }
}
@keyframes marchSel {
  from { stroke-dashoffset: 24; }
  to   { stroke-dashoffset: 0;  }
}
.ast-edge-idle {
  stroke-dasharray: 6 8;
  animation: marchIdle 1.6s linear infinite;
}
.ast-edge-sel {
  stroke-dasharray: 10 6;
  animation: marchSel 0.65s linear infinite;
}
`;

/* ─── Component ──────────────────────────────────────────────────────────── */

const CANVAS_W = 900;
const CANVAS_H = 540;

export default function AstGraphVisualizer() {
  const [positions, setPositions] = useState<Record<string, NodePos>>(bfsLayout);
  const [selected,  setSelected]  = useState<string | null>(null);
  const [search,    setSearch]    = useState("");

  // drag state (ref so no re-render on mousemove)
  const draggingNode = useRef<string | null>(null);
  const dragStart    = useRef<{ mx: number; my: number; nx: number; ny: number }>({ mx:0, my:0, nx:0, ny:0 });
  const svgRef       = useRef<SVGSVGElement>(null);

  // inject keyframe CSS once
  useEffect(() => {
    const el = document.createElement("style");
    el.innerHTML = ANIM_CSS;
    document.head.appendChild(el);
    return () => { document.head.removeChild(el); };
  }, []);

  /* convert screen → SVG coords */
  const svgPoint = useCallback((clientX: number, clientY: number) => {
    const svg = svgRef.current;
    if (!svg) return { x: clientX, y: clientY };
    const pt = svg.createSVGPoint();
    pt.x = clientX; pt.y = clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return { x: clientX, y: clientY };
    return pt.matrixTransform(ctm.inverse());
  }, []);

  /* node mousedown → start dragging that node */
  const onNodeMouseDown = useCallback((e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    e.preventDefault();
    const p = svgPoint(e.clientX, e.clientY);
    draggingNode.current = id;
    dragStart.current = {
      mx: p.x, my: p.y,
      nx: positions[id].x, ny: positions[id].y,
    };
    setSelected(id);
  }, [positions, svgPoint]);

  /* svg mousemove → update dragged node position */
  const onSvgMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (!draggingNode.current) return;
    const p = svgPoint(e.clientX, e.clientY);
    const dx = p.x - dragStart.current.mx;
    const dy = p.y - dragStart.current.my;
    const id = draggingNode.current;
    setPositions(prev => ({
      ...prev,
      [id]: {
        x: Math.max(0, Math.min(CANVAS_W - NODE_W, dragStart.current.nx + dx)),
        y: Math.max(0, Math.min(CANVAS_H - NODE_H, dragStart.current.ny + dy)),
      },
    }));
  }, [svgPoint]);

  const onSvgMouseUp = useCallback(() => {
    draggingNode.current = null;
  }, []);

  const isHighlighted = (id: string) =>
    search.length > 1 &&
    (NODES[id].label.toLowerCase().includes(search.toLowerCase()) ||
     NODES[id].type.toLowerCase().includes(search.toLowerCase()));

  /* edge anchor: bottom-centre of source, top-centre of target */
  const srcX = (id: string) => positions[id].x + NODE_W / 2;
  const srcY = (id: string) => positions[id].y + NODE_H;
  const dstX = (id: string) => positions[id].x + NODE_W / 2;
  const dstY = (id: string) => positions[id].y;

  const node = selected ? NODES[selected] : null;

  return (
    <div className="bg-[#13151b] border border-[#202430] rounded-2xl p-6 space-y-5">

      {/* ── Header ── */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-[#1f2432] pb-4">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <Network className="w-5 h-5 text-cyan-400" />
            <h3 className="text-xl font-bold text-white font-poppins tracking-tight">
              Abstract Syntax Tree — Node Graph
            </h3>
          </div>
          <p className="text-xs text-zinc-400 flex items-center space-x-1.5">
            <Move className="w-3.5 h-3.5 text-purple-400" />
            <span>
              <span className="text-purple-300">Drag any node</span> to reposition it · click to inspect · edges follow in real-time
            </span>
          </p>
        </div>
        <div className="relative w-full md:w-64">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search node or type…"
            className="w-full bg-[#181b24] border border-[#272c3d] focus:border-cyan-500 text-white placeholder-zinc-500 pl-9 pr-3 py-2 rounded-xl text-xs font-mono outline-none transition-colors"
          />
        </div>
      </div>

      {/* ── Metrics ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
        {[
          { label: "TOTAL NODES", val: NODE_DEFS.length,    color: "text-cyan-400" },
          { label: "TOTAL EDGES", val: EDGES.length,        color: "text-purple-400" },
          { label: "TREE DEPTH",  val: "4 Levels",          color: "text-emerald-400" },
          { label: "COMPLEXITY",  val: "O(n log n)",        color: "text-amber-400" },
        ].map(m => (
          <div key={m.label} className="bg-[#0f1117] border border-[#202430] p-3 rounded-xl">
            <span className="text-zinc-500 text-[10px] block uppercase mb-0.5">{m.label}</span>
            <span className={`text-lg font-bold ${m.color}`}>{m.val}</span>
          </div>
        ))}
      </div>

      {/* ── Canvas + Inspector ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">

        {/* SVG Canvas */}
        <div className="lg:col-span-8 bg-[#08090d] border border-[#1c2030] rounded-xl overflow-auto scrollbar-purple">
          {/* top label */}
          <div className="text-[10px] font-mono text-zinc-600 uppercase px-4 pt-3 pb-1 flex items-center justify-between">
            <span>AST NODE GRAPH — drag nodes to reposition</span>
            <span className="flex items-center space-x-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse" />
              <span>DUMMY · FUTURE: LIVE PARSE</span>
            </span>
          </div>

          <svg
            ref={svgRef}
            width={CANVAS_W}
            height={CANVAS_H}
            viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
            style={{ display: "block", cursor: draggingNode.current ? "grabbing" : "default" }}
            onMouseMove={onSvgMouseMove}
            onMouseUp={onSvgMouseUp}
            onMouseLeave={onSvgMouseUp}
          >
            <defs>
              {/* subtle grid dots */}
              <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
                <circle cx="1" cy="1" r="0.8" fill="#1e2438" />
              </pattern>

              {/* arrowheads */}
              <marker id="arr-idle" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">
                <path d="M0,0 L0,6 L8,3 z" fill="#374151" />
              </marker>
              <marker id="arr-sel" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">
                <path d="M0,0 L0,6 L8,3 z" fill="#a78bfa" />
              </marker>

              {/* glow filters */}
              <filter id="edge-glow" x="-40%" y="-40%" width="180%" height="180%">
                <feGaussianBlur stdDeviation="3" result="blur"/>
                <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
              </filter>
              <filter id="node-glow" x="-25%" y="-25%" width="150%" height="150%">
                <feGaussianBlur stdDeviation="5" result="blur"/>
                <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
              </filter>
            </defs>

            {/* canvas dot-grid background */}
            <rect width={CANVAS_W} height={CANVAS_H} fill="url(#grid)" />

            {/* ── Edges (drawn under nodes) ── */}
            {EDGES.map(({ from, to }) => {
              const x1 = srcX(from), y1 = srcY(from);
              const x2 = dstX(to),   y2 = dstY(to);
              const my = (y1 + y2) / 2;
              const isSel = selected === from || selected === to;
              return (
                <path
                  key={`${from}-${to}`}
                  className={isSel ? "ast-edge-sel" : "ast-edge-idle"}
                  d={`M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`}
                  fill="none"
                  stroke={isSel ? "#8b5cf6" : "#2a3044"}
                  strokeWidth={isSel ? 2.5 : 1.5}
                  markerEnd={isSel ? "url(#arr-sel)" : "url(#arr-idle)"}
                  filter={isSel ? "url(#edge-glow)" : undefined}
                  style={{ pointerEvents: "none" }}
                />
              );
            })}

            {/* ── Nodes (drawn on top) ── */}
            {NODE_DEFS.map(n => {
              const { x, y } = positions[n.id];
              const isSel  = selected === n.id;
              const isDrag = draggingNode.current === n.id;
              const isHi   = isHighlighted(n.id);

              return (
                <g
                  key={n.id}
                  transform={`translate(${x},${y})`}
                  onMouseDown={e => onNodeMouseDown(e, n.id)}
                  onClick={e => { e.stopPropagation(); if (!isDrag) setSelected(isSel ? null : n.id); }}
                  style={{ cursor: isDrag ? "grabbing" : "grab" }}
                >
                  {/* aura */}
                  {(isSel || isHi || isDrag) && (
                    <rect
                      x={-6} y={-6} width={NODE_W + 12} height={NODE_H + 12}
                      rx={16} fill="none"
                      stroke={isHi ? "#22c55e" : n.stroke}
                      strokeWidth={2.5}
                      opacity={isDrag ? 0.7 : 0.45}
                      filter="url(#node-glow)"
                    />
                  )}

                  {/* body */}
                  <rect
                    x={0} y={0} width={NODE_W} height={NODE_H} rx={11}
                    fill={n.fill}
                    stroke={isSel || isDrag ? n.stroke : isHi ? "#22c55e" : "#1e2435"}
                    strokeWidth={isSel || isDrag ? 2.2 : 1.5}
                    style={{ filter: isDrag ? "drop-shadow(0 8px 24px rgba(0,0,0,0.6))" : undefined }}
                  />

                  {/* left accent bar */}
                  <rect x={0} y={0} width={4} height={NODE_H} rx={2} fill={n.stroke} opacity={0.9} />

                  {/* type */}
                  <text x={14} y={18} fontSize={8} fontFamily="monospace"
                    fill={n.textColor} opacity={0.8} fontWeight="700" letterSpacing="0.8">
                    {n.type.toUpperCase()}
                  </text>

                  {/* label */}
                  <text x={14} y={34} fontSize={11.5} fontFamily="monospace"
                    fill="#ffffff" fontWeight="bold" style={{ userSelect: "none" }}>
                    {n.label.length > 17 ? n.label.slice(0, 16) + "…" : n.label}
                  </text>

                  {/* detail */}
                  <text x={14} y={48} fontSize={8} fontFamily="monospace" fill="#3f4760"
                    style={{ userSelect: "none" }}>
                    {n.detail}
                  </text>

                  {/* drag handle icon (top-right) */}
                  <text x={NODE_W - 16} y={14} fontSize={9} fontFamily="monospace" fill="#3f4760">
                    ⠿
                  </text>

                  {/* child count badge */}
                  {n.children.length > 0 && (
                    <g transform={`translate(${NODE_W - 24}, 32)`}>
                      <rect x={0} y={0} width={18} height={14} rx={5} fill={n.stroke} opacity={0.2} />
                      <text x={9} y={10} fontSize={8} fontFamily="monospace"
                        fill={n.textColor} textAnchor="middle" fontWeight="bold">
                        {n.children.length}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
          </svg>
        </div>

        {/* ── Inspector ── */}
        <div className="lg:col-span-4 bg-[#0f1117] border border-[#1c2030] rounded-xl p-5 flex flex-col space-y-4">
          <div className="flex items-center justify-between border-b border-[#1e2435] pb-3">
            <span className="text-xs font-mono text-cyan-400 font-semibold flex items-center space-x-1.5">
              <Cpu className="w-4 h-4" />
              <span>NODE INSPECTOR</span>
            </span>
            {node && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded border"
                style={{ background: node.fill, color: node.textColor, borderColor: node.stroke }}>
                {node.type}
              </span>
            )}
          </div>

          {node ? (
            <div className="space-y-3 text-xs font-mono flex-1">
              <div>
                <span className="text-zinc-500 text-[10px] uppercase block mb-1">Identifier</span>
                <span className="text-sm font-bold px-3 py-1.5 rounded-lg border inline-block"
                  style={{ background: node.fill, color: "#fff", borderColor: node.stroke }}>
                  {node.label}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <span className="text-zinc-500 text-[10px] uppercase block">Node ID</span>
                  <span className="text-cyan-400">{node.id}</span>
                </div>
                <div>
                  <span className="text-zinc-500 text-[10px] uppercase block">Children</span>
                  <span className="text-white font-bold">{node.children.length}</span>
                </div>
                <div>
                  <span className="text-zinc-500 text-[10px] uppercase block">Position</span>
                  <span className="text-zinc-300">
                    ({Math.round(positions[node.id].x)}, {Math.round(positions[node.id].y)})
                  </span>
                </div>
                <div>
                  <span className="text-zinc-500 text-[10px] uppercase block">Hash</span>
                  <span className="text-emerald-400">
                    0x{node.id.split("").reduce((a, c) => a + c.charCodeAt(0), 0).toString(16).padStart(8, "0")}
                  </span>
                </div>
              </div>

              {node.children.length > 0 && (
                <div>
                  <span className="text-zinc-500 text-[10px] uppercase block mb-1.5">Outgoing Edges →</span>
                  <div className="space-y-1.5">
                    {node.children.map(c => (
                      <button key={c} onClick={() => setSelected(c)}
                        className="w-full flex items-center justify-between bg-[#13151b] border border-[#202430] hover:border-purple-500/50 px-3 py-1.5 rounded-lg transition-colors">
                        <span className="flex items-center space-x-2">
                          <GitBranch className="w-3 h-3 text-purple-400" />
                          <span className="text-zinc-300">{NODES[c]?.label || c}</span>
                        </span>
                        <span className="text-[9px] text-zinc-500">{NODES[c]?.type}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-[#13151b] border border-[#272c3d] rounded-xl p-3 flex items-start space-x-2">
                <Zap className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
                <p className="text-[10px] text-zinc-400 leading-relaxed">
                  <span className="text-white font-semibold">AST Search:</span>{" "}
                  Future queries will use ASST traversal (BFS/DFS hybrid) on live-parsed code.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center space-y-3 py-6">
              <div className="w-12 h-12 rounded-2xl bg-[#13151b] border border-[#272c3d] flex items-center justify-center">
                <Code2 className="w-6 h-6 text-zinc-600" />
              </div>
              <div>
                <p className="text-zinc-400 text-sm font-medium font-poppins">No node selected</p>
                <p className="text-zinc-600 text-xs mt-1 font-mono">
                  Drag any node to move it · click to inspect
                </p>
              </div>
              <div className="flex flex-wrap gap-1.5 justify-center mt-1">
                {["FunctionDecl","IfStatement","ForOfStatement","CallExpression"].map(t => (
                  <span key={t} className="text-[10px] font-mono bg-[#13151b] border border-[#202430] text-zinc-500 px-2 py-0.5 rounded">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Legend ── */}
      <div className="flex flex-wrap gap-x-5 gap-y-2 text-[11px] font-mono text-zinc-500 border-t border-[#1e2435] pt-3">
        {[
          { color: "#7c3aed", label: "Root / Program" },
          { color: "#059669", label: "FunctionDecl" },
          { color: "#0891b2", label: "Import / Literal" },
          { color: "#d97706", label: "IfStatement" },
          { color: "#dc2626", label: "ThrowStatement" },
          { color: "#2563eb", label: "AssignExpr" },
        ].map(l => (
          <span key={l.label} className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm inline-block border"
              style={{ background: l.color + "30", borderColor: l.color }} />
            <span>{l.label}</span>
          </span>
        ))}
        <span className="ml-auto flex items-center space-x-3 text-zinc-600">
          <span>─ ─ idle edge</span>
          <span className="text-purple-400">——— selected</span>
        </span>
      </div>
    </div>
  );
}
