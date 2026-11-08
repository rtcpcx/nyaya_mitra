# Conversational redesign: research and implementation notes

## Why the previous experience needed a redesign

The first inspected case output was a full structured report with intake, assessment, options, next steps, four clarification questions, triage, source notes and retrieved records. It was not a natural first conversational turn. Its retrieval list included TRAI and RBI records because the query mentioned a security deposit, although the described dispute was between a tenant and landlord. The retrieved records therefore did not support the tenancy-specific generalisation in the report.

The redesign separates three jobs that were previously bundled together:
- **Conversation:** understand the user's current turn, use recent session context and ask one useful question.
- **Evidence retrieval:** return only passages with meaningful topic relevance and the correct jurisdiction scope.
- **Audit/test output:** retain the structured model response, sources, triage and timing diagnostics without putting the entire internal report in the user's chat.

## External research consulted

1. **Streamlit chat interface and session state.** Streamlit documents `st.chat_input`, `st.chat_message`, `st.status` and `st.write_stream` as the building blocks for conversational applications. Session State stores values for the active user session and survives reruns; it is not durable case storage.
   - https://docs.streamlit.io/develop/api-reference/chat
   - https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state

2. **Gemini OpenAI compatibility.** Google's compatibility documentation confirms that the OpenAI Python client can connect to the Gemini endpoint and that the compatibility endpoint supports streaming. This project keeps the compact chat response JSON-validated for now; it measures generation time rather than streaming partially parsed JSON to the user. A future streaming change should be tested against the exact configured model and response format.
   - https://ai.google.dev/gemini-api/docs/openai

3. **Official Indian legal-source entry points.** India Code is the Government of India's legislation portal, and the Legislative Department publishes the Constitution of India. These official portals are appropriate verification destinations; a third-party indexed dataset remains a search aid and is not proof that a passage is current or operative.
   - https://www.indiacode.nic.in/indiacode/home.jsp
   - https://www.legislative.gov.in/documents

4. **Legal RAG limitations.** Empirical work on AI legal research systems reports that retrieval-augmented systems can still hallucinate. A 2025 study of commercial legal research tools reported hallucination rates between 17% and 33% in its evaluated setting. This supports treating retrieval as a risk-reduction mechanism, not a guarantee of correctness.
   - https://doi.org/10.1111/jels.12413

5. **Indian legal RAG research.** Recent India-focused work describes jurisdiction-specific statutory corpora, source attribution and retrieval evaluation as important design dimensions. These papers are useful design references, not proof that any particular implementation is legally reliable.
   - https://ieeexplore.ieee.org/abstract/document/11710573
   - https://ieeexplore.ieee.org/abstract/document/11712697

## Implemented changes

- Replaced the one-shot intake form as the primary experience with a chat interface.
- Kept recent conversation context in Streamlit Session State and passed prior turns to the conversation service.
- Added a compact response schema: `reply`, `next_question`, `case_summary` and `risk_level`.
- Normalised the response to one follow-up question; question text is removed from the main reply to avoid duplicate/multiple questions.
- Kept the legacy structured-analysis service for compatibility and testing.
- Added a tenancy vocabulary expansion and a strict relevance gate for chat retrieval. A source must contain tenancy-specific vocabulary and meaningful overlap with the user's account. Generic TRAI/RBI references to deposits are rejected.
- Preserved jurisdiction isolation: a confirmed state permits central/national plus matching-state records; an unknown state remains national-only.
- Added deterministic triage reconciliation so a model cannot downgrade a prompt/urgent rule flag.
- Added per-turn retrieval, model-generation and total timings.
- Kept raw model output, source records, triage and timings in the developer/test-bench expander and JSON downloads.
- Preserved factual document drafting in chat only when the current user message explicitly requests a named document; unsolicited model drafts are discarded.

## Validation and limitations

Offline regression tests use synthetic records and mocked model responses. They cover:
- tenancy source retrieval versus irrelevant TRAI/RBI deposit matches;
- state-specific source exclusion when jurisdiction is unknown;
- one-question conversation output;
- recent-turn continuity;
- triage priority preservation;
- no-source caveat and timing fields;
- the pre-existing draft and jurisdiction safeguards.

The tests do not establish live Gemini latency, legal correctness, complete national/state coverage, or production readiness. The tenancy filter is deliberately conservative and can miss a relevant provision written in different terminology. General semantic retrieval, reranking and citation-entailment verification remain future work.

**Latency claims:** the application now records the three relevant timings. No numerical speed-up is claimed until the same prompts are benchmarked on the user's local database and configured live provider before and after the change.

**Privacy:** chat history is session-scoped, but raw turn JSON is written to the local `raw_outputs/` folder. Those files can contain sensitive case details and should be protected and deleted when no longer required.
