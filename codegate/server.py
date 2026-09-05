"""CodeGate analysis server — persistent, cached, multi-file.

Why this exists: the CLI/frontend currently spawns `python -m codegate.webapi`
per request (~300ms of interpreter + import overhead). A long-lived server
keeps the analyzer warm (~28ms/analyze) and adds a content-addressed cache
(~1ms on repeat scans), plus a batch endpoint for whole-repo/team scans.

Endpoints (stdlib http.server, JSON):
    POST /analyze         {"source": str, "filename": str,
                           "fix": bool?, "ensemble": bool?}
    POST /analyze-batch   {"files": [{"source", "filename", "fix"?, "ensemble"?}]}
    GET  /health          {"ok": true, "cached": N, "cache_hits": M, "uptime": s}
    POST /shutdown        {"token": <optional>}  — stops the server

Cache: keyed by sha256(source + filename + flags). LRU (default 512 entries).
Concurrency: ThreadingHTTPServer; analysis holds the GIL but I/O-heavy
semgrep/ruff parts run in subprocesses, so threads are fine for scale-out.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional

from .analyzer import analyze_source
from .config import CodeGateConfig


class AnalysisCache:
    """Thread-safe LRU cache keyed by content hash."""

    def __init__(self, max_entries: int = 512) -> None:
        self.max = max_entries
        self._data: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def key(self, source: str, filename: str, fix: bool, ensemble: bool) -> str:
        h = hashlib.sha256()
        h.update(source.encode("utf-8"))
        h.update(filename.encode("utf-8"))
        h.update(b"fix" if fix else b"nofix")
        h.update(b"ens" if ensemble else b"noens")
        return h.hexdigest()

    def get(self, k: str) -> Optional[dict[str, Any]]:
        if k in self._data:
            self.hits += 1
            self._data.move_to_end(k)
            return self._data[k]
        self.misses += 1
        return None

    def put(self, k: str, result: dict[str, Any]) -> None:
        self._data[k] = result
        self._data.move_to_end(k)
        while len(self._data) > self.max:
            self._data.popitem(last=False)


class _Handler(BaseHTTPRequestHandler):
    cache: AnalysisCache = AnalysisCache()
    start_time: float = time.time()
    config: CodeGateConfig = CodeGateConfig.default()
    shutdown_token: str = ""

    # ------------------------------------------------------------------
    # plumbing
    # ------------------------------------------------------------------
    def log_message(self, fmt: str, *args) -> None:  # quiet unless verbose
        pass

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # routing
    # ------------------------------------------------------------------
    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/health":
            c = self.cache
            self._send(200, {
                "ok": True,
                "cached": len(c._data),
                "cache_hits": c.hits,
                "cache_misses": c.misses,
                "uptime_s": round(time.time() - self.start_time, 1),
                "python": __import__("sys").version.split()[0],
            })
        else:
            self._send(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        path = self.path.rstrip("/")
        body = self._read_body()
        try:
            if path == "/analyze":
                self._analyze_one(body)
            elif path == "/analyze-batch":
                self._analyze_batch(body)
            elif path == "/shutdown":
                tok = body.get("token", "")
                if self.shutdown_token and tok != self.shutdown_token:
                    self._send(403, {"ok": False, "error": "invalid shutdown token"})
                    return
                self._send(200, {"ok": True, "stopping": True})
                import threading
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                self._send(404, {"ok": False, "error": "not found"})
        except Exception as e:  # noqa: BLE001
            self._send(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})

    # ------------------------------------------------------------------
    # analysis
    # ------------------------------------------------------------------
    def _analyze_one(self, body: dict[str, Any]) -> None:
        source = body.get("source", "")
        filename = body.get("filename", "input.py")
        fix = bool(body.get("fix", False))
        ensemble = bool(body.get("ensemble", False))
        if not isinstance(source, str) or not source.strip():
            self._send(400, {"ok": False, "error": "source is required"})
            return
        key = self.cache.key(source, filename, fix, ensemble)
        cached = self.cache.get(key)
        if cached is not None:
            cached = dict(cached)
            cached["cache"] = "hit"
            self._send(200, cached)
            return
        result = _analyze(source, filename, fix, ensemble)
        self.cache.put(key, result)
        out = dict(result)
        out["cache"] = "miss"
        self._send(200, out)

    def _analyze_batch(self, body: dict[str, Any]) -> None:
        files = body.get("files", [])
        if not isinstance(files, list) or not files:
            self._send(400, {"ok": False, "error": "files[] is required"})
            return
        results = []
        for f in files:
            if not isinstance(f, dict):
                continue
            source = f.get("source", "")
            filename = f.get("filename", "input.py")
            fix = bool(f.get("fix", False))
            ensemble = bool(f.get("ensemble", False))
            key = self.cache.key(source, filename, fix, ensemble)
            cached = self.cache.get(key)
            if cached is not None:
                r = dict(cached)
                r["cache"] = "hit"
            else:
                r = _analyze(source, filename, fix, ensemble)
                r["cache"] = "miss"
                self.cache.put(key, r)
            r["filename"] = filename
            results.append(r)
        total_leaks = sum(len(r.get("leaks", [])) for r in results)
        self._send(200, {
            "ok": True,
            "files": len(results),
            "total_leaks": total_leaks,
            "results": results,
        })


def _analyze(source: str, filename: str, fix: bool, ensemble: bool) -> dict[str, Any]:
    """Runs the full webapi pipeline in-process (warm)."""
    from .webapi import analyze_full
    return analyze_full(source, filename=filename, fix=fix, ensemble=ensemble)


def serve(port: int = 8750, host: str = "127.0.0.1", max_cache: int = 512,
          shutdown_token: str = "") -> None:
    _Handler.cache = AnalysisCache(max_entries=max_cache)
    _Handler.shutdown_token = shutdown_token
    server = ThreadingHTTPServer((host, port), _Handler)
    print(f"CodeGate analysis server listening on http://{host}:{port} "
          f"(cache={max_cache}, thread per request)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codegate serve", description="Persistent CodeGate analysis server")
    parser.add_argument("--port", type=int, default=8750)
    parser.add_argument("--host", default="127.0.0.1", help="bind host (use 0.0.0.0 for remote)")
    parser.add_argument("--max-cache", type=int, default=512)
    parser.add_argument("--shutdown-token", default="", help="optional token required to stop the server")
    args = parser.parse_args(argv)
    serve(port=args.port, host=args.host, max_cache=args.max_cache,
          shutdown_token=args.shutdown_token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())