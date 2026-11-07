# Source-level review of the five supplied GitHub repositories

This review is based on the default-branch README and the named Python implementation files fetched from GitHub on 8 November 2026. Where a path was not available or the repository did not expose a requested file, that is stated rather than inferred. Repository README claims and reported benchmark scores are author-reported, not independently reproduced here.

## 1. JatinPhogat / Chatbot-for-Law-Queries-using-Gen-AI (NyaySetu)

Files inspected: `README.md`, `requirements.txt`, `app.py`, `nyaysetu.py`, `create_embeddings.py`.

**What the code does**
- Streamlit chat UI with session chat history.
- Loads `all-MiniLM-L6-v2` embeddings, opens a persistent Chroma vector store, retrieves top 4 similar chunks.
- Uses LangChain `ConversationalRetrievalChain` and Groq `llama-3.3-70b-versatile`.
- Ingestion reads every PDF in `data/`, splits with 1,000-character chunks and 200-character overlap, then stores chunks in Chroma.

**Good ideas adopted**
- Simple Streamlit UX.
- Persistent local vector store.
- A replaceable hosted LLM and local embedding model.
- Clear setup and document-ingestion separation.

**Problems / caveats**
- Prompt says both “based on context” and “legal knowledge”; this can let the model fill gaps from its own memory. Our prompt is stricter: specific legal propositions must be supported by retrieved text.
- Similarity-only retrieval and generic fixed-size chunks can miss exact section identifiers and document structure.
- The displayed answer is plain text; no explicit validation that a cited source supports a particular claim.
- README's 2–3 second latency and 2,300+ chunks are project claims, not verified by this review.
- `create_embeddings.py` calls ingestion at import time; importing it can unexpectedly rebuild the index.
- The listed requirements include Google GenAI and Groq integrations even though the inspected core path uses Groq.

## 2. Aahana-0204 / LAW-AI

Files inspected: `README.md`, `backend/app/services/rag_service.py`, `corpus_search.py`, `domain_classifier.py`, `llm_service.py`, `doc_generator_service.py`. The repository README describes React/Vite + Flask and a broader backend layout; the specific top-level `requirements.txt` and `app.py` paths were not present.

**What the code does**
- Domain classification is keyword-count based.
- Corpus search performs direct section/article lookup and then a hand-written BM25-like ranking over bundled Python corpus modules.
- The inspected `_bm25_score` computes an IDF-like term using term frequency within the current document, not document frequency across the corpus; therefore it is not textbook BM25.
- LLM service supports a deterministic template backend, Ollama, Groq, Gemini and Hugging Face API. It retries and falls back to the template engine.
- Document generator uses static string templates and field substitution rather than an LLM.

**Good ideas adopted**
- Fast exact section lookup before semantic similarity.
- Domain-aware intake.
- A model-independent provider adapter.
- Template-based drafting can be safer than unconstrained generation when the template itself is reviewed.

**Problems / caveats**
- A keyword classifier can misclassify stories that do not contain its expected vocabulary or mention multiple domains.
- A direct section match is only as correct/current as the corpus metadata and text; it is not inherently “100% accurate”.
- The RAG prompt's sources are constructed from local corpus hits, but the code path does not implement a robust claim-to-source entailment check.
- The static rental template includes specific default terms (e.g. deposit and payment conditions); such terms must not be presented as universal Indian law or silently inserted into a real agreement.
- The fallback template engine is not a generative model. The README's “no LLM” and Ollama/backend descriptions represent multiple modes, not one uniform model configuration.

## 3. niyam-sahaai / niyam-sahaai

Files inspected: `requirements.txt`, `app.py`. The README fetch returned 404 for the expected path on the connected default branch, so no README-based feature claims are relied on.

**What the code does**
- Streamlit interface using LangChain `OpenAI` and `OpenAIEmbeddings`.
- Opens an existing Chroma directory and uses similarity retrieval.
- Builds a history-aware retriever and conversational RAG chain.
- Maintains chat messages in Streamlit session state.

**Good ideas adopted**
- Conversation-aware query reformulation can help follow-up questions.
- Keep the LLM, embeddings and vector store as separate components.

**Problems / caveats visible in inspected code**
- The code calls `ChatMessageHistory()` in `get_session_history` but the inspected imports do not import that class. That function would fail if used.
- A `conversational_rag_chain` is constructed, but `chat()` invokes `rag_chain` directly; the constructed history wrapper is not used in that call path.
- Both `OpenAI` and `OpenAIEmbeddings` require valid API configuration, while the vector store is opened from a pre-existing local folder.
- The QA prompt tells the model to use context and say “I don't know”, but does not force numbered citations or validate support.
- This is a compact prototype, not a comprehensive legal intake/escalation system.

## 4. sanskar-94 / legal-research-assistant (Nyaya)

Files inspected: `README.md`, `requirements.txt`, `src/pipeline.py`, `src/retrieval/hybrid_search.py`, `config/prompts.py` (the repository README also describes the remaining pipeline modules).

**What the code does**
- Query classification into section lookup, case lookup, conceptual and mixed.
- Semantic Chroma retrieval plus exact identifier retrieval for section/article numbers, case names and AIR/SCC references.
- Weighted Reciprocal Rank Fusion combines the two ranked lists.
- Authority-aware reranking is described in the README: statutes/Constitution are ranked above judgments; judgment authority incorporates court level, recency and citation signals.
- Prompt requires `[SOURCE_N]` references; response parser checks source IDs; a confidence score uses retrieval quality, distinct citations, authority and use of retrieved passages.
- The pipeline maps some IPC/BNS section pairs before retrieval.
- README describes 112,555 chunks, 300 tests and a 50-question evaluation suite.

**Good ideas adopted**
- Never let the LLM be the source of legal knowledge.
- Exact legal identifier retrieval alongside semantic retrieval.
- Source IDs and citation validation.
- Explicit uncertainty and evaluation.
- Legal-aware chunking by statute section, Constitution article and judgment paragraph.

**Limitations from the project's own README**
- The embedding model is general-purpose; InLegalBERT was suggested but not tested.
- Many dataset items lack case metadata.
- IPC/BNS mapping covers 63 common sections, not the whole code.
- Hallucination checks are pattern-based and do not detect wrong claims attributed to a real source.
- The local Nyaya-Gen model was fine-tuned for only 50 effective updates and was not trained to combine/compare multiple sources.
- Reported metrics are author-reported; e.g. the documented Run A response rate was 0.30. They should not be treated as a guarantee.

**Most influential design reference**: this project provides the strongest architecture ideas for a legal research assistant, but its full 112k-chunk corpus and evaluation system are much larger than this prototype.

## 5. sandeepsahu1808 / Legal-Document-Retrieval-Virtual-Legal-Assistant

Files inspected: `README.md`, `legal-rag/rag/pipeline.py`, `legal-rag/rag/retriever.py`, `legal-rag/rag/generator.py`, `legal-rag/assistant/legal_assistant.py`.

**What the code does**
- FastAPI backend and Next.js frontend according to README.
- Embedding search over pgvector, a cross-encoder reranker, Gemini answer generation, and a separate personal legal assistant path.
- Classifies problems into criminal, civil, property, consumer, labour and family using keywords.
- The retriever contains a BM25 implementation, but the inspected `retrieve()` path runs semantic retrieval and reranking; it does not call `_bm25_search()`. Query expansion is optional and defaults to `False`.
- Confidence is based on average retrieval scores and simple no-information phrases.
- README reports 164,090 chunks and evaluation results, including 36.7% Precision@5 / Recall@10 and MRR 0.216. These are self-reported and reveal that retrieval still has substantial room to improve.

**Good ideas adopted**
- Separate issue classification, retrieval, generation and UI.
- Cross-encoder reranking is a worthwhile future upgrade.
- Track retrieval metrics rather than assuming a large corpus means good answers.
- Keep a dedicated “personal legal assistant” intake path.

**Problems / caveats**
- The README's hybrid-search claim is not reflected in the inspected default `retrieve()` path.
- Confidence thresholds on raw model scores are not calibrated legal confidence.
- The system's source names are surfaced, but the inspected generator prompt asks for citations without a rigorous claim-by-claim source validator.

## Cross-project conclusion

The most defensible design is not “train a new legal chatbot from scratch”. It is:
- A capable general LLM for language understanding and drafting.
- A traceable legal-source retrieval layer.
- Exact section/case identifier search plus semantic retrieval.
- Source-aware output and strict refusal to invent citations.
- A separate escalation layer that can recommend a human advocate.
- A regression/evaluation set that includes false-positive and false-negative risk scenarios.

This ZIP implements the core prototype and deliberately leaves larger production features (hybrid BM25 + dense search, reranking, verified legal corpus, claim-entailment checking, OCR, auth/privacy controls) as explicit next steps rather than pretending they are complete.
