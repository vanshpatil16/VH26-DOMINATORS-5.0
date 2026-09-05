/**
 * Trajectory tab — DeepSeek-harness style execution trace.
 * Shows every backend stage: parse, desugar, CFG build, resource scan,
 * path analysis, exception pass, fix generation. Each step is expandable
 * to reveal the raw JSON payload the analyzer produced.
 */
import { useState } from "react";
import { ChevronDown, ChevronRight, CircleCheck, CircleAlert, CircleDashed, Timer, Terminal } from "lucide-react";
import type { TrajectoryStep } from "@/lib/codegate";

const PHASE_STYLE: Record<string, { color: string; bg: string; border: string; label: string }> = {
  parse: { color: "text-cyan-300", bg: "bg-cyan-500/10", border: "border-cyan-500/30", label: "PARSE" },
  desugar: { color: "text-blue-300", bg: "bg-blue-500/10", border: "border-blue-500/30", label: "DESUGAR" },
  cfg: { color: "text-purple-300", bg: "bg-purple-500/10", border: "border-purple-500/30", label: "CFG" },
  resources: { color: "text-amber-300", bg: "bg-amber-500/10", border: "border-amber-500/30", label: "RESOURCES" },
  paths: { color: "text-emerald-300", bg: "bg-emerald-500/10", border: "border-emerald-500/30", label: "PATHS" },
  exceptions: { color: "text-orange-300", bg: "bg-orange-500/10", border: "border-orange-500/30", label: "EXCEPTIONS" },
  fix: { color: "text-pink-300", bg: "bg-pink-500/10", border: "border-pink-500/30", label: "FIX" },
};

const STATUS_ICON: Record<string, React.ReactNode> = {
  ok: <CircleCheck className="w-4 h-4 text-emerald-400" />,
  warn: <CircleAlert className="w-4 h-4 text-amber-400" />,
  error: <CircleAlert className="w-4 h-4 text-red-400" />,
  skipped: <CircleDashed className="w-4 h-4 text-zinc-500" />,
};

function StepRow({ step, index, isLast }: { step: TrajectoryStep; index: number; isLast: boolean }) {
  const [open, setOpen] = useState(index === 0);
  const style = PHASE_STYLE[step.phase] ?? {
    color: "text-zinc-300", bg: "bg-zinc-500/10", border: "border-zinc-500/30", label: step.phase.toUpperCase(),
  };

  return (
    <div className="relative pl-10">
      {/* timeline spine */}
      {!isLast && (
        <div className="absolute left-[15px] top-7 bottom-0 w-px bg-white/[0.06]" aria-hidden />
      )}
      {/* node dot */}
      <div className="absolute left-[9px] top-[6px] w-3.5 h-3.5 rounded-full border flex items-center justify-center"
        style={{
          borderColor: step.status === "ok" ? "#10b981" : step.status === "warn" ? "#f59e0b" : "#ef4444",
          background: "#0d0f14",
        }}
      >
        <div className="w-1.5 h-1.5 rounded-full"
          style={{ background: step.status === "ok" ? "#10b981" : step.status === "warn" ? "#f59e0b" : "#ef4444" }}
        />
      </div>

      <div className="pb-3">
        <button
          onClick={() => setOpen(!open)}
          className="w-full text-left group flex items-start gap-3 rounded-md border border-transparent hover:border-white/[0.08] hover:bg-[#0d0f14] transition-all px-3 py-2 -mx-3"
        >
          <span className="mt-0.5">{open ? <ChevronDown className="w-3.5 h-3.5 text-zinc-500" /> : <ChevronRight className="w-3.5 h-3.5 text-zinc-500" />}</span>
          <span className="flex-1 min-w-0">
            <span className="flex flex-wrap items-center gap-2">
              <span className={`inline-flex items-center gap-1 px-1.5 py-0.2 rounded border text-[9px] font-mono tracking-wider ${style.bg} ${style.border} ${style.color}`}>
                {style.label}
              </span>
              <span className="text-xs font-semibold text-zinc-200 group-hover:text-white transition-colors">
                {step.title}
              </span>
              {STATUS_ICON[step.status] ?? STATUS_ICON.ok}
              <span className="inline-flex items-center gap-1 text-[10px] font-mono text-zinc-500">
                <Timer className="w-3 h-3" /> {step.durationMs.toFixed(1)}ms
              </span>
            </span>
            <span className="block text-xs text-zinc-400 mt-0.5">{step.detail}</span>
          </span>
          <span className="text-[10px] font-mono text-zinc-600 mt-1 shrink-0">#{String(step.id).padStart(2, "0")}</span>
        </button>

        {open && (
          <div className="mt-1.5 rounded-md bg-[#0d0f14] border border-white/[0.06] overflow-hidden">
            <div className="flex items-center gap-2 px-3 py-1.5 border-b border-white/[0.06] bg-[#13161f]">
              <Terminal className="w-3 h-3 text-zinc-500" />
              <span className="text-[10px] font-mono text-zinc-400 tracking-wider">PAYLOAD</span>
            </div>
            <pre className="px-3.5 py-2.5 text-xs leading-relaxed font-mono text-zinc-300 overflow-x-auto max-h-80 overflow-y-auto custom-scrollbar">
              {JSON.stringify(step.data, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default function TrajectoryTab({ steps }: { steps: TrajectoryStep[] }) {
  const totalMs = steps.reduce((a, s) => a + s.durationMs, 0);
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between px-1">
        <p className="text-xs text-zinc-500">
          Execution trace of the CodeGate backend — expand any step to inspect its raw output.
        </p>
        <div className="flex items-center gap-3 text-[10px] font-mono text-zinc-500">
          <span>{steps.length} STEPS</span>
          <span>·</span>
          <span className="inline-flex items-center gap-1"><Timer className="w-3 h-3" />{totalMs.toFixed(1)}ms TOTAL</span>
        </div>
      </div>
      <div className="rounded-2xl border border-[#1c1f28] bg-[#0a0b0e] p-4">
        {steps.map((s, i) => (
          <StepRow key={s.id} step={s} index={i} isLast={i === steps.length - 1} />
        ))}
      </div>
    </div>
  );
}
