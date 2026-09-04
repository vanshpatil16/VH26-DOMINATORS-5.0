/**
 * REST surface for the LeakGuard admin panel, backed by MongoDB.
 *
 * Mounted at /api/admin by both the vite dev middleware and the express
 * production server, using the same raw (req, res) style as the CodeGate
 * bridge:
 *
 *   GET    /health                       connection check
 *   GET    /accounts                     watched GitHub accounts
 *   POST   /accounts                     add/update one { login, name, … }
 *   DELETE /accounts/:login              stop watching (drops its findings)
 *   GET    /findings?login=&repo=&…      stored findings, newest first
 *   POST   /findings                     upsert a scan's findings
 *   GET    /scans?login=&limit=          scan history
 *   GET    /stats?login=                 per-level / per-repo / per-branch rollup
 */
import { readJsonBody } from "./codegate-api";
import {
  accounts,
  connectionError,
  findings,
  isConfigured,
  ping,
  scans,
  type AccountDoc,
  type FindingDoc,
} from "./mongo";

interface IncomingFinding {
  source?: "ci" | "live";
  repo?: string;
  branch?: string;
  sha?: string | null;
  event?: string;
  prNumbers?: number[];
  path?: string;
  line?: number;
  level?: "error" | "warning" | "notice";
  title?: string;
  message?: string;
  func?: string | null;
  actor?: string | null;
  at?: string;
  url?: string | null;
}

/** Stable id so re-scanning the same commit updates rather than duplicates. */
function fingerprint(f: IncomingFinding): string {
  return [
    f.repo ?? "",
    f.branch ?? "",
    f.source ?? "ci",
    f.path ?? "",
    f.line ?? 0,
    f.func ?? "",
    f.sha ?? "",
  ].join("|");
}

function json(res: any, status: number, payload: unknown) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(payload));
}

function dbDown(res: any, err: unknown) {
  json(res, 503, {
    ok: false,
    error: err instanceof Error ? err.message : String(err),
    configured: isConfigured(),
    hint: isConfigured()
      ? "MongoDB is unreachable — check the Atlas IP allowlist and MONGODB_URI."
      : "Set MONGODB_URI in frontend/.env to enable persistence.",
  });
}

/** Handles every /api/admin/* request. `rest` is the path after /api/admin. */
export async function handleAdminApi(req: any, res: any, rest: string) {
  const url = new URL(rest || "/", "http://localhost");
  const route = url.pathname.replace(/\/+$/, "") || "/";
  const method = (req.method || "GET").toUpperCase();
  const q = url.searchParams;

  try {
    /* ── health ───────────────────────────────────────────────────────── */
    if (route === "/health") {
      const result = await ping();
      return json(res, result.ok ? 200 : 503, {
        ...result,
        configured: isConfigured(),
        lastError: connectionError(),
      });
    }

    /* ── accounts ─────────────────────────────────────────────────────── */
    if (route === "/accounts" && method === "GET") {
      const col = await accounts();
      const docs = await col.find({}).sort({ addedAt: 1 }).toArray();
      return json(res, 200, { ok: true, accounts: docs });
    }

    if (route === "/accounts" && method === "POST") {
      const body = await readJsonBody(req);
      const login = String(body.login ?? "").trim().replace(/^@/, "");
      if (!login) return json(res, 400, { ok: false, error: "login is required" });

      const col = await accounts();
      const now = new Date().toISOString();
      const doc: Partial<AccountDoc> = {
        login,
        name: body.name ?? null,
        avatarUrl: body.avatarUrl ?? null,
        repoCount: Number(body.repoCount ?? 0),
      };
      await col.updateOne(
        { _id: login.toLowerCase() },
        { $set: doc, $setOnInsert: { addedAt: now, lastScanAt: null } },
        { upsert: true }
      );
      const saved = await col.findOne({ _id: login.toLowerCase() });
      return json(res, 200, { ok: true, account: saved });
    }

    if (route.startsWith("/accounts/") && method === "DELETE") {
      const login = decodeURIComponent(route.slice("/accounts/".length)).toLowerCase();
      if (!login) return json(res, 400, { ok: false, error: "login is required" });

      const [accCol, findCol] = await Promise.all([accounts(), findings()]);
      await accCol.deleteOne({ _id: login });
      const dropped = await findCol.deleteMany({ login });
      return json(res, 200, { ok: true, removed: login, findingsDropped: dropped.deletedCount ?? 0 });
    }

    /* ── findings ─────────────────────────────────────────────────────── */
    if (route === "/findings" && method === "GET") {
      const filter: Record<string, unknown> = {};
      if (q.get("login")) filter.login = q.get("login")!.toLowerCase();
      if (q.get("repo")) filter.repo = q.get("repo");
      if (q.get("branch")) filter.branch = q.get("branch");
      if (q.get("level")) filter.level = q.get("level");
      if (q.get("source")) filter.source = q.get("source");

      const limit = Math.min(Number(q.get("limit") ?? 500), 2000);
      const col = await findings();
      const docs = await col.find(filter).sort({ at: -1 }).limit(limit).toArray();
      return json(res, 200, { ok: true, findings: docs, count: docs.length });
    }

    if (route === "/findings" && method === "POST") {
      const body = await readJsonBody(req);
      const login = String(body.login ?? "").trim().toLowerCase();
      const repo = String(body.repo ?? "").trim();
      const incoming: IncomingFinding[] = Array.isArray(body.findings) ? body.findings : [];
      if (!login || !repo) return json(res, 400, { ok: false, error: "login and repo are required" });

      const now = new Date().toISOString();
      const col = await findings();

      if (incoming.length > 0) {
        const ops = incoming.map(f => {
          const doc: Omit<FindingDoc, "_id" | "firstSeen"> = {
            login,
            repo: f.repo ?? repo,
            branch: f.branch ?? "(unknown)",
            sha: f.sha ?? null,
            event: f.event ?? "push",
            prNumbers: Array.isArray(f.prNumbers) ? f.prNumbers : [],
            source: f.source === "live" ? "live" : "ci",
            path: f.path ?? "",
            line: Number(f.line ?? 0),
            level: f.level ?? "error",
            title: f.title ?? "",
            message: f.message ?? "",
            func: f.func ?? null,
            actor: f.actor ?? null,
            at: f.at ?? now,
            url: f.url ?? null,
            lastSeen: now,
          };
          return {
            updateOne: {
              filter: { _id: fingerprint({ ...f, repo: doc.repo }) },
              update: { $set: doc, $setOnInsert: { firstSeen: now } },
              upsert: true,
            },
          };
        });
        await col.bulkWrite(ops as any, { ordered: false });
      }

      // findings that vanished from a re-scan of the same repo+source are stale
      if (body.replaceScope) {
        const scope: Record<string, unknown> = { login, repo, source: body.replaceScope.source ?? "ci" };
        if (body.replaceScope.branch) scope.branch = body.replaceScope.branch;
        const keep = incoming.map(f => fingerprint({ ...f, repo: f.repo ?? repo }));
        await col.deleteMany({ ...scope, _id: { $nin: keep } } as any);
      }

      const counts = { error: 0, warning: 0, notice: 0 };
      incoming.forEach(f => { counts[(f.level ?? "error") as keyof typeof counts] += 1; });

      const scanCol = await scans();
      await scanCol.insertOne({
        login,
        repo,
        at: now,
        runsInspected: Number(body.runsInspected ?? 0),
        errors: counts.error,
        warnings: counts.warning,
        notices: counts.notice,
        source: body.source === "live" ? "live" : "ci",
        branch: body.branch ?? null,
      });

      const accCol = await accounts();
      await accCol.updateOne({ _id: login }, { $set: { lastScanAt: now } });

      return json(res, 200, { ok: true, stored: incoming.length, counts });
    }

    /* ── scan history ─────────────────────────────────────────────────── */
    if (route === "/scans" && method === "GET") {
      const filter: Record<string, unknown> = {};
      if (q.get("login")) filter.login = q.get("login")!.toLowerCase();
      if (q.get("repo")) filter.repo = q.get("repo");
      const limit = Math.min(Number(q.get("limit") ?? 50), 500);

      const col = await scans();
      const docs = await col.find(filter).sort({ at: -1 }).limit(limit).toArray();
      return json(res, 200, { ok: true, scans: docs });
    }

    /* ── rollups ──────────────────────────────────────────────────────── */
    if (route === "/stats" && method === "GET") {
      const match: Record<string, unknown> = {};
      if (q.get("login")) match.login = q.get("login")!.toLowerCase();

      const col = await findings();
      const [byLevel, byRepo, byBranch] = await Promise.all([
        col.aggregate([{ $match: match }, { $group: { _id: "$level", count: { $sum: 1 } } }]).toArray(),
        col.aggregate([
          { $match: match },
          { $group: { _id: "$repo", total: { $sum: 1 }, errors: { $sum: { $cond: [{ $eq: ["$level", "error"] }, 1, 0] } } } },
          { $sort: { errors: -1, total: -1 } },
          { $limit: 50 },
        ]).toArray(),
        col.aggregate([
          { $match: match },
          { $group: { _id: { repo: "$repo", branch: "$branch" }, total: { $sum: 1 }, errors: { $sum: { $cond: [{ $eq: ["$level", "error"] }, 1, 0] } } } },
          { $sort: { errors: -1, total: -1 } },
          { $limit: 100 },
        ]).toArray(),
      ]);

      return json(res, 200, { ok: true, byLevel, byRepo, byBranch });
    }

    return json(res, 404, { ok: false, error: `no admin route for ${method} ${route}` });
  } catch (err) {
    return dbDown(res, err);
  }
}
