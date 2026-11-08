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



def test_conversation_returns_one_question_and_never_downgrades_triage(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "DATABASE_PATH", tmp_path / "missing.sqlite3")
    monkeypatch.setattr(service, "search_sources", lambda *a, **k: [])
    monkeypatch.setattr(service, "generate_conversation_json", lambda payload: {
        "reply": "I understand that a court notice can be time-sensitive. Keep the complete notice and envelope.",
        "next_question": "When did you receive it? Which court issued it?",
        "case_summary": "The user says they received a court notice.",
        "risk_level": "routine",
    })

    result = service.respond_to_turn("I received a court notice with a hearing tomorrow.")

    assert result["risk_level"] == "prompt"
    assert result["triage"]["level"] == "prompt"
    assert result["next_question"].count("?") == 1
    assert "couldn't verify a sufficiently relevant legal provision" in result["reply"]
    assert result["source_mode"] == "no_relevant_sources"
    assert set(result["timings_ms"]) == {"retrieval", "generation", "total"}


def test_conversation_carries_prior_turns_into_retrieval_and_prompt(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "DATABASE_PATH", tmp_path / "missing.sqlite3")
    captured = {}

    def fake_search(query, *args, **kwargs):
        captured["query"] = query
        captured["strict_relevance"] = kwargs.get("strict_relevance")
        return []

    def fake_generate(payload):
        captured["payload"] = payload
        return {
            "reply": "Thanks, that helps me understand the sequence.",
            "next_question": "Have you already handed over the keys?",
            "case_summary": "The user rented a home and says the landlord is withholding a deposit.",
            "risk_level": "routine",
        }

    monkeypatch.setattr(service, "search_sources", fake_search)
    monkeypatch.setattr(service, "generate_conversation_json", fake_generate)
    history = [
        {"role": "user", "content": "I rented a flat in Guwahati."},
        {"role": "assistant", "content": "I can help. What is the issue?"},
    ]

    result = service.respond_to_turn(
        "My landlord is withholding my security deposit.",
        history,
        "Guwahati, Assam",
    )

    assert "rented a flat in Guwahati" in captured["query"]
    assert captured["strict_relevance"] is True
    assert captured["payload"]["recent_conversation"] == history
    assert result["next_question"] == "Have you already handed over the keys?"
    assert result["source_mode"] == "no_relevant_sources"


def test_conversation_without_llm_is_transparent(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "DATABASE_PATH", tmp_path / "missing.sqlite3")
    monkeypatch.setattr(service, "search_sources", lambda *a, **k: [])
    result = service.respond_without_llm("My landlord is withholding my deposit.")
    assert "AI-generated legal explanations are currently disabled" in result["reply"]
    assert result["next_question"].count("?") == 1
    assert result["timings_ms"]["generation"] == 0.0
