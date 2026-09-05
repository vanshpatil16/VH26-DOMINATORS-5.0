"""Structured path enumeration — the poor man's CFG.

`LEAKGUARD_SPEC.md` phase P0-c builds a real basic-block CFG. The dataset
pipeline needs path-sensitive *features* before that exists, so this module
enumerates execution paths directly over the structured AST. It models the same
edge kinds the CFG will (NORMAL / TRUE / FALSE / EXCEPT / FINALLY / LOOP_BACK /
BREAK / CONTINUE / RETURN / RAISE) and is designed to be swapped out for, or
validated against, the block-based builder later.

A path is a sequence of `Event`s ending in a terminator. Everything downstream
(`features.py`, the verifier) only ever asks two questions of a path:

    * was this open-site executed on it?
    * did the handle get closed, escape, or get orphaned before the path ended?

Deliberate modelling decisions (each one is a documented edge case in
`dataset/mutated_code/edge_cases.md`):

    * `close()` is assumed not to raise. Generating an exception path *through*
      a close would flag every correct program.
    * `with sqlite3.connect(...) as conn` does NOT close (registry `ctx_closes`).
    * `yield` inside a plain generator forks an "abandoned" path, because a
      consumer may never resume it. `@contextmanager` / `@pytest.fixture`
      suppress that fork — the framework guarantees resumption.
    * `sys.exit` / `os._exit` terminate a path that is never counted as leaking.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

from .registry import (
    DEFAULT_REGISTRY,
    GENERIC_CLOSERS,
    ImportResolver,
    Registry,
    ResourceSpec,
    dotted_name,
)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

MAX_PATHS = 3000
MAX_RAISE_SPLITS = 8
MAX_LOOP_UNROLL = 2

TERM_FALL = "fall"
TERM_RETURN = "return"
TERM_RAISE = "raise"
TERM_BREAK = "break"
TERM_CONTINUE = "continue"
TERM_ABANDON = "abandon"        # generator suspended at yield and never resumed
TERM_EXIT = "process_exit"      # sys.exit / os._exit: the OS reclaims everything

#: Terminators that end the enclosing function.
FUNCTION_EXITS = frozenset({TERM_RETURN, TERM_RAISE, TERM_ABANDON, TERM_EXIT, TERM_FALL})

#: Calls that cannot realistically raise; excluded from EXCEPT-edge generation
#: so the path count stays sane on ordinary code.
NON_RAISING = frozenset(
    {
        "len", "str", "int", "float", "bool", "list", "dict", "set", "tuple",
        "print", "isinstance", "issubclass", "range", "enumerate", "repr",
        "sorted", "min", "max", "sum", "abs", "type", "id", "zip", "map",
        "filter", "any", "all", "hasattr", "bytes", "bytearray", "iter",
        "logging.debug", "logging.info", "logging.warning", "logging.error",
        "time.time", "time.monotonic",
    }
)

CONTAINER_ADDERS = frozenset({"append", "add", "extend", "insert", "put", "push", "setdefault"})

DEFERRED_CLOSERS = frozenset({"atexit.register", "weakref.finalize"})

CONTEXT_WRAPPERS = frozenset({"contextlib.closing", "closing", "contextlib.aclosing", "aclosing"})

EXIT_STACK_FACTORIES = frozenset(
    {"contextlib.ExitStack", "ExitStack", "contextlib.AsyncExitStack", "AsyncExitStack"}
)

STACK_ENTER = frozenset({"enter_context", "enter_async_context", "push", "callback"})

PROCESS_EXITS = frozenset({"sys.exit", "os._exit", "os.abort", "exit", "quit"})

#: Escape kinds that genuinely transfer *ownership*, making the site
#: unprovable. Passing a handle to an opaque call is deliberately NOT one of
#: them: `process(f)`, `json.load(f)` and `f.read()` overwhelmingly consume a
#: handle without closing it, and treating every use as a transfer collapses
#: recall (it turns the PDF benchmark cases 3a/7b/8d/9 into UNKNOWN). Whether a
#: callee closes its parameter is answered by function summaries instead, and
#: `escapes_call_arg` still reaches the model as a feature.
OWNERSHIP_TRANSFER_ESCAPES = frozenset({"return", "yield", "self_attr", "container", "global"})

#: Decorators that guarantee the generator body is resumed to completion.
GUARANTEED_RESUME_DECORATORS = (
    "contextmanager",
    "asynccontextmanager",
    "fixture",
    "yield_fixture",
)


# --------------------------------------------------------------------------- #
# Path data model
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Event:
    """One observable action on a path."""

    kind: str                       # open|close|stack_close|escape|reassign|raising_call
    handle: Optional[str]
    line: int
    detail: str = ""                # escape kind, callee name, resource call, ...
    owner: Optional[str] = None     # ExitStack variable that owns the handle


@dataclass(frozen=True)
class Path:
    events: Tuple[Event, ...]
    term: str
    line: int = 0

    def with_suffix(self, events: Sequence[Event], term: str, line: int = 0) -> "Path":
        return Path(self.events + tuple(events), term, line or self.line)


@dataclass
class ScopeContext:
    """Per-function analysis state."""

    registry: Registry
    resolver: ImportResolver
    handles: Set[str] = field(default_factory=set)
    stack_vars: Set[str] = field(default_factory=set)
    specs: Dict[str, ResourceSpec] = field(default_factory=dict)
    #: `reader, writer = await asyncio.open_connection(...)` yields two names
    #: for one resource; closing either closes the acquisition.
    aliases: Dict[str, str] = field(default_factory=dict)
    #: Names known to hold a lock-like object, so `x.acquire()` is an
    #: acquisition and an unrelated `job.acquire()` is not.
    lock_objects: Set[str] = field(default_factory=set)
    suppress_abandon: bool = False
    raise_splits: int = 0
    truncated: bool = False

    def canon(self, name: Optional[str]) -> Optional[str]:
        if name is None:
            return None
        return self.aliases.get(name, name)

    def can_split_raise(self) -> bool:
        if self.raise_splits >= MAX_RAISE_SPLITS:
            return False
        self.raise_splits += 1
        return True


# --------------------------------------------------------------------------- #
# Expression helpers
# --------------------------------------------------------------------------- #


def resolve_call_name(call: ast.Call, resolver: ImportResolver) -> Optional[str]:
    raw = dotted_name(call.func)
    return resolver.resolve(raw) if raw else None


LOCK_NAME_HINT = ("lock", "mutex", "sem", "gate", "guard", "latch", "barrier")


def match_resource(call: ast.Call, ctx: ScopeContext) -> Optional[ResourceSpec]:
    """Registry match for a *constructor* acquisition."""
    name = resolve_call_name(call, ctx.resolver)
    spec = ctx.registry.lookup(name) if name else None
    if spec is not None and spec.acquired_by:
        return None  # `threading.Lock()` allocates nothing; `.acquire()` does
    return spec


def match_acquire(call: ast.Call, ctx: ScopeContext) -> Optional[Tuple[str, ResourceSpec]]:
    """`lock.acquire()` — the acquisition for release-style resources."""
    func = call.func
    if not isinstance(func, ast.Attribute) or func.attr != "acquire":
        return None
    owner = target_name(func.value)
    if not owner:
        return None
    tail = owner.rsplit(".", 1)[-1].lower()
    if owner not in ctx.lock_objects and not any(hint in tail for hint in LOCK_NAME_HINT):
        return None
    spec = ctx.registry.lookup("threading.Lock")
    return (owner, spec) if spec else None


def unwrap(node: Optional[ast.AST]) -> Optional[ast.AST]:
    """Strip `await` so `await aiofiles.open(p)` looks like a plain call."""
    while isinstance(node, ast.Await):
        node = node.value
    return node


def target_name(node: Optional[ast.AST]) -> Optional[str]:
    """Handle name for an assignment target: `f` or `self.conn`."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return dotted_name(node)
    return None


def _is_closer_call(call: ast.Call, ctx: ScopeContext) -> Optional[Tuple[str, str]]:
    """Return (handle, method) when `call` releases a tracked handle."""
    func = call.func
    if not isinstance(func, ast.Attribute):
        # `os.close(fd)` style: module-level closer taking the handle.
        name = resolve_call_name(call, ctx.resolver)
        if name in ("os.close", "os.closerange") and call.args:
            handle = target_name(call.args[0])
            if handle and handle in ctx.handles:
                return handle, "os.close"
        return None
    owner = ctx.canon(target_name(func.value))
    if not owner or owner not in ctx.handles:
        return None
    spec = ctx.specs.get(owner)
    if spec is not None:
        allowed = set(spec.close) | set(GENERIC_CLOSERS)
    else:
        # No spec: the handle is a parameter or an alias, so accept any release
        # verb the registry knows about.
        allowed = set(ctx.registry.all_closers)
    allowed |= {"__exit__", "__aexit__"}
    if func.attr in allowed:
        return owner, func.attr
    return None


def _deferred_close(call: ast.Call, ctx: ScopeContext) -> Optional[str]:
    """Cleanup registered now and guaranteed to run later.

    Covers `atexit.register(f.close)`, `weakref.finalize(o, f.close)` and
    `stack.callback(f.close)` / `stack.push(f)` on an ExitStack.
    """
    name = resolve_call_name(call, ctx.resolver)
    func = call.func
    on_stack = (
        isinstance(func, ast.Attribute)
        and func.attr in ("callback", "push")
        and target_name(func.value) in ctx.stack_vars
    )
    if name not in DEFERRED_CLOSERS and not on_stack:
        return None
    for arg in list(call.args) + [kw.value for kw in call.keywords]:
        if isinstance(arg, ast.Attribute) and arg.attr in GENERIC_CLOSERS:
            owner = ctx.canon(target_name(arg.value))
            if owner and owner in ctx.handles:
                return owner
        if on_stack:
            owner = ctx.canon(target_name(arg))
            if owner and owner in ctx.handles:
                return owner
    return None


def _stack_close(call: ast.Call, ctx: ScopeContext) -> Optional[str]:
    func = call.func
    if isinstance(func, ast.Attribute) and func.attr in ("close", "aclose", "__exit__", "pop_all"):
        owner = target_name(func.value)
        if owner and owner in ctx.stack_vars:
            return owner
    return None


def _stack_enter(call: ast.Call, ctx: ScopeContext) -> Optional[str]:
    func = call.func
    if isinstance(func, ast.Attribute) and func.attr in STACK_ENTER:
        owner = target_name(func.value)
        if owner and owner in ctx.stack_vars:
            return owner
    return None


def _can_raise(node: ast.AST, ctx: ScopeContext) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            name = resolve_call_name(sub, ctx.resolver)
            if name is None:
                return True
            if name not in NON_RAISING and name.rsplit(".", 1)[-1] not in NON_RAISING:
                return True
        if isinstance(sub, ast.Assert):
            return True
    return False


def _process_exit(node: ast.AST, ctx: ScopeContext) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            if resolve_call_name(sub, ctx.resolver) in PROCESS_EXITS:
                return True
    return False


# --------------------------------------------------------------------------- #
# Event extraction for a single (non-compound) statement
# --------------------------------------------------------------------------- #


def _tuple_names(targets: Sequence[ast.AST]) -> List[str]:
    """Flatten `a, (b, c) = ...` into [a, b, c]."""
    out: List[str] = []
    for target in targets:
        if isinstance(target, (ast.Tuple, ast.List)):
            out.extend(_tuple_names(target.elts))
        else:
            name = target_name(target)
            if name:
                out.append(name)
    return out


def temp_handle(call: ast.Call) -> str:
    """Synthetic handle for an open-site that is never bound to a name."""
    return "<temp@%d:%d>" % (getattr(call, "lineno", 0), getattr(call, "col_offset", 0))


def escaping_names(node: Optional[ast.AST], ctx: ScopeContext) -> List[str]:
    """Handles that the *value* of an expression hands to the caller.

    `return fh` escapes; `return fh.read()` does not. Getting this wrong turns
    every correct read-and-return helper into an UNKNOWN.
    """
    inner = unwrap(node)
    if inner is None:
        return []
    if isinstance(inner, (ast.Name, ast.Attribute)):
        name = ctx.canon(target_name(inner))
        return [name] if name and name in ctx.handles else []
    if isinstance(inner, (ast.Tuple, ast.List, ast.Set)):
        out: List[str] = []
        for elt in inner.elts:
            out.extend(escaping_names(elt, ctx))
        return out
    if isinstance(inner, ast.Dict):
        out = []
        for value in inner.values:
            out.extend(escaping_names(value, ctx))
        return out
    if isinstance(inner, ast.IfExp):
        return escaping_names(inner.body, ctx) + escaping_names(inner.orelse, ctx)
    return []


def expression_events(
    node: ast.AST,
    ctx: ScopeContext,
    line: int,
    skip_calls: Optional[Set[int]] = None,
) -> List[Event]:
    """Events produced by evaluating an arbitrary expression.

    `skip_calls` holds the ids of resource calls the caller has already bound to
    a named handle, so `f = open(p)` does not also register a temp open-site.
    Unbound acquisitions such as a bare `subprocess.Popen(cmd)` statement or
    `json.load(open(p))` DO become temp open-sites — they are exactly the leaks
    a name-based tracker misses.
    """
    skip = set(skip_calls or ())
    opens: List[Event] = []
    rest: List[Event] = []
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        sub_line = getattr(sub, "lineno", line)

        closed = _is_closer_call(sub, ctx)
        if closed:
            rest.append(Event("close", closed[0], sub_line, detail=closed[1]))
            continue

        stack_var = _stack_close(sub, ctx)
        if stack_var:
            rest.append(Event("stack_close", None, sub_line, owner=stack_var))
            continue

        deferred = _deferred_close(sub, ctx)
        if deferred:
            rest.append(Event("close", deferred, sub_line, detail="deferred"))
            continue

        # `stack.enter_context(open(p))` anywhere, including inside a
        # comprehension: the stack takes ownership, it is not an escape.
        stack_owner = _stack_enter(sub, ctx)
        if stack_owner:
            for arg in sub.args:
                inner = unwrap(arg)
                if isinstance(inner, ast.Call):
                    spec = match_resource(inner, ctx)
                    if spec is not None:
                        temp = temp_handle(inner)
                        ctx.handles.add(temp)
                        ctx.specs.setdefault(temp, spec)
                        opens.append(
                            Event("open", temp, getattr(inner, "lineno", sub_line),
                                  detail=spec.call, owner=stack_owner)
                        )
                        skip.add(id(inner))
            continue

        acquired = match_acquire(sub, ctx)
        if acquired and id(sub) not in skip:
            owner, spec = acquired
            ctx.handles.add(owner)
            ctx.specs.setdefault(owner, spec)
            opens.append(Event("open", owner, sub_line, detail=spec.call))
            continue

        # An unbound acquisition becomes a temp open-site.
        if id(sub) not in skip:
            spec = match_resource(sub, ctx)
            if spec is not None:
                temp = temp_handle(sub)
                ctx.handles.add(temp)
                ctx.specs.setdefault(temp, spec)
                opens.append(Event("open", temp, sub_line, detail=spec.call))
                continue

        callee = resolve_call_name(sub, ctx.resolver) or "<dynamic>"
        method = callee.rsplit(".", 1)[-1]
        is_container_add = isinstance(sub.func, ast.Attribute) and method in CONTAINER_ADDERS

        for arg in list(sub.args) + [kw.value for kw in sub.keywords]:
            inner = unwrap(arg)
            if isinstance(inner, ast.Call):
                # `json.load(open(p))`: the temp handle escapes into the callee.
                if id(inner) not in skip and match_resource(inner, ctx) is not None:
                    rest.append(
                        Event(
                            "escape",
                            temp_handle(inner),
                            sub_line,
                            detail="call_arg:" + callee,
                        )
                    )
                continue
            name = ctx.canon(target_name(inner))
            if name and name in ctx.handles:
                kind = "container" if is_container_add else "call_arg:" + callee
                rest.append(Event("escape", name, sub_line, detail=kind))

        if _can_raise(sub, ctx):
            rest.append(Event("raising_call", None, sub_line, detail=callee))
    return opens + rest


def _open_binding(
    value: Optional[ast.AST], ctx: ScopeContext
) -> List[Tuple[ast.Call, ResourceSpec, Optional[str]]]:
    """Open-calls directly produced by an expression, with their owning stack.

    Returns (call_node, spec, stack_owner). Covers the direct form, the ternary
    form `open(a) if c else open(b)`, `closing(open(p))` and
    `stack.enter_context(open(p))`.
    """
    node = unwrap(value)
    found: List[Tuple[ast.Call, ResourceSpec, Optional[str]]] = []
    if node is None:
        return found
    if isinstance(node, ast.IfExp):
        found.extend(_open_binding(node.body, ctx))
        found.extend(_open_binding(node.orelse, ctx))
        return found
    if isinstance(node, ast.Call):
        name = resolve_call_name(node, ctx.resolver)
        if name in CONTEXT_WRAPPERS and node.args:
            return _open_binding(node.args[0], ctx)
        owner = _stack_enter(node, ctx)
        if owner and node.args:
            for call, spec, _ in _open_binding(node.args[0], ctx):
                found.append((call, spec, owner))
            return found
        spec = match_resource(node, ctx)
        if spec:
            found.append((node, spec, None))
    return found


def simple_statement_paths(stmt: ast.stmt, ctx: ScopeContext) -> List[Path]:
    """Paths produced by one non-compound statement."""
    line = getattr(stmt, "lineno", 0)
    events: List[Event] = []
    term = TERM_FALL

    if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        value = stmt.value
        targets = list(stmt.targets) if isinstance(stmt, ast.Assign) else [stmt.target]
        names = [n for n in (target_name(t) for t in targets) if n]
        if not names:
            # `reader, writer = await asyncio.open_connection(...)`: one
            # acquisition, several names. The first becomes canonical and the
            # rest alias to it, so closing any member closes the site.
            names = [n for n in _tuple_names(targets) if n][:1]
        openings = _open_binding(value, ctx) if value is not None else []

        if value is not None:
            events.extend(
                expression_events(value, ctx, line, {id(c) for c, _s, _o in openings})
            )
        # Drop the generic raising_call for a pure open: if `open()` raises no
        # resource was acquired, so that path cannot leak.
        if openings:
            events = [e for e in events if e.kind != "raising_call"]

        for name in names:
            if name in ctx.handles:
                events.append(Event("reassign", name, line))
        for call, spec, owner in openings:
            handle = names[0] if names else "<temp@%d>" % line
            ctx.specs.setdefault(handle, spec)
            events.append(
                Event(
                    "open",
                    handle,
                    getattr(call, "lineno", line),
                    detail=spec.call,
                    owner=owner,
                )
            )
            if handle.startswith("self."):
                events.append(Event("escape", handle, line, detail="self_attr"))
        # `self.fh = f` / `GLOBAL = f` escape an already-open handle.
        if value is not None and not openings:
            for src in escaping_names(value, ctx):
                for name in names:
                    if name.startswith("self.") or name.isupper():
                        events.append(Event("escape", src, line, detail="self_attr"))
        # `bucket[key] = f` is a container escape.
        for tgt in targets:
            if isinstance(tgt, ast.Subscript) and value is not None:
                for src in escaping_names(value, ctx):
                    events.append(Event("escape", src, line, detail="container"))

    elif isinstance(stmt, ast.Return):
        if stmt.value is not None:
            events.extend(expression_events(stmt.value, ctx, line))
            for name in escaping_names(stmt.value, ctx):
                events.append(Event("escape", name, line, detail="return"))
            # `return open(p)` hands the fresh handle straight to the caller.
            inner = unwrap(stmt.value)
            if isinstance(inner, ast.Call) and match_resource(inner, ctx) is not None:
                events.append(Event("escape", temp_handle(inner), line, detail="return"))
        term = TERM_RETURN

    elif isinstance(stmt, ast.Raise):
        if stmt.exc is not None:
            events.extend(expression_events(stmt.exc, ctx, line))
        term = TERM_RAISE

    elif isinstance(stmt, ast.Break):
        term = TERM_BREAK

    elif isinstance(stmt, ast.Continue):
        term = TERM_CONTINUE

    elif isinstance(
        stmt,
        (
            ast.Global,
            ast.Nonlocal,
            ast.Pass,
            ast.Import,
            ast.ImportFrom,
            ast.Delete,
            ast.FunctionDef,
            ast.AsyncFunctionDef,
            ast.ClassDef,
        ),
    ):
        pass  # nested scopes are analysed independently

    elif isinstance(stmt, ast.Expr):
        events.extend(expression_events(stmt.value, ctx, line))
        for sub in ast.walk(stmt.value):
            if isinstance(sub, (ast.Yield, ast.YieldFrom)) and sub.value is not None:
                if ctx.suppress_abandon:
                    continue  # @contextmanager / fixture: the handle comes back
                for name in escaping_names(sub.value, ctx):
                    events.append(Event("escape", name, line, detail="yield"))
        if _process_exit(stmt.value, ctx):
            return [Path(tuple(events), TERM_EXIT, line)]

    else:
        for child in ast.iter_child_nodes(stmt):
            if isinstance(child, ast.expr):
                events.extend(expression_events(child, ctx, line))

    paths = [Path(tuple(events), term, line)]

    # EXCEPT edge: this statement may raise before the next one runs.
    if term == TERM_FALL and not any(e.kind in ("close", "stack_close") for e in events):
        if _can_raise(stmt, ctx) and ctx.can_split_raise():
            # The callee already received the handle before it raised, so the
            # escape survives; the acquisition itself does not.
            pre = tuple(e for e in events if e.kind in ("raising_call", "escape"))
            paths.append(Path(pre, TERM_RAISE, line))

    # A generator that is never resumed abandons everything held at the yield.
    if not ctx.suppress_abandon:
        for sub in ast.walk(stmt):
            if isinstance(sub, (ast.Yield, ast.YieldFrom)):
                paths.append(Path(tuple(events), TERM_ABANDON, line))
                break
    return paths


# --------------------------------------------------------------------------- #
# Compound statements
# --------------------------------------------------------------------------- #


def _cap(paths: List[Path], ctx: ScopeContext) -> List[Path]:
    if len(paths) > MAX_PATHS:
        ctx.truncated = True
        return paths[:MAX_PATHS]
    return paths


def compose(stmts: Sequence[ast.stmt], ctx: ScopeContext) -> List[Path]:
    """Sequentially compose a statement list into a path set."""
    live: List[Path] = [Path((), TERM_FALL)]
    done: List[Path] = []
    for stmt in stmts:
        nxt: List[Path] = []
        for prefix in live:
            for suffix in statement_paths(stmt, ctx):
                merged = prefix.with_suffix(suffix.events, suffix.term, suffix.line)
                if suffix.term == TERM_FALL:
                    nxt.append(merged)
                else:
                    done.append(merged)
        live = _cap(nxt, ctx)
        done = _cap(done, ctx)
        if not live:
            break
    return _cap(live + done, ctx)


def _join(*paths: Path) -> Tuple[Event, ...]:
    events: Tuple[Event, ...] = ()
    for p in paths:
        events = events + p.events
    return events


def _catches_everything(handlers: Sequence[ast.ExceptHandler]) -> bool:
    for handler in handlers:
        if handler.type is None:
            return True
        if dotted_name(handler.type) in ("Exception", "BaseException"):
            return True
        if isinstance(handler.type, ast.Tuple):
            for elt in handler.type.elts:
                if dotted_name(elt) in ("Exception", "BaseException"):
                    return True
    return False


def _try_paths(node, ctx: ScopeContext) -> List[Path]:
    body = compose(node.body, ctx)
    orelse = compose(node.orelse, ctx) if node.orelse else [Path((), TERM_FALL)]
    finally_paths = compose(node.finalbody, ctx) if node.finalbody else [Path((), TERM_FALL)]
    handler_paths = [compose(h.body, ctx) for h in node.handlers]
    catch_all = _catches_everything(node.handlers)

    out: List[Path] = []
    for bp in body:
        if bp.term == TERM_FALL:
            for op in orelse:
                for fp in finally_paths:
                    term = fp.term if fp.term != TERM_FALL else op.term
                    out.append(Path(_join(bp, op, fp), term, bp.line))
        elif bp.term == TERM_RAISE and node.handlers:
            for hpaths in handler_paths:
                for hp in hpaths:
                    for fp in finally_paths:
                        term = fp.term if fp.term != TERM_FALL else hp.term
                        out.append(Path(_join(bp, hp, fp), term, bp.line))
            if not catch_all:
                for fp in finally_paths:
                    term = fp.term if fp.term != TERM_FALL else TERM_RAISE
                    out.append(Path(_join(bp, fp), term, bp.line))
        else:
            for fp in finally_paths:
                term = fp.term if fp.term != TERM_FALL else bp.term
                out.append(Path(_join(bp, fp), term, bp.line))
    return _cap(out, ctx)


def _with_paths(node, ctx: ScopeContext) -> List[Path]:
    """`with` / `async with` behave as an implicit try/finally."""
    line = getattr(node, "lineno", 0)
    prelude: List[Event] = []
    managed: List[Event] = []      # close events replayed on every exit
    for item in node.items:
        ctx_expr = unwrap(item.context_expr)
        var = target_name(item.optional_vars) if item.optional_vars else None

        if isinstance(ctx_expr, ast.Call):
            if resolve_call_name(ctx_expr, ctx.resolver) in EXIT_STACK_FACTORIES:
                if var:
                    ctx.stack_vars.add(var)
                    managed.append(Event("stack_close", None, line, owner=var))
                continue

        openings = _open_binding(item.context_expr, ctx)
        if openings:
            wrapped = isinstance(ctx_expr, ast.Call) and resolve_call_name(
                ctx_expr, ctx.resolver
            ) in CONTEXT_WRAPPERS
            for call, spec, owner in openings:
                handle = var or "<temp@%d>" % line
                ctx.specs.setdefault(handle, spec)
                prelude.append(
                    Event(
                        "open",
                        handle,
                        getattr(call, "lineno", line),
                        detail=spec.call,
                        owner=owner,
                    )
                )
                # `with sqlite3.connect(p) as c:` is a TRANSACTION manager and
                # leaves the connection open — unless wrapped in closing().
                if spec.ctx_closes or wrapped:
                    managed.append(Event("close", handle, line, detail="with"))
                if handle.startswith("self."):
                    prelude.append(Event("escape", handle, line, detail="self_attr"))
        else:
            prelude.extend(expression_events(item.context_expr, ctx, line))

    body = compose(node.body, ctx)
    out: List[Path] = []
    for bp in body:
        out.append(Path(tuple(prelude) + bp.events + tuple(managed), bp.term, bp.line or line))
    return _cap(out, ctx)


def _loop_paths(node, ctx: ScopeContext) -> List[Path]:
    line = getattr(node, "lineno", 0)
    header: List[Event] = []
    if isinstance(node, (ast.For, ast.AsyncFor)):
        header.extend(expression_events(node.iter, ctx, line))
    else:
        header.extend(expression_events(node.test, ctx, line))

    body = compose(node.body, ctx)
    orelse = compose(node.orelse, ctx) if node.orelse else [Path((), TERM_FALL)]
    body_opens = any(e.kind == "open" for p in body for e in p.events)

    def after_loop(prefix: Tuple[Event, ...], skip_else: bool, term_line: int) -> List[Path]:
        if skip_else:
            return [Path(prefix, TERM_FALL, term_line)]
        return [Path(prefix + op.events, op.term, term_line) for op in orelse]

    out: List[Path] = []
    out.extend(after_loop(tuple(header), False, line))       # zero iterations

    rounds: List[Tuple[Event, ...]] = [tuple(header)]
    unroll = MAX_LOOP_UNROLL if body_opens else 1
    for _ in range(unroll):
        next_rounds: List[Tuple[Event, ...]] = []
        for prefix in rounds:
            for bp in body:
                events = prefix + bp.events
                if bp.term in (TERM_FALL, TERM_CONTINUE):
                    next_rounds.append(events)
                    out.extend(after_loop(events, False, bp.line or line))
                elif bp.term == TERM_BREAK:
                    out.extend(after_loop(events, True, bp.line or line))
                else:
                    out.append(Path(events, bp.term, bp.line or line))
        rounds = next_rounds
        out = _cap(out, ctx)
        if not rounds:
            break
    return _cap(out, ctx)


def _if_paths(node: ast.If, ctx: ScopeContext) -> List[Path]:
    line = getattr(node, "lineno", 0)
    test = tuple(expression_events(node.test, ctx, line))
    branches = compose(node.body, ctx)
    other = compose(node.orelse, ctx) if node.orelse else [Path((), TERM_FALL)]
    return _cap([Path(test + p.events, p.term, p.line or line) for p in branches + other], ctx)


def _match_paths(node, ctx: ScopeContext) -> List[Path]:
    line = getattr(node, "lineno", 0)
    subject = tuple(expression_events(node.subject, ctx, line))
    out: List[Path] = []
    exhaustive = False
    for case in node.cases:
        pattern = case.pattern
        if isinstance(pattern, ast.MatchAs) and pattern.pattern is None:
            exhaustive = True
        for p in compose(case.body, ctx):
            out.append(Path(subject + p.events, p.term, p.line or line))
    if not exhaustive:
        out.append(Path(subject, TERM_FALL, line))
    return _cap(out, ctx)


def statement_paths(stmt: ast.stmt, ctx: ScopeContext) -> List[Path]:
    if isinstance(stmt, ast.If):
        return _if_paths(stmt, ctx)
    if isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
        return _loop_paths(stmt, ctx)
    if isinstance(stmt, (ast.With, ast.AsyncWith)):
        return _with_paths(stmt, ctx)
    if isinstance(stmt, ast.Try) or type(stmt).__name__ == "TryStar":
        return _try_paths(stmt, ctx)
    if type(stmt).__name__ == "Match":
        return _match_paths(stmt, ctx)
    return simple_statement_paths(stmt, ctx)


# --------------------------------------------------------------------------- #
# Scope-level entry point
# --------------------------------------------------------------------------- #


def collect_handle_names(node: ast.AST, ctx: ScopeContext) -> None:
    """Pre-pass: every name that can ever hold a resource in this scope.

    Bounding the handle set up front keeps `expression_events` from emitting an
    escape event for every identifier in the function.
    """
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            acquired = match_acquire(sub, ctx)
            if acquired:
                ctx.handles.add(acquired[0])
                ctx.specs.setdefault(acquired[0], acquired[1])
        if isinstance(sub, (ast.Assign, ast.AnnAssign)):
            targets = list(sub.targets) if isinstance(sub, ast.Assign) else [sub.target]
            if sub.value is None:
                continue
            value = unwrap(sub.value)
            names = [n for n in (target_name(t) for t in targets) if n]
            if isinstance(value, ast.Call):
                if resolve_call_name(value, ctx.resolver) in EXIT_STACK_FACTORIES:
                    ctx.stack_vars.update(names)
                    continue
                spec = ctx.registry.lookup(resolve_call_name(value, ctx.resolver) or "")
                if spec is not None and spec.acquired_by:
                    ctx.lock_objects.update(names or _tuple_names(targets))
                    continue
            if _open_binding(sub.value, ctx):
                if names:
                    ctx.handles.update(names)
                else:
                    members = _tuple_names(targets)
                    if members:
                        canonical = members[0]
                        ctx.handles.add(canonical)
                        for member in members[1:]:
                            ctx.aliases[member] = canonical
        elif isinstance(sub, (ast.With, ast.AsyncWith)):
            for item in sub.items:
                var = target_name(item.optional_vars) if item.optional_vars else None
                if not var:
                    continue
                expr = unwrap(item.context_expr)
                if isinstance(expr, ast.Call):
                    if resolve_call_name(expr, ctx.resolver) in EXIT_STACK_FACTORIES:
                        ctx.stack_vars.add(var)
                        continue
                if _open_binding(item.context_expr, ctx):
                    ctx.handles.add(var)


def guaranteed_resume(node: ast.AST) -> bool:
    for dec in getattr(node, "decorator_list", []) or []:
        target = dec.func if isinstance(dec, ast.Call) else dec
        name = dotted_name(target) or ""
        if name.rsplit(".", 1)[-1] in GUARANTEED_RESUME_DECORATORS:
            return True
    return False


def build_scope_context(
    node: ast.AST,
    resolver: ImportResolver,
    registry: Registry = DEFAULT_REGISTRY,
    lock_objects: Optional[Set[str]] = None,
    seed_handles: Optional[Set[str]] = None,
) -> ScopeContext:
    ctx = ScopeContext(registry=registry, resolver=resolver)
    ctx.suppress_abandon = guaranteed_resume(node)
    # Function summaries seed the parameter names so that `f.close()` inside the
    # callee registers as a close on a handle the callee never opened.
    ctx.handles.update(seed_handles or ())
    # Lock objects are discovered module-wide: `self._lock = threading.Lock()`
    # lives in __init__ while `self._lock.acquire()` lives in another method.
    ctx.lock_objects.update(lock_objects or ())
    # Two passes: the first discovers ExitStack variables that the second needs
    # in order to recognise `stack.enter_context(open(p))` as an open-site.
    collect_handle_names(node, ctx)
    collect_handle_names(node, ctx)
    return ctx


def collect_lock_objects(tree: ast.AST, resolver: ImportResolver,
                         registry: Registry = DEFAULT_REGISTRY) -> Set[str]:
    """Module-wide set of names bound to a release-style resource."""
    found: Set[str] = set()
    for sub in ast.walk(tree):
        if not isinstance(sub, (ast.Assign, ast.AnnAssign)):
            continue
        value = unwrap(sub.value) if sub.value is not None else None
        if not isinstance(value, ast.Call):
            continue
        raw = dotted_name(value.func)
        spec = registry.lookup(resolver.resolve(raw)) if raw else None
        if spec is not None and spec.acquired_by:
            targets = list(sub.targets) if isinstance(sub, ast.Assign) else [sub.target]
            found.update(_tuple_names(targets))
    return found


def enumerate_scope_paths(
    node: ast.AST,
    resolver: ImportResolver,
    registry: Registry = DEFAULT_REGISTRY,
    lock_objects: Optional[Set[str]] = None,
    seed_handles: Optional[Set[str]] = None,
) -> Tuple[List[Path], ScopeContext]:
    """Enumerate every exit path of a function / module body."""
    ctx = build_scope_context(node, resolver, registry, lock_objects, seed_handles)
    return compose(getattr(node, "body", []), ctx), ctx


# --------------------------------------------------------------------------- #
# Per-handle verdicts
# --------------------------------------------------------------------------- #


@dataclass
class HandleOutcome:
    """How one open-site fares across the enumerated path set."""

    total: int = 0
    leaking: int = 0
    #: Leaks on paths that end normally (return / fall-through / handled
    #: exception). These are build-breaking.
    leaking_normal: int = 0
    #: Leaks that only happen when an exception propagates out of the function.
    #: Real, but reporting them as hard failures would flag `f = open(p);
    #: data = f.read(); f.close()` — the most common correct-looking code there
    #: is. Reported as a warning tier instead.
    leaking_exception: int = 0
    closed: int = 0
    escaping: int = 0
    escape_kinds: Set[str] = field(default_factory=set)
    orphaned_by_reassign: int = 0
    raising_call_between: bool = False
    closed_anywhere: bool = False
    close_lines: Set[int] = field(default_factory=set)

    @property
    def leaking_fraction(self) -> float:
        return (self.leaking / self.total) if self.total else 0.0


def analyse_handle(paths: Sequence[Path], handle: str, open_line: int) -> HandleOutcome:
    """Decide, per path, whether this specific open-site is released."""
    outcome = HandleOutcome()
    for path in paths:
        opened = False
        stack_owner: Optional[str] = None
        closed = False
        escaped = False
        orphaned = False
        raising_after_open = False
        for event in path.events:
            if not opened:
                if event.kind == "open" and event.handle == handle and event.line == open_line:
                    opened = True
                    stack_owner = event.owner
                continue
            if event.kind == "raising_call" and not closed:
                raising_after_open = True
            if event.kind == "close" and event.handle == handle:
                closed = True
                outcome.closed_anywhere = True
                outcome.close_lines.add(event.line)
            elif event.kind == "stack_close" and stack_owner and event.owner == stack_owner:
                closed = True
                outcome.closed_anywhere = True
                outcome.close_lines.add(event.line)
            elif event.kind == "escape" and event.handle == handle:
                kind = event.detail.split(":", 1)[0]
                outcome.escape_kinds.add(kind)
                if kind in OWNERSHIP_TRANSFER_ESCAPES:
                    escaped = True
            elif event.kind == "reassign" and event.handle == handle and not closed:
                orphaned = True
            elif event.kind == "open" and event.handle == handle and event.line != open_line:
                if not closed:      # the variable was rebound by a later open
                    orphaned = True
        if not opened:
            continue
        outcome.total += 1
        if raising_after_open:
            outcome.raising_call_between = True
        if orphaned and not escaped:
            outcome.orphaned_by_reassign += 1
            _count_leak(outcome, path)
        elif closed:
            outcome.closed += 1
        elif escaped:
            outcome.escaping += 1
        elif path.term == TERM_EXIT:
            outcome.closed += 1     # the OS reclaims it; not a reportable leak
        else:
            _count_leak(outcome, path)
    return outcome


def _count_leak(outcome: HandleOutcome, path: Path) -> None:
    outcome.leaking += 1
    if path.term == TERM_RAISE:
        outcome.leaking_exception += 1
    else:
        outcome.leaking_normal += 1
