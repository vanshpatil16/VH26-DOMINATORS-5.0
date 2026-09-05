import { useState } from "react";
import {
  BookOpen, ShieldCheck, Cpu, Search,
  CheckCircle2, AlertTriangle, Sparkles, Brain,
  ChevronDown, ChevronRight, ExternalLink, Info, Zap, WifiOff
} from "lucide-react";
import type { KnowledgeBaseInfo, KnowledgeBaseContract } from "@/lib/codegate";

const RESOURCE_TYPES = ["ALL", "FILE", "SOCKET", "DATABASE", "LOCK", "TEMP_FILE", "HTTP"];

const BEHAVIOR_STYLE: Record<string, { color: string; bg: string; border: string }> = {
  CLOSES_INPUT:        { color: "text-emerald-300",  bg: "bg-emerald-500/10",  border: "border-emerald-500/30" },
  PRESERVES_INPUT:     { color: "text-blue-300",     bg: "bg-blue-500/10",     border: "border-blue-500/30"    },
  CREATES_RESOURCE:    { color: "text-indigo-300",   bg: "bg-indigo-500/10",   border: "border-indigo-500/30"  },
  RETURNS_RESOURCE:    { color: "text-indigo-300",   bg: "bg-indigo-500/10",   border: "border-indigo-500/30"  },
  TRANSFERS_OWNERSHIP: { color: "text-amber-300",    bg: "bg-amber-500/10",    border: "border-amber-500/30"   },
  CONDITIONAL_CLOSE:   { color: "text-orange-300",   bg: "bg-orange-500/10",   border: "border-orange-500/30"  },
  UNKNOWN:             { color: "text-zinc-400",     bg: "bg-zinc-500/10",     border: "border-zinc-500/30"    },
};

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 90 ? "bg-emerald-500" : pct >= 75 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2 min-w-0">
      <div className="flex-1 h-1 bg-white/[0.07] rounded-full overflow-hidden">
        <div className={`h-1 ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-[10px] font-mono font-semibold shrink-0 ${pct >= 90 ? "text-emerald-400" : pct >= 75 ? "text-amber-400" : "text-red-400"}`}>
        {pct}%
      </span>
    </div>
  );
}

function LLMContractCard({ contract }: { contract: KnowledgeBaseContract }) {
  const [open, setOpen] = useState(false);
  const bhv = BEHAVIOR_STYLE[contract.behavior] ?? BEHAVIOR_STYLE.UNKNOWN;
  return (
    <div className="rounded-md border border-indigo-500/25 bg-[#0d0f14] overflow-hidden shadow-sm">
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-start justify-between gap-3 p-3.5 text-left hover:bg-white/[0.02] transition-colors">
        <div className="flex-1 min-w-0 space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 text-[10px] font-mono font-semibold">
              <Brain className="w-2.5 h-2.5" /> LLM
            </span>
            <code className="text-indigo-300 text-xs font-mono font-bold">{contract.call}(…)</code>
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold ${bhv.color} ${bhv.bg} border ${bhv.border}`}>
              {contract.behavior}
            </span>
            <span className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-zinc-400 text-[10px] font-mono">
              {contract.resource_type}
            </span>
          </div>
          <ConfidenceBar value={contract.confidence} />
        </div>
        <div className="shrink-0 text-zinc-500 mt-1">
          {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </div>
      </button>
      {open && (
        <div className="border-t border-white/[0.06] p-3.5 space-y-3 text-xs font-mono">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-zinc-500">Exception Safety:</span>
            <span className={`px-1.5 py-0.5 rounded font-semibold text-[10px] ${contract.exception_safety === "GUARANTEED" ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30" : "bg-amber-500/15 text-amber-300 border border-amber-500/30"}`}>
              {contract.exception_safety}
            </span>
            <span className="text-zinc-700">·</span>
            <span className="text-zinc-500">Ownership:</span>
            <span className="px-1.5 py-0.5 rounded text-[10px] bg-white/5 border border-white/10 text-zinc-300">{contract.ownership}</span>
          </div>
          {contract.evidence && (
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-[10px] text-zinc-500 uppercase tracking-wider"><ExternalLink className="w-3 h-3" /> Evidence</div>
              <p className="text-zinc-300 leading-relaxed">{contract.evidence}</p>
            </div>
          )}
          {contract.reason && (
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-[10px] text-zinc-500 uppercase tracking-wider"><Info className="w-3 h-3" /> Reasoning</div>
              <p className="text-zinc-400 leading-relaxed whitespace-pre-wrap">{contract.reason}</p>
            </div>
          )}
          {contract.source && (
            <div className="flex items-center gap-2 pt-1 border-t border-white/[0.04] text-[10px] text-zinc-500">
              <span>Source:</span><span className="text-zinc-400">{contract.source}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function KnowledgeBaseTab({ kb }: { kb?: KnowledgeBaseInfo | null }) {
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const rules = kb?.rules ?? [
    { call: "open",                         type: "FILE",      close: ["close"],             weight: 1.0 },
    { call: "builtins.open",               type: "FILE",      close: ["close"],             weight: 1.0 },
    { call: "socket.socket",               type: "SOCKET",    close: ["close","shutdown"],  weight: 1.0 },
    { call: "sqlite3.connect",             type: "DATABASE",  close: ["close"],             weight: 1.0 },
    { call: "requests.Session",            type: "HTTP",      close: ["close"],             weight: 1.0 },
    { call: "threading.Lock.acquire",      type: "LOCK",      close: ["release"],           weight: 1.0 },
    { call: "tempfile.NamedTemporaryFile", type: "TEMP_FILE", close: ["close"],             weight: 1.0 },
  ];

  const matched       = kb?.matched       ?? [];
  const llmDiscovered = kb?.llmDiscovered ?? [];
  const llmAvailable  = kb?.llmAvailable  ?? false;
  const llmProvider   = kb?.llmProvider   ?? "none";
  const llmModel      = kb?.llmModel      ?? "";

  const filteredRules = rules.filter(r => {
    const cat   = selectedType === "ALL" || r.type?.toUpperCase().includes(selectedType);
    const query = searchQuery === "" || r.call.toLowerCase().includes(searchQuery.toLowerCase()) || r.type?.toLowerCase().includes(searchQuery.toLowerCase());
    return cat && query;
  });

  return (
    <div className="space-y-4 text-zinc-100 font-sans">

      {/* LLM Status Banner */}
      <div className={`flex items-center gap-3 px-3.5 py-2.5 rounded-md border text-xs font-mono ${llmAvailable ? "bg-indigo-500/10 border-indigo-500/25 text-indigo-300" : "bg-zinc-800/50 border-white/[0.08] text-zinc-500"}`}>
        {llmAvailable ? (
          <>
            <Brain className="w-4 h-4 shrink-0 text-indigo-400" />
            <span className="font-semibold text-indigo-200">LLM Resolver Active</span>
            <span className="text-zinc-500">·</span>
            <span className="capitalize">{llmProvider}</span>
            {llmModel && <><span className="text-zinc-600">·</span><code className="text-indigo-400">{llmModel}</code></>}
            <span className="ml-auto text-[10px] text-indigo-400 flex items-center gap-1 shrink-0">
              <Zap className="w-3 h-3" /> Auto-discovers unknown libraries
            </span>
          </>
        ) : (
          <>
            <WifiOff className="w-4 h-4 shrink-0" />
            <span>LLM Resolver offline — set <code className="px-1 py-0.5 bg-white/5 rounded">GEMINI_API_KEY</code>, <code className="px-1 py-0.5 bg-white/5 rounded">GROQ_API_KEY</code>, or <code className="px-1 py-0.5 bg-white/5 rounded">LLM_API_KEY</code> to enable auto-discovery</span>
          </>
        )}
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "TRACKED RULES",  val: kb?.rulesCount ?? rules.length, sub: "From resources.yaml",       icon: <BookOpen className="w-3.5 h-3.5 text-indigo-400" />,  valCls: "text-white" },
          { label: "API CONTRACTS",  val: kb?.contractsCount ?? 0,        sub: "Exception safety specs",    icon: <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />, valCls: "text-white" },
          { label: "MATCHED IN FILE",val: matched.length,                 sub: "Acquires in snippet",       icon: <Cpu className="w-3.5 h-3.5 text-cyan-400" />,         valCls: "text-white" },
          { label: "LLM DISCOVERED", val: llmDiscovered.length,           sub: "New this scan",             icon: <Brain className="w-3.5 h-3.5 text-indigo-400" />,     valCls: "text-indigo-300" },
        ].map(({ label, val, sub, icon, valCls }) => (
          <div key={label} className="bg-[#0d0f14] border border-white/[0.08] p-3.5 rounded-md space-y-1">
            <div className="flex items-center justify-between text-xs text-zinc-400 font-mono"><span>{label}</span>{icon}</div>
            <p className={`text-xl font-bold font-mono ${valCls}`}>{val}</p>
            <p className="text-[10px] text-zinc-500 font-mono">{sub}</p>
          </div>
        ))}
      </div>

      {/* LLM-Discovered Contracts */}
      {llmDiscovered.length > 0 ? (
        <div className="space-y-2.5">
          <div className="flex items-center gap-2 px-0.5">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <h3 className="text-xs font-semibold text-white tracking-tight">LLM-Discovered Contracts</h3>
            <span className="text-[10px] font-mono text-zinc-500">— resolved this scan &amp; persisted to resources.yaml</span>
          </div>
          {llmDiscovered.map((c, i) => <LLMContractCard key={`${c.library}.${c.function}-${i}`} contract={c} />)}
        </div>
      ) : llmAvailable ? (
        <div className="flex items-center gap-3 px-3.5 py-3 rounded-md border border-dashed border-white/[0.06] bg-[#0d0f14]/50 text-xs text-zinc-500 font-mono">
          <Brain className="w-4 h-4 text-zinc-600 shrink-0" />
          <span>No unknown external libraries in this snippet — LLM resolver was not triggered.</span>
        </div>
      ) : null}

      {/* Matched Acquires */}
      {matched.length > 0 && (
        <div className="bg-[#0d0f14] border border-emerald-500/20 rounded-md p-3.5 space-y-2.5">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-semibold text-white tracking-tight">KB Contracts Matched in This File</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {matched.map((m, i) => (
              <div key={i} className="bg-[#13161f] border border-white/[0.06] p-3 rounded-md space-y-2 text-xs font-mono">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-indigo-300 font-bold truncate">{m.acquire}(…)</span>
                  <div className="flex items-center gap-1 shrink-0">
                    {m.discovered_by === "llm" && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 text-[10px] font-semibold">
                        <Brain className="w-2.5 h-2.5" /> LLM
                      </span>
                    )}
                    <span className="px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-[10px]">{m.resource_type}</span>
                  </div>
                </div>
                <div className="flex items-center justify-between text-zinc-400 text-[11px]">
                  <span>Bound: <code className="text-amber-300">{m.var}</code> (L{m.line})</span>
                  <span>Release: <code className="text-emerald-300">{m.release}()</code></span>
                </div>
                <div className="flex items-center gap-2 pt-1 border-t border-white/[0.04] text-[10px]">
                  <span className="text-zinc-500">Exception Safety:</span>
                  <span className={`px-1.5 py-0.5 rounded font-semibold ${m.exception_safety === "GUARANTEED" ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30" : "bg-amber-500/15 text-amber-300 border border-amber-500/30"}`}>
                    {m.exception_safety}
                  </span>
                  {m.confidence !== undefined && (
                    <><span className="text-zinc-700 ml-auto">Confidence:</span><span className="text-zinc-400">{Math.round(m.confidence * 100)}%</span></>
                  )}
                </div>
                {m.evidence && <p className="text-[10px] text-zinc-500 border-t border-white/[0.04] pt-1.5 leading-relaxed">{m.evidence}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filter & Search */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#0d0f14] border border-white/[0.08] p-3 rounded-md">
        <div className="flex items-center gap-1.5 overflow-x-auto custom-scrollbar">
          {RESOURCE_TYPES.map(t => (
            <button key={t} onClick={() => setSelectedType(t)}
              className={`px-2.5 py-1 rounded text-xs font-mono transition-all whitespace-nowrap ${selectedType === t ? "bg-indigo-600 text-white font-semibold" : "bg-[#13161f] text-zinc-400 hover:text-white hover:bg-white/10"}`}>
              {t}
            </button>
          ))}
        </div>
        <div className="relative w-full sm:w-56 shrink-0">
          <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search KB rules…"
            className="w-full bg-[#13161f] border border-white/[0.08] focus:border-indigo-500 text-white placeholder-zinc-500 pl-8 pr-3 py-1 rounded text-xs font-mono outline-none transition-colors" />
        </div>
      </div>

      {/* Rules Registry Table */}
      <div className="bg-[#0d0f14] border border-white/[0.08] rounded-md overflow-hidden">
        <div className="grid grid-cols-[1.5fr_1fr_1.5fr_0.6fr_0.6fr] gap-2 px-4 py-2 bg-[#13161f] border-b border-white/[0.06] text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-semibold">
          <span>ACQUIRE FUNCTION</span><span>CATEGORY</span><span>REQUIRED RELEASE API</span><span>WEIGHT</span><span>SOURCE</span>
        </div>
        <div className="divide-y divide-white/[0.04] max-h-[360px] overflow-y-auto custom-scrollbar">
          {filteredRules.map((r, idx) => (
            <div key={idx} className="grid grid-cols-[1.5fr_1fr_1.5fr_0.6fr_0.6fr] gap-2 px-4 py-2.5 items-center hover:bg-white/[0.02] text-xs font-mono">
              <span className="text-indigo-300 font-medium truncate">{r.call}</span>
              <span className="inline-flex w-fit px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-zinc-300 text-[10px]">{r.type}</span>
              <span className="text-emerald-300 truncate">{Array.isArray(r.close) ? r.close.join(" / ") : r.close}</span>
              <span className="text-zinc-500 text-[11px]">{r.weight ?? "1.0"}</span>
              <span className="text-zinc-600 text-[10px]">yaml</span>
            </div>
          ))}
          {filteredRules.length === 0 && (
            <div className="p-6 text-center text-xs font-mono text-zinc-500">No Knowledge Base rules match search filter.</div>
          )}
        </div>
      </div>

      {/* Backend error */}
      {kb?.error && (
        <div className="flex items-start gap-2 px-3 py-2.5 rounded-md border border-amber-500/30 bg-amber-500/10 text-xs font-mono text-amber-300">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>KB error: {kb.error}</span>
        </div>
      )}
    </div>
  );
}
