# Nyaya Mitra architecture v2

```text
User story + location + language
            |
            v
Deterministic keyword triage (transparent, limited)
            |
            v
SQLite FTS5 search over local legal corpus
   |                    |
   |                    +--> Constitution articles/schedules/Preamble
   +--> Central/state/UT legislation and regulator provisions
            |
            v
Retrieved passages + provenance + status metadata
            |
            v
Groq OpenAI-compatible chat completion (key required)
            |
            v
Pydantic response validation + raw JSON storage
```

## Design choices

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
