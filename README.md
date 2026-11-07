# Nyaya Mitra — General-purpose Indian Legal Information Assistant

A Windows-friendly prototype with a real Groq LLM integration (API key required only for AI analysis), a nationwide legal corpus downloader, a local SQLite full-text search index, constitutional text retrieval, cautious issue-spotting, and raw output capture.

> **Not a lawyer / not legal advice.** This prototype does not determine legal rights, authenticate evidence, guarantee outcomes, or replace an advocate. The legal database is a point-in-time third-party compilation. Verify important provisions against the linked official source and current Gazette/notifications before relying on them.

## What this version changes

- Nationwide rather than Assam-only: downloads all available `in_*_legislation.parquet` and `in_*_regulations.parquet` files from Open India Law.
- Constitution: downloads structured articles, schedules and appendices from `GSMS-B/constitution-of-india-json` and indexes them as a distinct source category.
- No 50+ GB surprise: court judgments are **not** downloaded by default. They are optional because the published judgment chunks are very large. See `docs/DATA_SOURCES_AND_COVERAGE.md`.
- SQLite FTS5 keyword/full-text retrieval replaces the old Chroma + sentence-transformer path. This avoids downloading a second multi-hundred-MB embedding model and avoids embedding over a million legal provisions just to get started. Exact section/title matches and lexical ranking are supported.
- Groq default model updated to `openai/gpt-oss-120b`; the old `llama-3.3-70b-versatile` was deprecated for Developer/free tiers on 16 August 2026. Model IDs can change; check Groq's current model list.
- App remains usable for database search without a Groq key. AI case analysis activates when you add your key.
- Safer source handling, explicit jurisdiction, status and provenance in retrieved records, JSON validation, better error messages and tests.

## 1. Requirements

- Windows 10/11, PowerShell
- Python 3.11 (recommended)
- Internet for initial dataset downloads
- Hugging Face account/token with read access to `vaquill/open-india-law`
- Groq API key for actual AI analysis (you said you have not obtained it yet; that is okay)
- Disk space: legislation + regulator files are much smaller than judgments, but allow several GB for downloaded files and the SQLite index. Actual size varies with dataset snapshot.

## 2. Install (PowerShell)

Extract this ZIP to a short path such as `C:\nyaya_mitra` (avoid OneDrive-synced folders for the first run).

```powershell
cd C:\nyaya_mitra
.\setup_windows.ps1
```

The script creates the Python 3.11 virtual environment, installs requirements, checks Hugging Face login (and prompts if needed), then downloads and indexes the default legal corpus. If PowerShell blocks scripts, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal and retry.

If you prefer manual installation, use: `py -3.11 -m venv .venv`, activate `.venv`, then `python -m pip install --upgrade pip` and `pip install -r requirements.txt`.

If PowerShell blocks activation, run this once in that terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 3. Hugging Face authentication (for Open India Law)

You already successfully logged in in your earlier `C:\nyaya_research` environment. Hugging Face credentials are normally stored per Windows user, not inside this project. If this new environment does not recognise your login, run:

```powershell
hf auth login
```

Paste a **read** token privately at the hidden prompt. Never paste the token into ChatGPT, `.env`, source code, or GitHub. If the dataset page asks you to accept access conditions, do that in your browser first. The Constitution dataset is public; the Open India Law files may require your authenticated account.

## 4. Download and index the databases

If you used `setup_windows.ps1`, the download and indexing have already run. For a manual install, or whenever you want to refresh/rebuild the local corpus later, run from the project root:

```powershell
python setup_database.py
```

This performs the initial setup:

1. Downloads all published central/state/UT legislation Parquet files from Open India Law (`in_*_legislation.parquet`).
2. Downloads all published regulator/rules Parquet files (`in_*_regulations.parquet`).
3. Downloads Constitution `articles.jsonl`, `schedules.jsonl`, `appendices.jsonl`, and `CONSTITUTION_DATASET.json` (used to capture the Preamble as well).
4. Builds `data/nyaya_mitra.sqlite3`, a local searchable index.
5. Writes `data/download_manifest.json` with source repositories and timestamps.

**Do not run this from a folder containing your API key in a public/shared location.** Dataset files and index stay local and are excluded from Git by `.gitignore`.

The process can take time, especially indexing a large nationwide dataset. It prints progress per Parquet batch. It can be rerun safely; downloaded files are cached and the index is rebuilt from the files on disk.

### Correct folder structure

The downloader creates this structure automatically; do not manually rename files:

```text
nyaya_mitra/
├── app.py
├── setup_database.py
├── requirements.txt
├── .env                         # create from .env.example
├── data/
│   ├── open_india_law/
│   │   ├── in_central_legislation.parquet
│   │   ├── in_assam_legislation.parquet
│   │   ├── in_maharashtra_legislation.parquet
│   │   ├── ... all available state/UT legislation files
│   │   └── in_*_regulations.parquet
│   ├── constitution/
│   │   ├── articles.jsonl
│   │   ├── schedules.jsonl
│   │   └── appendices.jsonl
│   ├── nyaya_mitra.sqlite3
│   └── download_manifest.json
├── knowledge_base/custom/        # optional additional PDFs/TXT/MD
├── raw_outputs/                  # generated analyses (created on use)
└── logs/
```

## 5. Add Groq API key later

You can finish the database setup before you have a Groq key. When you obtain it:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set:

```dotenv
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=your_actual_groq_key_here
LLM_MODEL=openai/gpt-oss-120b
```

Save `.env`. Do not commit it or share the key. The previous model `llama-3.3-70b-versatile` was deprecated for Developer/free usage in August 2026; the default has been changed to Groq's recommended GPT-OSS 120B replacement. If Groq's current console lists another preferred model, change `LLM_MODEL` accordingly.

## 6. Run Nyaya Mitra

```powershell
.\run_nyaya.ps1
```

Or run `streamlit run app.py` directly inside the activated virtual environment.

The app opens in your browser. It has:
- Nationwide legal source search (works without Groq key)
- Case-story intake and triage
- LLM analysis once the API key is configured
- Retrieved-source display with source URLs, jurisdiction, status and provenance
- Downloadable raw JSON output

If you skipped database setup, use **Download and index nationwide legal database** in the sidebar.

## 7. Optional: add judgments (large download)

Open India Law publishes Supreme Court and High Court judgment chunks, but the combined snapshot is tens of GB. They are intentionally excluded from the default setup so the first install is manageable. Once legislation search works, you can download judgment Parquet files with:

```powershell
python -m src.dataset_manager download --include-judgments
```

Then rebuild the index:

```powershell
python -m src.dataset_manager index
```

Only do this if you have sufficient disk space and time. Judgment records are chunks, not necessarily one row per complete case; the dataset documentation says to group by `case_id` and order by `chunk_index` when reconstructing judgments. This prototype treats retrieved chunks as research passages, not as a complete case-law citator.

## 8. Tests and diagnostics

```powershell
python -m compileall -q .
pytest -q
python -m src.dataset_manager status
```

The included offline test suite currently passes **11 tests** in the build environment. It uses synthetic local fixtures for the Parquet ingestion path; it does not prove that a live Hugging Face download or live Groq completion will succeed on your machine. Those need to be checked during your first setup and after you add the API key.

To test the Groq connection after setting the key:

```powershell
python -m src.llm --test
```

This sends a minimal test request and incurs any applicable provider usage. No live Groq request is made when the key is missing.

## 9. Legal-source policy and limitations

- Open India Law is the primary nationwide source for central/state/UT legislation and regulator material in this prototype. Its dataset card says legislation is sourced from India Code and provides per-provision source URLs. It is a snapshot and can become stale.
- The Constitution JSONL is a third-party structured transcription. It is kept separate and must be checked against the Legislative Department's official Constitution publication for consequential questions.
- `in_force` and `act_status` are dataset metadata, not a legal opinion or guarantee of commencement/current applicability. State-specific amendments, rules, notifications and commencement dates may matter.
- The default download excludes judgments. No claim-law answer should be treated as a verified precedent search until judgment data is added and reviewed.
- Search is SQLite FTS5 lexical retrieval, not a legal expert system. It may miss relevant passages and may rank a superficially similar section.
- No OCR, document authentication, case-status integration, deadline computation, user accounts, encryption-at-rest, retention controls or production deployment hardening. Hindi/Assamese and other language output has not yet been quality-validated.
- The first-pass risk triage uses transparent keywords and can miss urgent facts. If in doubt, consult a lawyer.
- Never cite a statute, section, case, deadline or procedure unless the retrieved material supports it. Even then, show the source and ask the user to verify current official text.
- Obtain an advocate's review before sending notices, complaints, affidavits, contracts, wills or court filings.

## 10. Dataset attribution

Open India Law dataset: Vaquill AI, CC BY 4.0 as stated on its dataset card. Preserve attribution and source links. Constitution structured dataset: GSMS-B, CC BY 4.0 as stated on its dataset card; the Constitution itself is a Government of India legal text. Review the dataset licences and any applicable provider terms before commercial distribution.

See:
- `docs/DATA_SOURCES_AND_COVERAGE.md`
- `docs/ARCHITECTURE.md`
- `docs/REPOSITORY_REVIEW.md` (review of the five reference repositories previously supplied)
