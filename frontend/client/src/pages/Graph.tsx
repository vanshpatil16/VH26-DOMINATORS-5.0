import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "wouter";
import {
  ArrowLeft,
  GitBranch,
  Sparkles,
  FolderGit2,
  FileCode2,
  RefreshCw,
  Search,
  Github,
} from "lucide-react";
import AstGraphVisualizer from "../components/AstGraphVisualizer";
import {
  fetchUserRepos,
  fetchRepoMeta,
  fetchRepoTree,
  fetchFileContent,
  type GitHubRepo,
  type RepoFile,
} from "../lib/github";
import { runCodegateAnalysis, type AstNode } from "../lib/codegate";

/** Contents API caps at 1 MB; anything near that is not worth parsing either. */
const MAX_FILE_BYTES = 400_000;

/** "owner/repo", "github.com/owner/repo", or a full clone URL → [owner, repo]. */
function parseRepoInput(raw: string): [string, string] | null {
  const cleaned = raw
    .trim()
    .replace(/^https?:\/\/(www\.)?github\.com\//i, "")
    .replace(/\.git$/i, "")
    .replace(/\/+$/, "");
  const parts = cleaned.split("/").filter(Boolean);
  if (parts.length < 2) return null;
  return [parts[0], parts[1]];
}

export default function Graph() {
  const [owner, setOwner] = useState<string>(
    () => localStorage.getItem("connected_github_user") || "OmkarKudalkar23"
  );
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [repo, setRepo] = useState<GitHubRepo | null>(null);

  const [files, setFiles] = useState<RepoFile[]>([]);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [fileQuery, setFileQuery] = useState("");

  const [ast, setAst] = useState<AstNode | null>(null);
  const [leakCount, setLeakCount] = useState<number | null>(null);

  const [loadingRepos, setLoadingRepos] = useState(false);
  const [loadingTree, setLoadingTree] = useState(false);
  const [loadingAst, setLoadingAst] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [repoInput, setRepoInput] = useState("");

  /* ── analyse one file: GitHub source → CodeGate parser → AST ───────────── */
  const analyzeFile = useCallback(
    async (target: GitHubRepo, path: string) => {
      setActiveFile(path);
      setLoadingAst(true);
      setError(null);
      setAst(null);
      setLeakCount(null);

      const [repoOwner] = target.full_name.split("/");
      const source = await fetchFileContent(
        repoOwner,
        target.name,
        path,
        target.default_branch
      );

      if (source === null) {
        setLoadingAst(false);
        setError(`Could not download ${path} from ${target.full_name} (GitHub API error or rate limit).`);
        return;
      }

      try {
        const result = await runCodegateAnalysis(source, path.split("/").pop() || path, false);
        if (!result.ok || !result.ast) {
          setError(result.error || `CodeGate could not parse ${path} (syntax error?).`);
        } else {
          setAst(result.ast);
          setLeakCount(result.summary.leakCount);
        }
      } catch (err) {
        setError(
          `Analyzer unreachable: ${err instanceof Error ? err.message : String(err)}. ` +
            `The Python backend serves POST /api/codegate/analyze — run the app from the repo root with CodeGate installed (pip install -e .).`
        );
      } finally {
        setLoadingAst(false);
      }
    },
    []
  );

  /* ── load a repo's Python file tree, then auto-open the first file ─────── */
  const loadRepo = useCallback(
    async (target: GitHubRepo) => {
      setRepo(target);
      setFiles([]);
      setActiveFile(null);
      setAst(null);
      setLeakCount(null);
      setError(null);
      setLoadingTree(true);

      const [repoOwner] = target.full_name.split("/");
      const tree = await fetchRepoTree(
        repoOwner,
        target.name,
        target.default_branch || "main"
      );
      const usable = tree.filter((f) => f.size > 0 && f.size <= MAX_FILE_BYTES);
      setFiles(usable);
      setLoadingTree(false);

      if (usable.length === 0) {
        setError(
          `No parseable Python files in ${target.full_name}. CodeGate analyses .py sources — pick another repository.`
        );
        return;
      }
      await analyzeFile(target, usable[0].path);
    },
    [analyzeFile]
  );

  /* ── repo list for the connected GitHub account ────────────────────────── */
  const loadRepos = useCallback(
    async (login: string) => {
      setLoadingRepos(true);
      setError(null);
      const list = await fetchUserRepos(login);
      setRepos(list);
      setLoadingRepos(false);

      if (list.length === 0) {
        setError(`No public repositories found for @${login} (unknown user or GitHub rate limit).`);
        return;
      }
      const preferred = list.find((r) => r.language === "Python") || list[0];
      await loadRepo(preferred);
    },
    [loadRepo]
  );

  useEffect(() => {
    void loadRepos(owner);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── manual owner/repo entry ───────────────────────────────────────────── */
  const openManualRepo = async () => {
    const parsed = parseRepoInput(repoInput);
    if (!parsed) {
      setError("Enter a repository as owner/repo or a github.com URL.");
      return;
    }
    const [o, r] = parsed;
    setError(null);
    setLoadingTree(true);
    const meta = await fetchRepoMeta(o, r);
    setLoadingTree(false);
    if (!meta) {
      setError(`Repository ${o}/${r} not found (private repo or GitHub rate limit).`);
      return;
    }
    setOwner(o);
    setRepos((prev) => (prev.some((p) => p.full_name === meta.full_name) ? prev : [meta, ...prev]));
    await loadRepo(meta);
  };

  const visibleFiles = useMemo(() => {
    const q = fileQuery.trim().toLowerCase();
    const list = q ? files.filter((f) => f.path.toLowerCase().includes(q)) : files;
    return list.slice(0, 300);
  }, [files, fileQuery]);

  const sourceLabel = repo && activeFile ? `${repo.full_name} · ${activeFile}` : undefined;

  return (
    <div className="min-h-screen bg-[#07080a] text-zinc-100 font-poppins selection:bg-purple-500/30 selection:text-purple-200 p-4 md:p-8 space-y-6">
      {/* Navigation & Header */}
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
                AST & Code Graph Visualizer
              </h1>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-400 text-[10px] font-medium tracking-wide">
                <Sparkles className="w-3 h-3" /> Dynamic Canvas
              </span>
            </div>
            <p className="text-xs text-zinc-400 mt-0.5">
              Interactive node & edge flow parsed from real repository source pulled via the GitHub API
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#0d0e12] border border-[#1c1f28] text-xs text-zinc-400">
            <GitBranch className="w-3.5 h-3.5 text-purple-400" />
            <span>Interactive Drag & Marching-Ant Flow</span>
          </div>
        </div>
      </header>

      {/* Source picker: repository + file, straight from the GitHub API */}
      <section className="bg-[#13151b] border border-[#202430] rounded-2xl p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-[#1f2432] pb-3">
          <div className="flex items-center gap-2">
            <Github className="w-4 h-4 text-purple-400" />
            <h2 className="text-sm font-semibold text-white">Source repository</h2>
            <span className="text-[11px] font-mono text-zinc-500">@{owner}</span>
            {repo && (
              <span className="text-[11px] font-mono text-zinc-600">
                · branch {repo.default_branch}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto">
            <input
              type="text"
              value={repoInput}
              onChange={(e) => setRepoInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void openManualRepo();
              }}
              placeholder="owner/repo or github.com URL…"
              className="flex-1 md:w-64 bg-[#181b24] border border-[#272c3d] focus:border-purple-500 text-white placeholder-zinc-500 px-3 py-2 rounded-xl text-xs font-mono outline-none transition-colors"
            />
            <button
              onClick={() => void openManualRepo()}
              className="px-3 py-2 rounded-xl bg-[#181b24] border border-[#272c3d] hover:bg-[#202533] text-zinc-300 hover:text-white text-xs font-medium transition-colors"
            >
              Load
            </button>
            <button
              onClick={() => void loadRepos(owner)}
              title="Reload repositories from GitHub"
              className="p-2 rounded-xl bg-[#181b24] border border-[#272c3d] hover:bg-[#202533] text-zinc-300 hover:text-white transition-colors"
            >
              <RefreshCw
                className={`w-4 h-4 ${loadingRepos ? "animate-spin text-purple-400" : ""}`}
              />
            </button>
          </div>
        </div>

        {/* Repository pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-purple">
          <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest flex items-center gap-1 mr-2 flex-shrink-0">
            <FolderGit2 className="w-3.5 h-3.5 text-purple-400" />
            <span>REPOS:</span>
          </span>
          {repos.length === 0 && !loadingRepos && (
            <span className="text-xs text-zinc-600 font-mono">none loaded</span>
          )}
          {repos.map((r) => {
            const active = repo?.full_name === r.full_name;
            return (
              <button
                key={r.id}
                onClick={() => void loadRepo(r)}
                className={`flex-shrink-0 px-3 py-1.5 rounded-xl text-xs font-medium border transition-colors ${
                  active
                    ? "bg-purple-500/15 border-purple-500/50 text-purple-200"
                    : "bg-[#181b24] border-[#272c3d] text-zinc-400 hover:text-white hover:border-purple-500/30"
                }`}
              >
                {r.name}
                {r.language && (
                  <span className="ml-2 text-[10px] font-mono text-zinc-500">{r.language}</span>
                )}
              </button>
            );
          })}
        </div>

        {/* Python file picker */}
        <div className="space-y-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest flex items-center gap-1">
              <FileCode2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>
                PYTHON SOURCES{files.length > 0 ? ` · ${files.length}` : ""}
                {loadingTree ? " · loading tree…" : ""}
              </span>
            </span>
            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={fileQuery}
                onChange={(e) => setFileQuery(e.target.value)}
                placeholder="Filter files by path…"
                className="w-full bg-[#181b24] border border-[#272c3d] focus:border-cyan-500 text-white placeholder-zinc-500 pl-9 pr-3 py-2 rounded-xl text-xs font-mono outline-none transition-colors"
              />
            </div>
          </div>

          <div className="max-h-44 overflow-y-auto scrollbar-purple grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-1.5 pr-1">
            {visibleFiles.map((f) => {
              const active = activeFile === f.path;
              return (
                <button
                  key={f.sha + f.path}
                  onClick={() => repo && void analyzeFile(repo, f.path)}
                  title={f.path}
                  className={`flex items-center justify-between gap-2 px-3 py-1.5 rounded-lg border text-[11px] font-mono transition-colors ${
                    active
                      ? "bg-cyan-500/10 border-cyan-500/40 text-cyan-200"
                      : "bg-[#0f1117] border-[#202430] text-zinc-400 hover:text-white hover:border-purple-500/40"
                  }`}
                >
                  <span className="truncate">{f.path}</span>
                  <span className="text-[9px] text-zinc-600 flex-shrink-0">
                    {(f.size / 1024).toFixed(1)}kB
                  </span>
                </button>
              );
            })}
            {!loadingTree && files.length === 0 && (
              <span className="text-xs text-zinc-600 font-mono py-2">
                No .py files in this repository.
              </span>
            )}
          </div>

          {ast && leakCount !== null && (
            <p className="text-[11px] font-mono text-zinc-500">
              CodeGate parsed{" "}
              <span className="text-cyan-400">{activeFile}</span> ·{" "}
              <span className={leakCount > 0 ? "text-amber-400" : "text-emerald-400"}>
                {leakCount} resource leak{leakCount === 1 ? "" : "s"}
              </span>{" "}
              found in this file
            </p>
          )}
        </div>
      </section>

      {/* Main AST Graph Visualizer Canvas */}
      <main className="w-full">
        <AstGraphVisualizer
          tree={ast}
          sourceLabel={sourceLabel}
          loading={loadingAst || loadingTree}
          error={error}
        />
      </main>
    </div>
  );
}
