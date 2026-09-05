"""User-defined rule DSL: project-local YAML rules without touching CodeGate source.

Snippets intentionally carry NO imports so the duck-type fallback stays off
(head not in import map) — these tests isolate the DSL merge path.
"""
import json
import subprocess
import sys
import textwrap

from codegate.analyzer import analyze_source
from codegate.config import (
    CodeGateConfig,
    load_user_rules,
)
from codegate.server import AnalysisCache
from codegate.webapi import analyze_full


def check(src, expect_leak, name, config=None):
    leaks = analyze_source(textwrap.dedent(src), filename=name, config=config)
    path_leaks = [lk for lk in leaks if lk.kind in ("path", "path+exception")]
    got = len(path_leaks) > 0
    assert got == expect_leak, (
        f"{name}: expect_leak={expect_leak} got={got} "
        f"path={[l.message for l in path_leaks]} "
        f"all={[(l.kind, l.acquire_line) for l in leaks]}"
    )


def write_rules(tmp_path, text):
    p = tmp_path / "rules.yaml"
    p.write_text(textwrap.dedent(text))
    return str(p)


def config_with_rules(path):
    config = CodeGateConfig.default()
    config.user_rules_path = path
    return config


# ── loader: both schemas ──
def test_loader_accepts_acquire_schema(tmp_path):
    p = write_rules(tmp_path, """\
        - acquire: acme.db.connect
          release: close
          alt_releases: [quit]
        """)
    specs = load_user_rules(p)
    assert len(specs) == 1
    assert specs[0].acquire == "acme.db.connect"
    assert specs[0].release == "close"
    assert specs[0].alt_releases == ["quit"]


def test_loader_accepts_call_schema(tmp_path):
    p = write_rules(tmp_path, """\
        resources:
          - call: acme.db.connect
            type: DATABASE
            close: [close, quit]
        """)
    specs = load_user_rules(p)
    assert len(specs) == 1
    assert specs[0].acquire == "acme.db.connect"
    assert specs[0].release == "close"
    assert specs[0].alt_releases == ["quit"]


def test_loader_skips_bad_entries(tmp_path):
    p = write_rules(tmp_path, """\
        - {}
        - close: [close]
        - acquire: acme.db.connect
        """)
    specs = load_user_rules(p)
    assert len(specs) == 1
    assert specs[0].acquire == "acme.db.connect"
    assert specs[0].release == "close"  # default release


def test_loader_missing_file_is_empty(tmp_path):
    assert load_user_rules(str(tmp_path / "nope.yaml")) == []


# ── end-to-end: user rule drives detection ──
def test_user_rule_flags_leak(tmp_path):
    p = write_rules(tmp_path, """\
        - acquire: acme.db.connect
          release: close
        """)
    leaks = analyze_source(
        textwrap.dedent("""\
        def f():
            h = acme.db.connect("prod")
            x = h
            if not x:
                return None
            h.close()
            return x
        """),
        filename="dsl_leak",
        config=config_with_rules(p),
    )
    path = [lk for lk in leaks if lk.kind in ("path", "path+exception")]
    assert len(path) == 1
    assert path[0].confidence == "definite"  # user rule, not inference


def test_user_rule_safe_quiet(tmp_path):
    p = write_rules(tmp_path, """\
        - acquire: acme.db.connect
          release: close
        """)
    check(
        """\
        def f():
            h = acme.db.connect("prod")
            x = h
            if not x:
                h.close()
                return None
            h.close()
            return x
        """,
        False,
        "dsl_safe",
        config=config_with_rules(p),
    )


def test_unknown_without_rule_silent():
    check(
        """\
        def f():
            h = acme.db.connect("prod")
            x = h
            if not x:
                return None
            h.close()
            return x
        """,
        False,
        "dsl_no_rule",
        config=CodeGateConfig.default(),
    )


def test_auto_load_from_project_dir(tmp_path, monkeypatch):
    d = tmp_path / ".codegate"
    d.mkdir()
    (d / "rules.yaml").write_text(
        textwrap.dedent("""\
        - acquire: acme.db.connect
          release: close
        """)
    )
    monkeypatch.chdir(tmp_path)
    check(
        """\
        def f():
            h = acme.db.connect("prod")
            x = h
            if not x:
                return None
            h.close()
            return x
        """,
        True,
        "dsl_autoload",
        config=CodeGateConfig.default(),
    )
