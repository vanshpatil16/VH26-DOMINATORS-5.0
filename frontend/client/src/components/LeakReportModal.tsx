/**
 * LeakReportModal — Professional, print-ready security audit report.
 * Path-sensitive resource-leak findings across a GitHub repository.
 */
import React, { useState, useEffect, useCallback } from "react";
import {
  X,
  ShieldAlert,
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Printer,
  RefreshCw,
  FolderGit2,
  GitBranch,
  Clock,
  ChevronDown,
  ChevronRight,
  Loader2,
  ExternalLink,
  FileCode,
  Activity,
} from "lucide-react";
import { fetchRepoTree, fetchFileContent } from "@/lib/github";
import { runCodegateAnalysis, type Leak } from "@/lib/codegate";

/* ─── Types ─────────────────────────────────────────────────────────────── */

interface FileReport {
  path: string;
  status: "clean" | "leaked" | "error" | "scanning";
  leaks: Leak[];
  errorMsg?: string;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  owner: string;
  repo: string;
  branch?: string;
}

/* ─── Severity config ───────────────────────────────────────────────────── */

const KIND: Record<string, { label: string; shortLabel: string; color: string; bg: string; border: string }> = {
  path: {
    label: "Confirmed Path Leak",
    shortLabel: "PATH LEAK",
    color: "text-rose-300",
    bg: "bg-rose-500/10",
    border: "border-rose-500/25",
  },
  exception: {
    label: "Exception-Safety Risk",
    shortLabel: "EXCEPTION",
    color: "text-amber-300",
    bg: "bg-amber-500/10",
    border: "border-amber-500/25",
  },
  "path+exception": {
    label: "Path + Exception Leak",
    shortLabel: "CRITICAL",
    color: "text-purple-300",
    bg: "bg-purple-500/10",
    border: "border-purple-500/25",
  },
};

/* ─── Print CSS injected once ───────────────────────────────────────────── */

const PRINT_STYLE = `
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

@media print {
  * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }

  /* Hide background website elements so only the report appears */
  body > div:not(#root), 
  #root > div > *:not(#report-overlay),
  nav, header, sidebar, .print\\:hidden { 
    display: none !important; 
  }

  /* Ensure body and html background are light for printing */
  html, body {
    background: #ffffff !important;
    color: #111111 !important;
    margin: 0 !important;
    padding: 0 !important;
    height: auto !important;
    overflow: visible !important;
  }

  #report-overlay {
    position: static !important;
    background: #ffffff !important;
    backdrop-filter: none !important;
    align-items: flex-start !important;
    padding: 0 !important;
    width: 100% !important;
    height: auto !important;
    inset: auto !important;
  }

  #report-modal-card {
    position: static !important;
    max-width: 100% !important;
    max-height: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    overflow: visible !important;
    background: #ffffff !important;
    border: none !important;
    color: #111111 !important;
  }

  #report-header {
    background: #ffffff !important;
    border-bottom: 2px solid #111111 !important;
    padding: 24px 32px 20px !important;
  }

  #report-header h2 { color: #000000 !important; font-size: 22px !important; }
  #report-header .meta-tag { color: #444444 !important; font-family: 'JetBrains Mono', monospace !important; }

  #report-stats { background: #f4f4f6 !important; border-bottom: 1px solid #cccccc !important; }
  #report-stats .stat-cell { background: #f4f4f6 !important; border: none !important; border-right: 1px solid #cccccc !important; }
  #report-stats .stat-num { color: #000000 !important; }
  #report-stats .stat-num.red { color: #dc2626 !important; }
  #report-stats .stat-num.amber { color: #d97706 !important; }
  #report-stats .stat-num.green { color: #16a34a !important; }
  #report-stats .stat-label { color: #555555 !important; }

  #report-body { overflow: visible !important; padding: 24px 32px !important; background: #ffffff !important; color: #111111 !important; }

  .exec-summary { background: #f8fafc !important; border: 1px solid #cbd5e1 !important; border-radius: 8px !important; padding: 16px !important; margin-bottom: 20px !important; }
  .exec-summary h3 { color: #0f172a !important; }
  .exec-summary p { color: #334155 !important; }
  .risk-badge { border: 1px solid currentColor !important; border-radius: 4px !important; padding: 2px 8px !important; font-family: 'JetBrains Mono', monospace !important; font-size: 10px !important; font-weight: 700 !important; }

  .file-card { background: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 6px !important; margin-bottom: 10px !important; break-inside: avoid !important; }
  .file-card.leaked { border-color: #f87171 !important; background: #fef2f2 !important; }
  .file-card-header { padding: 10px 14px !important; color: #111111 !important; cursor: default !important; background: transparent !important; }
  .file-card-header .fname { color: #0f172a !important; font-family: 'JetBrains Mono', monospace !important; font-size: 11px !important; font-weight: 600 !important; }
  .file-card-header .fpath { color: #64748b !important; font-family: 'JetBrains Mono', monospace !important; font-size: 10px !important; }
  .leak-count-badge { background: #fee2e2 !important; color: #dc2626 !important; border: 1px solid #fca5a5 !important; border-radius: 3px !important; font-family: 'JetBrains Mono', monospace !important; font-size: 9px !important; font-weight: 700 !important; padding: 1px 6px !important; }
  .clean-badge { color: #16a34a !important; font-family: 'JetBrains Mono', monospace !important; font-size: 10px !important; }

  .leak-detail { border-top: 1px solid #e2e8f0 !important; padding: 12px 14px !important; background: #ffffff !important; }
  .sev-badge { font-family: 'JetBrains Mono', monospace !important; font-size: 9px !important; font-weight: 700 !important; padding: 1px 6px !important; border-radius: 3px !important; border: 1px solid !important; }
  .sev-badge.path { background: #fee2e2 !important; color: #dc2626 !important; border-color: #fca5a5 !important; }
  .sev-badge.exception { background: #fef3c7 !important; color: #d97706 !important; border-color: #fcd34d !important; }
  .sev-badge.critical { background: #f3e8ff !important; color: #7e22ce !important; border-color: #d8b4fe !important; }

  .detail-grid { display: grid !important; grid-template-columns: repeat(3, 1fr) !important; gap: 8px !important; margin: 8px 0 !important; }
  .detail-cell { background: #f8fafc !important; border: 1px solid #cbd5e1 !important; border-radius: 4px !important; padding: 6px 8px !important; }
  .detail-cell .label { color: #64748b !important; font-family: 'JetBrains Mono', monospace !important; font-size: 9px !important; text-transform: uppercase !important; margin-bottom: 2px !important; }
  .detail-cell .value { font-family: 'JetBrains Mono', monospace !important; font-size: 11px !important; font-weight: 600 !important; color: #0f172a !important; }
  .finding-box { background: #f8fafc !important; border: 1px solid #cbd5e1 !important; border-radius: 4px !important; padding: 8px 10px !important; margin: 6px 0 !important; }
  .finding-box .label { color: #64748b !important; font-size: 9px !important; font-family: 'JetBrains Mono', monospace !important; text-transform: uppercase !important; margin-bottom: 3px !important; }
  .finding-box p { color: #1e293b !important; font-size: 11px !important; line-height: 1.5 !important; }
  .fix-box { background: #f0fdf4 !important; border: 1px solid #86efac !important; border-radius: 4px !important; padding: 8px 10px !important; margin: 6px 0 !important; }
  .fix-box .label { color: #15803d !important; font-size: 9px !important; font-family: 'JetBrains Mono', monospace !important; text-transform: uppercase !important; margin-bottom: 3px !important; }
  .fix-box p { color: #14532d !important; font-size: 11px !important; font-family: 'JetBrains Mono', monospace !important; }

  #report-footer { border-top: 1px solid #cbd5e1 !important; padding: 10px 32px !important; color: #64748b !important; font-size: 10px !important; font-family: 'JetBrains Mono', monospace !important; background: #ffffff !important; }
}
`;

let styleInjected = false;
function injectPrintStyle() {
  if (styleInjected || typeof document === "undefined") return;
  const tag = document.createElement("style");
  tag.textContent = PRINT_STYLE;
  document.head.appendChild(tag);
  styleInjected = true;
}

/* ─── Risk level helper ─────────────────────────────────────────────────── */

function riskLevel(confirmed: number, total: number) {
  if (total === 0) return { label: "CLEAN", cls: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10", printCls: "text-[#1a7a4a]" };
  if (confirmed > 3) return { label: "CRITICAL", cls: "text-rose-300 border-rose-500/40 bg-rose-500/10", printCls: "text-[#c0392b]" };
  if (confirmed > 0) return { label: "HIGH", cls: "text-orange-300 border-orange-500/30 bg-orange-500/10", printCls: "text-[#d35400]" };
  return { label: "MEDIUM", cls: "text-amber-300 border-amber-500/30 bg-amber-500/10", printCls: "text-[#b7760d]" };
}

/* ─── Component ─────────────────────────────────────────────────────────── */

export default function LeakReportModal({ isOpen, onClose, owner, repo, branch = "main" }: Props) {
  const [scanning, setScanning] = useState(false);
  const [done, setDone] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0, current: "" });
  const [reports, setReports] = useState<FileReport[]>([]);
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());

  useEffect(() => { injectPrintStyle(); }, []);

  const totalLeaks = reports.reduce((n, r) => n + r.leaks.length, 0);
  const confirmedLeaks = reports.reduce(
    (n, r) => n + r.leaks.filter((l) => l.kind === "path" || l.kind === "path+exception").length, 0
  );
  const exceptionRisks = reports.reduce(
    (n, r) => n + r.leaks.filter((l) => l.kind === "exception").length, 0
  );
  const cleanFiles = reports.filter((r) => r.status === "clean").length;
  const leakyFiles = reports.filter((r) => r.status === "leaked").length;
  const risk = riskLevel(confirmedLeaks, totalLeaks);

  const runScan = useCallback(async () => {
    if (!owner || !repo) return;
    setScanning(true);
    setDone(false);
    setReports([]);
    setExpandedFiles(new Set());

    try {
      const tree = await fetchRepoTree(owner, repo, branch);
      const pyFiles = tree.filter((f) => f.path.endsWith(".py") && f.size > 0 && f.size < 200_000).slice(0, 30);
      setProgress({ done: 0, total: pyFiles.length, current: "" });

      const results: FileReport[] = [];
      for (let i = 0; i < pyFiles.length; i++) {
        const file = pyFiles[i];
        setProgress({ done: i, total: pyFiles.length, current: file.path });

        const source = await fetchFileContent(owner, repo, file.path, branch);
        if (!source) {
          results.push({ path: file.path, status: "error", leaks: [], errorMsg: "Could not fetch file" });
          setReports([...results]);
          continue;
        }

        try {
          const result = await runCodegateAnalysis(source, file.path.split("/").pop() || file.path, false);
          if (!result.ok) {
            results.push({ path: file.path, status: "error", leaks: [], errorMsg: result.error || "Analysis failed" });
          } else if (result.leaks?.length > 0) {
            results.push({ path: file.path, status: "leaked", leaks: result.leaks });
          } else {
            results.push({ path: file.path, status: "clean", leaks: [] });
          }
        } catch (e) {
          results.push({
            path: file.path, status: "error", leaks: [],
            errorMsg: e instanceof Error ? e.message : "Analyzer offline",
          });
        }
        setReports([...results]);
      }
      setProgress({ done: pyFiles.length, total: pyFiles.length, current: "" });
    } catch (e) {
      console.error("LeakReport scan failed:", e);
    } finally {
      setScanning(false);
      setDone(true);
    }
  }, [owner, repo, branch]);

  useEffect(() => {
    if (isOpen && !done && !scanning) runScan();
  }, [isOpen]);

  const toggleFile = (path: string) => {
    setExpandedFiles((prev) => {
      const next = new Set(prev);
      next.has(path) ? next.delete(path) : next.add(path);
      return next;
    });
  };

  if (!isOpen) return null;

  const scanPct = progress.total > 0 ? Math.round((progress.done / progress.total) * 100) : 0;
  const now = new Date().toLocaleString("en-US", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

  return (
    <div
      id="report-overlay"
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        id="report-modal-card"
        className="relative w-full max-w-4xl max-h-[92vh] flex flex-col rounded-xl bg-[#0d0f14] border border-white/[0.08] shadow-2xl overflow-hidden font-sans"
      >
        {/* ── Header ── */}
        <div id="report-header" className="relative flex-shrink-0 bg-[#13161f] border-b border-white/[0.06] px-5 py-4">
          {/* Close */}
          <button
            onClick={onClose}
            className="print:hidden absolute top-3.5 right-3.5 p-1 rounded-md text-zinc-500 hover:text-white hover:bg-white/10 transition-all"
          >
            <X className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-4 pr-8">
            {/* Icon */}
            <div className="w-9 h-9 rounded-md bg-rose-500/10 border border-rose-500/25 flex items-center justify-center shrink-0">
              <ShieldAlert className="w-5 h-5 text-rose-400" />
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-3 mb-1">
                <h2 className="text-lg font-bold text-white tracking-tight">Security Audit Report</h2>
                <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">CodeGate Static Analysis</span>
              </div>
              <div className="flex flex-wrap gap-4 text-[11px] text-zinc-400 font-mono meta-tag">
                <span className="flex items-center gap-1.5">
                  <FolderGit2 className="w-3.5 h-3.5 text-zinc-500" />{owner}/{repo}
                </span>
                <span className="flex items-center gap-1.5">
                  <GitBranch className="w-3.5 h-3.5 text-zinc-500" />{branch}
                </span>
                <span className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-zinc-500" />{now}
                </span>
              </div>
            </div>

            {/* Actions */}
            {done && (
              <div className="print:hidden flex items-center gap-2 flex-shrink-0">
                <button
                  onClick={runScan}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white/5 border border-[#262b3a] text-zinc-300 hover:text-white hover:border-zinc-500 transition-all"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Re-scan
                </button>
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#1d2033] border border-[#303752] text-zinc-200 hover:text-white hover:bg-[#252843] transition-all"
                >
                  <Printer className="w-3.5 h-3.5" /> Print / Save PDF
                </button>
              </div>
            )}
          </div>

          {/* Progress bar */}
          {scanning && (
            <div className="mt-4">
              <div className="flex items-center justify-between mb-1 text-[10px] font-mono">
                <span className="text-zinc-400 flex items-center gap-1.5">
                  <Loader2 className="w-3 h-3 animate-spin text-zinc-400" />
                  {progress.current
                    ? <span>Analyzing <span className="text-zinc-200">{progress.current}</span></span>
                    : "Preparing analysis…"}
                </span>
                <span className="text-zinc-500">{progress.done}/{progress.total} files</span>
              </div>
              <div className="h-1 w-full bg-[#16181f] rounded-full overflow-hidden">
                <div
                  className="h-full bg-zinc-400 rounded-full transition-all duration-300"
                  style={{ width: `${scanPct}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* ── Stats Bar ── */}
        {(done || reports.length > 0) && (
          <div id="report-stats" className="flex-shrink-0 grid grid-cols-4 divide-x divide-[#1a1d28] border-b border-[#1e2130]">
            {[
              { label: "Total Findings", value: totalLeaks, numCls: totalLeaks > 0 ? "text-rose-300 red" : "text-zinc-300", icon: <Activity className="w-3.5 h-3.5" /> },
              { label: "Confirmed Leaks", value: confirmedLeaks, numCls: confirmedLeaks > 0 ? "text-rose-300 red" : "text-zinc-500", icon: <AlertOctagon className="w-3.5 h-3.5" /> },
              { label: "Exception Risk", value: exceptionRisks, numCls: exceptionRisks > 0 ? "text-amber-300 amber" : "text-zinc-500", icon: <AlertTriangle className="w-3.5 h-3.5" /> },
              { label: "Clean Files", value: cleanFiles, numCls: "text-emerald-400 green", icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
            ].map((s) => (
              <div key={s.label} className="stat-cell flex flex-col items-center justify-center py-3.5 px-2 bg-[#09090d]">
                <span className={`stat-num text-xl font-bold font-poppins tracking-tight ${s.numCls}`}>{s.value}</span>
                <span className="stat-label text-[9px] font-mono text-zinc-500 uppercase tracking-widest mt-0.5">{s.label}</span>
              </div>
            ))}
          </div>
        )}

        {/* ── Body ── */}
        <div id="report-body" className="flex-1 overflow-y-auto p-5 space-y-2.5 custom-scrollbar">

          {/* Scanning placeholder */}
          {scanning && reports.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 gap-2.5">
              <Loader2 className="w-8 h-8 animate-spin text-zinc-500" />
              <p className="text-sm font-medium text-zinc-300">Running analysis…</p>
              <p className="text-[11px] font-mono text-zinc-500">Path-sensitive resource-leak detection on Python source</p>
            </div>
          )}

          {/* Executive Summary */}
          {done && (
            <div className="exec-summary rounded-xl bg-[#0f1018] border border-[#1e2230] p-5 mb-1">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <h3 className="text-sm font-semibold text-white tracking-tight mb-0.5">Executive Summary</h3>
                  <p className="text-[11px] font-mono text-zinc-500">
                    Path-sensitive static analysis · {reports.length} files scanned · {owner}/{repo}@{branch}
                  </p>
                </div>
                <span className={`risk-badge flex-shrink-0 text-[10px] font-mono font-bold px-3 py-1 rounded border ${risk.cls}`}>
                  {risk.label}
                </span>
              </div>
              <p className="text-xs text-zinc-400 leading-relaxed">
                CodeGate completed path-sensitive control-flow analysis of{" "}
                <span className="text-zinc-200 font-medium">{reports.length} Python source files</span>.{" "}
                {totalLeaks === 0 ? (
                  <span className="text-emerald-400">No resource leaks detected. All acquire–release paths appear safe.</span>
                ) : (
                  <>
                    <span className="text-zinc-200 font-medium">{totalLeaks} finding{totalLeaks !== 1 ? "s" : ""}</span> across{" "}
                    <span className="text-zinc-200 font-medium">{leakyFiles} file{leakyFiles !== 1 ? "s" : ""}</span>.{" "}
                    {confirmedLeaks > 0 && (
                      <>{confirmedLeaks} confirmed path-level leak{confirmedLeaks !== 1 ? "s" : ""} where resources are provably not released on one or more control-flow paths. </>
                    )}
                    {exceptionRisks > 0 && (
                      <>{exceptionRisks} exception-safety issue{exceptionRisks !== 1 ? "s" : ""} where a may-throw call between acquire and release can cause resource escape.</>
                    )}
                  </>
                )}
              </p>
            </div>
          )}

          {/* File Reports */}
          {reports.map((fileReport) => {
            const isExpanded = expandedFiles.has(fileReport.path);
            const fname = fileReport.path.split("/").pop() || fileReport.path;
            const dir = fileReport.path.includes("/") ? fileReport.path.substring(0, fileReport.path.lastIndexOf("/") + 1) : "";

            return (
              <div
                key={fileReport.path}
                className={`file-card rounded-xl border overflow-hidden transition-all duration-150 ${
                  fileReport.status === "leaked"
                    ? "leaked bg-[#0f1018] border-rose-500/25"
                    : "bg-[#0b0c13] border-[#181b26]"
                }`}
              >
                {/* File row */}
                <button
                  onClick={() => toggleFile(fileReport.path)}
                  className="file-card-header w-full flex items-center justify-between gap-3 px-4 py-3 text-left hover:bg-white/[0.02] transition-colors group"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    {fileReport.status === "leaked" ? (
                      <AlertOctagon className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
                    ) : fileReport.status === "error" ? (
                      <AlertTriangle className="w-3.5 h-3.5 text-zinc-600 flex-shrink-0" />
                    ) : (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500/80 flex-shrink-0" />
                    )}

                    <div className="min-w-0">
                      <span className="fname font-mono text-[11px] font-semibold text-zinc-100 group-hover:text-white transition-colors">
                        {dir && <span className="text-zinc-500 font-normal">{dir}</span>}{fname}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    {fileReport.status === "leaked" && (
                      <span className="leak-count-badge inline-block px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-rose-500/10 text-rose-300 border border-rose-500/25">
                        {fileReport.leaks.length} {fileReport.leaks.length === 1 ? "finding" : "findings"}
                      </span>
                    )}
                    {fileReport.status === "clean" && (
                      <span className="clean-badge text-[10px] font-mono text-emerald-500/70">Clean</span>
                    )}
                    {fileReport.status === "error" && (
                      <span className="text-[10px] font-mono text-zinc-600">Skipped</span>
                    )}
                    {isExpanded
                      ? <ChevronDown className="w-3.5 h-3.5 text-zinc-600" />
                      : <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />
                    }
                  </div>
                </button>

                {/* Expanded leaks */}
                {isExpanded && fileReport.leaks.length > 0 && (
                  <div className="border-t border-[#181b26] divide-y divide-[#131620]">
                    {fileReport.leaks.map((leak, idx) => {
                      const sev = KIND[leak.kind] || KIND["path"];
                      const sevPrintCls = leak.kind === "exception" ? "exception" : leak.kind === "path+exception" ? "critical" : "path";

                      return (
                        <div key={idx} className="leak-detail px-4 py-4 space-y-2.5">
                          {/* Finding header */}
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={`sev-badge ${sevPrintCls} inline-block text-[9px] font-mono font-semibold px-2 py-0.5 rounded border ${sev.bg} ${sev.color} ${sev.border}`}>
                              {sev.shortLabel}
                            </span>
                            <span className="text-[11px] font-mono font-semibold text-zinc-200">
                              {leak.func}()
                            </span>
                            <a
                              href={`https://github.com/${owner}/${repo}/blob/${branch}/${fileReport.path}#L${leak.acquire_line || leak.line}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="print:hidden ml-auto text-[10px] font-mono text-zinc-500 hover:text-zinc-300 flex items-center gap-1 transition-colors"
                            >
                              L{leak.acquire_line || leak.line} <ExternalLink className="w-3 h-3" />
                            </a>
                            <span className="hidden print:inline ml-auto text-[10px] font-mono text-zinc-500">
                              Line {leak.acquire_line || leak.line}
                            </span>
                          </div>

                          {/* Detail grid */}
                          <div className="detail-grid grid grid-cols-3 gap-2">
                            {[
                              { label: "Variable", value: leak.var, valCls: "text-rose-300" },
                              { label: "Acquire", value: leak.acquire, valCls: "text-amber-300" },
                              { label: "Release", value: leak.release, valCls: "text-emerald-400" },
                            ].map((d) => (
                              <div key={d.label} className="detail-cell bg-[#0c0e15] border border-[#181b26] rounded-lg p-2.5">
                                <p className="label text-[9px] font-mono text-zinc-600 uppercase mb-1">{d.label}</p>
                                <p className={`value text-[11px] font-mono font-semibold ${d.valCls}`}>{d.value}</p>
                              </div>
                            ))}
                          </div>

                          {/* Finding message */}
                          <div className="finding-box bg-[#0c0e15] border border-[#181b26] rounded-lg px-3 py-2.5">
                            <p className="label text-[9px] font-mono text-zinc-600 uppercase mb-1.5">Finding</p>
                            <p className="text-[11px] text-zinc-400 leading-relaxed">{leak.message}</p>
                          </div>

                          {/* Exception note */}
                          {leak.exception_note && (
                            <div className="finding-box bg-amber-950/15 border border-amber-500/15 rounded-lg px-3 py-2.5">
                              <p className="label text-[9px] font-mono text-amber-600 uppercase mb-1.5">Exception Path</p>
                              <p className="text-[11px] text-amber-300/80 leading-relaxed">{leak.exception_note}</p>
                            </div>
                          )}

                          {/* Remediation */}
                          <div className="fix-box bg-emerald-950/10 border border-emerald-500/15 rounded-lg px-3 py-2.5">
                            <p className="label text-[9px] font-mono text-emerald-600/80 uppercase mb-1.5">Remediation</p>
                            <p className="text-[11px] font-mono text-emerald-300/80 leading-relaxed">
                              Replace bare <span className="text-amber-300">{leak.acquire}</span> with a{" "}
                              <span className="font-semibold text-emerald-300">with</span> statement, or add a{" "}
                              <span className="font-semibold text-emerald-300">finally</span> block that unconditionally calls{" "}
                              <span className="text-rose-300">{leak.release}</span>.
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Error detail */}
                {isExpanded && fileReport.status === "error" && (
                  <div className="border-t border-[#181b26] px-4 py-3">
                    <p className="text-[11px] font-mono text-zinc-600">{fileReport.errorMsg}</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* ── Footer ── */}
        {done && (
          <div
            id="report-footer"
            className="flex-shrink-0 border-t border-[#1e2130] bg-[#09090d] px-6 py-2.5 flex items-center justify-between text-[10px] font-mono text-zinc-600"
          >
            <span>
              {owner}/{repo} · {branch} · {reports.length} files · {totalLeaks} finding{totalLeaks !== 1 ? "s" : ""}
            </span>
            <div className="print:hidden flex items-center gap-4">
              <button onClick={runScan} className="hover:text-zinc-300 transition-colors">Re-scan</button>
              <button onClick={onClose} className="hover:text-zinc-300 transition-colors">Close</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
