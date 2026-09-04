"""HARDEN-1/2/3 regression tests: match desugar, edge dedupe, exception safety."""
import textwrap

import pytest

from codegate.analyzer import analyze_source
from codegate.config import CodeGateConfig


def _cfg(src, **kw):
    config = CodeGateConfig.default()
    for k, v in kw.items():
        setattr(config, k, v)
    return analyze_source(textwrap.dedent(src), filename="t.py", config=config)


# ---------------------------------------------------------------------------
# HARDEN-1: match statements
# ---------------------------------------------------------------------------

def test_match_path_leak():
    leaks = _cfg("""
    def f(x, p):
        match x:
            case 1:
                fh = open(p)
                return fh.read()   # never closed
            case _:
                return 2
    """)
    kinds = [lk.kind for lk in leaks]
    assert any("path" in k for k in kinds), f"expected path leak in match case, got {leaks}"


def test_match_exception_leak():
    leaks = _cfg("""
    def f(x, p):
        match x:
            case 1:
                fh = open(p)       # line 5 after desugar (leading blank = line 1)
                return fh.read()   # raise here -> fh leaks
            case _:
                fh2 = open(p)
                fh2.close()
                return 2
    """)
    assert any(lk.acquire_line == 5 for lk in leaks), \
        f"expected leak for fh (line 5), got {[(lk.kind, lk.acquire_line) for lk in leaks]}"
    # case _ is safe (closed immediately, no may-throw call in between)


def test_match_safe_case():
    leaks = _cfg("""
    def f(x, p):
        match x:
            case 1:
                fh = open(p)
                fh.close()
                return 1
            case _:
                return 2
    """)
    path_leaks = [lk for lk in leaks if "path" in lk.kind and "exception" not in lk.kind]
    assert not path_leaks


# ---------------------------------------------------------------------------
# HARDEN-2: edge dedupe — no duplicate edges break path enumeration
# ---------------------------------------------------------------------------

def test_try_except_no_duplicate_edges():
    from codegate.scalpel_patch import build_cfg
    import ast
    src = textwrap.dedent("""
    def g(p):
        try:
            f = open(p)
            data = f.read()
        except OSError:
            f = None
        data = f.read()
        f.close()
    """)
    fcfg = list(build_cfg(src).functioncfgs.values())[0]
    for b in fcfg.get_all_blocks():
        exits = [(e.target.id, ast.dump(e.exitcase) if e.exitcase else None) for e in b.exits]
        preds = [p.source.id for p in b.predecessors]
        assert len(set(exits)) == len(exits), f"dup exits in B{b.id}: {exits}"
        assert len(set(preds)) == len(preds), f"dup preds in B{b.id}: {preds}"


# ---------------------------------------------------------------------------
# HARDEN-3: exception-path leak detection
# ---------------------------------------------------------------------------

def test_exception_no_finally_flagged():
    leaks = _cfg("""
    def unsound(p):
        f = open(p)
        data = f.read()   # raise -> f leaks
        f.close()
        return data
    """)
    assert len(leaks) == 1
    assert "exception" in leaks[0].kind
    assert "read" in leaks[0].message


def test_exception_finally_clean():
    leaks = _cfg("""
    def sound(p):
        f = open(p)
        try:
            data = f.read()
            return data
        finally:
            f.close()
    """)
    assert leaks == []


def test_exception_with_clean():
    leaks = _cfg("""
    def sound(p):
        with open(p) as f:
            return f.read()
    """)
    assert leaks == []


def test_exception_caught_clean():
    leaks = _cfg("""
    def sound(p):
        f = open(p)
        try:
            data = f.read()
        except OSError:
            data = None
        f.close()
        return data
    """)
    assert leaks == []


def test_exception_outer_with_flagged():
    # with does NOT protect outer resources on exception
    leaks = _cfg("""
    def unsound(p):
        f = open(p)
        with open(p + '.tmp') as g:
            data = f.read()
        f.close()
        return data
    """)
    assert any(lk.acquire_line == 3 for lk in leaks), f"outer-with leak missed: {leaks}"


def test_exception_finally_without_close_flagged():
    leaks = _cfg("""
    def unsound(p):
        f = open(p)
        try:
            data = f.read()
        finally:
            print('done')
        f.close()
        return data
    """)
    assert any(lk.acquire_line == 3 for lk in leaks), f"finally-no-close missed: {leaks}"


def test_exception_alias_finally_clean():
    leaks = _cfg("""
    def sound(p):
        f = open(p)
        g = f
        try:
            data = g.read()
        finally:
            g.close()
    """)
    assert leaks == []


def test_exception_disabled():
    leaks = _cfg("""
    def unsound(p):
        f = open(p)
        data = f.read()
        f.close()
        return data
    """, exception_safety=False)
    assert leaks == []  # path analysis alone sees it as safe


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
