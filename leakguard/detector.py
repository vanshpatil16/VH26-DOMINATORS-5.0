"""Open-site detection and per-site path verdicts.

Everything here is AST-driven. There is no regex over source text anywhere in
the detection path, which is what makes the A6-style decoy (a docstring that
says "remember to call f.close()") a non-event.

The detector produces one `OpenSite` per resource acquisition, decorated with
the static context the feature extractor needs (loop nesting, guarding `finally`
blocks, enclosing class ownership, route decorators) plus the path-sensitive
`HandleOutcome` from `pathmodel`.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

from .pathmodel import (
    OWNERSHIP_TRANSFER_ESCAPES,
    HandleOutcome,
    Path,
    analyse_handle,
    collect_lock_objects,
    enumerate_scope_paths,
)
from .disposal import collect_disposal  # noqa: F401
from .registry import (
    DEFAULT_REGISTRY,
    GENERIC_CLOSERS,
    ImportResolver,
    Registry,
    ResourceSpec,
    collect_aliases,
    dotted_name,
)

#: Methods whose body is understood as the owner releasing its attributes.
OWNER_CLOSER_METHODS = frozenset(
    {
        "close", "aclose", "__exit__", "__aexit__", "__del__", "shutdown",
        "stop", "dispose", "cleanup", "teardown", "disconnect", "quit",
        "release", "finalize", "destroy",
    }
)

#: Extra release verbs that only make sense on an owned attribute.
OWNER_RELEASE_VERBS = frozenset({"wait", "communicate", "join", "__exit__", "__aexit__"})

#: Decorators that put a function on a request path — high exposure.
ROUTE_DECORATOR_HINTS = (
    "route", "get", "post", "put", "patch", "delete", "websocket",
    "task", "job", "periodic_task", "shared_task", "endpoint", "command",
)

VERDICT_SAFE = "SAFE"
VERDICT_LEAK = "DEFINITE_LEAK"
#: Provable, but only when an exception propagates out of the function. Real
#: (CPython raises ResourceWarning for it) yet reporting it as a build failure
#: would flag the single most common shape of correct-looking Python, so it
#: gets its own warning tier and does not fail CI by default.
VERDICT_EXCEPTION_LEAK = "EXCEPTION_PATH_LEAK"
VERDICT_UNKNOWN = "UNKNOWN"

#: Verdicts that block a build (spec section 10).
BLOCKING_VERDICTS = frozenset({VERDICT_LEAK})


# --------------------------------------------------------------------------- #
# Static context collected in one AST walk
# --------------------------------------------------------------------------- #


@dataclass
class StaticContext:
    loop_lines: Set[int] = field(default_factory=set)
    try_lines: Set[int] = field(default_factory=set)
    finally_lines: Set[int] = field(default_factory=set)
    with_lines: Set[int] = field(default_factory=set)
    except_lines: Set[int] = field(default_factory=set)
    line_scope: Dict[int, str] = field(default_factory=dict)
    line_class: Dict[int, str] = field(default_factory=dict)
    has_main_guard: bool = False


def _block_lines(stmts: Sequence[ast.stmt]) -> Set[int]:
    lines: Set[int] = set()
    for stmt in stmts:
        for sub in ast.walk(stmt):
            line = getattr(sub, "lineno", None)
            if line is not None:
                lines.add(line)
    return lines


def _is_main_guard(node: ast.If) -> bool:
    test = node.test
    if not isinstance(test, ast.Compare) or not isinstance(test.left, ast.Name):
        return False
    if test.left.id != "__name__":
        return False
    for comparator in test.comparators:
        if isinstance(comparator, ast.Constant) and comparator.value == "__main__":
            return True
    return False


def collect_static_context(tree: ast.AST) -> StaticContext:
    ctx = StaticContext()

    def walk(node: ast.AST, scope: str, cls: Optional[str], in_loop: bool) -> None:
        for child in ast.iter_child_nodes(node):
            line = getattr(child, "lineno", None)
            if line is not None:
                ctx.line_scope.setdefault(line, scope or "<module>")
                if cls:
                    ctx.line_class.setdefault(line, cls)
                if in_loop:
                    ctx.loop_lines.add(line)

            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(child, f"{scope}.{child.name}" if scope else child.name, cls, False)
            elif isinstance(child, ast.ClassDef):
                walk(child, f"{scope}.{child.name}" if scope else child.name, child.name, in_loop)
            elif isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
                ctx.loop_lines.update(_block_lines(child.body))
                walk(child, scope, cls, True)
            elif isinstance(child, (ast.With, ast.AsyncWith)):
                ctx.with_lines.update(_block_lines(child.body))
                ctx.with_lines.add(child.lineno)
                walk(child, scope, cls, in_loop)
            elif isinstance(child, ast.Try) or type(child).__name__ == "TryStar":
                ctx.try_lines.update(_block_lines(child.body))
                ctx.finally_lines.update(_block_lines(getattr(child, "finalbody", [])))
                for handler in child.handlers:
                    ctx.except_lines.update(_block_lines(handler.body))
                walk(child, scope, cls, in_loop)
            else:
                if isinstance(child, ast.If) and _is_main_guard(child):
                    ctx.has_main_guard = True
                walk(child, scope, cls, in_loop)

    walk(tree, "", None, False)
    return ctx


# --------------------------------------------------------------------------- #
# Intra-class ownership + intra-module function summaries
# --------------------------------------------------------------------------- #


def collect_class_ownership(tree: ast.AST) -> Dict[str, Set[str]]:
    """class name -> attribute names released by one of its closer methods.

    This is the single highest-value false-positive rule in the codebase:
    `self.conn = sqlite3.connect(...)` in `__init__` is only a leak when nothing
    in the class ever releases it.
    """
    owned: Dict[str, Set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        closed: Set[str] = set()
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name not in OWNER_CLOSER_METHODS:
                continue
            for sub in ast.walk(item):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                    if sub.func.attr in GENERIC_CLOSERS or sub.func.attr in OWNER_RELEASE_VERBS:
                        target = dotted_name(sub.func.value)
                        if target and target.startswith("self."):
                            closed.add(target)
                    # contextlib.closing(self.db) inside the closer counts too.
                    for arg in sub.args:
                        name = dotted_name(arg)
                        if name and name.startswith("self.") and sub.func.attr in (
                            "closing",
                            "enter_context",
                        ):
                            closed.add(name)
                if isinstance(sub, ast.withitem):
                    target = dotted_name(sub.context_expr)
                    if target and target.startswith("self."):
                        closed.add(target)
        owned[node.name] = closed
    return owned


def collect_class_closer_methods(tree: ast.AST) -> Dict[str, Set[str]]:
    """class name -> the closer-shaped methods it defines (possibly empty).

    A class with a `close()` that releases something *else* is a different
    situation from a class with no lifecycle method at all, and the model gets
    to see both.
    """
    methods: Dict[str, Set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        methods[node.name] = {
            item.name
            for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            and item.name in OWNER_CLOSER_METHODS
        }
    return methods


def collect_function_summaries(
    tree: ast.AST,
    resolver: ImportResolver,
    registry: Registry = DEFAULT_REGISTRY,
) -> Dict[str, Dict[str, str]]:
    """function name -> {parameter: "all" | "some"}.

    "all" means the callee releases that parameter on *every* one of its exit
    paths, so the caller's site is provably safe. "some" means it releases it on
    at least one path — the PDF benchmark case `cleanup(f, condition)` — which
    is precisely an UNKNOWN, never a SAFE.

    A deliberately shallow, single-module approximation of the P2
    interprocedural fixpoint: it reuses the same path enumerator rather than
    pattern-matching the body, so `if condition: f.close()` is distinguished
    from `f.close()` for free.
    """
    summaries: Dict[str, Dict[str, str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        params = {a.arg for a in node.args.args} | {a.arg for a in node.args.kwonlyargs}
        params |= {a.arg for a in getattr(node.args, "posonlyargs", [])}
        params.discard("self")
        params.discard("cls")
        if not params:
            continue
        paths, _ctx = enumerate_scope_paths(node, resolver, registry, seed_handles=params)
        if not paths:
            continue
        verdicts: Dict[str, str] = {}
        for param in sorted(params):
            closing = sum(
                1
                for path in paths
                if any(e.kind == "close" and e.handle == param for e in path.events)
            )
            if closing == len(paths):
                verdicts[param] = "all"
            elif closing:
                verdicts[param] = "some"
        if verdicts:
            summaries[node.name] = verdicts
    return summaries


# --------------------------------------------------------------------------- #
# Open sites
# --------------------------------------------------------------------------- #


@dataclass
class OpenSite:
    file: str
    line: int
    handle: str
    call: str
    resource_type: str
    weight: float
    is_async: bool
    scope: str
    class_name: Optional[str]
    in_loop: bool
    in_try: bool
    in_with: bool
    in_finally: bool
    decorators: Tuple[str, ...]
    outcome: HandleOutcome
    close_lines: Tuple[int, ...]
    close_guarded: bool
    escape_callees: Tuple[str, ...]
    class_closes_attr: bool
    class_has_any_closer: bool
    callee_closes_param: bool
    callee_may_close_param: bool
    is_test_or_script: bool
    path_truncated: bool
    # Module-level disposal evidence (see leakguard/disposal.py). Defaulted so
    # every existing constructor call stays valid; only `analyse_module` fills
    # them in. They are inputs to the confidence model, never to `verdict`:
    # the rules must keep answering UNKNOWN here, because a heuristic about what
    # the caller *appears* to do is not a proof.
    escape_disposed: bool = False
    escape_recipient_unknown: bool = False
    container_drained: bool = False

    @property
    def escapes(self) -> Set[str]:
        return self.outcome.escape_kinds

    @property
    def is_route(self) -> bool:
        return is_route_decorated(self.decorators)

    @property
    def is_owned_attribute(self) -> bool:
        return bool(self.class_name) and self.handle.startswith("self.")

    @property
    def verdict(self) -> str:
        """Rules-only verdict. UNKNOWN is a first-class answer, never promoted."""
        if self.class_closes_attr or self.callee_closes_param:
            return VERDICT_SAFE
        # Proven released on every enumerated path. This has to outrank the
        # escape check: passing a handle to `json.load(fh)` inside a
        # try/finally is an escape *and* a guaranteed close.
        if self.outcome.total and self.outcome.closed == self.outcome.total:
            return VERDICT_SAFE
        # Intra-class ownership (spec 5b): an attribute nothing in the class
        # ever releases is the high-value leak pylint and leakaudit both miss.
        if self.is_owned_attribute:
            return VERDICT_LEAK
        # A callee that closes the handle on *some* of its paths is exactly the
        # case we must not resolve either way.
        if self.callee_may_close_param:
            return VERDICT_UNKNOWN
        if self.outcome.escape_kinds & OWNERSHIP_TRANSFER_ESCAPES:
            return VERDICT_UNKNOWN
        if self.outcome.leaking_normal > 0:
            return VERDICT_LEAK
        if self.outcome.leaking_exception > 0:
            return VERDICT_EXCEPTION_LEAK
        if self.path_truncated:
            return VERDICT_UNKNOWN
        return VERDICT_SAFE


@dataclass
class ModuleAnalysis:
    file: str
    sites: List[OpenSite]
    parse_error: Optional[str] = None


def _scope_nodes(tree: ast.Module) -> List[ast.AST]:
    """Module body plus every function body, each analysed independently."""
    scopes: List[ast.AST] = [tree]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scopes.append(node)
    return scopes


def _decorator_names(node: ast.AST) -> Tuple[str, ...]:
    names: List[str] = []
    for dec in getattr(node, "decorator_list", []) or []:
        target = dec.func if isinstance(dec, ast.Call) else dec
        name = dotted_name(target)
        if name:
            names.append(name)
    return tuple(names)


def is_route_decorated(decorators: Sequence[str]) -> bool:
    for name in decorators:
        tail = name.rsplit(".", 1)[-1]
        if tail in ROUTE_DECORATOR_HINTS and "." in name:
            return True
    return False


def is_test_or_script_path(path: str, has_main_guard: bool) -> bool:
    normalised = path.replace("\\", "/")
    base = os.path.basename(normalised)
    if base.startswith("test_") or base.endswith("_test.py") or base == "conftest.py":
        return True
    if "/tests/" in normalised or "/test/" in normalised:
        return True
    return has_main_guard


def _escape_callees(paths: Sequence[Path], handle: str) -> Tuple[str, ...]:
    callees: List[str] = []
    for path in paths:
        for event in path.events:
            if event.kind == "escape" and event.handle == handle:
                if event.detail.startswith("call_arg:"):
                    name = event.detail.split(":", 1)[1]
                    if name not in callees:
                        callees.append(name)
    return tuple(callees)


def analyse_module(
    source: str,
    filename: str,
    registry: Registry = DEFAULT_REGISTRY,
) -> ModuleAnalysis:
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:  # a mutant that fails to parse is a pipeline bug
        return ModuleAnalysis(file=filename, sites=[], parse_error=str(exc))

    resolver: ImportResolver = collect_aliases(tree)
    static = collect_static_context(tree)
    ownership = collect_class_ownership(tree)
    disposal = collect_disposal(tree, ownership)
    closer_methods = collect_class_closer_methods(tree)
    summaries = collect_function_summaries(tree, resolver, registry)
    test_or_script = is_test_or_script_path(filename, static.has_main_guard)

    sites: List[OpenSite] = []
    seen: Set[Tuple[str, int]] = set()

    lock_objects = collect_lock_objects(tree, resolver, registry)

    for scope_node in _scope_nodes(tree):
        paths, scope_ctx = enumerate_scope_paths(scope_node, resolver, registry, lock_objects)
        opens: Dict[Tuple[str, int], str] = {}
        for path in paths:
            for event in path.events:
                if event.kind == "open" and event.handle:
                    opens[(event.handle, event.line)] = event.detail

        for (handle, line), call in sorted(opens.items(), key=lambda kv: kv[0][1]):
            if (handle, line) in seen:
                continue
            seen.add((handle, line))
            spec: Optional[ResourceSpec] = registry.lookup(call)
            outcome = analyse_handle(paths, handle, line)
            class_name = static.line_class.get(line)
            class_closes = bool(class_name and handle in ownership.get(class_name, set()))
            callees = _escape_callees(paths, handle)
            verdict_by_callee = [
                summaries.get(c.rsplit(".", 1)[-1], {}) for c in callees
            ]
            closes_param = any(
                "all" in verdicts.values() for verdicts in verdict_by_callee
            )
            may_close_param = not closes_param and any(
                "some" in verdicts.values() for verdicts in verdict_by_callee
            )
            sites.append(
                OpenSite(
                    file=filename,
                    line=line,
                    handle=handle,
                    call=call,
                    resource_type=spec.type if spec else "UNKNOWN",
                    weight=spec.weight if spec else 1.0,
                    is_async=spec.is_async if spec else False,
                    scope=static.line_scope.get(line, "<module>"),
                    class_name=class_name,
                    in_loop=line in static.loop_lines,
                    in_try=line in static.try_lines,
                    in_with=line in static.with_lines,
                    in_finally=line in static.finally_lines,
                    decorators=_decorator_names(scope_node),
                    outcome=outcome,
                    close_lines=tuple(sorted(outcome.close_lines)),
                    close_guarded=any(
                        cl in static.finally_lines or cl in static.with_lines
                        for cl in outcome.close_lines
                    ),
                    escape_callees=callees,
                    class_closes_attr=class_closes,
                    class_has_any_closer=bool(closer_methods.get(class_name or "", set())),
                    callee_closes_param=closes_param,
                    callee_may_close_param=may_close_param,
                    is_test_or_script=test_or_script,
                    path_truncated=scope_ctx.truncated,
                    escape_disposed=disposal.escape_disposed(
                        static.line_scope.get(line, "<module>")),
                    escape_recipient_unknown=disposal.recipient_unknown(
                        static.line_scope.get(line, "<module>")),
                    container_drained=disposal.container_drained(
                        static.line_scope.get(line, "<module>")),
                )
            )
    sites.sort(key=lambda s: (s.line, s.handle))
    return ModuleAnalysis(file=filename, sites=sites)


def analyse_file(path: str, registry: Registry = DEFAULT_REGISTRY) -> ModuleAnalysis:
    with open(path, "r", encoding="utf-8") as handle:
        source = handle.read()
    return analyse_module(source, path, registry)
