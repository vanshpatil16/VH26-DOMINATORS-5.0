"""Comprehensive unit test suite for LeakGuard External API Resource Semantics.

Mocks LLM interactions so the test suite runs 100% offline, deterministically, and fast.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
import textwrap
from unittest.mock import MagicMock, patch

import pytest
import yaml

from codegate.analyzer import analyze_source
from codegate.api_semantics import APISemanticsResolver
from codegate.config import CodeGateConfig
from codegate.knowledge_base import APIContract, KnowledgeBase
from codegate.llm_resolver import LLMResolver
from codegate.validator import validate_contract


# Helper fixture for isolated resources.yaml
@pytest.fixture
def temp_kb_file():
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w+", delete=False) as tf:
        initial_data = {
            "resources": [
                {"call": "open", "type": "FILE", "close": ["close"], "weight": 1.0}
            ],
            "api_contracts": [
                {
                    "library": "some_library",
                    "function": "cleanup",
                    "resource_type": "FILE",
                    "behavior": "CLOSES_INPUT",
                    "ownership": "CONSUME",
                    "confidence": 0.95,
                    "evidence": "Docs",
                    "source": "docs",
                    "discovered_by": "manual",
                },
                {
                    "library": "some_library",
                    "function": "process",
                    "resource_type": "FILE",
                    "behavior": "PRESERVES_INPUT",
                    "ownership": "BORROW",
                    "confidence": 0.95,
                    "evidence": "Docs",
                    "source": "docs",
                    "discovered_by": "manual",
                },
                {
                    "library": "external_library",
                    "function": "get_file",
                    "resource_type": "FILE",
                    "behavior": "RETURNS_RESOURCE",
                    "ownership": "RETURN",
                    "confidence": 0.90,
                    "evidence": "Docs",
                    "source": "docs",
                    "discovered_by": "manual",
                },
                {
                    "library": "external_library",
                    "function": "transfer",
                    "resource_type": "FILE",
                    "behavior": "TRANSFERS_OWNERSHIP",
                    "ownership": "TRANSFER",
                    "confidence": 0.92,
                    "evidence": "Docs",
                    "source": "docs",
                    "discovered_by": "manual",
                },
            ],
        }
        yaml.dump(initial_data, tf)
        tf_path = Path(tf.name)
    yield tf_path
    if tf_path.exists():
        tf_path.unlink()


# 1. Known API -> CLOSES_INPUT
def test_1_known_api_closes_input(temp_kb_file):
    src = textwrap.dedent("""
    import some_library
    def foo(path):
        f = open(path)
        some_library.cleanup(f)
        return
    """)
    config = CodeGateConfig.default()
    config.kb_path = str(temp_kb_file)
    leaks = analyze_source(src, filename="test.py", config=config)
    path_leaks = [l for l in leaks if l.kind in ("path", "path+exception")]
    assert len(path_leaks) == 0


# 2. Known API -> PRESERVES_INPUT
def test_2_known_api_preserves_input(temp_kb_file):
    src = textwrap.dedent("""
    import some_library
    def foo(path):
        f = open(path)
        some_library.process(f)
        return
    """)
    config = CodeGateConfig.default()
    config.kb_path = str(temp_kb_file)
    leaks = analyze_source(src, filename="test.py", config=config)
    path_leaks = [l for l in leaks if l.kind in ("path", "path+exception")]
    assert len(path_leaks) > 0


# 3. Known API -> RETURNS_RESOURCE
def test_3_known_api_returns_resource(temp_kb_file):
    src = textwrap.dedent("""
    import external_library
    def foo():
        f = external_library.get_file()
        f.close()
        return
    """)
    config = CodeGateConfig.default()
    config.kb_path = str(temp_kb_file)
    leaks = analyze_source(src, filename="test.py", config=config)
    path_leaks = [l for l in leaks if l.kind in ("path", "path+exception")]
    assert len(path_leaks) == 0


# 4. Known API -> TRANSFERS_OWNERSHIP
def test_4_known_api_transfers_ownership(temp_kb_file):
    src = textwrap.dedent("""
    import external_library
    def foo(path):
        f = open(path)
        external_library.transfer(f)
        return
    """)
    config = CodeGateConfig.default()
    config.kb_path = str(temp_kb_file)
    leaks = analyze_source(src, filename="test.py", config=config)
    path_leaks = [l for l in leaks if l.kind in ("path", "path+exception")]
    assert len(path_leaks) == 0


# 5. Unknown API -> LLM fallback
def test_5_unknown_api_llm_fallback(temp_kb_file):
    kb = KnowledgeBase(kb_path=temp_kb_file)
    mock_llm = MagicMock(spec=LLMResolver)
    mock_llm.is_available.return_value = True
    mock_llm.resolve_api_semantics.return_value = {
        "library": "new_lib",
        "function": "close_stream",
        "resource_type": "FILE",
        "behavior": "CLOSES_INPUT",
        "ownership": "CONSUME",
        "confidence": 0.95,
        "evidence": "Docs",
        "source": "docs",
        "reason": "Closes argument",
    }
    resolver = APISemanticsResolver(kb=kb, llm_resolver=mock_llm, min_confidence=0.85)
    contract = resolver.resolve_call("new_lib.close_stream", "FILE")
    assert contract.behavior == "CLOSES_INPUT"
    assert mock_llm.resolve_api_semantics.called


# 6. LLM returns valid contract
def test_6_llm_valid_contract():
    raw_data = {
        "library": "lib",
        "function": "fn",
        "resource_type": "FILE",
        "behavior": "CLOSES_INPUT",
        "ownership": "CONSUME",
        "confidence": 0.90,
    }
    valid, reason, contract = validate_contract(raw_data, min_confidence=0.85)
    assert valid
    assert contract is not None
    assert contract.behavior == "CLOSES_INPUT"


# 7. LLM returns malformed JSON
def test_7_llm_malformed_json():
    resolver = LLMResolver(config={"provider": "mock", "api_key": "dummy", "model": "m", "base_url": "", "timeout": 5, "min_confidence": 0.85})
    res = resolver._parse_json_payload("not a json string {{{")
    assert res is None


# 8. LLM returns invalid enum
def test_8_llm_invalid_enum():
    raw_data = {
        "library": "lib",
        "function": "fn",
        "behavior": "SUPER_MAGIC_CLOSE",
        "ownership": "CONSUME",
        "confidence": 0.95,
    }
    valid, reason, contract = validate_contract(raw_data)
    assert not valid
    assert "Invalid behavior" in reason


# 9. LLM confidence below threshold
def test_9_llm_confidence_below_threshold():
    raw_data = {
        "library": "lib",
        "function": "fn",
        "behavior": "CLOSES_INPUT",
        "ownership": "CONSUME",
        "confidence": 0.60,
    }
    valid, reason, contract = validate_contract(raw_data, min_confidence=0.85)
    assert not valid
    assert "below minimum required threshold" in reason


# 10. Missing API key
def test_10_missing_api_key(temp_kb_file):
    kb = KnowledgeBase(kb_path=temp_kb_file)
    mock_llm = MagicMock(spec=LLMResolver)
    mock_llm.is_available.return_value = False
    resolver = APISemanticsResolver(kb=kb, llm_resolver=mock_llm)
    contract = resolver.resolve_call("unknown_lib.func")
    assert contract.behavior == "UNKNOWN"
    assert "LLM API key not configured" in contract.reason


# 11. LLM timeout/failure
def test_11_llm_timeout_failure(temp_kb_file):
    kb = KnowledgeBase(kb_path=temp_kb_file)
    mock_llm = MagicMock(spec=LLMResolver)
    mock_llm.is_available.return_value = True
    mock_llm.resolve_api_semantics.return_value = None
    resolver = APISemanticsResolver(kb=kb, llm_resolver=mock_llm)
    contract = resolver.resolve_call("unknown_lib.func")
    assert contract.behavior == "UNKNOWN"


# 12. Duplicate knowledge-base entry
def test_12_duplicate_kb_entry(temp_kb_file):
    kb = KnowledgeBase(kb_path=temp_kb_file)
    initial_count = len(kb.contracts)
    contract = APIContract(
        library="some_library",
        function="cleanup",
        behavior="CLOSES_INPUT",
        confidence=0.99,
    )
    kb.save_contract(contract)
    assert len(kb.contracts) == initial_count  # updated, not duplicated


# 13. Knowledge-base update
def test_13_kb_update(temp_kb_file):
    kb = KnowledgeBase(kb_path=temp_kb_file)
    contract = APIContract(
        library="brand_new_lib",
        function="safe_func",
        behavior="CLOSES_INPUT",
        confidence=0.90,
    )
    kb.save_contract(contract)
    reloaded = KnowledgeBase(kb_path=temp_kb_file)
    found = reloaded.lookup("brand_new_lib", "safe_func")
    assert found is not None
    assert found.behavior == "CLOSES_INPUT"


# 14. Corrupted/invalid resources.yaml handling
def test_14_corrupted_yaml_handling():
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w+", delete=False) as tf:
        tf.write("CORRUPTED YAML: ::: [[invalid")
        tf_path = Path(tf.name)
    try:
        kb = KnowledgeBase(kb_path=tf_path)
        assert kb.contracts == []
    finally:
        if tf_path.exists():
            tf_path.unlink()


# 15. User-defined function handled statically without LLM
def test_15_user_defined_func_static_no_llm(temp_kb_file):
    src = textwrap.dedent("""
    def my_cleanup(f):
        f.close()

    def main(path):
        f = open(path)
        my_cleanup(f)
        return
    """)
    config = CodeGateConfig.default()
    config.kb_path = str(temp_kb_file)
    leaks = analyze_source(src, filename="test.py", config=config)
    path_leaks = [l for l in leaks if l.kind in ("path", "path+exception")]
    assert len(path_leaks) == 0


# 16. Deterministic DEFINITE_LEAK cannot be overridden by LLM
def test_16_deterministic_leak_not_overridden(temp_kb_file):
    src = textwrap.dedent("""
    def bad(path):
        f = open(path)
        return
    """)
    config = CodeGateConfig.default()
    config.kb_path = str(temp_kb_file)
    leaks = analyze_source(src, filename="test.py", config=config)
    path_leaks = [l for l in leaks if l.kind in ("path", "path+exception")]
    assert len(path_leaks) > 0
    assert any(l.confidence == "definite" for l in path_leaks)


# 17. Deterministic SAFE cannot be incorrectly changed by ML/LLM
def test_17_deterministic_safe_preserved(temp_kb_file):
    src = textwrap.dedent("""
    def safe(path):
        with open(path) as f:
            data = f.read()
        return data
    """)
    config = CodeGateConfig.default()
    config.kb_path = str(temp_kb_file)
    leaks = analyze_source(src, filename="test.py", config=config)
    path_leaks = [l for l in leaks if l.kind in ("path", "path+exception")]
    assert len(path_leaks) == 0


# 18. Returned resource is tracked by existing resource tracker
def test_18_returned_resource_tracked(temp_kb_file):
    src = textwrap.dedent("""
    import external_library
    def foo():
        f = external_library.get_file()
        # Not closed -> leak!
        return 1
    """)
    config = CodeGateConfig.default()
    config.kb_path = str(temp_kb_file)
    leaks = analyze_source(src, filename="test.py", config=config)
    path_leaks = [l for l in leaks if l.kind in ("path", "path+exception")]
    assert len(path_leaks) > 0
    assert path_leaks[0].var == "f"
