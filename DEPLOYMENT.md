# Deployment guide — NYAYA MITRA

## Current deployment target

The app is a Streamlit application. Streamlit Community Cloud is the simplest first hosting target. This repository change prepares the app for that platform, but an owner of the GitHub/Streamlit accounts must complete the final deployment and add the provider secret.

## Deploy on Streamlit Community Cloud

1. Push/merge the reviewed application branch into the repository branch you intend to deploy.
2. Sign in to Streamlit Community Cloud with the GitHub account that can access `rtcpcx/nyaya_mitra`.
3. Create an app:
   - Repository: `rtcpcx/nyaya_mitra`
   - Branch: the reviewed deployment branch (normally `main` after merge)
   - Main file path: `app.py`
4. Open the app's **Settings → Secrets** and add the values below. Use the provider's real API key only in Streamlit Secrets; never commit it to Git.

```toml
LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
LLM_API_KEY = "YOUR_PROVIDER_API_KEY"
LLM_MODEL = "YOUR_SUPPORTED_MODEL_ID"
LLM_CHAT_TIMEOUT_SECONDS = "60"
LLM_CHAT_MAX_RETRIES = "0"
SAVE_RAW_OUTPUTS = "false"
```

The app reads local `.env` values first and falls back to Streamlit Secrets. The provider key is not required to boot the interface, but AI-generated chat responses will be disabled without it.

## Legal database setup

The application can download the prebuilt SQLite FTS5 index from a private Hugging Face dataset repository at startup. This avoids rebuilding the index on Streamlit Community Cloud.

1. Create a **private dataset repository** on Hugging Face and upload the prebuilt file as `nyaya_mitra.sqlite3` at the repository root.
2. Create a read-only Hugging Face access token that can read that private repository.
3. In Streamlit Community Cloud, open **App → Settings → Secrets** and add:

```toml
HF_DATABASE_REPO_ID = "YOUR_HF_USERNAME/nyaya-mitra-db"
HF_TOKEN = "YOUR_READ_ONLY_HUGGING_FACE_TOKEN"
```

4. Restart/redeploy the app. On startup, `app.py` checks `DATABASE_PATH`; if the file is absent and the Hugging Face repository secret is configured, it downloads the database into the configured data directory. If the database is already present in the runtime, it is reused.

The Hugging Face token must remain in Streamlit Secrets and must never be committed to Git. The SQLite file is intentionally excluded from Git by `.gitignore`.

Streamlit Community Cloud's local filesystem is not guaranteed to persist across restarts. A cold start may therefore download the full database again and take several minutes. Confirm that the app's available disk space and resource limits can accommodate the database. The download only transfers the prebuilt index; it does not rebuild it.

If the Hugging Face secrets are absent, the app continues to start without the database and displays its existing database-not-indexed status. Do not use the sidebar's **Download / update legal database** action on the hosted app unless you specifically intend to download all source datasets and rebuild the index there.

## Privacy and production cautions

- Raw turn JSON files are disabled by default. Keep `SAVE_RAW_OUTPUTS = "false"` in hosted environments.
- Chat history is session memory, not durable case storage. Users should download their own export if they need a copy.
- Do not promise confidentiality, privilege, lawyer-client protection, or permanent deletion.
- Do not collect full bank/card numbers, passwords, OTPs or unnecessary identity documents.
- This is a legal-information prototype, not a law firm. Keep advocate-review warnings and emergency/deadline escalation visible.
- Before public launch, test with synthetic cases, verify source relevance and current official law, check rate limits/costs, and review the hosting provider's data retention and privacy terms.

## Local run

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

For local use, put provider settings in the ignored `.env` file. Never paste the API key into source code or commit it.
