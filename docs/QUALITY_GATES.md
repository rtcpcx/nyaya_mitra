# Quality gates and regression coverage

This branch addresses four prototype failure modes:

1. **Jurisdiction isolation:** confirmed-state analysis includes national/central and matching-state records only. If the state is missing or unrecognised, state-specific records are excluded until location is confirmed. The manual source explorer remains unrestricted.
2. **Triage consistency:** model output cannot downgrade an urgent/prompt first-pass rule flag.
3. **Draft restraint:** unsolicited drafts are removed unless the user explicitly requests a named document. Prompts prohibit adding unprovided payment/agreement facts or requesting full bank details and credentials.
4. **Provider-neutral errors:** missing-key errors refer to the configured LLM API rather than incorrectly assuming Groq.

Run locally:

```powershell
python -m compileall -q .
pytest -q
```

These offline tests do not prove live provider availability, current legal validity, legal completeness, or perfect model compliance. A qualified advocate must review consequential outputs and formal documents.
