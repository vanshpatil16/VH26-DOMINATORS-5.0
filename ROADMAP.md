# CodeGate — Product & Scalability Roadmap

Current state (built): deterministic CFG analyzer, autofix, CLI + GUI, ensemble
(semgrep/ruff), GitHub Actions + pre-commit, benchmark vs LLM, admin panel
(MongoDB), persistent analysis server with cache.

## Where CodeGate is today (latency measured)

| Path | Latency |
|---|---|
| CLI one-shot spawn (per request) | ~310 ms |
| **Persistent server, warm miss** | **~4–28 ms** |
| **Persistent server, cache hit** | **~1–16 ms** |
| Batch (N files, warm) | ~3.5 ms/file |

## Sellable-product architecture (target)

```
                        ┌──────────────────────────────────────────────┐
  Users / CI / IDE      │              CodeGate Cloud (per-tenant)      │
                        │                                              │
  ┌─────────┐           │  ┌──────────────┐   ┌─────────────────────┐  │
  │  IDE ext │─────────▶│  │  API gateway │──▶│ Analysis server(s)   │ │
  │  CLI     │─────────▶│  │  auth · quota│   │ (warm, cached, batch) │ │
  │  CI      │─────────▶│  │  rate limit  │   └──────────┬──────────┘  │
  │  Web GUI │─────────▶│  └──────┬───────┘              │             │
  └─────────┘           │         │                      ▼             │
                        │         │            ┌──────────────────┐    │
                        │         └───────────▶│ Results DB (Mongo│    │
                        │                      │ / Postgres)       │    │
                        │                      └──────────────────┘    │
                        └──────────────────────────────────────────────┘
```

## Build order (what's left)

### Tier 1 — Multi-tenant backend (makes it sellable)
1. **Auth** — replace the admin username/password stub with real auth:
   - JWT session tokens (access + refresh), bcrypt password hashing
   - Org/team model: `org → projects → members (owner/admin/member)`
   - API keys for CI/IDE (per-user, scoped to project)
2. **Tenant isolation** — every finding/scan/account doc gets `org_id`;
   Mongo queries always filter by it (prevent cross-tenant reads).
3. **Usage metering** — count `analyze` calls per org per month;
   store in Mongo, expose `GET /api/billing/usage`. Basis for tiers:
   - Free: 1 project, 500 scans/mo
   - Team: 10 projects, 20k scans/mo, admin panel
   - Enterprise: unlimited, on-prem/private-cloud option
4. **Quotas + rate limiting** — token bucket per API key/org on the gateway;
   429 responses with `Retry-After`.

### Tier 2 — Scale the analysis plane
5. **Worker pool** — analysis is CPU-bound; run N server processes behind a
   simple router (`/analyze` fans out). Cache becomes Redis (shared across
   workers) instead of in-memory LRU.
6. **GitHub App integration** — webhook receiver: `push`/`pull_request` →
   scan changed files → post results as PR check + comment (the managed
   version of the existing CI action). Store per-commit fingerprints.
7. **Incremental analysis** — parse once per commit, analyze only changed
   functions (function-level cache keyed by `(repo, func, content-hash)`).

### Tier 3 — Admin/team analytics (extend existing panel)
8. **Per-developer error attribution** — findings joined to commit author
   (via GitHub API) → "who introduced this leak" view + trend.
9. **Leak density / trend charts** — per repo/branch over time (already has
   BranchRisk + HotFiles; add time-series).
10. **Fix-rate tracking** — mark finding as fixed when a later scan no longer
    reports it (fingerprint diff); show team fix velocity.
11. **Notifications** — Slack/Discord webhook per new definite leak.

### Tier 4 — Sellability polish
12. **On-prem deployment** — Dockerfile + docker-compose (server + web + mongo),
    `CODEGATE_LICENSE` env for licensing.
13. **Public docs + pricing page** — pricing tiers, security page.
14. **Data residency option** — region-pinned tenants (for enterprise sales).

## Latency already solved
- Persistent server (warm interpreter) + content-addressed cache + batch API
  → from 310 ms to ~1–4 ms per file for repeat scans.
- Frontend bridge auto-prefers the server (`CODEGATE_SERVER_URL`), falls back
  to spawn.

## What NOT to build (yet)
- LLM-based analysis as a core path (benchmark showed LLM ≈ CodeGate on this
  corpus at 9k tokens vs 0; keep LLM as optional enhancement, not the product)
- Replacing Scalpel/LibCST (already proven sufficient)
- Multi-region global infra before paying customers exist

## Quick start for self-hosting today
```bash
codegate serve --port 8750 --host 0.0.0.0 --shutdown-token <secret>
# GUI/CLI/IDE automatically use it when reachable
```