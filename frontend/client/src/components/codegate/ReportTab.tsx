/**
 * Report tab — human-friendly leak cards (mirrors the CLI's friendly output).
 */
import { AlertTriangle, ShieldCheck, Zap, Lightbulb } from "lucide-react";
import type { Leak } from "@/lib/codegate";

const KIND_LABEL: Record<Leak["kind"], { text: string; cls: string }> = {
  path: { text: "PATH LEAK", cls: "bg-red-500/10 border-red-500/30 text-red-400" },
  exception: { text: "EXCEPTION LEAK", cls: "bg-orange-500/10 border-orange-500/30 text-orange-400" },
  "path+exception": { text: "PATH + EXCEPTION LEAK", cls: "bg-red-500/10 border-red-500/40 text-red-400" },
};

function LeakCard({ lk }: { lk: Leak }) {
  return (
    <div className="rounded-2xl border border-red-500/20 bg-[#0d0b0c] p-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`px-2 py-0.5 rounded-full border text-[10px] font-medium tracking-wide ${KIND_LABEL[lk.kind].cls}`}>
          {KIND_LABEL[lk.kind].text}
        </span>
        <span className="text-xs font-mono text-zinc-400">
          {lk.file || "input"}:<span className="text-zinc-200">{lk.acquire_line}</span>
        </span>
        <span className="text-[11px] text-zinc-500">in {lk.func}()</span>
      </div>

      <p className="text-sm text-zinc-200">
        <span className="font-mono text-amber-300">'{lk.var}'</span>
        {" = "}
        <span className="font-mono text-cyan-300">{lk.acquire}(...)</span>
        {" — not guaranteed to be "}
        <span className="font-mono text-emerald-300">{lk.release}()</span>
        {"'d"}
      </p>

      {lk.path_sources && lk.path_sources.length > 0 && (
        <div className="rounded-xl bg-[#0a0b0e] border border-[#1c1f28] p-3 space-y-1.5">
          <p className="text-[10px] font-mono text-red-400 tracking-widest">✗ LEAKING PATH — resource never closed</p>
          <p className="text-[11px] font-mono text-zinc-400 break-all">
            {lk.path_sources[0].map((s, i) => (
              <span key={i}>
                {i > 0 && <span className="text-zinc-600"> → </span>}
                {s}
              </span>
            ))}
          </p>
        </div>
      )}
      {lk.safe_path_sources && lk.safe_path_sources.length > 0 && (
        <div className="rounded-xl bg-[#0a0b0e] border border-[#1c1f28] p-3 space-y-1.5">
          <p className="text-[10px] font-mono text-emerald-400 tracking-widest">✓ SAFE PATH (for contrast)</p>
          <p className="text-[11px] font-mono text-zinc-500 break-all">
            {lk.safe_path_sources[0].map((s, i) => (
              <span key={i}>
                {i > 0 && <span className="text-zinc-700"> → </span>}
                {s}
              </span>
            ))}
          </p>
        </div>
      )}

      {lk.exception_note && (
        <p className="flex items-start gap-2 text-xs text-amber-300/90">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
          {lk.exception_note}
        </p>
      )}

      <p className="flex items-start gap-2 text-xs text-zinc-300">
        <Lightbulb className="w-3.5 h-3.5 mt-0.5 shrink-0 text-emerald-400" />
        <span>
          Fix with{" "}
          <code className="px-1 py-0.5 rounded bg-[#0a0b0e] border border-[#1c1f28] font-mono text-[11px] text-emerald-300">
            with {lk.acquire}(...) as {lk.var}:
          </code>{" "}
          or wrap in try/finally with{" "}
          <code className="px-1 py-0.5 rounded bg-[#0a0b0e] border border-[#1c1f28] font-mono text-[11px] text-emerald-300">
            {lk.var}.{lk.release}()
          </code>
        </span>
      </p>
    </div>
  );
}

export default function ReportTab({ leaks, fix, filename }: {
  leaks: Leak[];
  fix?: { applied: boolean; code?: string; diff?: string; reason?: string };
  filename: string;
}) {
  if (!leaks.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3">
        <ShieldCheck className="w-10 h-10 text-emerald-400" />
        <p className="text-sm font-medium text-zinc-200">No resource leaks detected</p>
        <p className="text-xs text-zinc-500">Every acquire is closed on all reachable paths — and safely on exceptions.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Zap className="w-4 h-4 text-red-400" />
        <p className="text-sm font-medium text-zinc-100">
          {leaks.length} leak{leaks.length > 1 ? "s" : ""} found in {filename}
        </p>
      </div>
      {leaks.map((lk, i) => (
        <LeakCard key={i} lk={lk} />
      ))}
      {fix?.applied && fix.diff && (
        <div className="rounded-2xl border border-emerald-500/20 bg-[#0a0f0c] p-4">
          <p className="text-[10px] font-mono text-emerald-400 tracking-widest mb-2">💡 AUTOFIX PREVIEW (comments & formatting preserved)</p>
          <pre className="text-[11px] font-mono text-zinc-300 whitespace-pre-wrap overflow-x-auto">{fix.diff}</pre>
        </div>
      )}
    </div>
  );
}
