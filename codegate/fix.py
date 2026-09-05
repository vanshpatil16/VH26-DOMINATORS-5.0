"""LibCST autofix: turn leaked  f = open(...) ... f.close()  into  with open(...) as f: ..."""

from __future__ import annotations

import ast

import libcst as cst
from libcst.metadata import PositionProvider
from pathlib import Path

from .analyzer import Leak
from .config import CodeGateConfig


def _all_specs():
    """All default resource specs (for release-method matching)."""
    return CodeGateConfig.default().resources


class _WithFixer(cst.CSTTransformer):
    """Inside a target function, replace first acquire + middle + close with `with`."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, func_name: str, leak: Leak):
        super().__init__()
        self.func_name = func_name
        self.leak = leak
        # Will be set when we enter the target function
        self._inside_target = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if node.name.value == self.func_name:
            return True
        return True  # need to traverse all to find nested, but leaf will be filtered

    def leave_FunctionDef(self, original: cst.FunctionDef, updated: cst.FunctionDef) -> cst.FunctionDef:
        if original.name.value != self.func_name:
            return updated
        # Use ORIGINAL node's positions (metadata is on original nodes, not updated copies)
        orig_stmts = list(original.body.body)
        stmts = list(updated.body.body)
        if not stmts:
            return updated

        # Find the acquire statement by IDENTITY (variable + acquire API),
        # NOT by line number — earlier fixes may shift lines within the file.
        acquire_idx: int | None = None
        close_idx: int | None = None
        acquire_stmt = None
        release_var = None

        for idx, stmt in enumerate(orig_stmts):
            if not (isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1
                    and isinstance(stmt.body[0], cst.Assign)):
                continue
            assign = stmt.body[0]
            targets = [t.target for t in assign.targets]
            if not (len(targets) == 1 and isinstance(targets[0], cst.Name)
                    and targets[0].value == self.leak.var):
                continue
            if not isinstance(assign.value, cst.Call):
                continue
            func = assign.value.func
            func_name = ""
            if isinstance(func, cst.Name):
                func_name = func.value
            elif isinstance(func, cst.Attribute):
                func_name = func.attr.value
            # identity match: variable name + acquire API name overlap
            if self.leak.acquire in func_name or func_name in self.leak.acquire:
                acquire_idx = idx
                acquire_stmt = stmt
                release_var = targets[0].value
                break

        if acquire_idx is None:
            return updated

        # Find close: look for `<var>.<release>` after acquire (release may be
        # "close" or an alt release like "wait"/"cleanup" — match any known one)
        release_methods = {self.leak.release} | {
            r for spec in _all_specs()
            for r in [spec.release] + list(getattr(spec, "alt_releases", []))
        }
        for idx in range(len(stmts) - 1, acquire_idx, -1):
            stmt = stmts[idx]
            code_snippet = cst.Module(body=[stmt]).code
            for method in release_methods:
                if f"{release_var}.{method}()" in code_snippet:
                    close_idx = idx
                    break
            if close_idx is not None:
                break

        if close_idx is None:
            # No close to remove — this is a leak without any close at all. Fix by wrapping everything after acquire into with.
            # For conservative fix, wrap from acquire+1 to end (excluding final return if exists?)
            # But we need a close to know release name; use leak.release
            close_idx = None

        # Build WithItem from the acquire's RHS Call — use UPDATED statement to preserve exact formatting
        # acquire_stmt is from original, but we should get the corresponding updated stmt to keep whitespace
        updated_acquire_stmt = stmts[acquire_idx] if acquire_idx is not None else None
        source_assign_stmt = updated_acquire_stmt if isinstance(updated_acquire_stmt, cst.SimpleStatementLine) and len(updated_acquire_stmt.body)==1 and isinstance(updated_acquire_stmt.body[0], cst.Assign) else acquire_stmt
        if isinstance(source_assign_stmt, cst.SimpleStatementLine):
            assign_node: cst.Assign = source_assign_stmt.body[0]  # type: ignore
            open_call: cst.Call = assign_node.value  # type: ignore
            var_name = release_var or self.leak.var

            # Preserve the exact open_call (including args, whitespace)
            with_item = cst.WithItem(
                item=open_call,
                asname=cst.AsName(name=cst.Name(var_name)),
            )

            # Determine middle statements: those between acquire and close (exclusive)
            if close_idx is not None:
                middle = stmts[acquire_idx + 1 : close_idx]
            else:
                # No close found: wrap all following stmts (except maybe the final return which stays inside with)
                # Heuristic: if last stmt is Return, keep it inside with
                middle = stmts[acquire_idx + 1 :]

            # Fix leading_lines for first middle stmt: drop pure blank line before header
            if middle:
                first = middle[0]
                if isinstance(first, cst.SimpleStatementLine):
                    # Drop first empty line that is comment-less (the blank line after `f = open`)
                    new_leading = tuple(ll for ll in first.leading_lines if ll.comment is not None)
                    # If we removed the blank but now first statement has no leading comment, ensure we don't lose formatting after `with:`
                    # IndentedBlock will handle indent; with header already provides newline, so this is correct
                    # Keep at least empty if original had comment? Already kept
                    middle = [first.with_changes(leading_lines=new_leading)] + list(middle[1:])
                elif hasattr(first, "leading_lines"):
                    # e.g., If
                    new_leading = tuple(ll for ll in first.leading_lines if ll.comment is not None)  # type: ignore
                    middle = [first.with_changes(leading_lines=new_leading)] + list(middle[1:])  # type: ignore

            # Build with node
            # If middle is empty, we still create with with empty body (rare)
            # Preserve last return outside with if it exists and close_idx was the close line
            if close_idx is not None:
                # Keep statements after close (including return) outside with
                trailing = stmts[close_idx + 1 :]
                with_node = cst.With(
                    items=[with_item],
                    body=cst.IndentedBlock(body=list(middle)) if middle else cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
                )
                new_body_list = [with_node] + list(trailing)
            else:
                # No close: all middle stays inside with
                with_node = cst.With(
                    items=[with_item],
                    body=cst.IndentedBlock(body=list(middle)) if middle else cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
                )
                new_body_list = [with_node]

            return updated.with_changes(body=updated.body.with_changes(body=new_body_list))

        return updated


def _fixable(leaks: list[Leak]) -> list[Leak]:
    """Only SAFE fixability may be transformed (§5: detection and fixability
    are separate; a wrong autofix is worse than no autofix)."""
    return [lk for lk in leaks if getattr(lk, "fixability", "unknown") == "safe"]


def fix_source(source: str, leaks: list[Leak], config: CodeGateConfig | None = None) -> str:
    """Apply with-fix for each SAFE leak (one per function). Returns new source.

    Unsafe/unknown fixability findings are left untouched on purpose (§4/§5/§25).
    """
    safe = _fixable(leaks)
    if not safe:
        return source
    # Group leaks by function (fix one leak per function at a time for simplicity)
    by_func: dict[str, Leak] = {}
    for lk in safe:
        # Keep first leak per func
        if lk.func not in by_func:
            by_func[lk.func] = lk

    module = cst.parse_module(source)
    for func_name, leak in by_func.items():
        wrapper = cst.MetadataWrapper(module)
        fixer = _WithFixer(func_name, leak)
        try:
            # Must visit via wrapper.module so MetadataProvider is resolved
            new_module = wrapper.visit(fixer)
            # visit returns a CST node; ensure it's a Module
            module = new_module if isinstance(new_module, cst.Module) else wrapper.module.visit(fixer)
        except Exception as e:
            # Fallback: try raw visit (should not need metadata for this transformer aside from positions,
            # but positions are needed to locate acquire line)
            try:
                wrapper2 = cst.MetadataWrapper(module)
                module = wrapper2.module.visit(fixer)
            except Exception as e2:
                print(f"[fix] warning: failed to fix {func_name}: {e} / {e2}")
                continue
    return module.code


def _leak_identity(lk) -> tuple:
    """Line-shift-tolerant identity for a finding: function + variable +
    acquire API + kind. Survives line-number shifts caused by a fix
    (e.g. removing `f.close()` shifts everything below by one line)."""
    return (lk.func, lk.var, lk.acquire, lk.kind)


def fix_source_validated(source: str, leaks: list[Leak], config: CodeGateConfig | None = None
                         ) -> dict:
    """Full autofix validation pipeline (§27):

        Detect leak → SAFE-only candidate → LibCST transform → parse check
        → re-run CodeGate → targeted leak gone? no new definite leaks?
        → accept / reject

    Identity is LINE-SHIFT TOLERANT: findings are matched by
    (func, var, acquire, kind), so removing a `close` line during the
    transform does not falsely re-attribute every finding below it.

    Returns {"applied": bool, "code": str, "rejected": [reasons]}.
    """
    from .analyzer import analyze_source
    if config is None:
        config = CodeGateConfig.default()

    safe = _fixable(leaks)
    if not safe:
        return {"applied": False, "code": source, "rejected": [
            "no SAFE-fixability findings (unsafe/unknown left unmodified)"]}

    def definite_ids(src: str) -> set[tuple]:
        return {
            _leak_identity(lk)
            for lk in analyze_source(src, filename="<fixval>", config=config)
            if lk.confidence == "definite"
        }

    before = definite_ids(source)
    rejected: list[str] = []
    candidate = source
    for lk in safe:
        step = fix_source(candidate, [lk], config)
        if step == candidate:
            continue  # transformer made no change for this leak
        # 1) syntax check
        try:
            ast.parse(step)
        except SyntaxError as e:
            rejected.append(f"{lk.func}:{lk.acquire_line} — transformed code does not parse: {e}")
            continue
        # 2) targeted leak must be gone (identity-based, line-shift tolerant)
        after = analyze_source(step, filename="<fixval>", config=config)
        target_id = _leak_identity(lk)
        still = [x for x in after if _leak_identity(x) == target_id
                 and x.confidence == "definite"]
        if still:
            rejected.append(f"{lk.func}:{lk.acquire_line} — targeted definite leak still present after fix")
            continue
        # 3) no new definite leaks anywhere (identity comparison)
        new_definite = definite_ids(step) - before
        if new_definite:
            rejected.append(f"{lk.func}:{lk.acquire_line} — fix would introduce new definite leaks: {sorted(new_definite)}")
            continue
        candidate = step  # accept

    if candidate == source:
        return {"applied": False, "code": source, "rejected": rejected or ["no applicable safe fix"]}
    return {"applied": True, "code": candidate, "rejected": rejected}


def fix_file(path: str | Path, leaks: list[Leak] | None = None, config: CodeGateConfig | None = None, in_place: bool = False) -> str:
    """Fix a file on disk (if in_place, write back). Returns fixed source."""
    p = Path(path)
    src = p.read_text(encoding="utf-8")
    if leaks is None:
        from .analyzer import analyze_source
        if config is None:
            from .config import CodeGateConfig
            config = CodeGateConfig.default()
        leaks = analyze_source(src, filename=str(p), config=config)
    fixed = fix_source(src, leaks, config)
    if in_place and fixed != src:
        p.write_text(fixed, encoding="utf-8")
    return fixed
