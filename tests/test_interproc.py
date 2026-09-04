"""Interprocedural regression tests — helper(f) parameter-effect propagation."""
import textwrap

import pytest

from codegate.analyzer import analyze_source
from codegate.config import CodeGateConfig


def path_leaks(src: str):
    leaks = analyze_source(textwrap.dedent(src), filename="t.py", config=CodeGateConfig.default())
    return [lk for lk in leaks if "path" in lk.kind]


def test_helper_releases_param_caller_safe():
    leaks = path_leaks("""
    def helper(f):
        f.close()

    def caller(path):
        f = open(path)
        helper(f)
        return 1
    """)
    assert len(leaks) == 0, f"helper(f) closing its param should make caller safe: {leaks}"


def test_helper_leaks_param_propagates_to_call_site():
    leaks = path_leaks("""
    def helper(g):
        if g:
            g.close()

    def caller(path):
        f = open(path)
        helper(f)
        return 1
    """)
    assert len(leaks) == 1
    assert "passed to 'helper()'" in leaks[0].message
    assert "never closes its parameter" in leaks[0].message


def test_helper_escapes_param_caller_safe():
    leaks = path_leaks("""
    def factory(h):
        return h

    def caller(path):
        f = open(path)
        factory(f)
        return 1
    """)
    assert len(leaks) == 0, f"ownership escape via helper return should not leak: {leaks}"


def test_unconditional_leak_in_helper_propagates():
    leaks = path_leaks("""
    def bad(g):
        return 1   # never closes g

    def caller(path):
        f = open(path)
        bad(f)
        return 1
    """)
    assert len(leaks) == 1
    assert "passed to 'bad()'" in leaks[0].message


def test_try_finally_helper_caller_safe():
    leaks = path_leaks("""
    def guarded(g):
        try:
            data = g.read()
            return data
        finally:
            g.close()

    def caller(path):
        f = open(path)
        guarded(f)
        return 1
    """)
    assert len(leaks) == 0


def test_positional_args_second_param():
    # helper closes its SECOND param; f2 is safe, f1 leaks
    leaks = path_leaks("""
    def mixed(a, b):
        b.close()

    def caller(p1, p2):
        f1 = open(p1)
        f2 = open(p2)
        mixed(f1, f2)
        return 1
    """)
    assert len(leaks) == 1
    assert leaks[0].var == "f1", f"expected f1 to leak (helper closes b only): {leaks}"


def test_positional_args_first_param():
    # helper closes its FIRST param; f1 is safe, f2 leaks
    leaks = path_leaks("""
    def mixed(a, b):
        a.close()

    def caller(p1, p2):
        f1 = open(p1)
        f2 = open(p2)
        mixed(f1, f2)
        return 1
    """)
    assert len(leaks) == 1
    assert leaks[0].var == "f2", f"expected f2 to leak (helper closes a only): {leaks}"


def test_fallthrough_if_in_helper_not_assumed_released():
    # Scalpel used to lose the fall-through exit after `if`, making this look
    # like "always releases". The graph fix keeps the terminal exit node.
    leaks = path_leaks("""
    def maybe_close(g):
        if g:
            g.close()

    def caller(path):
        f = open(path)
        maybe_close(f)
        return 1
    """)
    assert len(leaks) == 1, "helper that closes only conditionally must leak"


def test_unknown_callee_still_conservative():
    # calling an undefined function: handle stays live -> exit leak (unchanged)
    leaks = path_leaks("""
    def caller(path):
        f = open(path)
        mystery(f)   # not defined in this module
        return 1
    """)
    assert len(leaks) == 1


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
