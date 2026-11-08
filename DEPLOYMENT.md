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

After the app starts, use **Download / update legal database** in the sidebar. The first download/indexing can take time and may exceed a free hosting instance's resource limits. If it fails, build the database in a controlled environment and arrange a supported persistent database/data volume before production use. Do not assume the local SQLite index survives a Streamlit Community Cloud restart.

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
