# Resource-Leak Edge Cases — Research Catalogue and Mutation Coverage

This is the reference document for `dataset/mutated_code/`. It answers three
questions:

1. **What can possibly go wrong** when deciding whether a Python resource is
   released — the full taxonomy, not just the cases we happen to handle.
2. **Which of those we mutate**, with which operator, at what cap.
3. **Where we knowingly stop**, and why an honest `UNKNOWN` is the correct
   answer there.

Every edge case has a stable `EC-*` id. Corpus manifests reference those ids in
their `edge_cases` field, so coverage is queryable rather than aspirational.

---

## 0. Why any of this is a bug in a garbage-collected language

Worth restating, because it is the first question anyone asks.

- **Refcount cleanup is a CPython implementation detail.** PyPy, Jython and
  GraalPy do not promptly finalise. Code that relies on it is non-portable.
- **It never fires inside a reference cycle**, when the handle is held on
  `self`, or when it is appended to a container that outlives the scope.
- **Timing is non-deterministic.** A loop opening 5,000 files exhausts the
  descriptor limit long before collection catches up.
- **It does not apply at all** to the things that actually take services down:
  pooled DB connections, sockets, `subprocess.Popen` pipes, `threading.Lock`,
  `multiprocessing.Pool`.
- **CPython itself calls it a bug** — that is why `ResourceWarning` exists, and
  why `python -X dev -W error::ResourceWarning` turns it into a test failure.

---

## 1. Taxonomy of the acquisition itself

Before cleanup can be checked, the acquisition has to be recognised. These are
the ways an acquisition hides.

| ID | Edge case | Example | Why it is hard |
|---|---|---|---|
| `EC-ACQ-01` | Plain constructor | `f = open(p)` | The baseline. |
| `EC-ACQ-02` | Aliased import | `import socket as sk; sk.socket()` | Needs import-alias resolution, not name matching. |
| `EC-ACQ-03` | `from x import y` | `from sqlite3 import connect; connect(p)` | The dotted registry key never appears in source. |
| `EC-ACQ-04` | Vendored path | `pkg._vendor.urllib3.PoolManager()` | Suffix matching, but only on dotted entries. |
| `EC-ACQ-05` | Unbound acquisition | `subprocess.Popen(cmd)` as a bare statement | No name to track; a name-keyed tracker misses it entirely. |
| `EC-ACQ-06` | Nested in a call | `json.load(open(p))` | The handle exists only as a temporary. |
| `EC-ACQ-07` | Tuple unpacking | `reader, writer = await asyncio.open_connection(h, p)` | One acquisition, two names; only one of them closes. |
| `EC-ACQ-08` | Conditional acquisition | `f = open(a) if cond else open(b)` | Two sites, one handle, one close. |
| `EC-ACQ-09` | Acquisition in a comprehension | `[stack.enter_context(open(p)) for p in paths]` | Variable count of handles, resolved by the stack. |
| `EC-ACQ-10` | Release-style resource | `lock.acquire()` | The **constructor acquires nothing**; `threading.Lock()` is free. Modelling the constructor as the acquisition makes every lock in every class a false positive. |
| `EC-ACQ-11` | Factory indirection | `conn = make_connection()` | Requires interprocedural return-type reasoning. → `UNKNOWN`. |
| `EC-ACQ-12` | Dynamic acquisition | `getattr(mod, name)()`, `eval` | Not statically resolvable → out of scope, documented. |

---

## 2. Context managers and cleanup constructs

| ID | Edge case | Correct verdict | Note |
|---|---|---|---|
| `EC-CTX-01` | `with open(p) as f:` | SAFE | The baseline correct form. |
| `EC-CTX-02` | Multi-item `with a() as x, b() as y:` | SAFE | Both handles released, including on the exception path. |
| `EC-CTX-03` | Nested `with` blocks | SAFE | Inner and outer both unwind. |
| `EC-CTX-04` | `contextlib.closing(x)` | SAFE | Adapts a non-manager; also `aclosing`. |
| `EC-CTX-05` | `ExitStack().enter_context(f)` | SAFE | Dynamic number of handles; the stack owns them. |
| `EC-CTX-06` | `ExitStack` closed manually in `finally` | SAFE | No `with` on the stack itself. |
| `EC-CTX-07` | `stack.callback(f.close)` / `stack.push(f)` | SAFE | Registration, not a call. |
| `EC-CTX-08` | `contextlib.suppress` wrapping the **close** | SAFE | Suppressing an error *from* the close is not skipping it. |
| `EC-CTX-09` | `contextlib.suppress` wrapping the **body**, close outside | SAFE | Distinct from `EC-CTX-08`, easy to confuse. |
| `EC-CTX-10` | `with` whose `__exit__` does **not** release | **LEAK** | See `EC-DB-01`. The most under-appreciated case here. |
| `EC-CTX-11` | `ExitStack` created but `enter_context` never called on the handle | **LEAK** | Adversarial B15: reads as managed, is not. |
| `EC-CTX-12` | `stack.pop_all()` transferring ownership out | UNKNOWN | Ownership deliberately moved elsewhere. |

---

## 3. Control flow — the core of the problem

| ID | Edge case | Correct verdict | Note |
|---|---|---|---|
| `EC-CF-01` | Early `return` between open and close | **LEAK** | The canonical case from the problem statement. |
| `EC-CF-02` | Early return nested two levels deep | **LEAK** | Defeats any non-path-sensitive rule. |
| `EC-CF-03` | Multiple returns, only some closing | **LEAK** | Partial-cleanup shape. |
| `EC-CF-04` | `return` from inside a loop | **LEAK** | Loop exit is not the only exit. |
| `EC-CF-05` | `try: ... finally: close()` | SAFE | Covers every path including propagation. |
| `EC-CF-06` | `try/except/finally`, close in `finally` | SAFE | The handler must not be the only closer. |
| `EC-CF-07` | Close only in `except` | **LEAK** | The success path leaks. |
| `EC-CF-08` | Close only on the success path, handler returns | **LEAK** | Mirror of `EC-CF-07`; adversarial B5. |
| `EC-CF-09` | Close in `try` **after** a call that can raise | EXCEPTION_PATH_LEAK | See §11.1. |
| `EC-CF-10` | Close in `else:` of `try/except/else` | SAFE only if no handler path escapes | `else` runs only when the body did not raise. |
| `EC-CF-11` | Acquisition itself inside `try`, handler returns | SAFE | If `open()` raises, nothing was acquired. |
| `EC-CF-12` | `finally: pass` (cleanup deleted) | **LEAK** | The classic mutation of `EC-CF-05`. |
| `EC-CF-13` | `return` inside `finally` swallowing an exception | SAFE for the resource, but hides errors | Worth a lint, not a leak. |
| `EC-CF-14` | Close after `break` / `continue` skips it | **LEAK** | Loop-local control flow. |
| `EC-CF-15` | `for ... else:` / `while ... else:` cleanup | SAFE or LEAK depending | The `else` does not run after `break`. |
| `EC-CF-16` | `match`/`case` with no wildcard arm | **LEAK** | The implicit fall-through arm has no close. |
| `EC-CF-17` | `except*` (`TryStar`, 3.11+) exception groups | as `EC-CF-05` | Different AST node, same semantics. |
| `EC-CF-18` | `sys.exit()` / `os._exit()` before close | SAFE | The OS reclaims everything; never report it. |
| `EC-CF-19` | `assert` between open and close | EXCEPTION_PATH_LEAK | Raises whenever `-O` is off. |
| `EC-CF-20` | Infinite loop / `while True` with no exit | UNKNOWN | No reachable exit path to verify. |
| `EC-CF-21` | Nested-branch matrix where exactly one path misses | **LEAK** | The PDF's "branch depth" case; pure CFG work. |

---

## 4. Loops

| ID | Edge case | Correct verdict | Note |
|---|---|---|---|
| `EC-LOOP-01` | Acquire and release inside the loop body | SAFE | One handle live at a time. |
| `EC-LOOP-02` | Acquire in the loop, close **after** the loop | **LEAK** | Only the final handle is closed; every earlier one leaks. Needs 2-iteration unrolling to see. |
| `EC-LOOP-03` | Acquire in the loop, never closed | **LEAK** | Descriptor exhaustion; highest exposure weight. |
| `EC-LOOP-04` | Acquire before the loop, close inside it | **LEAK** on the zero-iteration path | An empty iterable is a real path. |
| `EC-LOOP-05` | `continue` skipping the close | **LEAK** | |
| `EC-LOOP-06` | Handles accumulated into a list, closed later in one sweep | UNKNOWN → SAFE if the sweep is provable | Container escape. |
| `EC-LOOP-07` | Nested loops, close at the wrong nesting depth | **LEAK** | |

---

## 5. Aliasing, reassignment and lifetime

| ID | Edge case | Correct verdict | Note |
|---|---|---|---|
| `EC-ALIAS-01` | Reassign before close | **LEAK** of the first handle | `f = open(a); f = open(b); f.close()`. |
| `EC-ALIAS-02` | Reassign in one branch only | **LEAK** on that path | Data flow x CFG. |
| `EC-ALIAS-03` | Two handles, close called twice on the same one | **LEAK** of the other | Adversarial B9; reads as balanced. |
| `EC-ALIAS-04` | Ternary acquisition, single close | SAFE | Two sites, one live handle. |
| `EC-ALIAS-05` | Simple alias `g = f; g.close()` | SAFE | Needs alias tracking; **not** modelled → conservative. |
| `EC-ALIAS-06` | Tuple-unpack alias, one member closes | SAFE | `reader, writer = ...; writer.close()`. |
| `EC-ALIAS-07` | Swap through a container | UNKNOWN | |
| `EC-ALIAS-08` | `del f` without close | **LEAK** on non-CPython | `del` drops the reference, not the descriptor. |
| `EC-ALIAS-09` | Shadowing in a nested function or closure | UNKNOWN | Separate scope. |

---

## 6. Escape and ownership transfer

The governing rule: **escaped ⇒ `UNKNOWN`, never `DEFINITE_LEAK`.** But not
every use is an escape, and that distinction decides the FP/FN balance.

| ID | Edge case | Correct verdict | Note |
|---|---|---|---|
| `EC-ESC-01` | `return open(p)` / `return f` | UNKNOWN | Caller owns it. Adversarial A4. |
| `EC-ESC-02` | Stored in a module-level dict or list | UNKNOWN | Lifetime leaves the function. |
| `EC-ESC-03` | Assigned to `self.X` | see §7 | Ownership moves to the object. |
| `EC-ESC-04` | Assigned to a `global` / `nonlocal` | UNKNOWN | |
| `EC-ESC-05` | `yield`ed from a plain generator | UNKNOWN | The consumer decides. |
| `EC-ESC-06` | Passed to an **unresolved** call | *not* an ownership transfer | `process(f)`, `json.load(f)` overwhelmingly do not close. Treating every use as a transfer collapses recall. Surfaced to the model as `escapes_call_arg`. |
| `EC-ESC-07` | Passed to a callee whose name suggests cleanup | UNKNOWN | `_shutdown(f)`, `release(handle)`. |
| `EC-ESC-08` | Passed to a callee proven to close on **all** paths | SAFE | Function summary. Adversarial A7. |
| `EC-ESC-09` | Passed to a callee that closes on **some** paths | UNKNOWN | `def cleanup(f, cond): if cond: f.close()`. Must not resolve either way. |
| `EC-ESC-10` | Captured by a closure or lambda | UNKNOWN | |
| `EC-ESC-11` | Passed across a module boundary | UNKNOWN | Needs whole-program analysis. |
| `EC-ESC-12` | Registered on a callback or observer | UNKNOWN | |

---

## 7. Intra-class ownership

The highest-value single rule in the codebase, and the biggest false-positive
source in real Python.

| ID | Edge case | Correct verdict | Note |
|---|---|---|---|
| `EC-OWN-01` | `self.conn = connect()` and the class defines `close()` / `__exit__` releasing it | SAFE | |
| `EC-OWN-02` | Released in `__del__` | SAFE | Fragile in practice, but it is a closer. |
| `EC-OWN-03` | Released in `shutdown()` / `stop()` / `dispose()` / `teardown()` | SAFE | Naming varies wildly. |
| `EC-OWN-04` | Borrowed from a pool and returned, never closed | SAFE | Check-in is the correct release. |
| `EC-OWN-05` | **No method of the class ever releases it** | **LEAK** | The high-value finding pylint and leakaudit both miss. |
| `EC-OWN-06` | The class closes a *different* attribute | **LEAK** for the unreleased one | Partial ownership. |
| `EC-OWN-07` | Released only in a method that is never called | **LEAK** in practice | Needs call-graph reachability → currently SAFE, documented FN. |
| `EC-OWN-08` | Released by a base class or mixin | SAFE | Needs MRO reasoning → documented FP risk. |
| `EC-OWN-09` | Attribute reassigned in another method, orphaning the first | **LEAK** | `self.conn = connect()` called twice. |
| `EC-OWN-10` | Dataclass / `__slots__` / `attrs` field | as `EC-OWN-01` | Different AST shape, same rule. |

---

## 8. Generators, coroutines and frameworks

| ID | Edge case | Correct verdict | Note |
|---|---|---|---|
| `EC-GEN-01` | `@contextmanager` with cleanup after `yield` | SAFE | The framework guarantees resumption. |
| `EC-GEN-02` | Plain generator with `try/finally` around the `yield` | SAFE | `GeneratorExit` runs the `finally`. |
| `EC-GEN-03` | Plain generator, close after `yield`, **no** `finally` | **LEAK** | An abandoned generator never reaches the close. |
| `EC-GEN-04` | `@pytest.fixture` yield-fixture | SAFE | pytest drives the teardown half. |
| `EC-GEN-05` | FastAPI `Depends` generator dependency | SAFE | Same guarantee, different framework. |
| `EC-GEN-06` | `@asynccontextmanager` | SAFE | Async twin of `EC-GEN-01`. |
| `EC-GEN-07` | `yield from` delegating ownership | UNKNOWN | |
| `EC-ASYNC-01` | `async with aiohttp.ClientSession()` | SAFE | |
| `EC-ASYNC-02` | `AsyncExitStack.enter_async_context` | SAFE | |
| `EC-ASYNC-03` | `await writer.wait_closed()` in `finally` | SAFE | Two-step async close. |
| `EC-ASYNC-04` | `session = aiohttp.ClientSession()` never closed | **LEAK** | Adversarial B3; the async differentiator. |
| `EC-ASYNC-05` | `close()` called but never awaited | **LEAK** | A coroutine created and dropped. |
| `EC-ASYNC-06` | Task cancelled between open and close | EXCEPTION_PATH_LEAK | `CancelledError` is an exception path. |
| `EC-ASYNC-07` | `asyncio.run` / event-loop teardown | UNKNOWN | |
| `EC-FW-01` | pytest fixture (see `EC-GEN-04`) | SAFE | |
| `EC-FW-02` | Acquisition inside a route handler | LEAK, **high exposure** | `@app.route` multiplies risk by request rate. |
| `EC-FW-03` | Framework-managed dependency injection | SAFE | |
| `EC-FW-04` | Celery / background task | LEAK, high exposure | Long-lived worker process. |

---

## 9. Resource-family specifics

Each family has its own release verb, and getting the verb wrong is the same bug
class as missing the close entirely.

| ID | Edge case |
|---|---|
| `EC-DB-01` | **`with sqlite3.connect(p) as conn:` does NOT close the connection.** It is a *transaction* context manager: it commits or rolls back and leaves the connection open. Same for `psycopg2`, `pymysql`, `MySQLdb`, `cx_Oracle`. Registry flag `ctx_closes: false`. |
| `EC-DB-02` | Cursor and connection are separate resources; closing one does not close the other. |
| `EC-DB-03` | Connection returned to a pool rather than closed (see `EC-OWN-04`). |
| `EC-DB-04` | Transaction left open — a lock leak rather than a handle leak. Out of scope, worth naming. |
| `EC-CLOSE-01` | The release verb is not `close`: `Popen.wait`, `Pool.terminate`, `Executor.shutdown`, `Lock.release`, `FTP.quit`, `PoolManager.clear`. |
| `EC-CLOSE-02` | `shutdown()` **then** `close()` on a socket — either alone satisfies us. |
| `EC-PROC-01` | `with subprocess.Popen(...)` waits and closes the pipes (3.2+). |
| `EC-PROC-02` | `communicate()` reaps the child and drains the pipes. |
| `EC-PROC-03` | `Popen` never waited — a zombie process plus three leaked pipe descriptors. |
| `EC-PROC-04` | `Popen` with `stdout=PIPE` where only `wait()` is called — deadlock risk, pipes still leak. |
| `EC-POOL-01` | `Pool.close()` **and** `join()`; `close()` alone leaves workers. |
| `EC-POOL-02` | `ThreadPoolExecutor` context manager calls `shutdown(wait=True)`. |
| `EC-LOCK-01` | `with lock:` releases. |
| `EC-LOCK-02` | `acquire()` / `release()` in `try/finally`. |
| `EC-LOCK-03` | `acquire()` released on only one path — a deadlock, not a descriptor leak, and far worse. |
| `EC-LOCK-04` | `acquire(timeout=...)` returning False then `release()` unconditionally — a different bug. |
| `EC-WRAP-01` | `os.fdopen(fd)` — closing the wrapper closes the descriptor; closing neither leaks the raw fd. |
| `EC-WRAP-02` | `socket.makefile()` — the file wrapper and the socket are separate closes. |
| `EC-MMAP-01` | `mmap` closed while a slice is still referenced. |
| `EC-DEFER-01` | `atexit.register(f.close)` — cleanup deferred to interpreter exit. |
| `EC-DEFER-02` | `weakref.finalize(obj, f.close)` — cleanup tied to an owner's lifetime. |
| `EC-DEFER-03` | `tempfile.TemporaryDirectory` released by `cleanup()`, not `close()`. |

---

## 10. Decoys — code that must **not** be flagged

The problem statement warns explicitly that judges probe with these. Every one is
a regex-based tool failing.

| ID | Decoy | Why a naive tool fails |
|---|---|---|
| `EC-DECOY-01` | Docstring saying "remember to call `f.close()`" | Text search finds a close that is not code. |
| `EC-DECOY-02` | Leaky code inside a string constant or template | The reverse: text search finds an *open* that is not code. |
| `EC-DECOY-03` | The leaky implementation survives only as a comment | Comments never reach an AST. |
| `EC-DECOY-04` | A domain object with its own `open()` — `valve.open()` | Name matching hits the builtin `open` entry. Suffix matching must require a dot. |
| `EC-DECOY-05` | `close` as a dict key or column name (`bar["close"]`) | |
| `EC-DECOY-06` | A `close()` on something that is not a resource (`ticket.close()`) | |
| `EC-DECOY-07` | A variable named `open_file` that never opened anything | |
| `EC-DECOY-08` | `# noqa` / `# type: ignore` near the site | Irrelevant, but pattern tools react. |
| `EC-SYNTAX-01` | Walrus or comprehension inside the managed block | The handle is used, not escaped. |
| `EC-SYNTAX-02` | Decorators wrapping the whole function | Must not hide the body. |
| `EC-SYNTAX-03` | Type annotations mentioning the resource type | |

---

## 11. Policy decisions and deliberate divergences

Three judgement calls a reader would otherwise mistake for bugs.

### 11.1 The exception tier

```python
f = open(p)
data = f.read()      # if this raises, f leaks
f.close()
```

This is a **real** leak — CPython emits `ResourceWarning` for it — and
`LEAKGUARD_SPEC.md` case B6 says to flag it. It is also the single most common
shape of ordinary correct-looking Python, and `LeakGuard_Dataset_Test_Cases.pdf`
case 1a labels it SAFE.

Both are right, so it gets its own verdict: **`EXCEPTION_PATH_LEAK`**, reported
as a warning and **not** a build failure. `DEFINITE_LEAK` is reserved for a leak
on a path that terminates *normally* — return, fall-through, or a handled
exception. The distinction is one line in the path model: whether the leaking
path's terminator is an unhandled `raise`.

This is what stops the tool being switched off in week two while keeping the
finding visible.

### 11.2 Passing a handle to a call is a *use*, not an ownership transfer

Treating `process(f)` as an escape turns PDF cases 3a, 7b, 8d and 9 — all
unambiguous leaks — into `UNKNOWN`. Ownership transfer is reserved for `return`,
`yield`, `self.X = f`, container insertion and `global`. Whether a callee
releases its parameter is answered by function summaries (`EC-ESC-08` /
`EC-ESC-09`), and `escapes_call_arg` still reaches the model as a feature.

### 11.3 `close()` is assumed not to raise

Generating an exception path *through* a close would flag every correct program.
The cost is a documented false negative when `close()` itself fails.

---

## 12. Mutation operators — what each one breaks

The mutation pass is owned by the AST work in progress; this table is the
contract it should satisfy. Caps are fractions of the positive class. Without
them the model learns one operator and collapses on the rest.

| Operator | Transformation | Edge cases exercised | Cap |
|---|---|---|---|
| `M1_with_to_bare` | `with open(p) as f:` → `f = open(p)`, body de-indented | `EC-CTX-01`, `EC-CF-09` | 20% |
| `M2_delete_branch_close` | Remove the close on one branch | `EC-CF-03`, `EC-CF-07`, `EC-CF-21` | 20% |
| `M3_insert_early_return` | Insert a guard `return` between open and close | `EC-CF-01`, `EC-CF-02` | 20% |
| `M4_close_into_try` | Move the close from `finally` into a raising `try` | `EC-CF-09`, `EC-CF-12` | 15% |
| `M5_success_path_only` | Close only on the success path, handler returns | `EC-CF-08` | 10% |
| `M6_reassign_before_close` | Rebind the handle before the close | `EC-ALIAS-01`, `EC-ALIAS-02` | 10% |
| `M7_hoist_open_into_loop` | Move the acquisition inside a loop | `EC-LOOP-02`, `EC-LOOP-03` | 5% |
| `M8_async_close_removal` | `async with S() as s:` → `s = S()` | `EC-ASYNC-04`, `EC-ASYNC-05` | async only |
| `M9_exitstack_to_bare` | Drop `stack.enter_context` | `EC-CTX-05`, `EC-CTX-11` | 5% |
| `M10_remove_class_closer` | Delete the class's closer method | `EC-OWN-05`, `EC-OWN-06` | 10% |
| `M11_close_into_except` | Move the close into `except` only | `EC-CF-07` | 10% |
| `M12_close_wrong_handle` | Retarget the close to another handle | `EC-ALIAS-03` | 5% |
| `M13_finally_to_pass` | Replace the `finally` body with `pass` | `EC-CF-12` | 10% |
| `M14_ctx_manager_swap` | `closing(sqlite3.connect(p))` → `sqlite3.connect(p)` in a `with` | `EC-DB-01`, `EC-CTX-10` | 5% |

### Contract for every generated mutant

A mutant is only usable as training data if it carries its provenance:

```json
{"sample_id": "M3-0042",
 "path": "dataset/mutated_code/generated/M3_insert_early_return/xyz.py",
 "folder": "mutated_code", "origin": "generated",
 "family": "<INHERITED FROM THE SOURCE SAMPLE>",
 "label": 1,
 "operator": "M3_insert_early_return",
 "derived_from": "S-0117",
 "edge_cases": ["EC-CF-01"],
 "expected_leak_lines": [12],
 "expected_unknown_lines": [],
 "resource_types": ["FILE"],
 "note": "guard return inserted between open and close",
 "source_sha1": "<sha1 of the written file>"}
```

Four rules that matter more than the rest:

1. **`family` is inherited from the source sample, never regenerated.** A mutant
   and its original in different splits is the classic way to double a reported
   F1. `tools/extract_features.py` splits on `family`.
2. **`expected_leak_lines` holds the *acquisition* line of the site the mutation
   broke** — not the line the mutation edited. The label is per open-site.
3. **The mutant must parse.** `tools/verify_dataset.py` fails the build otherwise.
4. **Verify the mutation actually broke something.** Run the analyser before and
   after: if the verdict did not change, the mutant is mislabelled noise. This is
   the most common way a mutation corpus quietly poisons a model.

`tools/corpus_lib.build_sample()` produces this record; use it rather than
hand-rolling the JSON.

---

## 13. Coverage against `LeakGuard_Dataset_Test_Cases.pdf`

All 28 benchmark cases from the PDF were run through the analyser.

### Covered by the PDF and by us

| PDF section | Our ids | Status |
|---|---|---|
| 1. Normal open/close | `EC-ACQ-01`, `EC-CF-09` | yes (1a lands on our exception tier, §11.1) |
| 2. Early return: nested, multiple, loop | `EC-CF-01`–`EC-CF-04` | yes, all four |
| 3. Exception paths | `EC-CF-05`–`EC-CF-08` | yes |
| 4. Branching and branch depth | `EC-CF-21`, `EC-LOOP-*` | yes |
| 5. Multiple resources tracked independently | `EC-ALIAS-03` | yes |
| 6. Reassignment, and reassignment under a branch | `EC-ALIAS-01`, `EC-ALIAS-02` | yes |
| 7. Passed to a function; conditional cleanup in the callee | `EC-ESC-06`, `EC-ESC-08`, `EC-ESC-09` | yes, including the `UNKNOWN` case |
| 8. Safe patterns, and acquisition inside `try` | `EC-CTX-01`, `EC-CF-05`, `EC-CF-11` | yes |
| 9. Combined hard case | `EC-CF-08` + `EC-ALIAS-03` | yes |

**Nothing in the PDF is unaddressed.** The only divergence is cases 1a / 3c / 5b /
8c, where the PDF says SAFE and we say `EXCEPTION_PATH_LEAK` — a non-blocking
warning tier that exists precisely to reconcile the PDF with spec case B6.

### Edge cases we add beyond the PDF

The PDF covers file handles with `open`/`close` and straight-line CFG. These are
additions, roughly in descending order of how much they change the outcome:

1. `EC-DB-01` — `with sqlite3.connect(...)` does not close. The PDF has no DB
   context-manager case, and this one silently mislabels real code.
2. `EC-OWN-01`–`EC-OWN-10` — intra-class ownership, including the `EC-OWN-05`
   no-closer leak. Absent from the PDF entirely.
3. `EC-ACQ-10` — locks acquire on `acquire()`, not on construction.
4. `EC-CTX-04`–`EC-CTX-12` — `closing`, `ExitStack`, `AsyncExitStack`,
   `callback`, `push`, `suppress`.
5. `EC-GEN-01`–`EC-GEN-07` — `@contextmanager`, generator abandonment, pytest
   fixtures, FastAPI dependencies.
6. `EC-ASYNC-01`–`EC-ASYNC-07` — the whole async family.
7. `EC-DECOY-01`–`EC-DECOY-08` — the false-positive traps. The PDF asks for FP
   control but supplies no decoys.
8. `EC-ACQ-05`–`EC-ACQ-09` — unbound acquisitions, nesting, tuple unpacking,
   comprehensions.
9. `EC-CLOSE-01` / `EC-PROC-*` / `EC-POOL-*` / `EC-LOCK-*` — non-`close` release
   verbs across six resource families.
10. `EC-DEFER-01`–`EC-DEFER-03` — `atexit`, `weakref.finalize`.
11. `EC-CF-16`–`EC-CF-19` — `match`/`case`, `except*`, `sys.exit`, `assert`.
12. `EC-LOOP-02` — acquire in a loop, close after it. Needs two-iteration
    unrolling; no single-pass analysis sees it.
13. `EC-ACQ-02`–`EC-ACQ-04` — import aliasing and vendored paths.
14. Exposure weighting: a leaked DB connection in an `@app.route` handler is not
    the same finding as a leaked file in a one-shot script (`EC-FW-02`).

### Schema differences

The PDF's schema (`id`, `resource_type`, `acquisition`, `cleanup`, `label`,
`leak_type`, `difficulty`, `acquisition_lines`, `cleanup_lines`,
`expected_paths`, `reason`, `fix_pattern`) is per-test-case. Ours is a per-sample
manifest plus a per-**open-site** feature row, because one file can hold several
acquisitions with different labels. The mapping is direct:

| PDF field | Ours |
|---|---|
| `id` | `sample_id` |
| `resource_type` | `resource_types` (a list — one file can hold several) |
| `acquisition` | `resource_call` in the feature row |
| `cleanup` | derived; the registry holds the release verbs |
| `label` | `label` plus the four-way rules `verdict` |
| `leak_type` | `operator` + `edge_cases` |
| `difficulty` | implicit in `origin` (`synthesized` < `handwritten`) |
| `acquisition_lines` | `line`, one per feature row |
| `cleanup_lines` | `close_lines` on the `OpenSite` |
| `expected_paths` | `leaking_path_fraction` and the `HandleOutcome` counts |
| `reason` | `note` + `leakguard.features.describe()` |
| `fix_pattern` | the counterfactual line in the report |

The PDF's recommendation to *"split by program/seed family rather than randomly
splitting individual mutations"* is implemented as the `family` field and the
sha1-bucketed grouped split.

---

## 14. Known limitations — the honest list

Documented here rather than discovered by a judge. Each is an `UNKNOWN` or a
known false negative, never a silent wrong answer.

| ID | Limitation |
|---|---|
| `EC-LIMIT-01` | Cross-module escape. Summaries are single-module. |
| `EC-LIMIT-02` | Handles stored in dicts or lists and closed by a later sweep. |
| `EC-LIMIT-03` | Dynamic `getattr`-based closes; `eval` / `exec`. |
| `EC-LIMIT-04` | C-extension resources with no Python-visible close. |
| `EC-LIMIT-05` | Metaclass- or decorator-created handles. |
| `EC-LIMIT-06` | Inheritance: a closer defined on a base class (`EC-OWN-08`). |
| `EC-LIMIT-07` | Call-graph reachability — a closer that is never called (`EC-OWN-07`). |
| `EC-LIMIT-08` | Simple aliasing `g = f` (`EC-ALIAS-05`). |
| `EC-LIMIT-09` | Path explosion: enumeration is capped at 3,000 paths and 8 exception split points; beyond that the verdict degrades to `UNKNOWN`. |
| `EC-LIMIT-10` | Loop unrolling is depth 2, so a leak that first appears on the third iteration is invisible. |
| `EC-LIMIT-11` | `close()` raising (§11.3). |
| `EC-LIMIT-12` | Cache eviction policies — named in the problem statement, but not a handle leak and not modelled. |

---

<!-- BEGIN GENERATED COVERAGE -->
_Coverage table is generated by `python tools/build_dataset.py`; re-run it after
the mutation pass lands._
<!-- END GENERATED COVERAGE -->
