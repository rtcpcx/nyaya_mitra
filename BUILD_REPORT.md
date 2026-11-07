# Build and verification report

Build target: Nyaya Mitra generalist nationwide prototype, 8 November 2026.

## Checks completed

- `python -m compileall -q .` — passed.
- `pytest -q` — **11 passed**.
- SQLite FTS5 smoke test — created a temporary index, inserted a Constitution Article 21 fixture, and successfully retrieved it by `Article 21 personal liberty`.
- `python -m src.dataset_manager status` — runs and correctly reports that the packaged project has no pre-downloaded database yet.
- Hugging Face Hub installed in the build environment; inspected the current `snapshot_download` and `hf_hub_download` signatures and confirmed the used arguments are supported.

## Not verified in this build environment

- Live Hugging Face download and access permissions: the build environment has no outbound network access. The user's prior local download proves they have authenticated and downloaded the Assam Parquet file, but the new all-jurisdiction downloader still needs to be run on their Windows machine.
- Reading a real Parquet file: PyArrow is declared in `requirements.txt`, but it could not be installed in this network-isolated build environment. Automated database tests mock the Parquet row iterator and test the downstream SQLite indexing/search logic.
- Streamlit runtime: Streamlit was not installed in this build environment, so the app was syntax-compiled but not launched interactively.
- Live Groq completion: no API key was provided, intentionally. The LLM path has not been live-tested. It is configured for `openai/gpt-oss-120b` based on Groq's current production model documentation; confirm availability and pricing in your Groq console before use.

## Important interpretation

The 11 passing tests establish that the tested local logic and fixtures pass. They do not establish legal accuracy, completeness of the database, currentness of every provision, or live provider connectivity. Run the first full setup on the target Windows machine, inspect the download manifest and corpus counts, then run the test scenarios with a real Groq key and preserve the raw JSON outputs.
