"""Desugar Python 3.10+ match statements into if/elif chains.

Scalpel's CFGBuilder has no visit_Match — match bodies are swallowed
(single block, no branch structure). Desugaring to if/elif lets the
existing CFG handle it. Only simple patterns are desugared:

    case 1:            -> subject == 1
    case "a":          -> subject == "a"
    case None/True:    -> subject is None/True
    case 1 | 2:        -> subject == 1 or subject == 2
    case x:            -> wildcard/capture -> else branch (binding dropped)
    case [1, 2]: etc.  -> UNSUPPORTED (match left intact, conservatively)

Unsupported matches are left as-is; the analyzer treats them as one path
(documented limitation).
"""

from __future__ import annotations

import ast

# Marker for wildcard (case x: / case _:)
_WILDCARD = object()


def _pattern_to_test(subject: ast.expr, pattern: ast.pattern):
    """Convert pattern to a condition expr. Returns (test, wildcard_flag).
    test=None + wildcard=True means wildcard/else. test=None + False = unsupported.
    """
    if isinstance(pattern, ast.MatchValue):
        return ast.Compare(left=subject, ops=[ast.Eq()], comparators=[pattern.value]), False
    if isinstance(pattern, ast.MatchSingleton):
        return ast.Compare(left=subject, ops=[ast.Is()], comparators=[pattern.value]), False
    if isinstance(pattern, ast.MatchAs):
        if pattern.pattern is None:
            return None, True  # case _ or case x (capture, binding dropped)
        test, _ = _pattern_to_test(subject, pattern.pattern)
        return test, False
    if isinstance(pattern, ast.MatchOr):
        tests = []
        for p in pattern.patterns:
            t, wild = _pattern_to_test(subject, p)
            if t is None or wild:
                return None, False
            tests.append(t)
        return ast.BoolOp(op=ast.Or(), values=tests), False
    return None, False  # MatchSequence, MatchMapping, MatchClass, MatchStar: unsupported


class MatchDesugarer(ast.NodeTransformer):
    def visit_Match(self, node: ast.Match):
        # First desugar any nested matches inside case bodies
        self.generic_visit(node)

        subject = node.subject
        cases = list(node.cases)

        # Trailing wildcard case becomes the else-branch
        else_body: list[ast.stmt] | None = None
        if cases:
            _, wild = _pattern_to_test(subject, cases[-1].pattern)
            if wild:
                else_body = cases[-1].body
                cases = cases[:-1]

        # Build elif chain from last to first
        tail: list[ast.stmt] = else_body if else_body is not None else [ast.Pass()]

        for case in reversed(cases):
            # Respect guards: `case p if cond` -> require cond too
            test, wild = _pattern_to_test(subject, case.pattern)
            if test is None:
                # Unsupported pattern in non-trailing position: bail entirely
                return node
            if case.guard is not None:
                test = ast.BoolOp(op=ast.And(), values=[test, case.guard])
            new_if = ast.If(test=test, body=case.body, orelse=tail)
            ast.copy_location(new_if, node)
            tail = [new_if]

        if len(tail) == 1 and isinstance(tail[0], ast.If):
            return tail[0]
        # No usable cases; replace with pass to keep body valid
        if not cases and else_body is None:
            return ast.Pass()
        return tail


def desugar_module(tree: ast.Module) -> ast.Module:
    """Apply match desugaring and fix locations."""
    tree = MatchDesugarer().visit(tree)
    ast.fix_missing_locations(tree)
    return tree
