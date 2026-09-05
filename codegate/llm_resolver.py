"""LLM Resolver module for LeakGuard External API Resource Semantics.

Interrogates Gemini, Groq, or OpenAI-compatible LLM endpoints to determine the
resource lifecycle semantics of an unknown library/function API, returning
a structured JSON payload.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Optional

# Note: httpx is imported lazily inside _query_llm to prevent ModuleNotFoundError on import

logger = logging.getLogger(__name__)


def load_env_file() -> None:
    """Load local .env file into os.environ if python-dotenv or simple parser is available."""
    try:
        from dotenv import load_dotenv

        for cand in [Path.cwd() / ".env", Path.home() / ".env"]:
            if cand.exists():
                load_dotenv(cand)
                break
    except Exception:
        # Fallback simple .env reader if python-dotenv is not installed
        for cand in [Path.cwd() / ".env", Path.home() / ".env"]:
            if cand.exists():
                try:
                    for line in cand.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            os.environ.setdefault(k.strip(), v.strip().strip("'\""))
                except Exception:
                    pass


def get_llm_config() -> dict[str, Any]:
    """Resolve LLM provider credentials, endpoints, and timeout parameters."""
    load_env_file()

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    llm_key = os.environ.get("LLM_API_KEY", "").strip() or os.environ.get("CODEGATE_LLM_KEY", "").strip()
    
    model = os.environ.get("LLM_MODEL", "").strip()
    base_url = os.environ.get("LLM_BASE_URL", "").strip()
    
    timeout = float(os.environ.get("LLM_TIMEOUT", "30.0"))
    min_confidence = float(os.environ.get("LLM_KB_MIN_CONFIDENCE", "0.85"))

    provider = "none"
    api_key = ""

    if gemini_key:
        provider = "gemini"
        api_key = gemini_key
        model = model or "gemini-1.5-flash"
    elif groq_key:
        provider = "groq"
        api_key = groq_key
        model = model or "llama-3.3-70b-versatile"
        base_url = base_url or "https://api.groq.com/openai/v1"
    elif llm_key:
        provider = "openai"
        api_key = llm_key
        model = model or "deepseek-v4-flash"
        base_url = base_url or "https://opencode.ai/zen/go/v1"

    return {
        "provider": provider,
        "api_key": api_key,
        "model": model,
        "base_url": base_url.rstrip("/"),
        "timeout": timeout,
        "min_confidence": min_confidence,
    }


class LLMResolver:
    """Invokes LLM fallback to resolve external API resource semantics."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.cfg = config or get_llm_config()

    def is_available(self) -> bool:
        return bool(self.cfg.get("api_key"))

    def resolve_api_semantics(
        self, library: str, function: str, resource_type: str = "FILE", source_context: str = ""
    ) -> Optional[dict[str, Any]]:
        """Interrogates LLM for API resource semantics.

        Returns structured dict or None on failure/missing key.
        """
        if not self.is_available():
            logger.info("External API knowledge unavailable: LLM API key not configured.")
            return None

        prompt = f"""
You are an expert static program analysis assistant specializing in Python resource leak detection.
Determine the EXACT resource lifecycle semantics for the external library function call:

Library/Module: {library}
Function/API: {function}
Resource Type: {resource_type}
Source Context: {source_context or "N/A"}

Answer the following questions:
- Does this function close the supplied resource? (CLOSES_INPUT)
- Does it leave the resource open? (PRESERVES_INPUT)
- Does it consume ownership of the resource? (TRANSFERS_OWNERSHIP / CONSUME)
- Does it create and return a new resource handle to the caller? (RETURNS_RESOURCE / CREATES_RESOURCE)
- Is the behavior unknown or conditional? (UNKNOWN / CONDITIONAL_CLOSE)

Respond ONLY with a single valid JSON object containing NO extra commentary or markdown:
{{
  "library": "{library}",
  "function": "{function}",
  "resource_type": "{resource_type}",
  "behavior": "CLOSES_INPUT | PRESERVES_INPUT | CREATES_RESOURCE | RETURNS_RESOURCE | TRANSFERS_OWNERSHIP | CONDITIONAL_CLOSE | UNKNOWN",
  "ownership": "BORROW | CONSUME | TRANSFER | RETURN | UNKNOWN",
  "exception_safety": "GUARANTEED | NOT_GUARANTEED | UNKNOWN",
  "confidence": 0.95,
  "evidence": "Short citation of official documentation or type stub info",
  "source": "Official API documentation",
  "reason": "Detailed technical explanation of resource handling behavior"
}}
"""

        try:
            raw_text = self._query_llm(prompt)
            if not raw_text:
                return None

            return self._parse_json_payload(raw_text)
        except Exception as e:
            logger.warning(f"LLM API resolution failed for {library}.{function}: {e}")
            return None

    def _query_llm(self, prompt: str) -> Optional[str]:
        try:
            import httpx
        except ImportError:
            logger.warning("httpx module is not installed. LLM resolution disabled.")
            return None

        load_env_file()
        timeout = float(os.environ.get("LLM_TIMEOUT", "30.0"))

        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        llm_key = os.environ.get("LLM_API_KEY", "").strip() or os.environ.get("CODEGATE_LLM_KEY", "").strip()

        candidates: list[dict[str, Any]] = []
        if groq_key:
            candidates.append({
                "type": "groq",
                "key": groq_key,
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "model": os.environ.get("LLM_MODEL", "openai/gpt-oss-20b"),
            })
        if gemini_key:
            g_model = os.environ.get("LLM_MODEL", "").strip()
            if not g_model or "gemini" not in g_model.lower():
                g_model = "gemini-flash-latest"
            if g_model.startswith("models/"):
                g_model = g_model[7:]
            candidates.append({
                "type": "gemini",
                "key": gemini_key,
                "url": f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent?key={gemini_key}",
                "model": g_model,
            })
        if llm_key:
            base_url = os.environ.get("LLM_BASE_URL", "https://opencode.ai/zen/go/v1").rstrip("/")
            candidates.append({
                "type": "openai",
                "key": llm_key,
                "url": f"{base_url}/chat/completions",
                "model": os.environ.get("LLM_MODEL", "deepseek-v4-flash"),
            })

        for cand in candidates:
            try:
                if cand["type"] == "gemini":
                    headers = {"Content-Type": "application/json"}
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"},
                    }
                    resp = httpx.post(cand["url"], headers=headers, json=payload, timeout=timeout)
                    resp.raise_for_status()
                    data = resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {cand['key']}",
                    }
                    payload = {
                        "model": cand["model"],
                        "temperature": 0.0,
                        "messages": [
                            {"role": "system", "content": "You output strictly valid JSON."},
                            {"role": "user", "content": prompt},
                        ],
                    }
                    resp = httpx.post(cand["url"], headers=headers, json=payload, timeout=timeout)
                    resp.raise_for_status()
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"LLM provider '{cand['type']}' failed ({e}). Trying next provider...")

        return None

    def _parse_json_payload(self, text: str) -> Optional[dict[str, Any]]:
        text = text.strip()
        # Clean markdown code blocks if present
        if "```" in text:
            match = re.search(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL)
            if match:
                text = match.group(1)
            else:
                text = re.sub(r"```(?:json)?|```", "", text).strip()

        try:
            return json.loads(text)
        except Exception:
            # Fallback regex extraction of outermost JSON object
            match = re.search(r"({.*})", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            return None
