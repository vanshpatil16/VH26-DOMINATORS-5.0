"""Minimal LLM client used ONLY by the benchmark tool.

Records token usage from the API response so the report can show real
token consumption (input / output / total) per case. Not wired into
the analysis pipeline — the deterministic engine never calls an LLM.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import httpx


def get_api_config() -> dict[str, str]:
    """Resolve LLM credentials: .env → env vars → opencode auth.json."""
    try:
        from dotenv import load_dotenv
        for candidate in (Path.cwd() / ".env", Path.home() / "codeGate" / ".env"):
            if candidate.exists():
                load_dotenv(candidate)
    except Exception:
        pass

    key = os.environ.get("CODEGATE_LLM_KEY", "")
    base = os.environ.get("CODEGATE_LLM_BASE_URL", "https://opencode.ai/zen/go/v1").rstrip("/")
    model = os.environ.get("CODEGATE_LLM_MODEL", "deepseek-v4-flash")

    if not key:
        # fallback: opencode's auth store (opencode-go provider)
        try:
            auth = json.loads(
                Path.home().joinpath(".local/share/opencode/auth.json").read_text()
            )
            key = (auth.get("opencode-go") or {}).get("key", "")
            if not base.startswith("opencode"):
                base = "https://opencode.ai/zen/go/v1"
        except Exception:
            pass
    return {"key": key, "base_url": base, "model": model}


def llm_available() -> bool:
    return bool(get_api_config()["key"])


class BenchLLM:
    """Thin OpenAI-compatible client capturing usage. Fails closed."""

    def __init__(self, config: dict[str, str] | None = None, timeout: float = 60.0) -> None:
        cfg = config or get_api_config()
        self.key = cfg["key"]
        self.base_url = cfg["base_url"]
        self.model = cfg["model"]
        self.timeout = timeout

    def ask(self, user: str, system: str = "") -> Optional[dict[str, Any]]:
        """Returns {"text": ..., "usage": {prompt_tokens, completion_tokens,
        total_tokens}} or None on failure."""
        if not self.key:
            return None
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.key}",
                         "Content-Type": "application/json"},
                json={"model": self.model, "temperature": 0.0, "messages": messages},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return {
                "text": text,
                "usage": {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                "model": data.get("model", self.model),
            }
        except Exception:
            return None