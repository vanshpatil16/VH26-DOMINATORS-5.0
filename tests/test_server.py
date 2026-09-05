"""Tests for the persistent analysis server (codegate.server)."""
import json
import sys
import threading
import time
import urllib.request

import pytest

sys.path.insert(0, ".")
from codegate.server import AnalysisCache, serve


@pytest.fixture(scope="module")
def server_url():
    port = 8871
    t = threading.Thread(target=serve, kwargs={"port": port}, daemon=True)
    t.start()
    # wait for health
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
            break
        except Exception:
            time.sleep(0.5)
    yield f"http://127.0.0.1:{port}"
    # no shutdown call; daemon thread dies with the process


def post(url, path, payload, timeout=120):
    req = urllib.request.Request(
        f"{url}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def test_health(server_url):
    with urllib.request.urlopen(f"{server_url}/health", timeout=5) as r:
        h = json.loads(r.read())
    assert h["ok"] is True
    assert "cached" in h and "cache_hits" in h


def test_analyze_and_cache(server_url):
    src = "def f(p):\n    f = open(p)\n    return f.read()\n"
    r1 = post(server_url, "/analyze", {"source": src, "filename": "t.py"})
    assert r1["ok"] is True
    assert r1["cache"] == "miss"
    assert len(r1["leaks"]) >= 1
    r2 = post(server_url, "/analyze", {"source": src, "filename": "t.py"})
    assert r2["cache"] == "hit"
    assert r2["leaks"] == r1["leaks"]


def test_analyze_batch(server_url):
    src = "def f(p):\n    f = open(p)\n    return f.read()\n"
    r = post(server_url, "/analyze-batch", {
        "files": [
            {"source": src, "filename": "a.py"},
            {"source": "x = 1", "filename": "b.py"},
        ]
    })
    assert r["ok"] is True
    assert r["files"] == 2
    assert r["total_leaks"] >= 1
    assert r["results"][0]["filename"] == "a.py"


def test_analyze_requires_source(server_url):
    try:
        post(server_url, "/analyze", {"filename": "t.py"})
        assert False, "should have raised HTTPError 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400


def test_cache_lru_eviction():
    c = AnalysisCache(max_entries=2)
    k1 = c.key("a", "t.py", False, False)
    k2 = c.key("b", "t.py", False, False)
    k3 = c.key("c", "t.py", False, False)
    c.put(k1, {"leaks": 1})
    c.put(k2, {"leaks": 2})
    c.put(k3, {"leaks": 3})
    assert c.get(k1) is None  # evicted (LRU)
    assert c.get(k2) == {"leaks": 2}
    assert c.get(k3) == {"leaks": 3}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])