import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def _path_env(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default))
    return value if value.is_absolute() else (ROOT / value).resolve()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b").strip()
OPEN_INDIA_LAW_DIR = _path_env("OPEN_INDIA_LAW_DIR", "./data/open_india_law")
CONSTITUTION_DIR = _path_env("CONSTITUTION_DIR", "./data/constitution")
DATABASE_PATH = _path_env("DATABASE_PATH", "./data/nyaya_mitra.sqlite3")
TOP_K = max(1, min(20, int(os.getenv("TOP_K", "8"))))
