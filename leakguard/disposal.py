"""Module-level disposal evidence for handles whose ownership escapes.

`pathmodel.py` answers "is this handle released on every path *inside* this
function". For the sites the confidence model is actually asked about, that
question has already been answered "cannot tell": the handle was returned,
yielded, appended to a container, or stashed in a module global, and the
release -- if there is one -- happens somewhere else in the file.

Without this pass the feature vector for a factory that hands its handle to a
`with contextlib.closing(...)` is **byte-identical** to the vector for one whose
caller drops the handle on the floor. Same call, same line shape, same escape
kind. A model given those vectors cannot beat the base rate, and the measured
false-alarm rate on rules-UNKNOWN sites was 100%.

So this module walks the rest of the file and records what the recipient does:

* `disposing_functions` -- functions whose returned or yielded handle some caller
  demonstrably releases: wraps it in `with`/`closing`, adopts it as an attribute
  its class closes, closes the local it was assigned to, or drains it in a loop.
* `called_functions` -- functions invoked anywhere in the module at all. A
  factory nobody calls here is genuinely undecidable rather than suspicious, and
  the model is told which of the two it is looking at.
* `drained_globals` -- module-level containers some loop empties by closing the
  elements, for the `_REGISTRY[key] = handle` shape.

This stays *evidence*, never a verdict. It contributes three inputs to a
probability; the rules layer keeps its own answer, and a proof still outranks a
probability.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .registry import GENERIC_CLOSERS, suggests_close

#: Methods that put a handle into a container.
_CONTAINER_ADDERS = ("append", "add", "insert", "put", "extend")

#: Wrappers that adopt a handle and release it at block exit.
_ADOPTING_WRAPPERS = ("closing", "aclosing", "enter_context", "enter_async_context")


def _name_of(node: ast.AST) -> Optional[str]:
    """Dotted name for a Name or Attribute, else None."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _name_of(node.value)
        return "%s.%s" % (base, node.attr) if base else node.attr
    return None


def _callee_name(call: ast.Call) -> Optional[str]:
    """Bare callee name: `mod.helper(...)` -> `helper`."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _calls_in(node: ast.AST) -> List[ast.Call]:
    return [child for child in ast.walk(node) if isinstance(child, ast.Call)]


def _closes(node: ast.AST, target: str) -> bool:
    """Does `node` contain `target.<closer>()` or an adopting wrapper on it?"""
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Attribute) and func.attr in GENERIC_CLOSERS:
            if _name_of(func.value) == target:
                return True
        callee = _callee_name(child)
        # An adopting wrapper, or a helper whose *name* says it releases what it
        # is handed -- the same naming heuristic `callee_name_suggests_close`
        # already applies one level down, applied here to the caller.
        if callee and (callee in _ADOPTING_WRAPPERS or suggests_close(callee)):
            for arg in child.args:
                if _name_of(arg) == target:
                    return True
    return False


def _drains(node: ast.AST, target: str) -> bool:
    """Does `node` contain a loop over `target` that closes each element?"""
    for child in ast.walk(node):
        if not isinstance(child, (ast.For, ast.AsyncFor)):
            continue
        iterated = child.iter
        base: Optional[str]
        if isinstance(iterated, ast.Call):
            # `target.values()` / `target.items()`
            callee_path = _name_of(iterated.func)
            base = (callee_path.rsplit(".", 1)[0]
                    if callee_path and "." in callee_path else None)
        else:
            base = _name_of(iterated)
        if base != target:
            continue
        loop_var = _name_of(child.target)
        if loop_var and any(_closes(stmt, loop_var) for stmt in child.body):
            return True
    return False


def _adopted_expression(node: ast.AST, functions: Dict[str, ast.AST]) -> Set[str]:
    """Known functions whose call sits inside an adopting wrapper in `node`.

    `h = stack.enter_context(contextlib.closing(make()))` releases `make()`'s
    handle at block exit, but the wrapper never sees the name `h`, so a
    name-based search finds nothing. Match on the expression instead.
    """
    found: Set[str] = set()
    for call in _calls_in(node):
        callee = _callee_name(call)
        if callee and (callee in _ADOPTING_WRAPPERS or suggests_close(callee)):
            for argument in call.args:
                found.update(_direct_callees(argument, functions))
    return found


def _loop_aliases(loop: ast.AST, loop_var: str) -> Set[str]:
    """Names the loop body binds to the loop variable."""
    aliases: Set[str] = set()
    for child in ast.walk(loop):
        if isinstance(child, ast.Assign) and _name_of(child.value) == loop_var:
            for target in child.targets:
                name = _name_of(target)
                if name:
                    aliases.add(name)
    return aliases


def _released_in_scope(scope: ast.AST, target: str) -> bool:
    """Is `target` closed, adopted or drained anywhere in this function body?"""
    if _closes(scope, target) or _drains(scope, target):
        return True
    for child in ast.walk(scope):
        if isinstance(child, (ast.With, ast.AsyncWith)):
            for item in child.items:
                if _name_of(item.context_expr) == target:
                    return True
    return False


@dataclass
class Disposal:
    """What the rest of the module does with handles that leave a function."""

    disposing_functions: Set[str] = field(default_factory=set)
    called_functions: Set[str] = field(default_factory=set)
    drained_globals: Set[str] = field(default_factory=set)
    #: function name -> containers that function stores handles into
    container_targets: Dict[str, Set[str]] = field(default_factory=dict)
    #: functions that return one of those containers to their caller
    returns_container: Set[str] = field(default_factory=set)

    def escape_disposed(self, scope: str) -> bool:
        if scope in self.disposing_functions:
            return True
        for container in self.container_targets.get(scope, ()):
            if container in self.drained_globals:
                return True
        return False

    def recipient_unknown(self, scope: str) -> bool:
        """True when nothing in this module consumes the escaping value."""
        return scope not in self.called_functions

    def container_drained(self, scope: str) -> bool:
        targets = self.container_targets.get(scope, set())
        if not targets:
            return False
        if any(target in self.drained_globals for target in targets):
            return True
        return scope in self.returns_container and scope in self.disposing_functions


def _function_defs(tree: ast.AST) -> Dict[str, ast.AST]:
    out: Dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, node)
    return out


def _class_by_line(tree: ast.AST) -> Dict[int, str]:
    line_class: Dict[int, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for child in ast.walk(node):
                if hasattr(child, "lineno"):
                    line_class.setdefault(child.lineno, node.name)
    return line_class


def _direct_callees(node: ast.AST, functions: Dict[str, ast.AST]) -> Set[str]:
    """Known module functions invoked anywhere inside `node`."""
    return {name for name in (_callee_name(call) for call in _calls_in(node))
            if name in functions}


def _collect_container_targets(functions: Dict[str, ast.AST],
                               disposal: Disposal) -> None:
    for name, node in functions.items():
        targets: Set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Attribute) and func.attr in _CONTAINER_ADDERS:
                    base = _name_of(func.value)
                    if base:
                        targets.add(base)
            elif isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Subscript):
                        base = _name_of(target.value)
                        if base:
                            targets.add(base)
        if not targets:
            continue
        disposal.container_targets[name] = targets
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value is not None:
                if _name_of(child.value) in targets:
                    disposal.returns_container.add(name)


def _record_disposition(
    statement: ast.AST,
    caller: ast.AST,
    functions: Dict[str, ast.AST],
    ownership: Dict[str, Set[str]],
    line_class: Dict[int, str],
    disposal: Disposal,
) -> None:
    # with <expr containing F(...)> as x:   /   with closing(F(...)) as x:
    if isinstance(statement, (ast.With, ast.AsyncWith)):
        for item in statement.items:
            disposal.disposing_functions.update(
                _direct_callees(item.context_expr, functions))
        return

    # for v in F(...):  ...  v.close()   -- or `kept = v` then `kept.close()`
    # after the loop, which is how a consumer keeps the last handle around.
    if isinstance(statement, (ast.For, ast.AsyncFor)):
        callees = _direct_callees(statement.iter, functions)
        if callees:
            loop_var = _name_of(statement.target)
            if loop_var:
                released = any(_closes(stmt, loop_var) for stmt in statement.body)
                if not released:
                    released = any(_closes(caller, alias)
                                   for alias in _loop_aliases(statement, loop_var))
                if released:
                    disposal.disposing_functions.update(callees)
        return

    if not isinstance(statement, ast.Assign) or statement.value is None:
        return
    callees = _direct_callees(statement.value, functions)
    if not callees:
        return

    # The call is wrapped in something that owns it: `closing(make())`,
    # `stack.enter_context(make())`. The binding name is irrelevant.
    disposal.disposing_functions.update(
        _adopted_expression(statement.value, functions))

    for target in statement.targets:
        target_name = _name_of(target)
        if not target_name:
            continue
        # self.conn = _acquire(...) inside a class whose closer releases `conn`
        if (isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"):
            class_name = line_class.get(getattr(statement, "lineno", -1))
            released = ownership.get(class_name or "", set())
            if ("self.%s" % target.attr) in released or target.attr in released:
                disposal.disposing_functions.update(callees)
            continue
        # x = F(...) and x is released later in the same function body
        if _released_in_scope(caller, target_name):
            disposal.disposing_functions.update(callees)


def collect_disposal(
    tree: ast.AST,
    ownership: Optional[Dict[str, Set[str]]] = None,
) -> Disposal:
    """Walk the module once and record what happens to escaping handles.

    `ownership` is `detector.collect_class_ownership`'s output: class name ->
    attributes the class demonstrably releases. Passing it lets a factory whose
    result is adopted as `self.conn` by a class with a real `close()` count as
    disposed, which is the most common legitimate escape in production code.
    """
    ownership = ownership or {}
    disposal = Disposal()
    functions = _function_defs(tree)
    line_class = _class_by_line(tree)

    _collect_container_targets(functions, disposal)

    # Module-level containers some loop empties by closing every element.
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and _drains(tree, target.id):
                disposal.drained_globals.add(target.id)

    for statement in ast.walk(tree):
        if isinstance(statement, ast.stmt):
            disposal.called_functions.update(_direct_callees(statement, functions))

    # Disposition is judged per enclosing function, never module-wide: a drain
    # in some *other* function must not credit this caller's local. Module-level
    # statements are judged against the module body alone, for the same reason.
    for caller in functions.values():
        for statement in ast.walk(caller):
            _record_disposition(statement, caller, functions, ownership,
                                line_class, disposal)
    for statement in getattr(tree, "body", []):
        _record_disposition(statement, tree, functions, ownership,
                            line_class, disposal)
    return disposal
