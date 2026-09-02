from unittest.mock import MagicMock, patch

import agents.llm as llm_mod


def test_available_models_order(monkeypatch):
    monkeypatch.setattr(llm_mod, "openai_api_key", lambda: "sk-test")
    monkeypatch.setattr(llm_mod, "groq_api_key", lambda: "gsk-test")
    monkeypatch.setattr(llm_mod, "google_api_key", lambda: "google-test")
    models = llm_mod.available_models()
    assert models[0] == "openai/gpt-4o-mini"
    assert "groq/llama-3.1-8b-instant" in models
    assert "gemini/gemini-2.0-flash" in models


def test_available_models_skips_missing(monkeypatch):
    monkeypatch.setattr(llm_mod, "openai_api_key", lambda: "")
    monkeypatch.setattr(llm_mod, "groq_api_key", lambda: "gsk-test")
    monkeypatch.setattr(llm_mod, "google_api_key", lambda: "")
    assert llm_mod.available_models() == ["groq/llama-3.1-8b-instant"]


def test_chat_uses_fallback_model(monkeypatch):
    monkeypatch.setattr(
        llm_mod,
        "available_models",
        lambda: ["openai/gpt-4o-mini", "groq/llama-3.1-8b-instant"],
    )
    fake = MagicMock()
    fake.choices = [MagicMock(message=MagicMock(content="hello from fallback"))]
    fake.model = "groq/llama-3.1-8b-instant"
    with patch("litellm.completion", return_value=fake) as mocked:
        out = llm_mod.chat([{"role": "user", "content": "hi"}])
    assert out["content"] == "hello from fallback"
    assert "groq" in out["model"]
    kwargs = mocked.call_args.kwargs
    assert kwargs["model"] == "openai/gpt-4o-mini"
    assert kwargs["fallbacks"] == ["groq/llama-3.1-8b-instant"]


def test_chat_no_keys_raises(monkeypatch):
    monkeypatch.setattr(llm_mod, "available_models", lambda: [])
    try:
        llm_mod.chat([{"role": "user", "content": "hi"}])
        assert False, "expected NoLLMAvailable"
    except llm_mod.NoLLMAvailable:
        pass
