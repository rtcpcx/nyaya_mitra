# Data sources, scope and verification

## 1. Open India Law — primary legislation/regulation corpus

Repository: https://huggingface.co/datasets/vaquill/open-india-law
Publisher repository: https://github.com/Vaquill-AI/open-india-law
License shown on the dataset card: CC BY 4.0 (attribution required).

The downloader selects all files matching:

- `in_*_legislation.parquet` — central, state and Union Territory legislation
- `in_*_regulations.parquet` — published regulator/rules material

The dataset card describes 22,265 enactments and 1,098,577 legislation/regulatory provisions in its published snapshot. It states that legislation is sourced from India Code and each provision has a source URL. It also explicitly says district and trial court decisions are not included. The dataset is a point-in-time snapshot; its own card warns that it can become stale.

### Why Assam is not the default

Assam was the first downloaded test file because the developer is testing the pipeline from Assam. It is only one state file. The application now downloads all available state/UT legislation files plus central laws and regulator files. Retrieval does not assume the user is in Assam; the user must supply the relevant state/city and the model must not infer jurisdiction from which record happened to rank highest.

### Status metadata

The database preserves `act_status`, `in_force`, `year`, `amendment_count` when present, jurisdiction/state, legal subject, source publisher and source URL. These are dataset fields, not an independent legal verification. In particular, `in_force=True` is not a guarantee that a provision applies to the facts, has commenced in the relevant territory, or has not been changed by a later Gazette notification or state amendment.

## 2. Constitution of India — separate structured collection

Repository: https://huggingface.co/datasets/GSMS-B/constitution-of-india-json
Official verification destination: https://www.legislative.gov.in/documents
License shown on the dataset card: CC BY 4.0.

The project downloads `articles.jsonl`, `schedules.jsonl`, `appendices.jsonl` and `CONSTITUTION_DATASET.json`. It indexes articles, schedules, appendices and the Preamble separately under `source_type=constitution`.

**Important provenance qualification:** this is a third-party structured transcription. The dataset card describes its text as incorporating amendments through the 106th Amendment Act, 2023 and identifies the Legislative Department as the official source. The project does not independently certify the transcription. For a consequential constitutional answer, check the current official publication, amendments, commencement and relevant Supreme Court interpretation.

## 3. Court judgments are optional

Open India Law publishes Supreme Court and High Court judgment chunks. The combined snapshot is tens of GB. It is intentionally excluded from the default download. Run:

```powershell
python -m src.dataset_manager download --include-judgments
python -m src.dataset_manager index
```

The source documentation says judgment records are chunks and may need grouping by `case_id` and ordering by `chunk_index` to reconstruct full judgments. This prototype only surfaces matching chunks. It is not a complete citator and must not present a chunk as a complete judgment.

## 4. Retrieval and source display

- SQLite FTS5 performs lexical retrieval over title, section number and text.
- Search result metadata is displayed with jurisdiction, status, year, publisher and URL.
- The LLM is told to cite only passages actually retrieved.
- A retrieved source is a research lead, not proof of current legal effect or applicability.
- If no passage supports a specific proposition, the assistant must say that the legal detail is not verified in the retrieved material.

## 5. Scope limitations

- No district/trial court decisions in the default corpus.
- No automatic current-law web lookup or Gazette monitoring.
- No complete amendment/commencement validation pipeline.
- No OCR for scanned custom PDFs.
- No case-status or cause-list access.
- No legal deadline calculator.
- The lexical index can miss relevant documents and is not semantic legal reasoning.
- The Constitution structured dataset is third-party transcribed text, not an official machine-readable API.

## 6. Attribution

Retain attribution to Vaquill AI and GSMS-B as required by their stated dataset licences, and retain official source URLs. Review licences and terms before commercial distribution or redistribution of the downloaded corpus.
