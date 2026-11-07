$ErrorActionPreference = "Stop"
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    throw "Virtual environment not found. Run .\setup_windows.ps1 first."
}
. .\.venv\Scripts\Activate.ps1
streamlit run app.py
