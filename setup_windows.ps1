$ErrorActionPreference = "Stop"

Write-Host "=== Nyaya Mitra Windows setup ===" -ForegroundColor Cyan
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.11 from https://www.python.org/downloads/windows/ and enable the Python Launcher."
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    py -3.11 -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

hf auth whoami 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Hugging Face login is required for the Open India Law dataset. Paste your read token at the hidden prompt." -ForegroundColor Yellow
    hf auth login
}

python setup_database.py
Write-Host "Database setup finished. Start the app with: streamlit run app.py" -ForegroundColor Green
