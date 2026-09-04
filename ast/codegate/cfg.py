"""Stdlib-only control-flow-graph builder for CodeGate.

Why this module exists
----------------------
The upstream ``ast/cfg`` branch built its CFG with Scalpel (see
``codegate.scalpel_patch``).  ``python-scalpel`` pins ``typed-ast``, which
publishes no wheels for Python >= 3.9 and needs a C toolchain to compile, so
the analyzer could not run at all on Python 3.13.  This module rebuilds the
exact slice of the Scalpel CFG surface that ``codegate.analyzer`` consumes::

    CFG.entryblock / .finalblocks / .functioncfgs / .class_cfgs / .get_all_blocks()
    Block.id / .statements / .exits / .predecessors / .func_calls / .at() / .is_empty()
    Link.source / .target / .exitcase

and adds the edge taxonomy LEAKGUARD_SPEC section 5[4] asks for: NORMAL, TRUE,
FALSE, EXCEPT, FINALLY, LOOP_BACK, BREAK, CONTINUE, RETURN, RAISE, AWAIT.

Modelling notes (deliberate, documented imprecision)
---------------------------------------------------
* Statements inside a ``try`` body live in singleton blocks so each one carries
  its own EXCEPT edge to the handlers.  The edge leaves *after* the statement is
  recorded, i.e. it models "this statement ran, then something raised".  That is
  what makes ``try/finally`` (close always runs) distinguishable from
  ``try/except`` (close skipped on the raising path).
* An exception with no enclosing handler gets no edge to function exit by
  default.  Adding one would mark every ``f = open(p); use(f); f.close()`` as a
  leak, since ``use(f)`` can raise -- exactly the false-positive flood the spec
  warns about.  Pass ``raise_to_exit=True`` to enable it for feature extraction,
  where ``raising_call_between`` wants that path to exist.
* ``return`` inside a ``try`` routes through the innermost enclosing ``finally``
  block.  Nested finallys chain to the innermost one only.
* Loop bodies are entered once; the back edge is marked LOOP_BACK and the
  visited-set in the analyzer stops traversal there.
"""

from __future__ import annotations

import ast
import itertools
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

# --------------------------------------------------------------------------- #
# Edge taxonomy
# --------------------------------------------------------------------------- #

NORMAL = "NORMAL"
TRUE = "TRUE"
FALSE = "FALSE"
EXCEPT = "EXCEPT"
FINALLY = "FINALLY"
LOOP_BACK = "LOOP_BACK"
BREAK = "BREAK"
CONTINUE = "CONTINUE"
RETURN = "RETURN"
RAISE = "RAISE"
AWAIT = "AWAIT"

EDGE_KINDS = (
    NORMAL, TRUE, FALSE, EXCEPT, FINALLY,
    LOOP_BACK, BREAK, CONTINUE, RETURN, RAISE, AWAIT,
)


# --------------------------------------------------------------------------- #
# Graph model (Scalpel-compatible surface)
# --------------------------------------------------------------------------- #


class Link:
    """A directed CFG edge.  ``exitcase`` is the branch condition, if any."""

    __slots__ = ("source", "target", "exitcase", "kind")

    def __init__(self, source: "Block", target: "Block",
                 exitcase: Optional[ast.AST] = None, kind: str = NORMAL) -> None:
        self.source = source
        self.target = target
        self.exitcase = exitcase
        self.kind = kind

    def get_exitcase(self) -> Optional[ast.AST]:
        return self.exitcase

    def __repr__(self) -> str:
        return f"<Link {self.source.id}->{self.target.id} {self.kind}>"


class Block:
    """A basic block: a straight-line run of statements."""

    def __init__(self, id_: int) -> None:
        self.id = id_
        self.statements: List[ast.AST] = []
        self.func_calls: List[str] = []
        self.predecessors: List[Link] = []
        self.exits: List[Link] = []

    def is_empty(self) -> bool:
        return not self.statements

    def at(self) -> Optional[int]:
        """First source line covered by this block, or None if empty."""
        if self.statements:
            return getattr(self.statements[0], "lineno", None)
        return None

    def end(self) -> Optional[int]:
        if self.statements:
            return getattr(self.statements[-1], "lineno", None)
        return None

    def successors(self) -> List["Block"]:
        return [link.target for link in self.exits]

    def __repr__(self) -> str:
        return f"<Block {self.id} L{self.at()}-{self.end()} stmts={len(self.statements)}>"


class CFG:
    """Control-flow graph for one scope (module, function or class body)."""

    def __init__(self, name: str, asynchr: bool = False) -> None:
        self.name = name
        self.asynchr = asynchr
        self.entryblock: Optional[Block] = None
        self.finalblocks: List[Block] = []
        # (enclosing_block_id, qualified_name) -> CFG
        self.functioncfgs: dict = {}
        self.class_cfgs: dict = {}

    def get_all_blocks(self) -> List[Block]:
        """Blocks reachable from the entry block, in BFS order."""
        if self.entryblock is None:
            return []
        seen: set = set()
        out: List[Block] = []
        queue: List[Block] = [self.entryblock]
        while queue:
            block = queue.pop(0)
            if block.id in seen:
                continue
            seen.add(block.id)
            out.append(block)
            for link in block.exits:
                if link.target.id not in seen:
                    queue.append(link.target)
        return out

    def __iter__(self) -> Iterator[Block]:
        yield from self.get_all_blocks()

    def __repr__(self) -> str:
        return f"<CFG {self.name!r} blocks={len(self.get_all_blocks())}>"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

# Node types whose evaluation can raise.  Deliberately broad: a false "can
# raise" only adds a path, while a false "cannot raise" hides a real leak.
_RAISING_NODES = (
    ast.Call, ast.Subscript, ast.Attribute, ast.Raise,
    ast.Assert, ast.BinOp, ast.Await, ast.YieldFrom,
)

_NEVER_RAISES = (
    ast.Pass, ast.Break, ast.Continue, ast.Global,
    ast.Nonlocal, ast.Import, ast.ImportFrom,
)


def can_raise(stmt: ast.AST) -> bool:
    """True if executing ``stmt`` could transfer control to an exception handler."""
    if isinstance(stmt, _NEVER_RAISES):
        return False
    for node in ast.walk(stmt):
        if isinstance(node, _RAISING_NODES):
            return True
    return False


def _negate(test: ast.AST) -> ast.AST:
    """``not test`` as an AST, used as the FALSE-edge exitcase."""
    return ast.UnaryOp(op=ast.Not(), operand=test)


def _call_name(node: ast.Call) -> Optional[str]:
    """Dotted name for the func of a Call, e.g. ``socket.socket``."""
    parts: List[str] = []
    cur = node.func
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


def _catches_everything(handlers) -> bool:
    """True if some handler is a bare ``except:`` or catches (Base)Exception."""
    for handler in handlers:
        if handler.type is None:
            return True
        if isinstance(handler.type, ast.Name) and handler.type.id in ("Exception", "BaseException"):
            return True
    return False


@dataclass
class _ExcCtx:
    """The exception context of an enclosing ``try``."""

    handlers: List[Block] = field(default_factory=list)
    finally_block: Optional[Block] = None
    catches_all: bool = False


# --------------------------------------------------------------------------- #
# Builder
# --------------------------------------------------------------------------- #


class CFGBuilder:
    """Builds a CFG from Python source or an AST.

    Mirrors the Scalpel entry points (``build_from_src``, ``build``) so that
    ``codegate.analyzer`` needs no changes.
    """

    def __init__(self, raise_to_exit: bool = False,
                 _ids: Optional[Iterator[int]] = None,
                 _root: Optional[CFG] = None,
                 _qual: str = "") -> None:
        self.raise_to_exit = raise_to_exit
        self._ids = _ids if _ids is not None else itertools.count(1)
        self._root = _root
        self._qual = _qual

        self.cfg: Optional[CFG] = None
        self.current: Optional[Block] = None
        self.loop_stack: List[tuple] = []   # (continue_target, break_target)
        self.exc_stack: List[_ExcCtx] = []

    # -- public API -------------------------------------------------------- #

    def build_from_src(self, name: str, src: str) -> CFG:
        return self.build(name, ast.parse(src))

    def build_from_file(self, name: str, path) -> CFG:
        with open(path, "r", encoding="utf-8") as fh:
            return self.build_from_src(name, fh.read())

    def build(self, name: str, tree: ast.AST, asynchr: bool = False) -> CFG:
        cfg = CFG(name, asynchr=asynchr)
        self.cfg = cfg
        if self._root is None:
            self._root = cfg
        entry = self._new_block()
        cfg.entryblock = entry
        self.current = entry
        self._body(getattr(tree, "body", []))
        if self.current is not None and not self.current.exits:
            cfg.finalblocks.append(self.current)
        return cfg

    # -- graph plumbing ---------------------------------------------------- #

    def _new_block(self) -> Block:
        return Block(next(self._ids))

    def _link(self, source: Optional[Block], target: Block,
              exitcase: Optional[ast.AST] = None, kind: str = NORMAL) -> None:
        if source is None:
            return
        link = Link(source, target, exitcase, kind)
        source.exits.append(link)
        target.predecessors.append(link)

    def _ensure_current(self) -> Block:
        """Current block, creating a detached one if control flow is dead."""
        if self.current is None:
            self.current = self._new_block()
        return self.current

    # -- statement recording ----------------------------------------------- #

    def _record(self, stmt: ast.AST, walk_calls: bool = True) -> Block:
        """Append ``stmt`` to the current block and collect its call names."""
        block = self._ensure_current()
        block.statements.append(stmt)
        if walk_calls:
            self._collect_calls(block, stmt)
        return block

    @staticmethod
    def _collect_calls(block: Block, node: ast.AST) -> None:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                name = _call_name(sub)
                if name:
                    block.func_calls.append(name)

    def _add_simple(self, stmt: ast.AST) -> None:
        """Record a simple statement, wiring exception edges if inside a try."""
        block = self._record(stmt)
        ctx = self.exc_stack[-1] if self.exc_stack else None
        if ctx is None or not can_raise(stmt):
            return
        wired = False
        for handler in ctx.handlers:
            self._link(block, handler, None, EXCEPT)
            wired = True
        if ctx.finally_block is not None and not ctx.catches_all:
            self._link(block, ctx.finally_block, None, FINALLY)
            wired = True
        if not wired and self.raise_to_exit:
            exit_block = self._new_block()
            self._link(block, exit_block, None, RAISE)
            self.cfg.finalblocks.append(exit_block)
        # Split so the next statement gets its own exception edges.
        nxt = self._new_block()
        self._link(block, nxt, None, NORMAL)
        self.current = nxt

    # -- abrupt-exit targets ----------------------------------------------- #

    def _innermost_finally(self) -> Optional[Block]:
        for ctx in reversed(self.exc_stack):
            if ctx.finally_block is not None:
                return ctx.finally_block
        return None

    # -- traversal ---------------------------------------------------------- #

    def _body(self, stmts) -> None:
        for stmt in stmts:
            self._visit(stmt)

    def _visit(self, stmt: ast.AST) -> None:
        handler = getattr(self, "_visit_" + type(stmt).__name__, None)
        if handler is None:
            self._add_simple(stmt)
        else:
            handler(stmt)

    # -- branches ----------------------------------------------------------- #

    def _visit_If(self, node: ast.If) -> None:
        head = self._record(node, walk_calls=False)
        self._collect_calls(head, node.test)

        after = self._new_block()

        body_entry = self._new_block()
        self._link(head, body_entry, node.test, TRUE)
        self.current = body_entry
        self._body(node.body)
        self._link(self.current, after, None, NORMAL)

        if node.orelse:
            else_entry = self._new_block()
            self._link(head, else_entry, _negate(node.test), FALSE)
            self.current = else_entry
            self._body(node.orelse)
            self._link(self.current, after, None, NORMAL)
        else:
            self._link(head, after, _negate(node.test), FALSE)

        self.current = after

    def _visit_Match(self, node) -> None:
        head = self._record(node, walk_calls=False)
        after = self._new_block()
        exhaustive = False
        for case in node.cases:
            entry = self._new_block()
            self._link(head, entry, getattr(case, "guard", None), TRUE)
            self.current = entry
            self._body(case.body)
            self._link(self.current, after, None, NORMAL)
            pattern = getattr(case, "pattern", None)
            if type(pattern).__name__ == "MatchAs" and getattr(pattern, "pattern", None) is None:
                exhaustive = True
        if not exhaustive:
            self._link(head, after, None, FALSE)
        self.current = after

    # -- loops -------------------------------------------------------------- #

    def _loop(self, node, test: Optional[ast.AST], is_async: bool = False) -> None:
        pre = self._ensure_current()
        header = self._new_block()
        self._link(pre, header, None, AWAIT if is_async else NORMAL)
        self.current = header
        self._record(node, walk_calls=False)  # header carries the loop line

        after = self._new_block()
        body_entry = self._new_block()
        self._link(header, body_entry, test, TRUE)

        self.loop_stack.append((header, after))
        self.current = body_entry
        self._body(node.body)
        self._link(self.current, header, None, LOOP_BACK)
        self.loop_stack.pop()

        if node.orelse:
            else_entry = self._new_block()
            self._link(header, else_entry, _negate(test) if test else None, FALSE)
            self.current = else_entry
            self._body(node.orelse)
            self._link(self.current, after, None, NORMAL)
        else:
            self._link(header, after, _negate(test) if test else None, FALSE)

        self.current = after

    def _visit_For(self, node: ast.For) -> None:
        self._loop(node, node.iter)

    def _visit_AsyncFor(self, node) -> None:
        self._loop(node, node.iter, is_async=True)

    def _visit_While(self, node: ast.While) -> None:
        self._loop(node, node.test)

    # -- with --------------------------------------------------------------- #

    def _visit_With(self, node: ast.With, is_async: bool = False) -> None:
        # The With node itself must stay visible to the analyzer: that is how it
        # recognises a context-managed acquire as safe.
        head = self._record(node, walk_calls=False)
        for item in node.items:
            self._collect_calls(head, item.context_expr)

        body_entry = self._new_block()
        self._link(head, body_entry, None, AWAIT if is_async else NORMAL)
        self.current = body_entry
        self._body(node.body)

        after = self._new_block()
        # __exit__ runs on every path out of the body, like a finally.
        self._link(self.current, after, None, FINALLY)
        self.current = after

    def _visit_AsyncWith(self, node) -> None:
        self._visit_With(node, is_async=True)

    # -- try ---------------------------------------------------------------- #

    def _visit_Try(self, node) -> None:
        head = self._record(node, walk_calls=False)

        after = self._new_block()
        finally_entry = self._new_block() if node.finalbody else None
        handler_entries = [self._new_block() for _ in node.handlers]
        normal_target = finally_entry if finally_entry is not None else after

        ctx = _ExcCtx(
            handlers=handler_entries,
            finally_block=finally_entry,
            catches_all=_catches_everything(node.handlers),
        )

        body_entry = self._new_block()
        self._link(head, body_entry, None, NORMAL)
        self.current = body_entry
        self.exc_stack.append(ctx)
        self._body(node.body)
        if node.orelse:
            else_entry = self._new_block()
            self._link(self.current, else_entry, None, NORMAL)
            self.current = else_entry
            self._body(node.orelse)
        self.exc_stack.pop()
        self._link(self.current, normal_target, None, NORMAL)

        # Handler bodies run outside their own try but inside its finally.
        for handler, entry in zip(node.handlers, handler_entries):
            self.current = entry
            self.exc_stack.append(_ExcCtx(handlers=[], finally_block=finally_entry))
            self._body(handler.body)
            self.exc_stack.pop()
            self._link(self.current, normal_target, None, NORMAL)

        if finally_entry is not None:
            self.current = finally_entry
            self._body(node.finalbody)
            self._link(self.current, after, None, FINALLY)

        self.current = after

    # ``try/except*`` shares the Try shape.
    _visit_TryStar = _visit_Try

    # -- abrupt exits -------------------------------------------------------- #

    def _visit_Return(self, node: ast.Return) -> None:
        block = self._record(node)
        target = self._innermost_finally()
        if target is not None:
            self._link(block, target, None, RETURN)
        else:
            self.cfg.finalblocks.append(block)
        self.current = None

    def _visit_Raise(self, node: ast.Raise) -> None:
        block = self._record(node)
        ctx = self.exc_stack[-1] if self.exc_stack else None
        wired = False
        if ctx is not None:
            for handler in ctx.handlers:
                self._link(block, handler, None, EXCEPT)
                wired = True
            if ctx.finally_block is not None and not ctx.catches_all:
                self._link(block, ctx.finally_block, None, RAISE)
                wired = True
        if not wired:
            self.cfg.finalblocks.append(block)
        self.current = None

    def _visit_Break(self, node: ast.Break) -> None:
        block = self._record(node)
        if self.loop_stack:
            self._link(block, self.loop_stack[-1][1], None, BREAK)
        else:
            self.cfg.finalblocks.append(block)
        self.current = None

    def _visit_Continue(self, node: ast.Continue) -> None:
        block = self._record(node)
        if self.loop_stack:
            self._link(block, self.loop_stack[-1][0], None, CONTINUE)
        else:
            self.cfg.finalblocks.append(block)
        self.current = None

    # -- nested scopes ------------------------------------------------------- #

    def _subscope(self, name: str, body, asynchr: bool) -> CFG:
        sub_builder = CFGBuilder(
            raise_to_exit=self.raise_to_exit,
            _ids=self._ids,
            _root=self._root,
            _qual=name + ".",
        )
        wrapper = ast.Module(body=list(body), type_ignores=[])
        return sub_builder.build(name, wrapper, asynchr=asynchr)

    def _visit_function(self, node, asynchr: bool) -> None:
        block = self._record(node, walk_calls=False)
        qual = self._qual + node.name
        sub = self._subscope(qual, node.body, asynchr)
        # Register on the local scope and on the module root, so a single pass
        # over ``cfg.functioncfgs`` reaches methods and closures too.
        self.cfg.functioncfgs[(block.id, qual)] = sub
        if self._root is not None and self._root is not self.cfg:
            self._root.functioncfgs[(block.id, qual)] = sub

    def _visit_FunctionDef(self, node) -> None:
        self._visit_function(node, asynchr=False)

    def _visit_AsyncFunctionDef(self, node) -> None:
        self._visit_function(node, asynchr=True)

    def _visit_ClassDef(self, node) -> None:
        block = self._record(node, walk_calls=False)
        qual = self._qual + node.name
        sub = self._subscope(qual, node.body, asynchr=False)
        self.cfg.class_cfgs[(block.id, qual)] = sub
        if self._root is not None and self._root is not self.cfg:
            self._root.class_cfgs[(block.id, qual)] = sub


# --------------------------------------------------------------------------- #
# Convenience
# --------------------------------------------------------------------------- #


def build_cfg(src: str, name: str = "module", raise_to_exit: bool = False) -> CFG:
    return CFGBuilder(raise_to_exit=raise_to_exit).build_from_src(name, src)


def get_all_blocks_filtered(cfg: CFG) -> List[Block]:
    """Reachable blocks, minus empty joins (the entry block is always kept)."""
    return [b for b in cfg.get_all_blocks() if b.statements or b is cfg.entryblock]
