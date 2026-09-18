"""Provider-agnostic LLM router with priority fallback chain.

Ported from agent-orchestrator (Group I consolidation). Every provider is
called through its OpenAI-compatible endpoint, so swapping or adding models
is a roster change, not a code change:

  1. NVIDIA NIM  (NVIDIA_API_KEY)                  - fast MoE primary
  2. Gemini      (GOOGLE_API_KEY or GEMINI_API_KEY) - OpenAI-compat endpoint
  3. Groq        (GROQ_API_KEY)                     - production fallback

Override the Gemini model with LLM_MODEL, or set the full OpenAI-compatible
base URL with OPENAI_API_BASE. With no keys configured the router is inert
and callers fall back to deterministic behavior.
"""

from __future__ import annotations

import json
import logging
import os
import re

from openai import OpenAI, RateLimitError, APIError

log = logging.getLogger(__name__)

NVIDIA_MODELS = [
    "nvidia/nemotron-3.5-lightning-30b-a3b",  # fast, MoE
    "nvidia/nemotron-3-ultra-550b-a55b",      # best reasoning
]

GROQ_MODEL = "openai/gpt-oss-120b"

_CLIENTS: list | None = None  # lazy-initialized on first use


def _build_clients() -> list[tuple[OpenAI, str, str]]:
    clients: list[tuple[OpenAI, str, str]] = []

    nvidia_key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if nvidia_key:
        base_url = os.environ.get("OPENAI_API_BASE", "https://integrate.api.nvidia.com/v1")
        model_override = os.environ.get("LLM_MODEL", "").strip()
        models_to_try = [model_override] if model_override else NVIDIA_MODELS
        for model in models_to_try:
            clients.append(
                (
                    OpenAI(api_key=nvidia_key, base_url=base_url),
                    model,
                    f"NVIDIA NIM ({model.split('/')[-1]})",
                )
            )

    gemini_key = (
        os.environ.get("GOOGLE_API_KEY", "").strip()
        or os.environ.get("GEMINI_API_KEY", "").strip()
    )
    if gemini_key:
        clients.append(
            (
                OpenAI(
                    api_key=gemini_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                ),
                os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
                "Gemini",
            )
        )

    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if groq_key:
        clients.append(
            (
                OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1"),
                GROQ_MODEL,
                "Groq",
            )
        )

    if clients:
        log.info("LLM fallback chain: %s", " -> ".join(label for _, _, label in clients))
    else:
        log.warning("No LLM API key found; deterministic fallback will be used.")
    return clients


def _get_clients() -> list[tuple[OpenAI, str, str]]:
    global _CLIENTS
    if _CLIENTS is None:
        _CLIENTS = _build_clients()
    return _CLIENTS


def is_configured() -> bool:
    """True when at least one provider key is available."""
    return bool(_get_clients())


def chat_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 8000,
) -> dict:
    """Run a chat completion through the fallback chain and return parsed JSON.

    Falls back to the next provider on rate limits, API errors, truncation,
    or invalid JSON. Raises RuntimeError when every provider is exhausted.
    Callers should catch that and use their deterministic fallback.
    """

    last_error: Exception | None = None
    for client, model, label in _get_clients():
        try:
            log.info("Calling %s...", label)
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            choice = resp.choices[0]
            if choice.finish_reason == "length":
                raise json.JSONDecodeError("response truncated (finish_reason=length)", "", 0)
            raw = choice.message.content or ""
            raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
            raw = re.sub(r"```\s*$", "", raw.strip(), flags=re.MULTILINE)
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                raise json.JSONDecodeError("No JSON object found", raw, 0)
            result = json.loads(m.group())
            log.info("Got response from %s", label)
            return result
        except RateLimitError as e:
            log.warning("%s rate-limited, trying next. (%s)", label, e)
            last_error = e
        except APIError as e:
            log.warning("%s API error, trying next. (%s)", label, e)
            last_error = e
        except json.JSONDecodeError as e:
            log.warning("%s returned invalid JSON, trying next. (%s)", label, e)
            last_error = e

    raise RuntimeError(f"All LLM providers exhausted. Last error: {last_error}")
