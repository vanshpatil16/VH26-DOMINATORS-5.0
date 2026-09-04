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
  Network, AudioWaveform, Wand2, TriangleAlert, Upload, X, Scale, Sparkles,
  Zap, Cpu, CheckCircle2, Code2, Terminal, Layers
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
    <div className="min-h-screen bg-[#07080a] text-zinc-100 font-poppins selection:bg-purple-500/30 selection:text-purple-200 p-4 md:p-8 space-y-6">
      {/* ── Top Header Navigation Bar ── */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#1c1f28]">
        <div className="flex items-center gap-4">
          <Link
            to="/dashboard"
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#0d0e12] border border-[#1c1f28] hover:border-purple-500/50 hover:bg-[#13151c] text-zinc-400 hover:text-white transition-all duration-200 text-xs font-medium group shadow-sm shadow-black/40"
          >
            <ArrowLeft className="w-4 h-4 text-zinc-400 group-hover:-translate-x-0.5 transition-transform" />
            <span>Dashboard</span>
          </Link>
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center shadow-sm shadow-emerald-950/50">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              </div>
              <h1 className="text-xl md:text-2xl font-semibold text-white tracking-tight">
                CodeGate
              </h1>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-300 text-[10px] font-mono font-medium tracking-wide">
                <Sparkles className="w-3 h-3 text-purple-400" /> Path-Sensitive Static Suite
              </span>
            </div>
            <p className="text-xs text-zinc-400 mt-0.5">
              Scalpel CFG path evaluation, alias tracking, and LibCST auto-fix previews
            </p>
          </div>
        </div>

        {/* Live Execution Telemetry Bar */}
        {result ? (
          <div className="flex items-center gap-2 px-3.5 py-2 rounded-2xl bg-[#0c0d12] border border-[#1e2230] text-xs font-mono shadow-inner shadow-black/60">
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-300">
              <Zap className="w-3 h-3 text-purple-400" />
              <span>{result.summary.acquires} acquires</span>
            </div>
            <span className="text-zinc-700">•</span>
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-300">
              <Network className="w-3 h-3 text-cyan-400" />
              <span>{result.summary.functionsAnalyzed} CFGs</span>
            </div>
            <span className="text-zinc-700">•</span>
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300">
              <Layers className="w-3 h-3 text-amber-400" />
              <span>{result.summary.trajectorySteps} steps ({result.summary.analysisMs.toFixed(0)}ms)</span>
            </div>
            <span className="text-zinc-700">•</span>
            <div className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg border font-semibold ${
              result.summary.leakCount > 0
                ? "bg-red-500/10 border-red-500/40 text-red-400 animate-pulse"
                : "bg-emerald-500/10 border-emerald-500/40 text-emerald-400"
            }`}>
              {result.summary.leakCount > 0 ? (
                <>
                  <TriangleAlert className="w-3.5 h-3.5 text-red-400" />
                  <span>{result.summary.leakCount} leak{result.summary.leakCount > 1 ? "s" : ""}</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Clean</span>
                </>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-xs text-zinc-500 font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span>Ready for analysis</span>
          </div>
        )}
      </header>

      {/* ── Main Workspace Grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-[420px_1fr] gap-6 items-start">
        {/* ── Left Control & Editor Column ── */}
        <div className="space-y-4 lg:sticky lg:top-6">
          {/* Preset Demos Selector */}
          <div className="rounded-2xl bg-[#0c0d12] border border-[#1c1f28] p-3.5 space-y-2.5 shadow-md shadow-black/50">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                <Code2 className="w-3.5 h-3.5 text-purple-400" /> Sample Test Suites
              </span>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-emerald-500/40 bg-emerald-500/10 text-[11px] font-medium text-emerald-300 hover:border-emerald-500/70 hover:bg-emerald-500/20 transition-all duration-200 shadow-sm"
                title="Upload .py files"
              >
                <Upload className="w-3 h-3" />
                <span>Upload</span>
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
            <div className="flex items-center gap-1.5 flex-wrap">
              {DEMOS.map((d, i) => (
                <button
                  key={d.name}
                  onClick={() => pickDemo(i)}
                  className={`px-3 py-1.5 rounded-xl border text-xs font-medium transition-all duration-200 shadow-sm ${
                    activeFile.name === d.filename && activeFile.code === d.code
                      ? "bg-purple-600/25 border-purple-500/60 text-purple-200 font-semibold shadow-purple-950/40"
                      : "bg-[#11131a] border-[#1f2330] text-zinc-400 hover:border-purple-500/30 hover:text-zinc-200 hover:bg-[#161824]"
                  }`}
                >
                  {d.name}
                </button>
              ))}
            </div>
          </div>

          {/* Active Open File Tabs */}
          {files.length > 0 && (
            <div className="flex items-center gap-2 overflow-x-auto custom-scrollbar pb-1">
              {files.map((f, i) => (
                <span
                  key={`${f.name}-${i}`}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-mono transition-all duration-200 cursor-pointer shrink-0 shadow-sm ${
                    i === activeIdx
                      ? "bg-purple-950/40 border-purple-500/60 text-purple-200 font-medium"
                      : "bg-[#0d0e12] border-[#1c1f28] text-zinc-400 hover:text-zinc-200 hover:border-zinc-700 hover:bg-white/5"
                  }`}
                  onClick={() => { setActiveIdx(i); setResult(null); }}
                >
                  <FileCode2 className={`w-3.5 h-3.5 ${i === activeIdx ? "text-purple-400" : "text-zinc-500"}`} />
                  <span>{f.name}</span>
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

          {/* Code Editor Window */}
          <div
            className={`rounded-2xl border bg-[#0a0b0e] overflow-hidden transition-all duration-200 shadow-xl shadow-black/80 ${
              dragOver ? "border-purple-500/60 bg-purple-500/5 ring-2 ring-purple-500/20" : "border-[#1c1f28]"
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              if (e.dataTransfer.files.length) void addUploadedFiles(e.dataTransfer.files);
            }}
          >
            {/* Editor Window Bar */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#1c1f28] bg-[#0c0d12]">
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500/40" />
                  <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/40" />
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/40" />
                </div>
                <span className="text-zinc-700 mx-1">|</span>
                <input
                  value={activeFile.name}
                  onChange={(e) => {
                    const name = e.target.value;
                    setFiles((prev) => prev.map((f, i) => (i === activeIdx ? { ...f, name } : f)));
                  }}
                  className="bg-transparent text-xs font-mono text-zinc-300 focus:outline-none focus:text-white w-40"
                  spellCheck={false}
                />
              </div>
              <button
                onClick={() => { updateCode(""); setResult(null); }}
                className="text-zinc-500 hover:text-zinc-300 transition-colors p-1 rounded-md hover:bg-white/5"
                title="Clear code"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Editor Textarea */}
            <textarea
              value={activeFile.code}
              onChange={(e) => updateCode(e.target.value)}
              spellCheck={false}
              className="w-full h-[360px] bg-transparent p-4 font-mono text-xs leading-relaxed text-zinc-200 focus:outline-none resize-y selection:bg-purple-500/40 selection:text-purple-100 custom-scrollbar"
              placeholder="# Paste Python source code here, or drag & drop .py files…"
            />
          </div>

          {/* Analysis Config & Run Action Bar */}
          <div className="rounded-2xl bg-[#0c0d12] border border-[#1c1f28] p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md">
            <div className="flex flex-col gap-2">
              <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={autoFix}
                  onChange={(e) => setAutoFix(e.target.checked)}
                  className="rounded border-[#2a2f45] bg-[#07080a] text-purple-500 focus:ring-purple-500/30 accent-purple-500"
                />
                <Wand2 className="w-3.5 h-3.5 text-purple-400" />
                <span>LibCST auto-fix preview</span>
              </label>
              <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={useEnsemble}
                  onChange={(e) => setUseEnsemble(e.target.checked)}
                  className="rounded border-[#2a2f45] bg-[#07080a] text-emerald-500 focus:ring-emerald-500/30 accent-emerald-500"
                />
                <Scale className="w-3.5 h-3.5 text-emerald-400" />
                <span>Ensemble verifier (ruff + CodeGate)</span>
              </label>
            </div>

            <button
              onClick={() => void run()}
              disabled={running || !activeFile.code.trim()}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-purple-950/60 active:scale-95 shrink-0"
            >
              {running ? (
                <Loader2 className="w-4 h-4 animate-spin text-white" />
              ) : (
                <Play className="w-4 h-4 text-white fill-white" />
              )}
              <span>{running ? "Analyzing…" : "Run Analysis"}</span>
            </button>
          </div>

          {/* Backend Error Display */}
          {error && (
            <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-4 text-xs text-red-300 space-y-2 shadow-lg shadow-red-950/30">
              <div className="flex items-center gap-2 font-semibold text-red-400">
                <TriangleAlert className="w-4 h-4 shrink-0 text-red-400" />
                <span>Analyzer Failure</span>
              </div>
              <pre className="p-3 rounded-xl bg-black/60 border border-red-500/20 text-[11px] font-mono text-red-200 overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap custom-scrollbar">
                {error}
              </pre>
            </div>
          )}
        </div>

        {/* ── Right Results & Visualizations Panel ── */}
        <div className="w-full">
          {!result && !running && (
            <div className="flex flex-col items-center justify-center py-28 gap-4 text-center rounded-3xl border border-dashed border-[#1c1f28] bg-[#0c0d12]/50 p-8">
              <div className="w-14 h-14 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center shadow-inner">
                <AudioWaveform className="w-7 h-7 text-purple-400" />
              </div>
              <div className="max-w-md space-y-1">
                <h3 className="text-base font-semibold text-white">Ready to inspect Python code</h3>
                <p className="text-xs text-zinc-400">
                  Select a sample snippet or paste custom source code, then click <strong className="text-zinc-200 font-medium">Run Analysis</strong> to view leak cards, trajectory traces, CFG control flow, and AST tree visualizations.
                </p>
              </div>
              <div className="flex items-center gap-3 text-[11px] font-mono text-zinc-500 pt-2">
                <span className="flex items-center gap-1"><Cpu className="w-3.5 h-3.5 text-purple-400" /> Scalpel CFG</span>
                <span>•</span>
                <span className="flex items-center gap-1"><Terminal className="w-3.5 h-3.5 text-emerald-400" /> LibCST Fix</span>
                <span>•</span>
                <span className="flex items-center gap-1"><ShieldCheck className="w-3.5 h-3.5 text-cyan-400" /> Alias Tracking</span>
              </div>
            </div>
          )}

          {running && (
            <div className="flex flex-col items-center justify-center py-28 gap-4 rounded-3xl border border-[#1c1f28] bg-[#0c0d12] p-8 text-zinc-400">
              <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
              <div className="text-center space-y-1">
                <p className="text-sm font-medium text-white">Evaluating execution paths…</p>
                <p className="text-xs font-mono text-zinc-500">Constructing Scalpel CFG blocks & tracing alias allocations</p>
              </div>
            </div>
          )}

          {result && (
            <Tabs defaultValue="report" className="w-full">
              <TabsList className="bg-[#0c0d12] border border-[#1c1f28] p-1 rounded-2xl mb-5 flex flex-wrap gap-1">
                <TabsTrigger
                  value="report"
                  className="data-[state=active]:bg-purple-600/30 data-[state=active]:border-purple-500/50 data-[state=active]:text-purple-100 text-zinc-400 hover:text-white text-xs font-medium gap-2 transition-all px-4 py-2 rounded-xl border border-transparent"
                >
                  <ScrollText className="w-3.5 h-3.5 text-purple-400" />
                  <span>Report</span>
                  {result.summary.leakCount > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-red-500/20 border border-red-500/40 text-red-400 text-[10px] font-mono font-semibold">
                      {result.summary.leakCount}
                    </span>
                  )}
                </TabsTrigger>

                <TabsTrigger
                  value="trajectory"
                  className="data-[state=active]:bg-purple-600/30 data-[state=active]:border-purple-500/50 data-[state=active]:text-purple-100 text-zinc-400 hover:text-white text-xs font-medium gap-2 transition-all px-4 py-2 rounded-xl border border-transparent"
                >
                  <AudioWaveform className="w-3.5 h-3.5 text-amber-400" />
                  <span>Trajectory</span>
                  <span className="px-1.5 py-0.5 rounded-full bg-purple-500/20 border border-purple-500/30 text-purple-300 text-[10px] font-mono">
                    {result.summary.trajectorySteps}
                  </span>
                </TabsTrigger>

                <TabsTrigger
                  value="ast"
                  className="data-[state=active]:bg-purple-600/30 data-[state=active]:border-purple-500/50 data-[state=active]:text-purple-100 text-zinc-400 hover:text-white text-xs font-medium gap-2 transition-all px-4 py-2 rounded-xl border border-transparent"
                >
                  <FileCode2 className="w-3.5 h-3.5 text-cyan-400" />
                  <span>AST Tree</span>
                </TabsTrigger>

                <TabsTrigger
                  value="cfg"
                  className="data-[state=active]:bg-purple-600/30 data-[state=active]:border-purple-500/50 data-[state=active]:text-purple-100 text-zinc-400 hover:text-white text-xs font-medium gap-2 transition-all px-4 py-2 rounded-xl border border-transparent"
                >
                  <Network className="w-3.5 h-3.5 text-emerald-400" />
                  <span>CFG Flow</span>
                </TabsTrigger>

                {result.ensemble && (
                  <TabsTrigger
                    value="ensemble"
                    className="data-[state=active]:bg-purple-600/30 data-[state=active]:border-purple-500/50 data-[state=active]:text-purple-100 text-zinc-400 hover:text-white text-xs font-medium gap-2 transition-all px-4 py-2 rounded-xl border border-transparent"
                  >
                    <Scale className="w-3.5 h-3.5 text-pink-400" />
                    <span>Ensemble</span>
                    <span className="px-1.5 py-0.5 rounded-full bg-red-500/20 border border-red-500/40 text-red-400 text-[10px] font-mono">
                      {(result.ensemble.counts.confirmed_path_leak ?? 0) +
                        (result.ensemble.counts.confirmed_exception_unsafe ?? 0)}
                    </span>
                  </TabsTrigger>
                )}
              </TabsList>

              <TabsContent value="report" className="focus:outline-none">
                <ReportTab leaks={result.leaks} fix={result.fix} filename={result.filename} />
              </TabsContent>
              <TabsContent value="trajectory" className="focus:outline-none">
                <TrajectoryTab steps={result.trajectory} />
              </TabsContent>
              <TabsContent value="ast" className="focus:outline-none">
                <AstTreeTab ast={result.ast} />
              </TabsContent>
              <TabsContent value="cfg" className="focus:outline-none">
                <CfgGraphTab functions={result.cfg.functions} />
              </TabsContent>
              {result.ensemble && (
                <TabsContent value="ensemble" className="focus:outline-none">
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
