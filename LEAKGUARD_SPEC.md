# LeakGuard — Build Spec for Claude Code

You are building **LeakGuard**, a hackathon prototype, in 30 hours. Read this entire
document before writing code. Build in the order given. Do not skip ahead to the ML.

---

## 0. Mission in one paragraph

LeakGuard is a CI/CD-integrated static analyzer for **Python** that parses source into an
AST, builds a control-flow graph, and verifies that every opened resource (file, socket,
DB connection, subprocess, lock) is closed on **every** execution path — including early
returns, exception branches, and `async` paths. Provable leaks deterministically fail the
build. Cases that cannot be proven get an **explainable confidence score** from a small
logistic-regression model trained on a mutation-generated corpus, and are reported as
warnings rather than hard failures. The model is recalibrated **offline only** so CI stays
reproducible.

**Non-negotiable design law:** the same commit SHA must always produce the same verdict.
No online learning. No model updates at scan time. Ever.

---

## 1. Problem statement (as given, with correction)

> Unclosed resources — database connections left open, file objects never closed, sockets
> that never disconnect, caches with no eviction policy — are one of the most common and
> insidious causes of production failure. They don't crash anything immediately; they cause
> a slow bleed until a server falls over weeks later with no obvious single cause. Most
> teams discover them reactively via production alerts at 3 AM.
>
> Build a CI/CD-integrated static analyzer — a pre-commit hook or GitHub Action — that
> parses source code, tracks every resource-opening expression, and verifies each one is
> properly closed across all realistic code paths. If it isn't, the build fails with a
> precise, actionable report.
>
> **The core tension:** be aggressive enough to catch real leaks, but not so aggressive
> that teams disable the tool by week two. Scoring on false-positive discipline matters as
> much as raw detection.

### MVP requirements
1. Single-language parser — **Python** (the original PS said "Java or Go" on page 2 and
   "develop a tool for python" on page 3; Python is the target, ignore Java/Go entirely).
2. AST-based resource tracking — **not** regex or string matching. Judges will
   specifically probe with code that looks leaky in plain text but isn't, and vice versa.
3. Close-path verification accounting for early returns, exception paths, and
   reassignment/escape.
4. CI integration that genuinely **blocks a build** (exit code 1), not a warning in a log.

### Stretch goals
Auto-generated fix patches · false-positive benchmarking on seeded repos · VS Code
extension · **confidence scoring instead of binary pass/fail** ← this is our differentiator.

### Deliverables
1. Installable GitHub Action **and** pre-commit hook (not a manual demo script)
2. Sample repo with 5–10 deliberately seeded leaks the tool catches
3. Write-up with real FP/FN rates and an honest account of where the tool breaks down

---

## 2. Answers to the two questions that can sink the demo

Put both of these in the README verbatim. Judges will ask.

### "Python is garbage-collected — why is this even a bug?"
- Refcount-triggered cleanup is a **CPython implementation detail**. PyPy, Jython and
  GraalPy do not do it. Relying on it is non-portable.
- It never fires when the object is in a reference cycle, held on `self`, or appended to a
  container that outlives the scope.
- Timing is non-deterministic: a loop opening 5,000 files exhausts the fd limit long
  before collection catches up.
- It does not apply at all to the things that actually take services down: pooled DB
  connections, sockets, `subprocess.Popen` pipes, `threading.Lock`, `multiprocessing.Pool`.
- CPython itself treats this as a bug — that is why `ResourceWarning` exists.

### "How is this better than existing tools?"
- **pylint `R1732`** — syntactic only; catches `open()` outside `with`, nothing else. No
  path sensitivity, no early-return awareness, no exception paths.
- **leakaudit** (github.com/kriskimmerle/leakaudit) — closest competitor, 15 AST rules,
  zero deps. But it is rule-based with **no CFG**, so it cannot reason about which paths
  reach a close. Run it as a baseline and beat it on the adversarial corpus.
- **bandit / flake8-bugbear** — do not do path analysis at all; will find near-zero.
- **CodeQL** — real interprocedural dataflow, but needs a database build, takes minutes
  (unusable as a pre-commit hook), and ships one fixed FP tolerance for every team.
- **Our edge:** fast enough for pre-commit, CFG-path-aware rather than syntactic, handles
  async, and the only one whose false-positive threshold is **calibrated to the target
  repo's own conventions**.

Reference numbers to cite (Java literature, since no Python benchmark exists): on the
JLeaks dataset PMD achieves a 43.5% bug-detection rate at 5.1% false-alarm rate; the
LLM-augmented InferROI reaches 62.5% at 19.5%. If our Python numbers land in that range we
are at published-research level.

---

## 3. Architecture

```
Python source
     │
     ▼
[1] ast.parse ──────────► AST
     │
     ▼
[2] Resource Detector ──► open-sites (registry-matched, deterministic)
     │
     ▼
[3] Symbol Tracker ─────► handle ↔ resource binding, SSA-ish versioning
     │
     ▼
[4] CFG Builder ────────► basic blocks + edges (normal, exception, loop-back, async)
     │
     ▼
[5] Path Verifier ──────► for each open-site: which exit paths lack a close?
     │
     ├── all paths closed ─────────────────► SAFE           (silent)
     ├── some path provably leaks, no escape ─► DEFINITE_LEAK (exit 1, blocks build)
     └── cannot prove (escape / opaque call) ─► UNKNOWN
                                                  │
                                                  ▼
                                    [6] Feature Extraction (~14 features)
                                                  │
                                                  ▼
                                    [7] Logistic Regression + Platt calibration
                                                  │
                                                  ▼
                                    [8] Risk = P(leak) × exposure
                                                  │
                                    ┌─────────────┼─────────────┐
                                    ▼             ▼             ▼
                                 LIKELY        POSSIBLE       SAFE
                                    │             │             │
                                    └─────────────┴─────────────┘
                                                  ▼
                                    [9] Explainable report (CLI + SARIF)
                                                  ▼
                                   [10] CI gate — exit 0 / 1
```

Offline learning loop (never runs at scan time):

```
suppression comments in git  ─┐
explicit `leakguard feedback` ─┼─► feedback DB ─► retrain candidate ─► eval on holdout
git-history leak-fix commits ─┘                                            │
                                                          better? ─────────┤
                                                             │             │
                                                            yes            no
                                                             │             │
                                                    write model.json    reject
                                                    as a PR diff
```

---

## 4. Build order and hour budget

| Phase | Hours | Deliverable | Cuttable? |
|---|---|---|---|
| P0-a | 0–1 | Repo scaffold, CLI skeleton, resource registry | No |
| P0-b | 1–3 | AST walk → open-site detection + symbol tracking | No |
| P0-c | 3–9 | **CFG builder + path verifier** ← the whole project | Never |
| P0-d | 9–10.5 | Intra-class ownership rule (biggest FP source) | Never |
| P0-e | 10.5–13 | GitHub Action + pre-commit hook + SARIF + exit codes | No |
| P1-a | 2–5 (bg) | Dataset harvest script — **start early, runs in background** | No |
| P1-b | 13–17 | Mutation corpus + feature extraction + logistic regression | Degrade to hand-tuned weights |
| P1-c | 17–20 | Runtime oracle (`ResourceWarning` + audit hooks) | Keep — carries the write-up |
| P2-a | 20–23 | Function summaries / interprocedural fixpoint | Yes → fall back to UNKNOWN |
| P2-b | 23–25 | Git-history per-repo calibration | Yes |
| P3-a | 25–26.5 | Conformal threshold + reliability diagram | Yes |
| P3-b | 26.5–27.5 | Risk weighting + counterfactual line | Yes |
| P3-c | 27.5–28 | Uncertainty-sampled feedback | Yes |
| — | 28–30 | Seeded sample repo, write-up, demo rehearsal | No |

**Hard checkpoint at hour 18:** if the path verifier is still shaky, cut the ML entirely
and ship deterministic detection with hand-tuned weights. Detection working end-to-end
beats scoring bolted onto something broken.

---

## 5. Module specs

### [1] Resource registry — `leakguard/registry.py`

Deterministic, YAML-configurable. Do **not** use ML to decide what is a resource.

```yaml
resources:
  - call: "open"                  ; type: FILE      ; close: ["close"]      ; weight: 1.0
  - call: "io.open"               ; type: FILE      ; close: ["close"]      ; weight: 1.0
  - call: "codecs.open"           ; type: FILE      ; close: ["close"]      ; weight: 1.0
  - call: "tempfile.NamedTemporaryFile" ; type: FILE; close: ["close"]      ; weight: 1.0
  - call: "socket.socket"         ; type: SOCKET    ; close: ["close","shutdown"] ; weight: 2.0
  - call: "socket.create_connection" ; type: SOCKET ; close: ["close"]      ; weight: 2.0
  - call: "sqlite3.connect"       ; type: DB        ; close: ["close"]      ; weight: 3.0
  - call: "psycopg2.connect"      ; type: DB        ; close: ["close"]      ; weight: 3.0
  - call: "pymysql.connect"       ; type: DB        ; close: ["close"]      ; weight: 3.0
  - call: "subprocess.Popen"      ; type: PROCESS   ; close: ["wait","communicate","terminate","kill","__exit__"] ; weight: 2.5
  - call: "requests.Session"      ; type: SESSION   ; close: ["close"]      ; weight: 1.5
  - call: "urllib.request.urlopen"; type: SOCKET    ; close: ["close"]      ; weight: 2.0
  - call: "aiohttp.ClientSession" ; type: ASYNC_SESSION ; close: ["close"]  ; weight: 2.0 ; async: true
  - call: "asyncio.open_connection" ; type: ASYNC_SOCKET ; close: ["close"] ; weight: 2.0 ; async: true
  - call: "threading.Lock"        ; type: LOCK      ; close: ["release"]    ; weight: 1.5
  - call: "multiprocessing.Pool"  ; type: POOL      ; close: ["close","terminate","join"] ; weight: 2.5
  - call: "zipfile.ZipFile"       ; type: FILE      ; close: ["close"]      ; weight: 1.0
  - call: "shelve.open"           ; type: FILE      ; close: ["close"]      ; weight: 1.0
```

Resolve aliases: `import socket as sk` → `sk.socket` must match. Track `from x import y`.

### [3] Safe-construct recognizer

These must **all** be recognized as safe, or you will drown in false positives:

- `with open(p) as f:` and `async with`
- `with a() as x, b() as y:` (multiple items)
- `try: ... finally: f.close()`
- `contextlib.closing(x)`
- `contextlib.suppress` wrapping a close
- `contextlib.ExitStack().enter_context(f)` / `AsyncExitStack`
- `@contextmanager` generator where cleanup follows the `yield` (also inside its `finally`)
- pytest yield-fixtures (`@pytest.fixture` + `yield`)
- `atexit.register(f.close)`
- `weakref.finalize(obj, f.close)`

### [4] CFG builder

Nodes = basic blocks. Edge kinds: `NORMAL`, `TRUE`, `FALSE`, `EXCEPT`, `FINALLY`,
`LOOP_BACK`, `BREAK`, `CONTINUE`, `RETURN`, `RAISE`, `AWAIT`.

Critical detail: from **every statement that can raise** between open and close, add an
`EXCEPT` edge to the enclosing handler or to function exit. That is what makes
`try/finally` distinguishable from `try/except`. Handle `else` clauses on `for`/`while`/
`try`. Handle `with` as an implicit `try/finally`.

### [5] Path verifier

Backward reachability from each function exit to each open-site. An open-site is a
**proven leak** if there exists at least one exit path with no close on it, AND the handle
does not escape. Cap path enumeration (e.g. 10k paths) and fall back to a dataflow
lattice `{OPEN, CLOSED, MAYBE_CLOSED}` for pathological functions.

### [5b] Escape analysis + intra-class ownership

Escapes if: returned, `yield`ed, assigned to `self.X` / global / nonlocal, appended to a
container, or passed as an argument to an unresolved call. Escaped ⇒ `UNKNOWN`, never
`DEFINITE_LEAK`.

**Intra-class rule** (highest-value single rule in the codebase):
`self.conn = sqlite3.connect(...)` in `__init__` is the biggest FP source in real Python.
- If the enclosing class defines `close()`, `__exit__`, `__del__`, `shutdown()`, `stop()`,
  or `dispose()` whose body closes that same attribute → **SAFE**.
- If no method in the class ever closes it → **genuine high-value leak** that pylint and
  leakaudit both miss entirely. Make this a demo slide.

### [6] Feature vector (~14 features, all deterministic)

```python
FEATURES = [
    "leaking_path_fraction",       # float 0-1: exit paths with no close / total
    "escapes_return",              # bool
    "escapes_self_attr",           # bool
    "escapes_container",           # bool
    "escapes_call_arg",            # bool
    "callee_closes_param",         # bool, from function summaries (P2)
    "close_present_but_unguarded", # close exists, not in finally/with
    "in_loop",                     # open-site inside for/while
    "raising_call_between",        # a call that can raise sits between open & close
    "reassigned_before_close",     # handle rebound, orphaning the first
    "resource_type_weight",        # from registry
    "is_test_or_script_file",      # test_*.py, conftest.py, __main__ block
    "is_async_resource",           # async: true in registry
    "callee_name_suggests_close",  # arg passed to *close*/*shutdown*/*cleanup*/*release*
]
```

### [7] Model

Logistic regression, ~15 weights, shipped as `model.json`. Fit **Platt scaling** on a
held-out set; report a reliability diagram and Brier score. Then derive the gate threshold
via **split conformal prediction** from a configured tolerance:

```yaml
leakguard:
  max_false_alarm_rate: 0.05
```

so the threshold is derived from a guarantee, not hand-picked. This is the direct answer
to the PS's "teams disable noisy analyzers" tension.

### [8] Risk = P(leak) × exposure

Exposure multiplier from: in-loop, inside a function with a framework route decorator
(`@app.route`, `@router.get`), call-graph fan-in, and `resource_type_weight`. **Gate on
risk, rank the report by risk.** A leaked DB connection in a Flask handler is not the same
finding as a leaked file in a one-shot script.

### [9] Report format

```
DEFINITE LEAK  risk 2.7  (p=0.97 × exposure 2.8)
  sqlite3.connect() opened at api/handlers.py:42  [handle: conn]
  ├ 2 of 3 exit paths reach return without close      (+0.34)
  ├ early return at line 47 bypasses close at line 58 (+0.29)
  ├ handle does not escape function scope             (+0.28)
  ├ no finally/with wrapping the open site            (+0.21)
  └ inside @app.route handler — high exposure         (×2.8)

  Confidence would drop 0.97 → 0.06 if the open site were wrapped in `with`.
  Suppress: # leakguard: ignore — <reason>
```

The counterfactual line falls straight out of a linear model by flipping one feature, and
it doubles as the seed for the auto-fix stretch goal. Emit **SARIF** too — GitHub renders
it as inline PR annotations natively and it makes the prototype look like a real product.

### [10] CI gate

`DEFINITE_LEAK` → exit 1. `LIKELY` above conformal threshold → exit 1 (configurable).
`POSSIBLE` / `UNKNOWN` → exit 0, reported as warnings. Ship both a
`action.yml` GitHub Action and a `.pre-commit-hooks.yaml` entry.

---

## 6. Dataset pipeline

**Context to state in the write-up:** no Python resource-leak benchmark exists. JLeaks
(1,094 leaks from 321 Java projects) and DroidLeaks are Java-only. We are building the
first labeled Python resource-leak benchmark. The mutation pipeline is not a shortcut —
it is the only option.

### Source repos

Clone these to `corpus/repos/`. Pure Python, heavy resource usage, permissive licenses,
runnable test suites.

| Repo | Why | License |
|---|---|---|
| `psf/requests` + `urllib3/urllib3` | sockets, sessions, pooling | Apache-2.0 / MIT |
| `httpie/cli` | files + network + subprocess, readable | BSD-3 |
| `scrapy/scrapy` | sockets, files, connection reuse | BSD-3 |
| `yt-dlp/yt-dlp` | very heavy file I/O, thousands of open-sites | Unlicense |
| `aio-libs/aiohttp` | **async** resources — our differentiator | Apache-2.0 |
| `mitmproxy/mitmproxy` | sockets, TLS, long-lived connections | MIT |
| `borgbackup/borg` | fds at scale, careful cleanup code | BSD-3 |
| `pallets/werkzeug` | server sockets, file uploads | BSD-3 |
| `paramiko/paramiko` | sockets + sftp + threads (analyze only, LGPL — do not vendor) | LGPL |
| `python/cpython` → `Lib/` only | **precision oracle**, see below | PSF |

**CPython `Lib/` is the precision test.** Its test suite already runs clean under
`-W error::ResourceWarning`. Any finding LeakGuard produces there is either a real bug or
a false positive. If we flag 400 things in `Lib/`, our FP rate is terrible and we find out
before the judges do. Free precision check on ~300k lines.

Secondary source: **BugsInPy** (github.com/soarsmu/BugsInPy) — 501 real bugs from 17
Python projects (pandas, keras, matplotlib, scrapy, ansible, youtube-dl, tornado, black,
fastapi, httpie…), each with a unified-diff patch and buggy/fixed commit IDs. Grep those
patches for close/`with`/`finally` changes; low yield but every hit is pre-verified ground
truth worth naming in the write-up.

### Tier 1 — mutation corpus (~3,000 positives, ~3,000 negatives)

Take safe resource-handling sites from the repos above (negatives), apply an AST-level
mutation to produce a leak with a known line number (positives). The mutator knows exactly
which line it broke — that is the label.

**Balance the operators. Cap each at ~20% of the positive class**, or the model learns one
feature and collapses on the rest.

### Tier 2 — git-history mining (~200 strong positives)

```python
from pydriller import Repository

PATTERNS = [
    (r'^\+.*\.close\(\)',                      'close_added'),
    (r'^\+\s*with\s+.*\sas\s',                 'with_added'),
    (r'^\+\s*(try|finally)\s*:',               'finally_added'),
    (r'^\+.*contextlib\.(closing|ExitStack)',  'ctxmgr_added'),
    (r'^\+.*await\s+.*\.close\(\)',            'async_close_added'),
]
KEYWORDS = ('leak', 'unclosed', 'file descriptor', ' fd ', 'resourcewarning',
            'connection pool', 'exhaust', 'zombie', 'too many open files')

# For each commit touching .py files:
#   - require small diff (< 30 changed lines) → focused cleanup, not a refactor
#   - pre-image of a hunk that ADDS cleanup == a confirmed leak, label 1
#   - commit message matches KEYWORDS  → strong positive
#   - pattern match only               → weak positive (lower sample weight)
```

This also powers **per-repo calibration**: LeakGuard tunes itself against the target
repo's own history before its first scan. Regularize per-repo weights toward the global
mutant-trained weights (L2 pull) so a 40-commit repo doesn't overfit.

### Tier 3 — runtime oracle (~30 verified, high value)

```bash
python -X dev -W error::ResourceWarning -m pytest
```

`-X dev` enables `tracemalloc`, so `ResourceWarning` carries the **allocation traceback** —
the exact file and line where the leaked resource was opened. For non-file resources use
`sys.addaudithook` (stdlib 3.8+) on `socket.__new__`, `open`, `subprocess.Popen`, pair
open events against closes, and dump survivors at process exit.

What this buys:
- **Honest FN measurement** — every runtime-caught resource our static pass missed is a
  documented false negative with a line number. Deliverable 3 asks exactly for this.
- **UNKNOWN resolution** — a site we couldn't prove because the handle escaped into
  `process(f)` becomes decided the moment we observe it at runtime.
- **The demo moment:** `leakguard verify` prints
  `static flagged 7 · runtime confirmed 6 · found 1 we missed at db.py:88`.

Framing: *static analysis proposes, dynamic execution disposes.*

### Two things that will silently ruin the numbers

1. **Split by repository, not by file.** Duplicated corpora inflate reported metrics by up
   to 100%. Train on 8 repos, hold out 2. MinHash-dedup the mutant pool — vendored copies
   of `urllib3` appear in half these projects.
2. **Balance mutation operators** (see cap above).

---

## 7. Mutation operators — exact specs

Each operator is an `ast.NodeTransformer`. Emit a JSONL record per mutant:

```json
{"id":"m0417","repo":"httpie","file":"core.py","func":"download",
 "operator":"insert_early_return","open_line":42,"leak_line":47,
 "label":1,"orig_sha":"...","mutant_path":"corpus/mutants/m0417.py"}
```

### M1 — `with` → bare open (cap 20%)
```python
# before (label 0)                    # after (label 1)
with open(p) as f:                    f = open(p)
    data = f.read()                   data = f.read()
```

### M2 — delete close on one branch (cap 20%)
```python
f = open(p)                           f = open(p)
if cond:                              if cond:
    f.close(); return                     return          # ← leak
f.close()                             f.close()
```

### M3 — insert early return between open and close (cap 20%)
```python
f = open(p)                           f = open(p)
data = f.read()                       if not validate(p):
f.close()                                 return None     # ← leak
                                      data = f.read()
                                      f.close()
```

### M4 — move close inside a raising `try` (cap 15%)
```python
f = open(p)                           f = open(p)
try:                                  try:
    risky()                               risky()
finally:                                  f.close()       # ← skipped on raise
    f.close()                         except Exception:
                                          pass
```

### M5 — close only on the success path (cap 10%)
```python
try:                                  try:
    f = open(p); use(f)                   f = open(p); use(f); f.close()
finally:                              except OSError:
    f.close()                             log()           # ← leak on this path
```

### M6 — reassign before close (cap 10%)
```python
f = open(p); f.close()                f = open(p)         # ← first handle orphaned
g = open(q); g.close()                f = open(q)
                                      f.close()
```

### M7 — hoist open into a loop (cap 5%)
```python
with open(p) as f:                    for p in paths:
    for line in f: ...                    f = open(p)     # ← fd exhaustion
                                          process(f)
```

### M8 — async close removal (async repos only)
```python
async with aiohttp.ClientSession() as s:   s = aiohttp.ClientSession()
    await s.get(u)                         await s.get(u)  # ← never closed
```

### M9 — `ExitStack` → bare (safe→leak, tests the hard recognizer)
```python
with ExitStack() as st:               f = open(p)         # ← leak
    f = st.enter_context(open(p))
```

### M10 — remove the closer method from a class
```python
class C:                              class C:
    def __init__(s): s.db = conn()        def __init__(s): s.db = conn()
    def close(s): s.db.close()            # ← closer deleted, now a real leak
```

---

## 8. Adversarial corpus — hand-write these

`corpus/adversarial/safe/` (~40 files) and `corpus/adversarial/leaky/` (~15 files).
**This is the part that decides the demo.** The PS explicitly warns that a judge will probe
with code that looks leaky in text but isn't, and vice versa. Every one of these is a
slide.

### SAFE but looks leaky — must NOT be flagged

```python
# A1 ExitStack
stack = contextlib.ExitStack()
f = stack.enter_context(open(p))          # closed when stack unwinds

# A2 closing()
with contextlib.closing(urlopen(u)) as r: ...

# A3 @contextmanager, cleanup after yield
@contextmanager
def res(p):
    f = open(p)
    try: yield f
    finally: f.close()

# A4 escape — caller owns it
def helper(p):
    return open(p)                        # → UNKNOWN, never DEFINITE_LEAK

# A5 intra-class ownership
class C:
    def __init__(self): self.db = sqlite3.connect(":memory:")
    def __exit__(self, *a): self.db.close()

# A6 docstring/comment decoy — the regex killer
def load(p):
    """Reads a file. Remember to call f.close() when done."""
    with open(p) as f: return f.read()

# A7 close in a helper called on every path
def run(p):
    f = open(p)
    try: return use(f)
    finally: _shutdown(f)                 # summary: _shutdown closes param 0

# A8 pytest yield-fixture
@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:"); yield c; c.close()

# A9 multi-item with
with open(a) as f, open(b) as g: ...

# A10 atexit / weakref.finalize
f = open(p); atexit.register(f.close)

# A11 conditional open, both branches closed
f = open(a) if cond else open(b)
f.close()

# A12 close in except AND else AND finally variants
# A13 async with, correctly used
# A14 os.fdopen wrapping — closing the wrapper closes the fd
# A15 subprocess.Popen used as a context manager
```

### LEAKY but reads as fine — must BE flagged

```python
# B1 reassign orphans the first handle
f = open(p); f = open(q); f.close()

# B2 loop, fd exhaustion
for p in paths: f = open(p)

# B3 async session never closed
s = aiohttp.ClientSession()               # no close anywhere

# B4 class with no closer anywhere
class D:
    def __init__(self): self.conn = psycopg2.connect(DSN)

# B5 close present but only on the success path
try:
    c = connect(); c.execute(q); c.close()
except OperationalError:
    log.warning("failed")                 # ← leaked here

# B6 close after a call that can raise, no finally
f = open(p); parse(f.read()); f.close()

# B7 early return in a nested branch
def h(p, flag):
    f = open(p)
    if flag:
        if check(): return None           # ← leak
    f.close()

# B8 Popen never waited — zombie process
proc = subprocess.Popen(cmd)

# B9 close called on the wrong variable
f = open(a); g = open(b); f.close(); f.close()

# B10 close inside an `if` that isn't always taken
f = open(p)
if verbose: f.close()

# B11 lock acquired, released only on one path
# B12 resource opened in try, close in the SAME try after a raising call
# B13 generator that opens and never closes if not exhausted
# B14 close inside `except` only (not finally)
# B15 ExitStack created but enter_context never called on the handle
```

---

## 9. Evaluation protocol

Run and publish this table. It is the most persuasive artifact in the write-up.

| Tool | Seeded repo TP/FP | Adversarial safe FP | Adversarial leaky TP | Mutant holdout F1 | CPython `Lib/` FP count |
|---|---|---|---|---|---|
| pylint R1732 | | | | | |
| leakaudit | | | | | |
| bandit | | | | | |
| flake8-bugbear | | | | | |
| **LeakGuard (rules only)** | | | | | |
| **LeakGuard (+ ML confidence)** | | | | | |

Also report: reliability diagram, Brier score, conformal coverage vs configured tolerance,
and a per-operator recall breakdown (which mutation types we catch and which we miss).

---

## 10. Repo layout

```
leakguard/
  __init__.py  cli.py  registry.py  detector.py  tracker.py
  cfg.py  verifier.py  escape.py  ownership.py  summaries.py
  features.py  model.py  calibrate.py  risk.py
  report.py  sarif.py  suppress.py
  model.json                     # shipped weights, versioned in git
  resources.yaml
corpus/
  repos/                         # cloned sources (gitignored)
  mutants/  labels.jsonl
  adversarial/safe/  adversarial/leaky/
  history/leakfix_commits.jsonl
tools/
  harvest.py  mutate.py  runtime_oracle.py  bench.py
sample_repo/                     # 5-10 seeded leaks (Deliverable 2)
.github/workflows/leakguard.yml
action.yml
.pre-commit-hooks.yaml
README.md  WRITEUP.md
```

---

## 11. Guardrails — do not violate these

1. **No online learning.** Model weights load from `model.json` at scan time and never
   change during a scan. Recalibration is a separate `leakguard calibrate` command that
   emits a reviewable diff.
2. **No regex on source text** for detection. Everything through `ast`. Judges will probe
   this with A6-style decoys.
3. **`UNKNOWN` is a first-class verdict.** Never promote an unprovable case to
   `DEFINITE_LEAK`. "I can't prove this one, here's why" reads as rigorous, not weak, and
   it directly serves the PS's "documented edge case beats undocumented false negative."
4. **Every finding must be explainable** as a list of contributing evidence with weights.
   If you can't explain it, don't report it.
5. **Start `tools/harvest.py` in the first two hours** and let it clone/mine in the
   background while you build the CFG.
6. Write the limitations section of `WRITEUP.md` **as you go**, not at hour 29. Known
   limitations to document honestly: cross-module escape, resources stored in dicts/lists,
   dynamic `getattr`-based closes, C-extension resources, metaclass-created handles,
   `eval`/`exec`.

---

## 12. First task

Scaffold the repo, implement `registry.py` and `detector.py`, and get
`leakguard scan <file>` printing detected open-sites with file, line, handle name and
resource type. No CFG yet. Then immediately start `tools/harvest.py` cloning the corpus
repos in the background before moving on to the CFG.
