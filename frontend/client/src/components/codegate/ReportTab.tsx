/**
 * Report tab — human-friendly leak cards (mirrors the CLI's friendly output).
 * Styled with Glassmorphism and glowing leak severity badges.
 */
import { AlertTriangle, ShieldCheck, Zap, Lightbulb } from "lucide-react";
import type { Leak } from "@/lib/codegate";

const KIND_LABEL: Record<Leak["kind"], { text: string; cls: string }> = {
  path: { text: "PATH LEAK", cls: "bg-rose-500/10 border-rose-500/30 text-rose-300 shadow-[0_0_10px_rgba(244,63,94,0.12)]" },
  exception: { text: "EXCEPTION LEAK", cls: "bg-amber-500/10 border-amber-500/30 text-amber-300 shadow-[0_0_10px_rgba(245,158,11,0.12)]" },
  "path+exception": { text: "PATH + EXCEPTION LEAK", cls: "bg-rose-500/15 border-rose-500/40 text-rose-200 shadow-[0_0_14px_rgba(244,63,94,0.18)]" },
};

function LeakCard({ lk }: { lk: Leak }) {
  return (
    <div className="rounded-xl border border-rose-500/20 bg-[#0d0f17]/70 backdrop-blur-xl p-4 space-y-3.5 shadow-[0_8px_32px_rgba(0,0,0,0.4)] hover:border-rose-500/40 transition-all">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`px-2.5 py-0.5 rounded-full border text-[10px] font-mono font-bold tracking-wide ${KIND_LABEL[lk.kind].cls}`}>
          {KIND_LABEL[lk.kind].text}
        </span>
        <span className="text-xs font-mono text-zinc-400">
          {lk.file || "input"}:<span className="text-zinc-100 font-semibold">{lk.acquire_line}</span>
        </span>
        <span className="text-xs text-zinc-400 font-mono">in <span className="text-zinc-100">{lk.func}()</span></span>
      </div>

      <p className="text-xs sm:text-sm text-zinc-200 leading-relaxed font-sans">
        <span className="font-mono text-zinc-100 font-semibold">'{lk.var}'</span>
        {" = "}
        <span className="font-mono text-zinc-100 font-semibold">{lk.acquire}(...)</span>
        {" — not guaranteed to be "}
        <span className="font-mono text-zinc-100 font-semibold">{lk.release}()</span>
        {"'d"}
      </p>

      {lk.path_sources && lk.path_sources.length > 0 && (
        <div className="rounded-lg bg-black/50 border border-rose-500/20 p-3 space-y-1.5 backdrop-blur-md">
          <p className="text-[10px] font-mono text-rose-400 tracking-wider font-bold flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse" />
            LEAKING PATH — RESOURCE NEVER CLOSED
          </p>
          <p className="text-xs font-mono text-zinc-300 break-all leading-relaxed">
            {lk.path_sources[0].map((s, i) => (
              <span key={i}>
                {i > 0 && <span className="text-zinc-600 font-bold"> → </span>}
                <span className="text-zinc-200">{s}</span>
              </span>
            ))}
          </p>
        </div>
      )}
      {lk.safe_path_sources && lk.safe_path_sources.length > 0 && (
        <div className="rounded-lg bg-black/40 border border-emerald-500/20 p-3 space-y-1.5 backdrop-blur-md">
          <p className="text-[10px] font-mono text-emerald-400 tracking-wider font-bold">
            ✓ SAFE PATH (CONTRAST)
          </p>
          <p className="text-xs font-mono text-zinc-400 break-all leading-relaxed">
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
        <p className="flex items-start gap-2 text-xs text-amber-300 font-sans bg-amber-500/10 border border-amber-500/20 p-2.5 rounded-lg">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-400" />
          {lk.exception_note}
        </p>
      )}

      <div className="flex items-start gap-2 text-xs text-zinc-300 font-sans bg-emerald-500/10 border border-emerald-500/20 p-2.5 rounded-lg">
        <Lightbulb className="w-4 h-4 mt-0.5 shrink-0 text-emerald-400" />
        <span className="leading-relaxed">
          Fix with{" "}
          <code className="px-1.5 py-0.5 rounded bg-black/60 border border-emerald-400/30 font-mono text-[11px] text-emerald-300">
            with {lk.acquire}(...) as {lk.var}:
          </code>{" "}
          or wrap in try/finally with{" "}
          <code className="px-1.5 py-0.5 rounded bg-black/60 border border-emerald-400/30 font-mono text-[11px] text-emerald-300">
            {lk.var}.{lk.release}()
          </code>
        </span>
      </div>
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
      <div className="flex flex-col items-center justify-center py-16 gap-4 rounded-xl border border-emerald-500/30 bg-[#070b0e]/70 backdrop-blur-xl shadow-xl text-center px-4">
        <div className="w-14 h-14 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center shadow-[0_0_20px_rgba(16,185,129,0.2)]">
          <ShieldCheck className="w-8 h-8 text-emerald-400" />
        </div>
        <div className="space-y-1">
          <p className="text-sm font-bold text-white">No Resource Leaks Detected</p>
          <p className="text-xs text-zinc-400 max-w-sm">Every acquire call is safely closed on all control paths — and exception-safe.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 px-1">
        <Zap className="w-4 h-4 text-red-400" />
        <p className="text-xs font-mono text-zinc-300">
          {leaks.length} leak{leaks.length > 1 ? "s" : ""} detected in <span className="text-white font-bold">{filename}</span>
        </p>
      </div>
      {leaks.map((lk, i) => (
        <LeakCard key={i} lk={lk} />
      ))}
      {fix?.applied && fix.diff && (
        <div className="rounded-xl border border-emerald-500/35 bg-[#080d0b]/80 backdrop-blur-xl p-4 space-y-2.5 shadow-xl">
          <p className="text-[10px] font-mono text-emerald-400 tracking-wider font-bold flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            AUTOFIX PREVIEW (COMMENTS & FORMATTING PRESERVED)
          </p>
          <pre className="text-xs font-mono text-zinc-200 bg-black/60 p-3.5 rounded-lg border border-white/[0.08] whitespace-pre-wrap overflow-x-auto custom-scrollbar">{fix.diff}</pre>
        </div>
      )}
    </div>
  );
}

