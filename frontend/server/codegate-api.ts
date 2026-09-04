/**
 * CodeGate bridge: spawns the Python analyzer and returns its JSON.
 * Used by the vite dev middleware and the express production server.
 *
 * Requires: pip install -e ..  (from the repo root)
 * Optional: CODEGATE_PYTHON env var to pick the interpreter.
 */
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..");

export interface CodegateRequest {
  source: string;
  filename?: string;
  fix?: boolean;
  ensemble?: boolean;
}

export async function runCodegateAnalysis(req: CodegateRequest): Promise<unknown> {
  const py = process.env.CODEGATE_PYTHON || (process.platform === "win32" ? "python" : "python3");
  const args = ["-m", "codegate.webapi", "-"];
  if (req.fix) args.push("--fix");
  if (req.ensemble) args.push("--ensemble");
  if (req.filename) args.push("--filename", req.filename);

  return new Promise((resolve, reject) => {
    const child = spawn(py, args, {
      cwd: REPO_ROOT,
      env: process.env,
      shell: process.platform === "win32",
    });
    let out = "";
    let err = "";
    child.stdout.on("data", (d) => (out += d.toString()));
    child.stderr.on("data", (d) => (err += d.toString()));
    child.on("error", (e) =>
      reject(
        new Error(
          `Cannot start CodeGate (${py} ${args.join(" ")}): ${e.message}. ` +
            `Install it first: cd repo root && pip install -e . — or set CODEGATE_PYTHON.`,
        ),
      ),
    );
    child.on("close", (code) => {
      try {
        const firstBrace = out.indexOf("{");
        const lastBrace = out.lastIndexOf("}");
        if (firstBrace !== -1 && lastBrace > firstBrace) {
          const jsonStr = out.slice(firstBrace, lastBrace + 1);
          resolve(JSON.parse(jsonStr));
          return;
        }
        resolve(JSON.parse(out));
      } catch {
        if (out.trim().startsWith("{")) {
          try {
            resolve(JSON.parse(out.trim()));
            return;
          } catch {
            // fall through
          }
        }
        reject(
          new Error(
            `CodeGate exited with code ${code}. stderr: ${err.slice(0, 400) || "(empty)"} stdout: ${out.slice(0, 400)}`,
          ),
        );
      }
    });
    child.stdin.write(Buffer.from(req.source, "utf-8"));
    child.stdin.end();
  });
}

export function readJsonBody(req: any): Promise<any> {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk: Buffer) => {
      body += chunk.toString();
      if (body.length > 2_000_000) {
        reject(new Error("payload too large"));
        req.destroy();
      }
    });
    req.on("end", () => {
      try {
        resolve(JSON.parse(body || "{}"));
      } catch (e) {
        reject(new Error("invalid JSON body"));
      }
    });
    req.on("error", reject);
  });
}

/** Handler for POST /api/codegate/analyze (raw http request/response). */
export async function handleCodegateAnalyze(req: any, res: any) {
  try {
    const body = await readJsonBody(req);
    const source = typeof body.source === "string" ? body.source : "";
    if (!source.trim()) {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: false, error: "source is required" }));
      return;
    }
    const result = await runCodegateAnalysis({
      source,
      filename: typeof body.filename === "string" ? body.filename : "input.py",
      fix: Boolean(body.fix),
      ensemble: Boolean(body.ensemble),
    });
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(result));
  } catch (e: any) {
    res.writeHead(500, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: false, error: e?.message || String(e) }));
  }
}
