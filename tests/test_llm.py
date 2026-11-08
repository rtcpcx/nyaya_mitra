import sys
from types import SimpleNamespace

import pytest

from src import llm


def _fake_openai_module(openai_class, timeout_error=Exception):
    return SimpleNamespace(
        OpenAI=openai_class,
        APITimeoutError=timeout_error,
        APIConnectionError=ConnectionError,
        APIStatusError=RuntimeError,
    )


def test_chat_request_uses_bounded_settings_and_token_budget(monkeypatch):
    calls = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            calls["client"] = kwargs
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **kwargs):
            calls["request"] = kwargs
            message = SimpleNamespace(content='{"reply":"Connected","next_question":"","case_summary":"","risk_level":"routine","draft":""}')
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(llm, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(llm, "LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    monkeypatch.setattr(llm, "LLM_CHAT_TIMEOUT_SECONDS", 37)
    monkeypatch.setattr(llm, "LLM_CHAT_MAX_RETRIES", 0)
    monkeypatch.setitem(sys.modules, "openai", _fake_openai_module(FakeOpenAI))

    result = llm.generate_conversation_json({"user_message": "test"})

    assert result["reply"] == "Connected"
    assert calls["client"]["timeout"] == 37
    assert calls["client"]["max_retries"] == 0
    assert calls["request"]["max_tokens"] == 650
    assert calls["request"]["response_format"] == {"type": "json_object"}
    assert calls["request"]["extra_body"] == {
        "google": {"thinking_config": {"thinking_level": "low"}}
    }


def test_chat_timeout_has_actionable_provider_diagnostic(monkeypatch):
    class FakeTimeout(Exception):
        pass

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=lambda **kwargs: (_ for _ in ()).throw(FakeTimeout("timed out")))
            )

    monkeypatch.setattr(llm, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(llm, "LLM_CHAT_TIMEOUT_SECONDS", 45)
    monkeypatch.setattr(llm, "LLM_CHAT_MAX_RETRIES", 0)
    monkeypatch.setitem(sys.modules, "openai", _fake_openai_module(FakeOpenAI, FakeTimeout))

    with pytest.raises(RuntimeError, match=r"request timed out.*timeout is 45s"):
        llm.generate_conversation_json({"user_message": "test"})
