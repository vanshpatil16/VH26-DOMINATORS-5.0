/**
 * CodeGate — static resource-leak analyzer (GUI).
 * Monochrome premium glass 3-panel IDE layout: sidebar | editor | resizable results.
 * Paste code, pick a demo, or upload your own files (drag & drop supported),
 * then inspect:
 *   Report     — friendly leak cards
 *   Trajectory — DeepSeek-harness style execution trace of the backend
 *   AST        — real abstract syntax tree from the backend
 *   CFG        — control-flow graph per function with leak highlighting
 *   Ensemble   — ruff pre-filter + CodeGate CFG verification verdicts
 *   KB         — Knowledge base rules + LLM-discovered contracts
 */
import { useCallback, useMemo, useRef, useState, useEffect } from "react";
import { Link } from "wouter";
import {
  ArrowLeft, Play, Loader2, FileCode2, RotateCcw, ShieldCheck, ScrollText,
  Network, AudioWaveform, Wand2, TriangleAlert, Upload, X, Scale, Sparkles,
  Zap, Cpu, CheckCircle2, Code2, Terminal, Layers, BookOpen, Search,
  ChevronDown, ChevronRight, FolderOpen, Folder, Settings, Eye, Copy,
  Maximize2, Minimize2, PanelRightClose, PanelRight, Braces, FileText,
  GitBranch, Clock, Box, Workflow, GripVertical, SlidersHorizontal, RefreshCw
} from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { DEMOS, runCodegateAnalysis, type CodegateResult } from "@/lib/codegate";
import ReportTab from "@/components/codegate/ReportTab";
import TrajectoryTab from "@/components/codegate/TrajectoryTab";
import AstTreeTab from "@/components/codegate/AstTreeTab";
import CfgGraphTab from "@/components/codegate/CfgGraphTab";
import EnsembleTab from "@/components/codegate/EnsembleTab";
import KnowledgeBaseTab from "@/components/codegate/KnowledgeBaseTab";

interface LoadedFile {
  name: string;
  code: string;
}

/* ─── Sidebar folder groups ── */
const SIDEBAR_FOLDERS = [
  { label: "Samples", icon: "folder", items: DEMOS.map((d) => d.name) },
];

/* ─── Line-number gutter for the editor ── */
function LineNumbers({ count }: { count: number }) {
  return (
    <div
      className="cg-line-gutter select-none text-right pr-3 pt-[15px] pb-[15px] text-[11px] leading-[1.7] font-mono text-zinc-600 border-r border-white/[0.05] bg-white/[0.015] backdrop-blur-md min-w-[44px] shrink-0 tabular-nums"
      aria-hidden
    >
      {Array.from({ length: count }, (_, i) => (
        <div key={i}>{i + 1}</div>
      ))}
    </div>
  );
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
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sidebarWidth, setSidebarWidth] = useState(220);
  const [isResizingSidebar, setIsResizingSidebar] = useState(false);

  const [resultsPanelOpen, setResultsPanelOpen] = useState(true);
  const [resultsPanelWidth, setResultsPanelWidth] = useState(440);
  const [isResizingResults, setIsResizingResults] = useState(false);

  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({ Samples: true });
  const [configOpen, setConfigOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeFile = files[activeIdx] ?? { name: "input.py", code: "" };
  const lineCount = useMemo(() => activeFile.code.split("\n").length, [activeFile.code]);

  /* ─── Resizing mouse handlers ─── */
  const startResizingSidebar = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizingSidebar(true);
  }, []);

  const startResizingResults = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizingResults(true);
  }, []);

  useEffect(() => {
    if (!isResizingSidebar && !isResizingResults) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingSidebar) {
        const newWidth = e.clientX;
        setSidebarWidth(Math.max(160, Math.min(450, newWidth)));
      }
      if (isResizingResults) {
        const newWidth = window.innerWidth - e.clientX;
        const maxW = Math.min(window.innerWidth - 250, 1100);
        setResultsPanelWidth(Math.max(280, Math.min(maxW, newWidth)));
      }
    };

    const handleMouseUp = () => {
      setIsResizingSidebar(false);
      setIsResizingResults(false);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizingSidebar, isResizingResults]);

  const run = useCallback(async () => {
    setRunning(true);
    setError(null);
    setResultsPanelOpen(true);
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

  const toggleFolder = (label: string) => {
    setExpandedFolders((prev) => ({ ...prev, [label]: !prev[label] }));
  };

  const copyCode = () => {
    navigator.clipboard.writeText(activeFile.code);
  };

  return (
    <div
      className={`h-screen flex flex-col bg-[url('/bg-silk.jpg')] bg-cover bg-center bg-no-repeat text-zinc-100 font-sans selection:bg-white/20 selection:text-white overflow-hidden relative ${isResizingResults || isResizingSidebar ? "select-none cursor-col-resize" : ""
        }`}
    >
      {/* Dark tint overlay for ambient contrast */}
      <div className="absolute inset-0 bg-black/30 backdrop-brightness-[0.85] pointer-events-none z-0" />

      {/* ═══════ FLOATING GLASS TOP HEADER ═══════ */}
      <header className="mx-3 mt-3 px-4 h-12 bg-black/45 backdrop-blur-2xl border border-white/10 rounded-2xl flex items-center justify-between shrink-0 z-30 shadow-[0_8px_32px_rgba(0,0,0,0.6)]">
        {/* Left: Logo + Navigation */}
        <div className="flex items-center gap-3">
          <Link
            to="/dashboard"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.04] hover:bg-white/[0.09] border border-white/10 text-zinc-300 hover:text-white transition-all text-xs font-medium"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Dashboard</span>
          </Link>
          <div className="w-px h-4 bg-white/10" />
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center shadow-[0_0_15px_rgba(255,255,255,0.1)]">
              <ShieldCheck className="w-3.5 h-3.5 text-white" />
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-sm font-bold text-white tracking-tight font-poppins">CodeGate</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-md bg-white/10 border border-white/15 text-zinc-200">
                PRO IDE
              </span>
            </div>
          </div>
        </div>

        {/* Center: telemetry glass chips */}
        <div className="hidden md:flex items-center gap-2">
          {result ? (
            <>
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/40 backdrop-blur-xl border border-white/10 text-[10px] font-mono text-zinc-300 shadow-inner tabular-nums">
                <Zap className="w-3 h-3 text-cyan-400" />
                <span>{result.summary.acquires} acquires</span>
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/40 backdrop-blur-xl border border-white/10 text-[10px] font-mono text-zinc-300 shadow-inner tabular-nums">
                <Network className="w-3 h-3 text-indigo-400" />
                <span>{result.summary.functionsAnalyzed} CFG blocks</span>
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/40 backdrop-blur-xl border border-white/10 text-[10px] font-mono text-zinc-300 shadow-inner tabular-nums">
                <Clock className="w-3 h-3 text-amber-400" />
                <span>{result.summary.analysisMs.toFixed(0)}ms</span>
              </div>
              <div
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-[10px] font-mono font-semibold backdrop-blur-xl transition-all tabular-nums ${result.summary.leakCount > 0
                  ? "bg-rose-500/10 border-rose-500/30 text-rose-300 shadow-[0_0_15px_rgba(244,63,94,0.15)]"
                  : "bg-emerald-500/10 border-emerald-500/30 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.15)]"
                  }`}
              >
                {result.summary.leakCount > 0 ? (
                  <>
                    <TriangleAlert className="w-3 h-3 text-rose-400" />
                    <span>{result.summary.leakCount} LEAK{result.summary.leakCount > 1 ? "S" : ""} DETECTED</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-3 h-3" />
                    <span>SAFE (0 LEAKS)</span>
                  </>
                )}
              </div>
            </>
          ) : (
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-black/40 backdrop-blur-xl border border-white/10 text-[11px] font-mono text-zinc-300">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              <span>Ready for Static Analysis</span>
            </div>
          )}
        </div>

        {/* Right: controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className={`p-1.5 rounded-xl border transition-all ${sidebarOpen
              ? "bg-white/15 border-white/20 text-white"
              : "bg-transparent border-transparent text-zinc-400 hover:text-white hover:bg-white/10"
              }`}
            title="Toggle Explorer Sidebar"
          >
            {sidebarOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRight className="w-4 h-4" />}
          </button>

          <button
            onClick={() => void run()}
            disabled={running || !activeFile.code.trim()}
            className="flex items-center gap-2 px-4 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-semibold shadow-[0_0_15px_rgba(255,255,255,0.15)] transition-all border border-white/20 disabled:opacity-30 disabled:cursor-not-allowed active:scale-[0.97]"
          >
            {running ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-current" />
            )}
            <span className="hidden sm:inline">{running ? "Analyzing…" : "Run Analysis"}</span>
          </button>
        </div>
      </header>

      {/* ═══════ MAIN 3-PANEL BODY WITH TRANSPARENT GAPS ═══════ */}
      <div className="flex flex-1 p-3 gap-3 overflow-hidden relative z-10">

        {/* ─── 1. EXPLORER (FLOATING GLASS PANEL) ── */}
        {sidebarOpen && (
          <aside
            style={{ width: `${sidebarWidth}px` }}
            className="bg-black/40 backdrop-blur-2xl border border-white/10 rounded-2xl flex flex-col shrink-0 overflow-hidden shadow-[0_12px_40px_rgba(0,0,0,0.6)]"
          >
            {/* Sidebar header */}
            <div className="px-3.5 py-2.5 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
              <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-widest font-semibold">
                Explorer
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="p-1 rounded-lg hover:bg-white/10 text-zinc-400 hover:text-cyan-300 transition-colors"
                  title="Upload .py files"
                >
                  <Upload className="w-3.5 h-3.5" />
                </button>

              </div>
            </div>

            {/* Open files */}
            <div className="px-2.5 py-2 border-b border-white/10">
              <div className="flex items-center gap-1.5 px-1.5 mb-1.5">
                <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">Active Tabs</span>
              </div>
              {files.map((f, i) => (
                <button
                  key={`${f.name}-${i}`}
                  onClick={() => { setActiveIdx(i); setResult(null); }}
                  className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-xl text-[11px] font-mono transition-all group ${i === activeIdx
                    ? "bg-cyan-500/20 text-cyan-200 border border-cyan-400/30 shadow-[0_0_15px_rgba(6,182,212,0.15)] font-semibold"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.05] border border-transparent"
                    }`}
                >
                  <FileCode2 className={`w-3.5 h-3.5 shrink-0 ${i === activeIdx ? "text-cyan-400" : "text-zinc-500"}`} />
                  <span className="truncate flex-1 text-left">{f.name}</span>
                  {files.length > 1 && (
                    <span
                      onClick={(e) => { e.stopPropagation(); closeFile(i); }}
                      className="opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-red-400 transition-all p-0.5 rounded"
                    >
                      <X className="w-3 h-3" />
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Folder tree — Samples */}
            <div className="flex-1 overflow-y-auto custom-scrollbar px-2.5 py-2">
              {SIDEBAR_FOLDERS.map((folder) => (
                <div key={folder.label} className="mb-2">
                  <button
                    onClick={() => toggleFolder(folder.label)}
                    className="w-full flex items-center gap-1.5 px-2 py-1 text-[11px] font-medium text-zinc-300 hover:text-white rounded-lg hover:bg-white/[0.05] transition-colors"
                  >
                    {expandedFolders[folder.label]
                      ? <ChevronDown className="w-3.5 h-3.5 text-zinc-500" />
                      : <ChevronRight className="w-3.5 h-3.5 text-zinc-500" />
                    }
                    {expandedFolders[folder.label]
                      ? <FolderOpen className="w-3.5 h-3.5 text-amber-400/80" />
                      : <Folder className="w-3.5 h-3.5 text-amber-400/60" />
                    }
                    <span>{folder.label}</span>
                  </button>
                  {expandedFolders[folder.label] && (
                    <div className="pl-4 mt-1 space-y-0.5 border-l border-white/10 ml-2.5">
                      {folder.items.map((item, i) => (
                        <button
                          key={item}
                          onClick={() => pickDemo(i)}
                          className={`w-full flex items-center gap-2 px-2 py-1 rounded-lg text-[11px] font-mono transition-all ${activeFile.name === DEMOS[i].filename && activeFile.code === DEMOS[i].code
                            ? "bg-cyan-500/20 text-cyan-200 font-semibold border border-cyan-400/30"
                            : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.05]"
                            }`}
                        >
                          <FileText className={`w-3 h-3 shrink-0 ${activeFile.name === DEMOS[i].filename && activeFile.code === DEMOS[i].code
                            ? "text-cyan-400" : "text-zinc-500"
                            }`} />
                          <span className="truncate">{item}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Config section at bottom */}
            <div className="border-t border-white/10 px-2.5 py-2 bg-white/[0.02]">
              <button
                onClick={() => setConfigOpen(!configOpen)}
                className="w-full flex items-center gap-1.5 px-2 py-1 text-[11px] font-medium text-zinc-400 hover:text-white rounded-lg hover:bg-white/[0.05] transition-colors"
              >
                {configOpen ? <ChevronDown className="w-3.5 h-3.5 text-zinc-500" /> : <ChevronRight className="w-3.5 h-3.5 text-zinc-500" />}
                <Settings className="w-3.5 h-3.5 text-zinc-400" />
                <span>Analyzer Settings</span>
              </button>
              {configOpen && (
                <div className="pl-5 mt-2 space-y-2 border-l border-white/10 ml-2.5">
                  <label className="flex items-center gap-2 text-[11px] text-zinc-300 cursor-pointer select-none hover:text-white transition-colors">
                    <input
                      type="checkbox"
                      checked={autoFix}
                      onChange={(e) => setAutoFix(e.target.checked)}
                      className="rounded border-white/20 bg-black/40 text-cyan-500 focus:ring-cyan-500/30 accent-cyan-500 w-3.5 h-3.5"
                    />
                    <Wand2 className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Auto-fix engine</span>
                  </label>
                  <label className="flex items-center gap-2 text-[11px] text-zinc-300 cursor-pointer select-none hover:text-white transition-colors">
                    <input
                      type="checkbox"
                      checked={useEnsemble}
                      onChange={(e) => setUseEnsemble(e.target.checked)}
                      className="rounded border-white/20 bg-black/40 text-emerald-500 focus:ring-emerald-500/30 accent-emerald-500 w-3.5 h-3.5"
                    />
                    <Scale className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Ensemble verifier</span>
                  </label>
                </div>
              )}
            </div>
          </aside>
        )}

        {/* ─── LEFT SIDEBAR RESIZE DRAG HANDLE (TRANSPARENT GAP) ── */}
        {sidebarOpen && (
          <div
            onMouseDown={startResizingSidebar}
            onDoubleClick={() => setSidebarWidth(220)}
            title="Drag to resize Explorer sidebar"
            className="w-1.5 hover:w-1.5 bg-transparent cursor-col-resize z-20 flex items-center justify-center shrink-0 group select-none -mx-1.5"
          >
            <div className="w-[3px] h-12 rounded-full bg-white/20 group-hover:bg-cyan-400 group-hover:shadow-[0_0_12px_#06b6d4] transition-all" />
          </div>
        )}

        {/* ─── 2. IDE / CODE EDITOR (FLOATING GLASS PANEL) ── */}
        <main className="flex-1 flex flex-col min-w-0 bg-black/35 backdrop-blur-2xl border border-white/10 rounded-2xl overflow-hidden shadow-[0_12px_40px_rgba(0,0,0,0.6)]">
          {/* Editor file tabs bar */}
          <div className="flex items-center bg-black/30 backdrop-blur-md border-b border-white/10 shrink-0 overflow-x-auto custom-scrollbar">
            {files.map((f, i) => (
              <button
                key={`tab-${f.name}-${i}`}
                onClick={() => { setActiveIdx(i); setResult(null); }}
                className={`inline-flex items-center gap-2 px-4 py-2.5 text-[11px] font-mono border-r border-white/10 transition-all shrink-0 relative ${i === activeIdx
                  ? "bg-white/[0.08] text-zinc-100 font-semibold"
                  : "bg-transparent text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.03]"
                  }`}
              >
                <FileCode2 className={`w-3.5 h-3.5 ${i === activeIdx ? "text-cyan-400" : "text-zinc-600"}`} />
                <span>{f.name}</span>
                {files.length > 1 && (
                  <span
                    onClick={(e) => { e.stopPropagation(); closeFile(i); }}
                    className="ml-1 text-zinc-600 hover:text-red-400 transition-colors p-0.5 rounded"
                  >
                    <X className="w-3 h-3" />
                  </span>
                )}
                {i === activeIdx && (
                  <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-gradient-to-r from-cyan-400 to-indigo-500 shadow-[0_0_8px_rgba(6,182,212,0.8)]" />
                )}
              </button>
            ))}
            {/* Editor toolbar */}
            <div className="ml-auto flex items-center gap-1 px-3 shrink-0">
              <button
                onClick={copyCode}
                className="p-1.5 rounded-lg hover:bg-white/10 text-zinc-400 hover:text-white transition-colors"
                title="Copy source code"
              >
                <Copy className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => { updateCode(""); setResult(null); }}
                className="p-1.5 rounded-lg hover:bg-white/10 text-zinc-400 hover:text-white transition-colors"
                title="Clear code"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setResultsPanelOpen(!resultsPanelOpen)}
                className={`p-1.5 rounded-lg border transition-all ${resultsPanelOpen
                  ? "bg-cyan-500/20 border-cyan-400/30 text-cyan-300"
                  : "bg-transparent border-transparent text-zinc-400 hover:text-white hover:bg-white/10"
                  }`}
                title="Toggle Analysis Panel"
              >
                {resultsPanelOpen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {/* Editor body with line numbers */}
          <div
            className={`flex-1 flex overflow-hidden relative transition-all ${dragOver ? "ring-2 ring-cyan-500/50 bg-cyan-500/[0.04]" : ""
              }`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              if (e.dataTransfer.files.length) void addUploadedFiles(e.dataTransfer.files);
            }}
          >
            <LineNumbers count={lineCount} />
            <textarea
              value={activeFile.code}
              onChange={(e) => updateCode(e.target.value)}
              spellCheck={false}
              className="flex-1 bg-transparent p-[15px] font-mono text-[12px] leading-[1.7] text-zinc-100 focus:outline-none resize-none overflow-auto custom-scrollbar caret-cyan-400 selection:bg-cyan-500/25 selection:text-cyan-100"
              placeholder="# Paste Python source code here, or drag & drop .py files…"
            />

            {/* Drop overlay */}
            {dragOver && (
              <div className="absolute inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center pointer-events-none z-20">
                <div className="flex items-center gap-3 px-6 py-4 rounded-xl bg-[#090b10]/95 border border-cyan-400/40 text-cyan-300 text-sm font-medium shadow-[0_0_30px_rgba(6,182,212,0.3)]">
                  <Upload className="w-5 h-5 animate-bounce text-cyan-400" />
                  Drop .py files to analyze instantly
                </div>
              </div>
            )}
          </div>

          {/* Error display */}
          {error && (
            <div className="border-t border-red-500/30 bg-red-950/20 backdrop-blur-md px-4 py-2.5 text-xs text-red-300 space-y-1.5 shrink-0">
              <div className="flex items-center gap-2 font-semibold text-red-400">
                <TriangleAlert className="w-4 h-4 shrink-0" />
                <span>Analyzer Execution Failure</span>
              </div>
              <pre className="p-2.5 rounded-lg bg-black/60 border border-red-500/20 text-[10px] font-mono text-red-200 overflow-x-auto max-h-28 overflow-y-auto whitespace-pre-wrap custom-scrollbar">
                {error}
              </pre>
            </div>
          )}
        </main>

        {/* ─── ANALYSIS PANEL RESIZE DRAG HANDLE (TRANSPARENT GAP) ── */}
        {resultsPanelOpen && (
          <div
            onMouseDown={startResizingResults}
            onDoubleClick={() => setResultsPanelWidth(440)}
            title="Drag to adjust Analysis panel width, double-click to reset"
            className="w-1.5 hover:w-1.5 bg-transparent cursor-col-resize z-20 flex items-center justify-center shrink-0 group select-none -mx-1.5"
          >
            <div
              className={`w-[3px] h-12 rounded-full transition-all flex items-center justify-center ${isResizingResults
                ? "bg-cyan-400 shadow-[0_0_15px_#06b6d4]"
                : "bg-white/20 group-hover:bg-cyan-400 group-hover:shadow-[0_0_12px_#06b6d4]"
                }`}
            >
              <GripVertical className="w-2.5 h-2.5 text-zinc-950 opacity-80" />
            </div>
          </div>
        )}

        {/* ─── 3. ANALYSIS (FLOATING GLASS PANEL) ── */}
        {resultsPanelOpen && (
          <aside
            style={{ width: `${resultsPanelWidth}px` }}
            className={`bg-black/40 backdrop-blur-2xl border border-white/10 rounded-2xl flex flex-col shrink-0 overflow-hidden shadow-[0_12px_40px_rgba(0,0,0,0.6)] relative transition-all ${isResizingResults ? "ring-1 ring-cyan-500/50 shadow-cyan-500/20" : ""
              }`}
          >
            {/* Results panel header */}
            <div className="px-3.5 py-2.5 border-b border-white/10 flex items-center justify-between shrink-0 bg-white/[0.02]">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-lg bg-gradient-to-br from-indigo-500/30 to-cyan-500/30 border border-indigo-400/30 flex items-center justify-center shadow-inner">
                  <Eye className="w-3 h-3 text-cyan-300" />
                </div>
                <span className="text-[11px] font-mono font-bold text-white uppercase tracking-wider">
                  Analysis
                </span>
                {/* Resizable width indicator badge */}
                <span className="text-[9px] font-mono px-1.5 py-0.2 rounded-md bg-white/10 text-zinc-300 border border-white/15">
                  {resultsPanelWidth}px
                </span>
              </div>

              <div className="flex items-center gap-2">
                {/* Quick Preset Width Buttons */}
                <div className="hidden sm:flex items-center gap-1 border border-white/10 bg-black/40 p-0.5 rounded-lg">
                  <button
                    onClick={() => setResultsPanelWidth(340)}
                    className={`px-1.5 py-0.5 rounded-md text-[9px] font-mono transition-colors ${resultsPanelWidth === 340 ? "bg-cyan-500/30 text-cyan-300 font-bold" : "text-zinc-400 hover:text-zinc-200"
                      }`}
                    title="Compact width (340px)"
                  >
                    S
                  </button>
                  <button
                    onClick={() => setResultsPanelWidth(440)}
                    className={`px-1.5 py-0.5 rounded-md text-[9px] font-mono transition-colors ${resultsPanelWidth === 440 ? "bg-cyan-500/30 text-cyan-300 font-bold" : "text-zinc-400 hover:text-zinc-200"
                      }`}
                    title="Default width (440px)"
                  >
                    M
                  </button>
                  <button
                    onClick={() => setResultsPanelWidth(640)}
                    className={`px-1.5 py-0.5 rounded-md text-[9px] font-mono transition-colors ${resultsPanelWidth === 640 ? "bg-cyan-500/30 text-cyan-300 font-bold" : "text-zinc-400 hover:text-zinc-200"
                      }`}
                    title="Wide width (640px)"
                  >
                    L
                  </button>
                </div>

                {result && (
                  <div
                    className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold backdrop-blur-md ${result.summary.leakCount > 0
                      ? "bg-rose-500/10 text-rose-300 border border-rose-500/30 shadow-[0_0_10px_rgba(244,63,94,0.1)]"
                      : "bg-emerald-500/10 text-emerald-300 border border-emerald-500/30"
                      }`}
                  >
                    {result.summary.leakCount > 0 ? (
                      <><TriangleAlert className="w-3 h-3 text-rose-400" />{result.summary.leakCount} issue{result.summary.leakCount > 1 ? "s" : ""}</>
                    ) : (
                      <><CheckCircle2 className="w-3 h-3" />All clear</>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Results content area */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-3.5">
              {/* Empty state */}
              {!result && !running && (
                <div className="flex flex-col items-center justify-center h-full gap-5 text-center px-4 py-8">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500/20 via-indigo-500/15 to-purple-500/20 border border-white/15 flex items-center justify-center shadow-[0_0_30px_rgba(6,182,212,0.2)]">
                    <AudioWaveform className="w-8 h-8 text-cyan-300" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-sm font-bold text-white tracking-tight">Ready for Static Analysis</h3>
                    <p className="text-[11px] text-zinc-300 leading-relaxed max-w-[260px]">
                      Select a sample file or paste code in the editor, then click <strong className="text-cyan-300 font-medium">Run Analysis</strong>.
                    </p>
                  </div>
                  <div className="flex flex-wrap justify-center gap-2 max-w-[280px]">
                    {[
                      { icon: <Cpu className="w-3 h-3 text-cyan-400" />, label: "CFG Analysis" },
                      { icon: <Braces className="w-3 h-3 text-indigo-400" />, label: "AST Parsing" },
                      { icon: <Workflow className="w-3 h-3 text-emerald-400" />, label: "Path Trace" },
                      { icon: <Box className="w-3 h-3 text-amber-400" />, label: "Auto-Fix" },
                    ].map((feat) => (
                      <div
                        key={feat.label}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.05] border border-white/10 text-[10px] font-mono text-zinc-300 backdrop-blur-md shadow-sm"
                      >
                        {feat.icon}
                        <span>{feat.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Loading state */}
              {running && (
                <div className="flex flex-col items-center justify-center h-full gap-4 py-12">
                  <div className="relative">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500/25 to-indigo-500/25 border border-cyan-400/40 flex items-center justify-center shadow-[0_0_35px_rgba(6,182,212,0.4)]">
                      <Loader2 className="w-7 h-7 animate-spin text-cyan-300" />
                    </div>
                    <div className="absolute -inset-2 rounded-2xl bg-cyan-500/20 animate-ping pointer-events-none" />
                  </div>
                  <div className="text-center space-y-1">
                    <p className="text-xs font-semibold text-white">Analyzing resource semantics…</p>
                    <p className="text-[10px] font-mono text-cyan-300">Building CFG blocks & tracing paths</p>
                  </div>
                </div>
              )}

              {/* Results tabs */}
              {result && (
                <Tabs defaultValue="report" className="w-full">
                  <TabsList className="bg-black/50 backdrop-blur-xl border border-white/10 p-1.5 rounded-xl mb-4 grid grid-cols-3 gap-1.5 shadow-lg h-auto w-full">
                    <TabsTrigger
                      value="report"
                      className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-cyan-500/30 data-[state=active]:to-indigo-500/25 data-[state=active]:border-cyan-400/40 data-[state=active]:text-cyan-200 text-zinc-400 hover:text-zinc-200 text-[11px] font-medium gap-1.5 justify-center transition-all px-2 py-1.5 rounded-lg border border-transparent"
                    >
                      <ScrollText className="w-3.5 h-3.5" />
                      Report
                      {result.summary.leakCount > 0 && (
                        <span className="px-1.5 py-0.2 rounded-full bg-rose-500/20 border border-rose-500/40 text-rose-300 text-[9px] font-mono font-bold">
                          {result.summary.leakCount}
                        </span>
                      )}
                    </TabsTrigger>

                    <TabsTrigger
                      value="trajectory"
                      className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-cyan-500/30 data-[state=active]:to-indigo-500/25 data-[state=active]:border-cyan-400/40 data-[state=active]:text-cyan-200 text-zinc-400 hover:text-zinc-200 text-[11px] font-medium gap-1.5 justify-center transition-all px-2 py-1.5 rounded-lg border border-transparent"
                    >
                      <AudioWaveform className="w-3.5 h-3.5" />
                      Trace
                      <span className="px-1.5 py-0.2 rounded-full bg-white/10 text-zinc-300 text-[9px] font-mono">
                        {result.summary.trajectorySteps}
                      </span>
                    </TabsTrigger>

                    <TabsTrigger
                      value="ast"
                      className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-cyan-500/30 data-[state=active]:to-indigo-500/25 data-[state=active]:border-cyan-400/40 data-[state=active]:text-cyan-200 text-zinc-400 hover:text-zinc-200 text-[11px] font-medium gap-1.5 justify-center transition-all px-2 py-1.5 rounded-lg border border-transparent"
                    >
                      <Braces className="w-3.5 h-3.5" />
                      AST
                    </TabsTrigger>

                    <TabsTrigger
                      value="cfg"
                      className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-cyan-500/30 data-[state=active]:to-indigo-500/25 data-[state=active]:border-cyan-400/40 data-[state=active]:text-cyan-200 text-zinc-400 hover:text-zinc-200 text-[11px] font-medium gap-1.5 justify-center transition-all px-2 py-1.5 rounded-lg border border-transparent"
                    >
                      <Network className="w-3.5 h-3.5" />
                      CFG
                    </TabsTrigger>

                    <TabsTrigger
                      value="kb"
                      className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-cyan-500/30 data-[state=active]:to-indigo-500/25 data-[state=active]:border-cyan-400/40 data-[state=active]:text-cyan-200 text-zinc-400 hover:text-zinc-200 text-[11px] font-medium gap-1.5 justify-center transition-all px-2 py-1.5 rounded-lg border border-transparent"
                    >
                      <BookOpen className="w-3.5 h-3.5" />
                      KB
                      {result.knowledgeBase && (
                        <span className="px-1.5 py-0.2 rounded-full bg-white/10 text-zinc-300 text-[9px] font-mono">
                          {result.knowledgeBase.matched.length}
                        </span>
                      )}
                    </TabsTrigger>

                    {result.ensemble && (
                      <TabsTrigger
                        value="ensemble"
                        className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-cyan-500/30 data-[state=active]:to-indigo-500/25 data-[state=active]:border-cyan-400/40 data-[state=active]:text-cyan-200 text-zinc-400 hover:text-zinc-200 text-[11px] font-medium gap-1.5 justify-center transition-all px-2 py-1.5 rounded-lg border border-transparent"
                      >
                        <Scale className="w-3.5 h-3.5" />
                        Verify
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
                  <TabsContent value="kb" className="focus:outline-none">
                    <KnowledgeBaseTab kb={result.knowledgeBase} />
                  </TabsContent>
                  {result.ensemble && (
                    <TabsContent value="ensemble" className="focus:outline-none">
                      <EnsembleTab ensemble={result.ensemble} />
                    </TabsContent>
                  )}
                </Tabs>
              )}
            </div>
          </aside>
        )}
      </div>

      {/* ═══════ FLOATING GLASS BOTTOM STATUS BAR ═══════ */}
      <footer className="mx-3 mb-2 px-4 h-7 bg-black/45 backdrop-blur-2xl border border-white/10 rounded-xl flex items-center justify-between shrink-0 text-[10px] font-mono z-30 shadow-lg">
        <div className="flex items-center gap-3 text-zinc-400">
          <span className="flex items-center gap-1 text-zinc-300">
            <GitBranch className="w-3 h-3 text-cyan-400" />
            main
          </span>
          <span className="flex items-center gap-1 text-zinc-300">
            <FileCode2 className="w-3 h-3 text-indigo-400" />
            {activeFile.name}
          </span>
          <span>
            Ln {lineCount}, Col 1
          </span>
        </div>
        <div className="flex items-center gap-3 text-zinc-400">
          <span className="flex items-center gap-1 text-cyan-300">
            <Sparkles className="w-3 h-3 text-cyan-400" />

          </span>
          <span>Python</span>
          <span>UTF-8</span>
        </div>
      </footer>

      {/* ─── Always-mounted hidden file input (must be outside sidebar conditional so ref is always valid) ── */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".py,.pyi"
        multiple
        style={{ position: "absolute", width: 0, height: 0, opacity: 0, overflow: "hidden", pointerEvents: "none" }}
        onChange={(e) => {
          if (e.target.files) void addUploadedFiles(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
