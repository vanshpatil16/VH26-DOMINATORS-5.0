"""Automated tests for Exception Safety Contracts in LeakGuard."""

from __future__ import annotations

from pathlib import Path
import tempfile
import textwrap
import pytest
import yaml

from codegate.analyzer import analyze_source
from codegate.config import CodeGateConfig


@pytest.fixture
def custom_kb_file():
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w+", delete=False) as tf:
        data = {
            "resources": [
                {"call": "open", "type": "FILE", "close": ["close"], "weight": 1.0}
            ],
            "api_contracts": [
                {
                    "library": "ext_guaranteed",
                    "function": "transfer_file",
                    "resource_type": "FILE",
                    "behavior": "TRANSFERS_OWNERSHIP",
                    "ownership": "TRANSFER",
                    "exception_safety": "GUARANTEED",
                    "confidence": 0.95,
                },
                {
                    "library": "ext_not_guaranteed",
                    "function": "transfer_file",
                    "resource_type": "FILE",
                    "behavior": "TRANSFERS_OWNERSHIP",
                    "ownership": "TRANSFER",
                    "exception_safety": "NOT_GUARANTEED",
                    "confidence": 0.95,
                },
                {
                    "library": "ext_unknown",
                    "function": "transfer_file",
                    "resource_type": "FILE",
                    "behavior": "TRANSFERS_OWNERSHIP",
                    "ownership": "TRANSFER",
                    "exception_safety": "UNKNOWN",
                    "confidence": 0.95,
                },
                {
                    "library": "some_library",
                    "function": "process",
                    "resource_type": "FILE",
                    "behavior": "PRESERVES_INPUT",
                    "ownership": "BORROW",
                    "exception_safety": "UNKNOWN",
                    "confidence": 0.95,
                },
                {
                    "library": "ext_close_guaranteed",
                    "function": "process_and_close",
                    "resource_type": "FILE",
                    "behavior": "CLOSES_INPUT",
                    "ownership": "CONSUME",
                    "exception_safety": "GUARANTEED",
                    "confidence": 0.95,
                },
            ],
        }
        yaml.dump(data, tf)
        tf_path = Path(tf.name)
    yield tf_path
    if tf_path.exists():
        tf_path.unlink()


# TEST A: TRANSFERS_OWNERSHIP + TRANSFER + GUARANTEED => SAFE
def test_a_transfers_ownership_guaranteed(custom_kb_file):
    src = textwrap.dedent("""
    import ext_guaranteed

    def upload_file(path):
        f = open(path)
        ext_guaranteed.transfer_file(f)
        return "uploaded"
    """)
    config = CodeGateConfig.default()
    config.kb_path = str(custom_kb_file)
    leaks = analyze_source(src, filename="test_a.py", config=config)
    assert len(leaks) == 0  # SAFE!


# TEST B: TRANSFERS_OWNERSHIP + TRANSFER + NOT_GUARANTEED => EXCEPTION_PATH_LEAK
def test_b_transfers_ownership_not_guaranteed(custom_kb_file):
    src = textwrap.dedent("""
    import ext_not_guaranteed

    def upload_file(path):
        f = open(path)
        ext_not_guaranteed.transfer_file(f)
        return "uploaded"
    """)
    config = CodeGateConfig.default()
    config.kb_path = str(custom_kb_file)
    leaks = analyze_source(src, filename="test_b.py", config=config)
    assert len(leaks) == 1
    assert leaks[0].kind == "exception"
    assert "NOT_GUARANTEED" in leaks[0].exception_note


# TEST C: TRANSFERS_OWNERSHIP + TRANSFER + UNKNOWN => EXCEPTION_PATH_LEAK
def test_c_transfers_ownership_unknown(custom_kb_file):
    src = textwrap.dedent("""
    import ext_unknown

    def upload_file(path):
        f = open(path)
        ext_unknown.transfer_file(f)
        return "uploaded"
    """)
    config = CodeGateConfig.default()
    config.kb_path = str(custom_kb_file)
    leaks = analyze_source(src, filename="test_c.py", config=config)
    assert len(leaks) == 1
    assert leaks[0].kind == "exception"


# TEST D: PRESERVES_INPUT + BORROW => LEAK
def test_d_preserves_input_borrow(custom_kb_file):
    src = textwrap.dedent("""
    import some_library

    def read_file(path):
        f = open(path)
        some_library.process(f)
        return "done"
    """)
    config = CodeGateConfig.default()
    config.kb_path = str(custom_kb_file)
    leaks = analyze_source(src, filename="test_d.py", config=config)
    assert len(leaks) > 0
    assert any(l.kind in ("path", "path+exception") for l in leaks)


# TEST E: try/finally with external API => SAFE
def test_e_try_finally_safe(custom_kb_file):
    src = textwrap.dedent("""
    import ext_not_guaranteed

    def read_file(path):
        f = open(path)
        try:
            result = ext_not_guaranteed.transfer_file(f)
            return result
        finally:
            f.close()
    """)
    config = CodeGateConfig.default()
    config.kb_path = str(custom_kb_file)
    leaks = analyze_source(src, filename="test_e.py", config=config)
    assert len(leaks) == 0


# TEST F: CLOSES_INPUT + CONSUME + GUARANTEED => SAFE
def test_f_closes_input_guaranteed(custom_kb_file):
    src = textwrap.dedent("""
    import ext_close_guaranteed

    def read_file(path):
        f = open(path)
        result = ext_close_guaranteed.process_and_close(f)
        return result
    """)
    config = CodeGateConfig.default()
    config.kb_path = str(custom_kb_file)
    leaks = analyze_source(src, filename="test_f.py", config=config)
    assert len(leaks) == 0  # SAFE!
