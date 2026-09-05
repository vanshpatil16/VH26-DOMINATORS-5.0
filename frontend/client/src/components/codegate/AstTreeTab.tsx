/**
 * AST tab — renders the real Abstract Syntax Tree produced by the backend
 * as an interactive collapsible tree (fed by /api analysis JSON).
 */
import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Hash, Search } from "lucide-react";
import type { AstNode } from "@/lib/codegate";

const TYPE_COLORS: Record<string, string> = {
  Module: "text-purple-300",
  FunctionDef: "text-emerald-300",
  AsyncFunctionDef: "text-emerald-300",
  ClassDef: "text-fuchsia-300",
  If: "text-amber-300",
  For: "text-violet-300",
  While: "text-violet-300",
  With: "text-cyan-300",
  Try: "text-orange-300",
  Match: "text-blue-300",
  Return: "text-rose-300",
  Assign: "text-sky-300",
  Call: "text-green-300",
  Name: "text-zinc-300",
  Constant: "text-yellow-200",
};

function typeColor(t: string): string {
  return TYPE_COLORS[t] ?? "text-zinc-400";
}

function TreeNode({ node, depth, query, expanded, toggle }: {
  node: AstNode;
  depth: number;
  query: string;
  expanded: Set<string>;
  toggle: (id: string) => void;
}) {
  const hasKids = node.children.length > 0;
  const isOpen = expanded.has(node.id);
  const matches = query.length > 1 &&
    (node.label.toLowerCase().includes(query) || node.type.toLowerCase().includes(query));

  const highlight = matches
    ? "bg-purple-500/20 border border-purple-500/40"
    : "border border-transparent";

  return (
    <div style={{ paddingLeft: depth === 0 ? 0 : 16 }}>
      <div className={`inline-flex items-center gap-1.5 rounded px-1.5 py-0.5 my-px ${highlight}`}>
        {hasKids ? (
          <button onClick={() => toggle(node.id)} className="text-zinc-500 hover:text-white transition-colors">
            {isOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          </button>
        ) : (
          <span className="w-3" />
        )}
        <span className={`text-[11px] font-mono font-medium ${typeColor(node.type)}`}>{node.type}</span>
        {node.label !== node.type && (
          <span className="text-[11px] font-mono text-zinc-400">{node.label}</span>
        )}
        {node.line != null && (
          <span className="inline-flex items-center gap-0.5 text-[9px] font-mono text-zinc-600">
            <Hash className="w-2.5 h-2.5" />
            {node.line}
          </span>
        )}
        {hasKids && (
          <span className="text-[9px] font-mono text-zinc-700">{node.children.length}</span>
        )}
      </div>
      {hasKids && isOpen && (
        <div className="border-l border-[#1c1f28] ml-2">
          {node.children.map((c) => (
            <TreeNode key={c.id} node={c} depth={depth + 1} query={query} expanded={expanded} toggle={toggle} />
          ))}
        </div>
      )}
      {hasKids && !isOpen && (
        <span className="ml-2 text-[10px] font-mono text-zinc-700">…</span>
      )}
    </div>
  );
}

function collectIds(node: AstNode, ids: string[], maxDepth: number, depth = 0): void {
  ids.push(node.id);
  if (depth < maxDepth) node.children.forEach((c) => collectIds(c, ids, maxDepth, depth + 1));
}

export default function AstTreeTab({ ast }: { ast: AstNode | null }) {
  // default: expand first 2 levels
  const initial = useMemo(() => {
    const ids: string[] = [];
    if (ast) collectIds(ast, ids, 2);
    return new Set(ids);
  }, [ast]);
  const [expanded, setExpanded] = useState<Set<string>>(initial);
  const [query, setQuery] = useState("");

  if (!ast) {
    return <p className="text-xs text-zinc-500 p-6">Run an analysis to see the AST.</p>;
  }

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const countNodes = (n: AstNode): number => 1 + n.children.reduce((a, c) => a + countNodes(c), 0);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value.toLowerCase())}
            placeholder="Filter nodes…"
            className="w-full bg-[#0d0f14] border border-white/[0.08] rounded-md pl-8 pr-3 py-1.5 text-xs text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-indigo-500/50"
          />
        </div>
        <span className="text-[10px] font-mono text-zinc-500">{countNodes(ast)} nodes · click to expand</span>
      </div>
      <div className="rounded-md border border-white/[0.08] bg-[#0d0f14] p-4 overflow-x-auto max-h-[60vh] overflow-y-auto custom-scrollbar">
        <TreeNode node={ast} depth={0} query={query} expanded={expanded} toggle={toggle} />
      </div>
    </div>
  );
}
