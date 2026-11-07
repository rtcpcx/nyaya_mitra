from src import service


def test_local_only_mode_does_not_require_llm(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "DATABASE_PATH", tmp_path / "missing.sqlite3")
    result = service.analyze_without_llm("My employer has not paid salary")
    assert result["triage"]["level"] == "routine"
    assert result["source_mode"] == "no_sources_retrieved"
    assert "AI analysis is not enabled" in result["notice"]


def test_llm_key_missing_is_clear(monkeypatch):
    from src import llm
    monkeypatch.setattr(llm, "LLM_API_KEY", "")
    try:
        llm.generate_json({"task": "test"})
    except RuntimeError as exc:
        assert "LLM_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected missing API key error")
