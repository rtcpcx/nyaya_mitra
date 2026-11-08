# Nyaya Mitra architecture v2

```text
User chat turn + prior session conversation + location/language
            |
            v
Deterministic keyword triage (transparent, limited)
            |
            v
SQLite FTS5 retrieval + jurisdiction isolation
            |
            v
Conservative topic relevance gate
  - tenancy vocabulary expansion
  - reject generic deposit matches without tenancy context
            |
            v
Compact relevant passages + provenance + triage
            |
            v
Short conversational JSON response
            |
            v
Pydantic validation + one-question normalisation
            |
            v
Chat UI + per-turn timings + raw developer/test output
```

## Design choices

1. **Conversation-first interface:** the primary flow is a Streamlit chat, not a one-shot intake form. Session State holds the conversation for the active browser session; it is not durable storage. Each model turn receives recent context and asks at most one follow-up question. The legacy structured-analysis service remains available for evaluation and compatibility.
2. **Separate user and developer outputs:** ordinary users see a concise reply, one follow-up question, relevant sources and safety warnings. Raw model JSON, triage and latency diagnostics are exposed in a developer/test-bench expander and downloadable per-turn artifacts.
3. **Measured latency:** the conversation service records retrieval, model-generation and total elapsed milliseconds independently. This makes the slow stage observable; no speed improvement is claimed without measurements from the user's live provider and local database.
4. **Relevance-gated retrieval:** the conversation path uses an opt-in strict relevance filter. Tenancy queries add common tenancy synonyms to FTS5 recall, then require tenancy-specific vocabulary in the source and meaningful overlap with the user's query. Generic references to deposits in telecom or banking documents are not accepted as tenancy evidence. Manual source exploration keeps its broad search behaviour.

1. **Nationwide data model:** the database indexes all available central/state/UT legislation and regulator Parquet files. The user's state/city is an input to analysis, not a hard-coded Assam default.
2. **Separate Constitution source type:** Constitution passages are searchable but retain a distinct source type and explicit third-party transcription warning.
3. **SQLite FTS5 instead of embeddings for the MVP:** the earlier Chroma + sentence-transformers approach required downloading an embedding model and vectorizing a very large corpus. FTS5 provides a smaller, reproducible, local lexical baseline and exact title/section keyword search. Semantic retrieval and reranking remain future work.
4. **No automatic judgment download:** the judgment corpus is large; user opt-in is required.
5. **No Groq key required for ingestion/search:** setup and database search work independently. AI analysis activates after `LLM_API_KEY` is configured.
6. **No unsupported legal claims:** source-specific details must be grounded in retrieved passages. Dataset status does not equal legal validation.

## Data ingestion

`src/dataset_manager.py` downloads the selected Hugging Face files. `src/database.py` streams Parquet rows in batches and JSONL records into SQLite FTS5. The index is rebuilt on each explicit index operation; source files remain untouched. A manifest records repository IDs, patterns and timestamp.

## Known engineering limitations

- FTS5 is lexical, not semantic; query expansion, hybrid retrieval, reranking and citation entailment checks are not implemented.
- Rebuilding the full index is a long, single-process operation; no incremental update or resume checkpoint at the row level.
- Judgment chunks are not reconstructed into complete judgments.
- No authentication, encryption-at-rest, tenant isolation, audit-grade retention controls or production deployment safeguards.
- Triage is keyword-based and is not a safety classifier.
