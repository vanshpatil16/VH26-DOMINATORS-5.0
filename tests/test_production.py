"""Tests for the production-readiness hardening:
import tracking, expanded specs, contextlib, ensemble mode."""
import textwrap

import pytest

from codegate.analyzer import analyze_source
from codegate.config import CodeGateConfig
from codegate.imports import build_import_map, resolve_call_name


def _flagged(src, **cfg_kw):
    config = CodeGateConfig.default()
    for k, v in cfg_kw.items():
        setattr(config, k, v)
    return sorted(lk.acquire_line for lk in analyze_source(textwrap.dedent(src), filename="t.py", config=config))


# ── import tracking ──────────────────────────────────────────────────────

def test_import_map_basic():
    import ast
    tree = ast.parse("import sqlite3 as db\nfrom socket import socket as sock\nimport json\n")
    m = build_import_map(tree)
    assert m["db"] == "sqlite3"
    assert m["sock"] == "socket.socket"
    assert m["json"] == "json"


def test_resolve_call():
    assert resolve_call_name("s.socket", {"s": "socket"}) == "socket.socket"
    assert resolve_call_name("connect", {"connect": "psycopg2.connect"}) == "psycopg2.connect"
    assert resolve_call_name("open", {}) == "open"
    assert resolve_call_name("x.y", {}) == "x.y"


def test_aliased_db_connect_leak():
    lines = _flagged("""
    import sqlite3 as db
    def leak(p):
        c = db.connect(p)
        return c.execute("select 1")
    """)
    assert lines == [4]


def test_from_import_connect():
    lines = _flagged("""
    from psycopg2 import connect
    def leak(p):
        c = connect(p)
        return c.execute("select 1")
    """)
    assert lines == [4]


def test_from_import_aliased_socket():
    lines = _flagged("""
    from socket import socket as sock
    def f():
        s = sock()
        return s.recv(100)
    """)
    assert lines == [4]


# ── expanded specs ───────────────────────────────────────────────────────

def test_requests_session():
    lines = _flagged("""
    import requests
    def leak():
        s = requests.Session()
        return s.get("http://x")
    """)
    assert lines == [4]


def test_httpx_client():
    lines = _flagged("""
    import httpx
    def leak():
        c = httpx.Client()
        return c.get("http://x")
    """)
    assert lines == [4]


def test_popen_alt_release():
    # Popen closed via wait() — alt release, no leak
    lines = _flagged("""
    import subprocess
    def ok():
        p = subprocess.Popen(["ls"])
        p.wait()
        return 0
    """)
    assert lines == []


def test_popen_leak():
    lines = _flagged("""
    import subprocess
    def leak():
        p = subprocess.Popen(["ls"])
        return p.communicate()
    """)
    assert lines == [4]


# ── contextlib ───────────────────────────────────────────────────────────

def test_closing_kills_fp():
    lines = _flagged("""
    from contextlib import closing
    def ok(p):
        f = open(p)
        with closing(f):
            return f.read()
    """)
    assert lines == []


def test_exitstack_managed():
    lines = _flagged("""
    from contextlib import ExitStack
    from psycopg2 import connect
    def ok(p):
        with ExitStack() as es:
            c = es.enter_context(connect(p))
            return c.execute("select 1")
    """)
    assert lines == []


# ── regressions ──────────────────────────────────────────────────────────

def test_core_leak_regression():
    lines = _flagged("""
    def leak(path):
        f = open(path)
        data = f.read()
        if not data:
            return None
        f.close()
        return data
    """)
    assert lines == [3]


def test_with_regression():
    lines = _flagged("""
    def sound(p):
        with open(p) as f:
            return f.read()
    """)
    assert lines == []


# ── ensemble ─────────────────────────────────────────────────────────────

def test_ensemble_classification():
    from codegate.ensemble import run_ensemble
    src = textwrap.dedent("""
    import sqlite3 as db
    from contextlib import closing

    def branch_leak(cs):
        conn = db.connect(cs)
        row = conn.execute("select 1").fetchone()
        if not row:
            return None
        conn.close()
        return row

    def safe_with_closing(cs):
        with closing(db.connect(cs)) as conn:
            return conn.execute("select 1").fetchall()

    def closed_immediately(cs):
        conn = db.connect(cs)
        conn.close()
        return "ok"
    """)
    r = run_ensemble(src, filename="t.py")
    assert r["counts"]["confirmed_path_leak"] >= 1     # branch_leak
    assert r["counts"]["refuted_safe"] >= 1            # closed_immediately
    verdicts = {v["verdict"] for v in r["verified"]}
    assert "confirmed_path_leak" in verdicts
    assert "refuted_safe" in verdicts


def test_ensemble_open_flag():
    from codegate.ensemble import run_ensemble
    src = textwrap.dedent("""
    def f(p):
        fh = open(p)
        return fh.read()
    """)
    r = run_ensemble(src, filename="t.py")
    # pre-filters must fire on unguarded open() — semgrep's deep rule wins the
    # dedupe, ruff's SIM115 is a fallback for when semgrep is unavailable
    rules = [v["rule"] for v in r["verified"]]
    assert "codegate-unguarded-open" in rules or "SIM115" in rules
    assert r["counts"]["confirmed_path_leak"] >= 1


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))


# ── semgrep (deep pre-filter) ────────────────────────────────────────────

def _semgrep_available():
    from codegate.ensemble import _semgrep_binary
    return _semgrep_binary() is not None


@pytest.mark.skipif(not _semgrep_available(), reason="semgrep not installed")
def test_semgrep_finds_aliased_db():
    from codegate.ensemble import run_semgrep
    src = textwrap.dedent("""
    import sqlite3 as db
    def leak(p):
        conn = db.connect(p)
        return conn.execute("select 1")
    """)
    r = run_semgrep(src, "t.py")
    assert r["available"]
    lines = [f["line"] for f in r["findings"]]
    assert 4 in lines  # db.connect aliased -> caught by loose rule


@pytest.mark.skipif(not _semgrep_available(), reason="semgrep not installed")
def test_ensemble_semgrep_integration():
    from codegate.ensemble import run_ensemble
    src = textwrap.dedent("""
    import sqlite3 as db
    from contextlib import closing

    def branch_leak(cs):
        conn = db.connect(cs)
        row = conn.execute("select 1").fetchone()
        if not row:
            return None
        conn.close()
        return row

    def closed_immediately(cs):
        conn = db.connect(cs)
        conn.close()
        return "ok"
    """)
    r = run_ensemble(src, filename="t.py")
    assert r["semgrep"]["available"]
    assert r["counts"]["confirmed_path_leak"] >= 1
    assert r["counts"]["refuted_safe"] >= 1
    # semgrep finding actually made it through to verification
    assert any(v["tool"] == "semgrep" for v in r["verified"])


def test_ensemble_graceful_without_tools(monkeypatch):
    # if both semgrep and ruff are missing, the syntactic scout still works
    from codegate import ensemble as ens
    monkeypatch.setattr(ens, "_semgrep_binary", lambda: None)
    monkeypatch.setattr(ens, "_ruff_binary", lambda: None)
    src = textwrap.dedent("""
    def leak(p):
        f = open(p)
        return f.read()
    """)
    r = ens.run_ensemble(src, filename="t.py")
    assert r["semgrep"]["available"] is False
    assert r["counts"]["confirmed_path_leak"] >= 1  # syntactic scout caught it
