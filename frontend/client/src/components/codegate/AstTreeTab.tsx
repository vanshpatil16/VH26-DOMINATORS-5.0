/**
 * AST tab — renders the real Abstract Syntax Tree produced by the backend
 * as an interactive compact tree with subtle syntax color highlights.
 */
import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Hash, Search } from "lucide-react";
import type { AstNode } from "@/lib/codegate";

const TYPE_COLORS: Record<string, string> = {
  Module: "text-indigo-400 font-medium",
  FunctionDef: "text-cyan-400 font-semibold",
  AsyncFunctionDef: "text-teal-400 font-semibold",
  ClassDef: "text-purple-400 font-semibold",
  arguments: "text-zinc-400",
  arg: "text-zinc-300",
  If: "text-amber-400 font-medium",
  For: "text-amber-400 font-medium",
  While: "text-amber-400 font-medium",
  With: "text-amber-400 font-medium",
  Try: "text-orange-400 font-medium",
  Match: "text-amber-400 font-medium",
  Return: "text-rose-400 font-medium",
  Assign: "text-emerald-400",
  Call: "text-blue-400 font-medium",
  Attribute: "text-sky-400",
  Name: "text-violet-300 font-medium",
  Constant: "text-pink-400 font-mono",
  Str: "text-pink-300",
  Num: "text-emerald-300",
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
    ? "bg-yellow-500/10 border border-yellow-500/30 text-yellow-200"
    : "border border-transparent hover:bg-white/[0.04]";

  return (
    <div style={{ paddingLeft: depth === 0 ? 0 : 16 }}>
      <div className={`inline-flex items-center gap-1.5 rounded px-1.5 py-0.5 my-px transition-colors ${highlight}`}>
        {hasKids ? (
          <button onClick={() => toggle(node.id)} className="text-zinc-500 hover:text-white transition-colors">
            {isOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          </button>
        ) : (
          <span className="w-3" />
        )}
        <span className={`text-[11px] font-mono ${typeColor(node.type)}`}>{node.type}</span>
        {node.label !== node.type && (
          <span className="text-[11px] font-mono text-zinc-200">{node.label}</span>
        )}
        {node.line != null && (
          <span className="inline-flex items-center gap-0.5 text-[9px] font-mono text-zinc-500">
            <Hash className="w-2.5 h-2.5" />
            {node.line}
          </span>
        )}
        {hasKids && (
          <span className="text-[9px] font-mono text-zinc-600">{node.children.length}</span>
        )}
      </div>
      {hasKids && isOpen && (
        <div className="border-l border-white/[0.06] ml-2">
          {node.children.map((c) => (
            <TreeNode key={c.id} node={c} depth={depth + 1} query={query} expanded={expanded} toggle={toggle} />
          ))}
        </div>
      )}
      {hasKids && !isOpen && (
        <span className="ml-2 text-[10px] font-mono text-zinc-600">…</span>
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
    return <p className="text-xs text-zinc-500 p-6 font-sans">Run an analysis to see the AST.</p>;
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
    <div className="space-y-3 font-sans">
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value.toLowerCase())}
            placeholder="Filter nodes…"
            className="w-full bg-[#0d0f14]/80 border border-white/[0.08] rounded-md pl-8 pr-3 py-1 text-xs text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-white/30 font-mono"
          />
        </div>
        <span className="text-[10px] font-mono text-zinc-500">{countNodes(ast)} nodes · click to expand</span>
      </div>
      <div className="rounded-xl border border-white/10 bg-black/40 backdrop-blur-xl p-4 overflow-x-auto max-h-[60vh] overflow-y-auto custom-scrollbar">
        <TreeNode node={ast} depth={0} query={query} expanded={expanded} toggle={toggle} />
      </div>
    </div>
  );
}
