/**
 * MongoDB connection for the LeakGuard admin panel.
 *
 * One lazily-created client is shared by the vite dev middleware and the
 * express production server. Every call site gets a typed collection, and a
 * connection failure surfaces as a normal error rather than crashing the
 * server — the UI falls back to browser storage when the database is down.
 *
 * Configure with MONGODB_URI (and optionally MONGODB_DB) in frontend/.env.
 */
import { MongoClient, type Collection, type Db } from "mongodb";
import dotenv from "dotenv";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// server/ lives one level under the vite root, and .env sits beside package.json
dotenv.config({ path: path.resolve(__dirname, "..", ".env") });
dotenv.config({ path: path.resolve(__dirname, "..", "..", ".env") });

export interface AccountDoc {
  _id: string;              // github login, lowercased
  login: string;            // original casing
  name: string | null;
  avatarUrl: string | null;
  addedAt: string;
  lastScanAt: string | null;
  repoCount: number;
}

export interface FindingDoc {
  _id: string;              // stable fingerprint, so rescans update in place
  login: string;
  repo: string;             // owner/name
  branch: string;
  sha: string | null;
  event: string;            // push | pull_request | scan
  prNumbers: number[];
  source: "ci" | "live";
  path: string;
  line: number;
  level: "error" | "warning" | "notice";
  title: string;
  message: string;
  func: string | null;
  actor: string | null;
  at: string;               // when the run/scan happened
  url: string | null;
  firstSeen: string;
  lastSeen: string;
}

export interface ScanDoc {
  _id?: unknown;
  login: string;
  repo: string;
  at: string;
  runsInspected: number;
  errors: number;
  warnings: number;
  notices: number;
  source: "ci" | "live";
  branch: string | null;
}

let client: MongoClient | null = null;
let connecting: Promise<Db> | null = null;
let lastError: string | null = null;

export function isConfigured(): boolean {
  return !!process.env.MONGODB_URI;
}

export function connectionError(): string | null {
  return lastError;
}

export async function getDb(): Promise<Db> {
  const uri = process.env.MONGODB_URI;
  if (!uri) {
    lastError = "MONGODB_URI is not set — add it to frontend/.env";
    throw new Error(lastError);
  }

  if (client) return client.db(process.env.MONGODB_DB || "leakguard");
  if (connecting) return connecting;

  connecting = (async () => {
    // SRV lookups (mongodb+srv://) intermittently fail on flaky resolvers, so
    // a failed connect is retried before it is reported as down.
    let lastErr: unknown = null;

    for (let attempt = 1; attempt <= 3; attempt++) {
      const c = new MongoClient(uri, {
        serverSelectionTimeoutMS: 8000,
        connectTimeoutMS: 8000,
      });
      try {
        await c.connect();
        client = c;
        lastError = null;
        const db = c.db(process.env.MONGODB_DB || "leakguard");
        await ensureIndexes(db);
        return db;
      } catch (err) {
        lastErr = err;
        await c.close().catch(() => {});
        if (attempt < 3) await new Promise(r => setTimeout(r, 400 * attempt));
      }
    }

    lastError = lastErr instanceof Error ? lastErr.message : String(lastErr);
    connecting = null;
    throw lastErr instanceof Error ? lastErr : new Error(lastError);
  })();

  return connecting;
}

async function ensureIndexes(db: Db) {
  await Promise.all([
    db.collection<FindingDoc>("findings").createIndex({ login: 1, repo: 1, branch: 1 }),
    db.collection<FindingDoc>("findings").createIndex({ level: 1 }),
    db.collection<FindingDoc>("findings").createIndex({ at: -1 }),
    db.collection<ScanDoc>("scans").createIndex({ login: 1, at: -1 }),
  ]);
}

export async function accounts(): Promise<Collection<AccountDoc>> {
  return (await getDb()).collection<AccountDoc>("accounts");
}

export async function findings(): Promise<Collection<FindingDoc>> {
  return (await getDb()).collection<FindingDoc>("findings");
}

export async function scans(): Promise<Collection<ScanDoc>> {
  return (await getDb()).collection<ScanDoc>("scans");
}

/** Round-trip check used by GET /api/admin/health. */
export async function ping(): Promise<{ ok: boolean; db?: string; error?: string; ms?: number }> {
  const started = Date.now();
  try {
    const db = await getDb();
    await db.command({ ping: 1 });
    return { ok: true, db: db.databaseName, ms: Date.now() - started };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function closeMongo() {
  if (client) {
    await client.close().catch(() => {});
    client = null;
    connecting = null;
  }
}
