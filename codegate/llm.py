"""LLM fallback client — OpenAI-compatible, dotenv-driven, fail-closed.

CodeGate's LLM layer is a FALLBACK, never the verdict-maker:

  - deterministic CFG findings are never overridden into silence
  - the LLM only resolves UNKNOWN / potential findings, or proposes new
    resource config (scout mode)
  - every LLM-influenced verdict carries `verified_by: "llm"` + a reason
  - on any error / timeout / garbage JSON, it fails CLOSED (returns None),
    so the pipeline keeps working deterministically without it

Configuration (env vars or .env):
  CODEGATE_LLM_KEY         required
  CODEGATE_LLM_BASE_URL    default https://api.openai.com/v1
  CODEGATE_LLM_MODEL       default gpt-4o-mini
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import httpx


def _load_dotenv() -> None:
    """Minimal .env loader — loads CODEGATE_* vars from the repo root .env."""
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    here = Path(__file__).resolve().parents[1]
    for candidate in (here / ".env", Path.cwd() / ".env"):
        if candidate.exists():
            load_dotenv(candidate)
            return


_load_dotenv()


def llm_configured() -> bool:
    return bool(os.environ.get("CODEGATE_LLM_KEY"))


def llm_settings() -> dict[str, str]:
    return {
        "key": os.environ.get("CODEGATE_LLM_KEY", ""),
        "base_url": os.environ.get("CODEGATE_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        "model": os.environ.get("CODEGATE_LLM_MODEL", "gpt-4o-mini"),
    }


class LLMClient:
    """Thin OpenAI-compatible chat-completions client. Fails closed."""

    def __init__(self, key: str | None = None, base_url: str | None = None,
                 model: str | None = None, timeout: float = 60.0) -> None:
        s = llm_settings()
        self.key = key or s["key"]
        self.base_url = (base_url or s["base_url"]).rstrip("/")
        self.model = model or s["model"]
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.key) and bool(self.base_url) and bool(self.model)

    def query_json(self, system: str, user: str,
                   temperature: float = 0.0) -> Optional[dict[str, Any]]:
        """Send a chat request expecting a JSON answer. Returns parsed dict
        or None on ANY failure (fail-closed)."""
        if not self.configured:
            return None
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "temperature": temperature,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return _parse_json_lenient(text)
        except Exception:
            return None


def _parse_json_lenient(text: str) -> Optional[dict[str, Any]]:
    """Extract a JSON object from an LLM reply (handles ```json fences)."""
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        # strip code fences (optional ```json ... ```)
        t = t.split("```", 2)
        if len(t) >= 2:
            t = t[1]
        if t.startswith("json"):
            t = t[4:]
        t = t.strip()
    # try from first '{' to last '}'
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end > start:
        t = t[start : end + 1]
    try:
        parsed = json.loads(t)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None
