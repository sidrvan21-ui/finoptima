"""One chat helper: OpenAI → Groq → Gemini so writer/judge do not black out."""

from __future__ import annotations

import os
from typing import Any

from db.connection import google_api_key, groq_api_key, openai_api_key


class NoLLMAvailable(Exception):
    """No API keys, or every provider in the chain failed."""


def available_models() -> list[str]:
    """Build the failover chain from keys that exist in .env."""
    models: list[str] = []
    if openai_api_key():
        models.append("openai/gpt-4o-mini")
    if groq_api_key():
        models.append("groq/llama-3.1-8b-instant")
    gkey = google_api_key()
    if gkey:
        # LiteLLM expects GEMINI_API_KEY for gemini/* models.
        if not os.environ.get("GEMINI_API_KEY", "").strip():
            os.environ["GEMINI_API_KEY"] = gkey
        models.append("gemini/gemini-2.0-flash")
    return models


def chat(messages: list[dict[str, str]], *, temperature: float = 0) -> dict[str, Any]:
    """
    Call the first available model; LiteLLM tries fallbacks on failure.
    Returns {"content": str, "model": str}.
    """
    models = available_models()
    if not models:
        raise NoLLMAvailable("No LLM API keys in .env")

    primary, *fallbacks = models
    from litellm import completion

    kwargs: dict[str, Any] = {
        "model": primary,
        "messages": messages,
        "temperature": temperature,
    }
    if fallbacks:
        kwargs["fallbacks"] = fallbacks

    resp = completion(**kwargs)
    content = (resp.choices[0].message.content or "").strip()
    model = getattr(resp, "model", None) or primary
    return {"content": content, "model": str(model)}
