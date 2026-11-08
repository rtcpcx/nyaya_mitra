# Quality gates and regression coverage

## Current safeguards

1. **Jurisdiction isolation:** confirmed-state analysis includes central/national and matching-state records only. If the state is missing or unrecognised, state-specific records are excluded until location is confirmed. The manual source explorer remains unrestricted.
2. **Triage consistency:** the model cannot downgrade an urgent/prompt first-pass rule flag in either the legacy report path or conversational chat.
3. **Draft restraint:** the legacy structured-analysis path suppresses unsolicited drafts. The chat path does not create drafts unless explicitly asked for a named document.
4. **Conversation flow:** the primary app uses chat history held in Streamlit Session State, sends recent turns as context, and presents at most one clarifying question per turn. The current session is not durable case storage.
5. **User/developer separation:** concise replies and relevant source links are user-facing; raw model JSON, triage and latency metrics are placed in a developer/test-bench expander and downloadable JSON.
6. **Retrieval relevance:** chat retrieval expands common tenancy vocabulary and rejects generic deposit references unless the retrieved passage contains tenancy-specific language and overlaps meaningfully with the user's issue. Regression fixtures include irrelevant TRAI and RBI passages.
7. **Latency diagnostics:** each conversational turn records retrieval, model-generation and total elapsed milliseconds. Compare repeated runs on the same machine, database and provider before claiming a speed improvement.
8. **Provider-neutral operation:** the chat path uses the configured OpenAI-compatible provider, a 45-second default timeout, zero automatic retries by default, and a 650-token response cap. Timeout/retry settings can be overridden in the local `.env`; `python -m src.llm --test-chat` exercises the exact chat request and reports elapsed time.

## Run locally (PowerShell)

```powershell
python -m compileall -q .
pytest -q
```

The offline suite uses synthetic fixtures and mocked model responses. It does **not** test live Gemini/provider latency, live database retrieval quality on the user's full downloaded corpus, legal validity, model compliance in every case, or the completeness of Indian law. Run a small manual benchmark on the same case prompts before and after changes, inspect the raw JSON and source list, and ask a qualified advocate to review consequential legal outputs.

## Known limitations

- Retrieval remains SQLite FTS5 lexical search. The tenancy gate reduces one observed false-positive pattern; it is not a general legal relevance model and may exclude relevant material with different terminology.
- No vector retrieval, cross-encoder reranker, citation-entailment verifier or current-law/Gazette synchronisation is implemented.
- Session history is lost when the Streamlit session ends or is reset. Raw turn JSON is written locally and may contain sensitive case details; protect the machine and delete these files when no longer needed.
- Rule-based triage can miss urgent facts. It is not a safety classifier.
- No authentication, encryption-at-rest, tenant isolation, audit-grade retention controls or production deployment safeguards.
- A passing test suite does not establish legal completeness or production readiness.
