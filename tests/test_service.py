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


def test_triage_cannot_be_downgraded_and_unsolicited_draft_is_removed(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "DATABASE_PATH", tmp_path / "missing.sqlite3")
    monkeypatch.setattr(service, "search_sources", lambda *a, **k: [])
    monkeypatch.setattr(service, "generate_json", lambda payload: {
        "lawyer_recommendation": {"recommended": False, "why": [], "urgency": "routine"},
        "draft": "The tenant paid all rent and utilities under clause 8."
    })
    result = service.analyze_problem("I received a court notice and hearing date")
    assert result["lawyer_recommendation"]["recommended"] is True
    assert result["lawyer_recommendation"]["urgency"] == "prompt"
    assert result["draft"] == ""


def test_unknown_state_uses_national_only_retrieval(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "DATABASE_PATH", tmp_path / "missing.sqlite3")
    calls = {}
    def fake_search(*args, **kwargs):
        calls["jurisdiction_hint"] = args[3]
        calls.update(kwargs)
        return []
    monkeypatch.setattr(service, "search_sources", fake_search)
    monkeypatch.setattr(service, "generate_json", lambda payload: {})
    service.analyze_problem("My landlord is withholding a deposit", "Somewhere in India")
    assert calls["national_only"] is True
    assert calls["jurisdiction_hint"] is None


def test_explicit_draft_request_is_retained(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "DATABASE_PATH", tmp_path / "missing.sqlite3")
    monkeypatch.setattr(service, "search_sources", lambda *a, **k: [])
    monkeypatch.setattr(service, "generate_json", lambda payload: {"draft": "I request return of the stated deposit amount."})
    result = service.analyze_problem("Please draft a factual legal notice asking for return of my deposit.")
    assert result["draft"] == "I request return of the stated deposit amount."
