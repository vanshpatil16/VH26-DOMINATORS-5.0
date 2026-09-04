/**
 * CodeGate — static resource-leak analyzer (GUI).
 * Paste code, pick a demo, or upload your own files (drag & drop supported),
 * then inspect:
 *   Report     — friendly leak cards
 *   Trajectory — DeepSeek-harness style execution trace of the backend
 *   AST        — real abstract syntax tree from the backend
 *   CFG        — control-flow graph per function with leak highlighting
 *   Ensemble   — ruff pre-filter + CodeGate CFG verification verdicts
 */
import { useCallback, useRef, useState } from "react";
import { Link } from "wouter";
import {
  ArrowLeft, Play, Loader2, FileCode2, RotateCcw, ShieldCheck, ScrollText,
  Network, AudioWaveform, Wand2, TriangleAlert, Upload, X, Scale,
} from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { DEMOS, runCodegateAnalysis, type CodegateResult } from "@/lib/codegate";
import ReportTab from "@/components/codegate/ReportTab";
import TrajectoryTab from "@/components/codegate/TrajectoryTab";
import AstTreeTab from "@/components/codegate/AstTreeTab";
import CfgGraphTab from "@/components/codegate/CfgGraphTab";
import EnsembleTab from "@/components/codegate/EnsembleTab";

interface LoadedFile {
  name: string;
  code: string;
}

export default function Codegate() {
  const [files, setFiles] = useState<LoadedFile[]>([
    { name: DEMOS[0].filename, code: DEMOS[0].code },
  ]);
  const [activeIdx, setActiveIdx] = useState(0);
  const [autoFix, setAutoFix] = useState(true);
  const [useEnsemble, setUseEnsemble] = useState(true);
  const [result, setResult] = useState<CodegateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeFile = files[activeIdx] ?? { name: "input.py", code: "" };

  const run = useCallback(async () => {
    setRunning(true);
    setError(null);
    try {
      const r = await runCodegateAnalysis(activeFile.code, activeFile.name, autoFix, useEnsemble);
      setResult(r);
    } catch (e) {
      setError((e as Error).message);
      setResult(null);
    } finally {
      setRunning(false);
    }
  }, [activeFile, autoFix, useEnsemble]);

  const pickDemo = (i: number) => {
    const d = DEMOS[i];
    setFiles((prev) => {
      const existing = prev.findIndex((f) => f.name === d.filename);
      if (existing >= 0) {
        const next = [...prev];
        next[existing] = { name: d.filename, code: d.code };
        setActiveIdx(existing);
        return next;
      }
      setActiveIdx(prev.length);
      return [...prev, { name: d.filename, code: d.code }];
    });
    setResult(null);
    setError(null);
  };

  const addUploadedFiles = useCallback(async (list: FileList | File[]) => {
    const pyFiles = Array.from(list).filter(
      (f) => f.name.endsWith(".py") || f.name.endsWith(".pyi"),
    );
    if (!pyFiles.length) return;
    const loaded: LoadedFile[] = [];
    for (const f of pyFiles) {
      const code = await f.text();
      loaded.push({ name: f.name, code });
    }
    setFiles((prev) => {
      // replace existing files with the same name
      const merged = [...prev];
      let firstNewIdx = -1;
      loaded.forEach((lf) => {
        const at = merged.findIndex((p) => p.name === lf.name);
        if (at >= 0) {
          merged[at] = lf;
          if (firstNewIdx < 0) firstNewIdx = at;
        } else {
          if (firstNewIdx < 0) firstNewIdx = merged.length;
          merged.push(lf);
        }
      });
      setActiveIdx(firstNewIdx >= 0 ? firstNewIdx : 0);
      return merged;
    });
    setResult(null);
    setError(null);
  }, []);

  const closeFile = (idx: number) => {
    setFiles((prev) => {
      if (prev.length <= 1) return prev;
      const next = prev.filter((_, i) => i !== idx);
      setActiveIdx((a) => (idx < a ? a - 1 : Math.min(a, next.length - 1)));
      return next;
    });
    setResult(null);
  };

  const updateCode = (code: string) => {
    setFiles((prev) => prev.map((f, i) => (i === activeIdx ? { ...f, code } : f)));
  };

  return (
    <div className="min-h-screen bg-[#07080a] text-zinc-100 selection:bg-purple-500/30 selection:text-purple-200 p-4 md:p-8 space-y-5">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#1c1f28]">
        <div className="flex items-center gap-4">
          <Link
            to="/dashboard"
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#0d0e12] border border-[#1c1f28] hover:border-purple-500/50 hover:bg-[#13151c] text-zinc-400 hover:text-white transition-all duration-200 text-xs font-medium group shadow-sm shadow-black/40"
          >
            <ArrowLeft className="w-4 h-4 text-zinc-400 group-hover:-translate-x-0.5 transition-transform" />
            <span>Back to Dashboard</span>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl md:text-2xl font-semibold text-white tracking-tight flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                CodeGate
              </h1>
              <span className="px-2.5 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-400 text-[10px] font-medium tracking-wide">
                Resource-Leak Analyzer
              </span>
            </div>
            <p className="text-xs text-zinc-500 mt-0.5">
              Static path-sensitive analysis — every backend step is traceable in Trajectory
            </p>
          </div>
        </div>
        {result && (
          <div className="flex items-center gap-3 text-[11px] font-mono text-zinc-500">
            <span>{result.summary.acquires} resources</span>
            <span>·</span>
            <span>{result.summary.functionsAnalyzed} CFGs</span>
            <span>·</span>
            <span>{result.summary.trajectorySteps} steps</span>
            <span>·</span>
            <span className={result.summary.leakCount ? "text-red-400" : "text-emerald-400"}>
              {result.summary.leakCount} leak{result.summary.leakCount === 1 ? "" : "s"}
            </span>
          </div>
        )}
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-5 items-start">
        {/* ── Editor panel ── */}
        <div className="space-y-3 lg:sticky lg:top-4">
          <div className="flex items-center gap-2 flex-wrap">
            {DEMOS.map((d, i) => (
              <button
                key={d.name}
                onClick={() => pickDemo(i)}
                className={`px-3 py-1.5 rounded-xl border text-xs font-medium transition-all duration-200 shadow-sm ${
                  activeFile.name === d.filename && activeFile.code === d.code
                    ? "bg-purple-600/30 border-purple-500/60 text-purple-100 font-semibold shadow-purple-950/50"
                    : "bg-[#0d0e12] border-[#1c1f28] text-zinc-400 hover:border-purple-500/40 hover:text-zinc-100 hover:bg-[#13151c]"
                }`}
              >
                {d.name}
              </button>
            ))}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-emerald-500/40 bg-emerald-500/10 text-xs font-medium text-emerald-300 hover:border-emerald-500/70 hover:bg-emerald-500/20 hover:text-emerald-100 transition-all duration-200 shadow-sm shadow-emerald-950/40"
              title="Upload .py files (or drag & drop onto the editor)"
            >
              <Upload className="w-3.5 h-3.5" />
              Upload files
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".py,.pyi"
              multiple
              className="hidden"
              onChange={(e) => {
                if (e.target.files) void addUploadedFiles(e.target.files);
                e.target.value = "";
              }}
            />
          </div>

          {/* loaded file chips */}
          {files.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap pt-1">
              {files.map((f, i) => (
                <span
                  key={`${f.name}-${i}`}
                  className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-lg border text-xs font-mono transition-all duration-200 cursor-pointer shadow-sm ${
                    i === activeIdx
                      ? "bg-purple-950/40 border-purple-500/60 text-purple-200 font-medium"
                      : "bg-[#0d0e12] border-[#1c1f28] text-zinc-500 hover:text-zinc-300 hover:border-zinc-700 hover:bg-white/5"
                  }`}
                  onClick={() => { setActiveIdx(i); setResult(null); }}
                >
                  <FileCode2 className={`w-3.5 h-3.5 ${i === activeIdx ? "text-purple-400" : "text-zinc-500"}`} />
                  {f.name}
                  {files.length > 1 && (
                    <button
                      onClick={(e) => { e.stopPropagation(); closeFile(i); }}
                      className="text-zinc-500 hover:text-red-400 transition-colors p-0.5 rounded"
                      title="Remove file"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </span>
              ))}
            </div>
          )}

          <div
            className={`rounded-2xl border bg-[#0a0b0e] overflow-hidden transition-all ${
              dragOver ? "border-purple-500/60 bg-purple-500/5" : "border-[#1c1f28]"
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              if (e.dataTransfer.files.length) void addUploadedFiles(e.dataTransfer.files);
            }}
          >
            <div className="flex items-center justify-between px-3 py-2 border-b border-[#1c1f28] bg-[#0d0e12]">
              <div className="flex items-center gap-2">
                <FileCode2 className="w-3.5 h-3.5 text-zinc-500" />
                <input
                  value={activeFile.name}
                  onChange={(e) => {
                    const name = e.target.value;
                    setFiles((prev) => prev.map((f, i) => (i === activeIdx ? { ...f, name } : f)));
                  }}
                  className="bg-transparent text-[11px] font-mono text-zinc-300 focus:outline-none w-40"
                  spellCheck={false}
                />
              </div>
              <button
                onClick={() => { updateCode(""); setResult(null); }}
                className="text-zinc-600 hover:text-zinc-300 transition-colors"
                title="Clear"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
            <textarea
              value={activeFile.code}
              onChange={(e) => updateCode(e.target.value)}
              spellCheck={false}
              className="w-full h-[340px] bg-transparent p-4 font-mono text-[12px] leading-relaxed text-zinc-300 focus:outline-none resize-y"
              placeholder="# Paste Python code here, or drop .py files on me…"
            />
          </div>

          <div className="flex items-center justify-between gap-2">
            <div className="flex flex-col gap-1.5">
              <label className="flex items-center gap-2 text-xs text-zinc-400 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={autoFix}
                  onChange={(e) => setAutoFix(e.target.checked)}
                  className="accent-purple-500"
                />
                <Wand2 className="w-3.5 h-3.5 text-purple-400" />
                Generate autofix preview
              </label>
              <label className="flex items-center gap-2 text-xs text-zinc-400 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={useEnsemble}
                  onChange={(e) => setUseEnsemble(e.target.checked)}
                  className="accent-emerald-500"
                />
                <Scale className="w-3.5 h-3.5 text-emerald-400" />
                Ensemble: ruff + CodeGate verification
              </label>
            </div>
            <button
              onClick={() => void run()}
              disabled={running || !activeFile.code.trim()}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#f1f0ed] text-[#141516] hover:text-[#141516] focus:text-[#141516] active:text-[#141516] text-xs font-semibold hover:bg-white transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-md"
            >
              {running ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-[#141516]" />
              ) : (
                <Play className="w-3.5 h-3.5 text-[#141516]" />
              )}
              <span>{running ? "Analyzing…" : "Run Analysis"}</span>
            </button>
          </div>

          {error && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3.5 text-xs text-red-300 space-y-2">
              <div className="flex items-center gap-2 font-medium">
                <TriangleAlert className="w-4 h-4 shrink-0 text-red-400" />
                <span>Backend Execution Error</span>
              </div>
              <pre className="p-2.5 rounded-lg bg-black/40 border border-red-500/20 text-[11px] font-mono text-red-200 overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap">
                {error}
              </pre>
            </div>
          )}
        </div>

        {/* ── Results panel ── */}
        <div>
          {!result && !running && (
            <div className="flex flex-col items-center justify-center py-24 gap-3 text-center">
              <AudioWaveform className="w-10 h-10 text-zinc-700" />
              <p className="text-sm text-zinc-400">Run an analysis to see leaks, AST, CFG and the full backend trajectory.</p>
              <p className="text-xs text-zinc-600">Backend: Python (Scalpel CFG + LibCST fix) · Trajectory records every step</p>
            </div>
          )}
          {running && (
            <div className="flex items-center justify-center py-24 gap-3 text-zinc-400">
              <Loader2 className="w-5 h-5 animate-spin text-purple-400" />
              <span className="text-sm">Parsing · building CFG · tracing paths…</span>
            </div>
          )}
          {result && (
            <Tabs defaultValue="report" className="w-full">
              <TabsList className="bg-[#0d0e12] border border-[#1c1f28] mb-4">
                <TabsTrigger value="report" className="data-[state=active]:bg-purple-600/20 data-[state=active]:border-purple-500/40 data-[state=active]:text-purple-200 text-zinc-400 hover:text-white text-xs gap-1.5 transition-all">
                  <ScrollText className="w-3.5 h-3.5" />
                  Report
                  {result.summary.leakCount > 0 && (
                    <span className="ml-1 px-1.5 py-px rounded-full bg-red-500/20 text-red-400 text-[10px] font-mono">
                      {result.summary.leakCount}
                    </span>
                  )}
                </TabsTrigger>
                <TabsTrigger value="trajectory" className="data-[state=active]:bg-purple-600/20 data-[state=active]:border-purple-500/40 data-[state=active]:text-purple-200 text-zinc-400 hover:text-white text-xs gap-1.5 transition-all">
                  <AudioWaveform className="w-3.5 h-3.5" />
                  Trajectory
                  <span className="ml-1 px-1.5 py-px rounded-full bg-purple-500/20 text-purple-300 text-[10px] font-mono">
                    {result.summary.trajectorySteps}
                  </span>
                </TabsTrigger>
                <TabsTrigger value="ast" className="data-[state=active]:bg-purple-600/20 data-[state=active]:border-purple-500/40 data-[state=active]:text-purple-200 text-zinc-400 hover:text-white text-xs gap-1.5 transition-all">
                  <FileCode2 className="w-3.5 h-3.5" />
                  AST
                </TabsTrigger>
                <TabsTrigger value="cfg" className="data-[state=active]:bg-purple-600/20 data-[state=active]:border-purple-500/40 data-[state=active]:text-purple-200 text-zinc-400 hover:text-white text-xs gap-1.5 transition-all">
                  <Network className="w-3.5 h-3.5" />
                  CFG
                </TabsTrigger>
                {result.ensemble && (
                  <TabsTrigger value="ensemble" className="data-[state=active]:bg-purple-600/20 data-[state=active]:border-purple-500/40 data-[state=active]:text-purple-200 text-zinc-400 hover:text-white text-xs gap-1.5 transition-all">
                    <Scale className="w-3.5 h-3.5" />
                    Ensemble
                    <span className="ml-1 px-1.5 py-px rounded-full bg-red-500/20 text-red-400 text-[10px] font-mono">
                      {(result.ensemble.counts.confirmed_path_leak ?? 0) +
                        (result.ensemble.counts.confirmed_exception_unsafe ?? 0)}
                    </span>
                  </TabsTrigger>
                )}
              </TabsList>
              <TabsContent value="report">
                <ReportTab leaks={result.leaks} fix={result.fix} filename={result.filename} />
              </TabsContent>
              <TabsContent value="trajectory">
                <TrajectoryTab steps={result.trajectory} />
              </TabsContent>
              <TabsContent value="ast">
                <AstTreeTab ast={result.ast} />
              </TabsContent>
              <TabsContent value="cfg">
                <CfgGraphTab functions={result.cfg.functions} />
              </TabsContent>
              {result.ensemble && (
                <TabsContent value="ensemble">
                  <EnsembleTab ensemble={result.ensemble} />
                </TabsContent>
              )}
            </Tabs>
          )}
        </div>
      </div>
    </div>
  );
}
