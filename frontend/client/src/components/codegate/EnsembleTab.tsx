/**
 * Ensemble tab — ruff pre-filter + CodeGate CFG verification.
 * Shows every raw linter finding with its final verdict:
 * confirmed (with path evidence), exception-unsafe (upgraded), or refuted (suppressed).
 */
import { CheckCircle2, ShieldAlert, ShieldCheck, HelpCircle, Scissors, Ruler } from "lucide-react";
import type { EnsembleResult } from "@/lib/codegate";

const VERDICT_STYLE: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
  confirmed_path_leak: {
    label: "CONFIRMED LEAK",
    cls: "bg-red-500/10 border-red-500/30 text-red-400",
    icon: <ShieldAlert className="w-3.5 h-3.5" />,
  },
  confirmed_exception_unsafe: {
    label: "EXCEPTION-UNSAFE",
    cls: "bg-amber-500/10 border-amber-500/30 text-amber-400",
    icon: <ShieldAlert className="w-3.5 h-3.5" />,
  },
  refuted_safe: {
    label: "REFUTED (safe)",
    cls: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
    icon: <ShieldCheck className="w-3.5 h-3.5" />,
  },
  unverified: {
    label: "UNVERIFIED",
    cls: "bg-zinc-500/10 border-zinc-500/30 text-zinc-400",
    icon: <HelpCircle className="w-3.5 h-3.5" />,
  },
};

function pathToString(p: unknown): string {
  if (Array.isArray(p)) return p.join(" → ");
  return String(p ?? "");
}

export default function EnsembleTab({ ensemble }: { ensemble: EnsembleResult }) {
  const { counts, verified, semgrep, ruff, syntacticPrefilter, noiseReductionPct } = ensemble;
  const total = verified.length;

  return (
    <div className="space-y-4">
      {/* summary chips */}
      <div className="flex flex-wrap items-center gap-2 px-1">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#0d0f14] border border-white/[0.08] text-[11px] font-mono text-zinc-400">
          <Ruler className="w-3.5 h-3.5 text-cyan-400" />
          pre-filters: semgrep {semgrep?.available ? semgrep.findings.length : "n/a"} ·
          ruff {ruff?.available ? ruff.findings.length : "n/a"} + syntactic {syntacticPrefilter?.findings ?? 0}
        </span>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-red-500/10 border border-red-500/30 text-[11px] font-mono text-red-400">
          {counts.confirmed_path_leak ?? 0} confirmed
        </span>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/30 text-[11px] font-mono text-amber-400">
          {counts.confirmed_exception_unsafe ?? 0} exception-unsafe
        </span>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/30 text-[11px] font-mono text-emerald-400">
          <Scissors className="w-3.5 h-3.5" />
          {counts.refuted_safe ?? 0} refuted
        </span>
        {total > 0 && (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-indigo-500/10 border border-indigo-500/30 text-[11px] font-mono text-indigo-300">
            noise −{noiseReductionPct}%
          </span>
        )}
      </div>

      {!ruff?.available && ruff?.note && (
        <p className="text-[11px] text-zinc-500 px-1 font-mono">ruff: {ruff.note}</p>
      )}

      {total === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2 text-center rounded-md border border-white/[0.08] bg-[#0d0f14]">
          <CheckCircle2 className="w-8 h-8 text-emerald-500" />
          <p className="text-sm font-semibold text-zinc-200">No linter findings to verify</p>
          <p className="text-xs text-zinc-400">Nothing acquired outside a context manager.</p>
        </div>
      ) : (
        <div className="rounded-md border border-white/[0.08] bg-[#0d0f14] overflow-hidden shadow-sm">
          <div className="grid grid-cols-[64px_120px_1fr] gap-2 px-4 py-2 border-b border-white/[0.06] bg-[#13161f] text-[10px] font-mono tracking-wider text-zinc-400 font-semibold">
            <span>LINE</span>
            <span>VERDICT</span>
            <span>FINDING + EVIDENCE</span>
          </div>
          <div className="divide-y divide-white/[0.04]">
            {verified.map((v, i) => {
              const style = VERDICT_STYLE[v.verdict] ?? VERDICT_STYLE.unverified;
              const ev = v.evidence ?? {};
              const leaking = pathToString(ev.leaking_path);
              const note = (ev.note as string) || (ev.exception_note as string) || "";
              return (
                <div key={i} className="grid grid-cols-[64px_120px_1fr] gap-2 px-4 py-3 items-start hover:bg-white/[0.02] transition-colors">
                  <span className="text-xs font-mono text-zinc-400">{v.line ?? "?"}</span>
                  <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[9px] font-mono tracking-wider w-fit ${style.cls}`}>
                    {style.icon} {style.label}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs text-zinc-200 font-medium">
                      <span className="text-zinc-500 font-mono text-[10px] mr-1.5">[{v.tool}:{v.rule}]</span>
                      {v.message}
                    </p>
                    {leaking && leaking !== "None" && (
                      <p className="text-xs font-mono text-red-400/90 mt-1 truncate" title={leaking}>
                        ✗ {leaking}
                      </p>
                    )}
                    {note && !leaking && (
                      <p className="text-xs text-zinc-400 mt-1">{note}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
