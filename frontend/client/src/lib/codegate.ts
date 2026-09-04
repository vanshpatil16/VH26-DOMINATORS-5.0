/**
 * CodeGate API client + types.
 * Talks to POST /api/codegate/analyze (vite dev middleware / express route),
 * which spawns `python -m codegate.webapi` under the hood.
 */

export interface TrajectoryStep {
  id: number;
  phase: string;
  title: string;
  status: "ok" | "error" | "warn" | "skipped";
  detail: string;
  durationMs: number;
  data: Record<string, unknown>;
}

export interface Leak {
  file: string;
  func: string;
  line: number;
  col: number;
  var: string;
  acquire: string;
  release: string;
  message: string;
  acquire_line: number;
  kind: "path" | "exception" | "path+exception";
  leaking_paths: number[][];
  safe_paths: number[][];
  exception_note: string;
  path_sources?: string[][];
  safe_path_sources?: string[][];
}

export interface AstNode {
  id: string;
  type: string;
  label: string;
  line: number | null;
  children: AstNode[];
  truncated?: boolean;
}

export interface CfgBlock {
  id: number;
  statements: string[];
  lineStart: number | null;
  lineEnd: number | null;
  isEntry: boolean;
  isExit: boolean;
  funcCalls: { name: string; lineno: number; col_offset: number; params: string[] }[];
  tag: "leak" | "safe" | null;
}

export interface CfgEdge {
  from: number;
  to: number;
  label: string | null;
}

export interface CfgFunction {
  name: string;
  blocks: CfgBlock[];
  edges: CfgEdge[];
  leakBlocks: number[];
  safeBlocks: number[];
  hasLeak: boolean;
}

export interface EnsembleFinding {
  tool: string;
  rule: string | null;
  line: number | null;
  col: number | null;
  message: string | null;
  name: string | null;
  verdict: "confirmed_path_leak" | "confirmed_exception_unsafe" | "refuted_safe" | "unverified";
  evidence: Record<string, unknown>;
}

export interface EnsembleResult {
  semgrep: { available: boolean; findings: Record<string, unknown>[]; note?: string };
  ruff: { available: boolean; findings: Record<string, unknown>[]; note?: string };
  syntacticPrefilter?: { findings: number };
  verified: EnsembleFinding[];
  counts: Record<string, number>;
  noiseReductionPct: number;
}

export interface CodegateResult {
  ok: boolean;
  error?: string;
  filename: string;
  summary: {
    leakCount: number;
    pathLeaks: number;
    exceptionLeaks: number;
    acquires: number;
    functionsAnalyzed: number;
    analysisMs: number;
    trajectorySteps: number;
  };
  leaks: Leak[];
  trajectory: TrajectoryStep[];
  ast: AstNode | null;
  cfg: { functions: CfgFunction[] };
  fix?: { applied: boolean; code?: string; diff?: string; reason?: string };
  ensemble?: EnsembleResult | null;
}

export async function runCodegateAnalysis(
  source: string,
  filename: string,
  fix: boolean,
  ensemble = false,
): Promise<CodegateResult> {
  const res = await fetch("/api/codegate/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source, filename, fix, ensemble }),
  });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      msg = j.error || msg;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return (await res.json()) as CodegateResult;
}

/** Demo snippets for the GUI picker. */
export const DEMOS: { name: string; filename: string; code: string }[] = [
  {
    name: "Branch leak",
    filename: "read_file.py",
    code: `def read_file(path):
    f = open(path)

    data = f.read()

    if not data:
        return None   # LEAK: f never closed

    f.close()
    return data`,
  },
  {
    name: "Exception leak",
    filename: "download.py",
    code: `def download(url):
    f = open(url)
    data = f.read()   # if this raises, f leaks
    f.close()
    return data`,
  },
  {
    name: "Socket + alias",
    filename: "socket_leak.py",
    code: `import socket

def fetch(host, port):
    s = socket.socket()
    g = s
    data = g.recv(1024)
    if not data:
        return None   # LEAK: s never closed
    g.close()
    return data

def fetch_safe(host, port):
    s = socket.socket()
    try:
        s.connect((host, port))
        return s.recv(1024)
    finally:
        s.close()`,
  },
  {
    name: "Match statement",
    filename: "dispatch.py",
    code: `def dispatch(command, path):
    match command:
        case "open":
            fh = open(path)
            return fh.read()   # LEAK: fh never closed
        case "safe":
            fh = open(path)
            fh.close()
            return "ok"
        case _:
            return "unknown"`,
  },
  {
    name: "Clean code",
    filename: "clean.py",
    code: `def read_all(path):
    with open(path) as f:
        data = f.read()
    return data

def read_guarded(path):
    f = open(path)
    try:
        return f.read()
    finally:
        f.close()`,
  },
];
