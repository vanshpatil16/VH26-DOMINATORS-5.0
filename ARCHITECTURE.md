# CodeGate — Architecture Decision Record
# Generated after Phases 0-3 deep exploration (Scalpel + LibCST)

## TL;DR Division of Responsibility

```
Python source
     |
 +---+---+
 |       |
 v       v
SCALPEL  LIBCST
 |       |
 |       |  (parsing, formatting preservation, scopes, autofix)
 |       | (CFG, line numbers, func_calls, branch edges)
 +---+---+
     |
     v
 CodeGate logic:
   Resource tracking  +  Ownership tracking + Rules engine
     |
     v
 Path analysis (DFS over Scalpel CFG, live-resource dataflow)
     |
     v
  Report (+ Fix via LibCST)
```

### SCALPEL DOES
- CFG construction (intraprocedural, per function)
- Block abstraction (statements list, exits with exitcase AST, predecessors)
- Source line mapping (Block.at(), statement.lineno)
- Function call tracking (Block.func_calls)
- With / Try / If / Loop / Return handling (mostly)
- Provides AST nodes directly (no wrapper) -> easy to pattern-match

### LIBCST DOES
- Full concrete syntax tree (preserves comments, whitespace, formatting)
- PositionProvider (line/column), ScopeProvider (assignments/references), ParentNodeProvider
- Source-to-source transformation (CSTTransformer) without losing formatting
- Codemod infrastructure (VisitorBasedCodemodCommand, diff_code)
- Guarantee that auto-fix `with open(...) as f:` preserves user comments/empty lines with minor adjustment

### CODEGATE DOES
- Configurable acquire/release API definitions (e.g., open->close, socket->close, etc.)
- Alias / ownership tracking (on top of Scalpel, not reusing broken SSA)
- Path-sensitive liveness analysis (DFS over CFG with live-resource set)
- Leak decision: "exists path from acquire to function exit where live not closed?"
- Ownership transfer rules: `return f`, `helper(f)`, `global` store -> not necessarily leak (configurable)
- Try/finally & With recognition as safe patterns
- Reporting (line numbers, path evidence) + autofix via LibCST

---

## Scalpel Deep Findings

### Usable
- `CFGBuilder().build_from_src(name, src)` -> CFG with `functioncfgs` dict keyed by `(enclosing_block_id, func_name)` and `class_cfgs`
- `Block.id`, `Block.statements` (list of AST nodes), `Block.exits` (List[Link]), `Block.predecessors`, `Block.at()`, `Block.func_calls`
- `Link.source`, `Link.target`, `Link.exitcase` (AST expression for branch condition)
- `CFG.get_all_blocks()` BFS, `CFG.__iter__` generator, `CFG.entryblock`, `CFG.finalblocks`
- `Block.at()` maps to first statement lineno -> sufficient for reporting
- `ast.dump` pattern matching for `f = open(path)` and `f.close()`
- `with` statement preserved as single `ast.With` node in block
- Simple branches (If/else, nested, loops) correctly modeled with two exits

### Partially Broken / Limitations
- **Try/except without finally crashes**: `visit_Try` references `finally_block` unconditionally -> `UnboundLocalError` when `finalbody` empty. Workaround: patch or wrap builder.
- **Return creates empty phantom block**: `visit_Return` does `cfg.finalblocks.append(cur); cur = new_block()` -> empty block remains, and previous block's predecessor list contains it (`Block 5 preds [3,6]` where 6 is empty). After `clean_cfg`, phantom remains as predecessor. Need to filter empty blocks or fix builder.
- **Try/finally modeling is sound but nonstandard**: uses `Constant(True)` edges, final block duplication.

### Not Useful
- `scalpel.SSA` (both `SSA` and `SSA.const`) : requires `MNode` module-level CFG, provides renaming `{block:[{var: set([...])}]}` and const propagation, but:
  - Alias tracking is just import alias handling, not `g = f` resource alias.
  - API is `compute_SSA(cfg)` returning cryptic dict, not suitable for path-sensitive leak check.
  - Overkill and bug-prone; easier to implement lightweight liveness ourselves.
- `scalpel.core.mnode.MNode` : thin wrapper around AST + gen_cfg, adds indirection without value for CodeGate.
- `scalpel.typeinfer`, `scalpel.call_graph` (pycg wrapper), `scalpel.import_graph` : not needed for intraprocedural leak detection (future interprocedural can revisit).
- `scalpel.rewriter`: regex/AST rewriting, inferior to LibCST for autofix.

### Recommendation for Scalpel reuse
- **Use as library** (not fork) for CFG only. Add local thin wrapper `codegate.scalpel_patch` that:
  1. Fixes `visit_Try` bug (guard `finally_block`).
  2. Filters phantom empty blocks after `visit_Return` (or patches `clean_cfg` to remove them fully).
  3. Exposes helper `get_function_cfg(src, func_name)` -> CFG.
- Do NOT extend Scalpel's SSA or builder beyond those fixes. Do NOT create MyCFGNode.

---

## LibCST Deep Findings

### Usable
- `cst.parse_module(code)` preserves exact formatting + comments (verified roundtrip `mod.code == original`).
- MetadataWrapper + `PositionProvider`, `ScopeProvider`, `ParentNodeProvider` all work with installed `libcst` (native Rust parser). Local LibCST checkout requires building Rust native, so for CodeGate we **use pip libcst**, not local checkout.
- `ScopeProvider` correctly tracks assignments/references: `f = open()` -> Assignment f with one reference `f` in `g = f`. Covers alias chain.
- `CSTTransformer.leave_FunctionDef` can replace `f = open(); ...; f.close()` with `with open() as f: ...` while preserving comments (tested). Need to adjust `leading_lines` for first statement inside with to avoid double blank line.
- `cst.With(items=[WithItem(item=Call, asname=AsName)])` + `IndentedBlock` constructs with correctly.
- Multiple resources via `with open(a) as f, open(b) as g:` works (list of WithItems).
- `libcst.codemod.VisitorBasedCodemodCommand` available for file-level codemods (future batch fixing).

### Caveats
- Local `LibCST/` directory's `libcst.native` not built -> `import libcst` via `sys.path.insert(0, 'LibCST')` fails. Solution: `pip install libcst` already provides native extension. Do not use local checkout for runtime, only for reference.
- After transform, extra blank line after `with` header if first middle statement retains its two EmptyLines (blank + comment). Fix: strip one pure blank EmptyLine when moving.
- `ScopeProvider.assignments` is custom `Assignments` object (not len-able, iterate via `for a in scope.assignments`).

### Recommendation for LibCST reuse
- **Use as library** for parse + fix only. Do NOT reimplement parser/AST/CST.
- CodeGate flow: `Scalpel` reports leak at `Line X: f = open(...)` with function cfg path, then `LibCST` transformer locates same `f = open` CST node via PositionProvider overlap and rewrites.

---

## CodeGate-Specific Logic (Not in Either Library)

1. **Resource config**: YAML/JSON mapping `acquire: {func: "open", release: "close", kind: "method"}` etc. Handles `open`, `socket.socket`, `Tempfile`, user-defined.
2. **Alias analysis** (lightweight): `Assignments` + transitive closure `g = f`, `h = g` ; plus scope-aware kill on reassign.
3. **Ownership**: `return f` or `global f` or `self.f = f` etc. -> resource escapes, not leak (or optionally leak if config says no transfer).
4. **Path analysis engine**: DFS over `CFG` with `live` set, aliases dict, handling of:
   - acquire creates live resource id (lineno)
   - alias adds live
   - close removes live (all aliases)
   - reassignment kills previous without close -> leak
   - exit with non-empty live -> leak
   - `with` and `try/finally` recognized as always-safe (short-circuit)
5. **Report**: file, func, line, var, acquire API, leaking paths (block ids + exitcases), confidence.

## File Layout for CodeGate (Proposed)

```
codegate/
  __init__.py
  config.py          # resource definitions
  scalpel_patch.py   # wrapper + bug fixes
  alias.py           # alias/ownership helpers
  analyzer.py        # main DFS engine (uses scalpel CFG)
  libfix.py          # LibCST transformer for with-fix
  report.py
  cli.py
experiments/
  scalpel/*.py already done
  libcst/*.py already done
  codegate_prototype*.py  # early POC
tests/
  fixtures/ leak/safe cases
```

## Decisions Pending (Phase 4 next steps)

- [ ] Patch Scalpel Try bug in our wrapper or via monkey-patch at import time?
- [ ] Filter phantom empty blocks: do we patch clean_cfg or post-process `get_all_blocks()` to drop empty+no-exit?
- [ ] Ownership policy: should `return f` be leak or not? Make configurable.
- [ ] Interprocedural: for hackathon, intraprocedural only; note extensibility point via call_graph later.
- [ ] Minimal viable product for demo: handle only `open` vs generic config?

