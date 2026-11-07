from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from huggingface_hub import snapshot_download, hf_hub_download
from src.config import OPEN_INDIA_LAW_DIR, CONSTITUTION_DIR, DATABASE_PATH
from src.database import build_index, database_stats

OPEN_REPO = "vaquill/open-india-law"
CONSTITUTION_REPO = "GSMS-B/constitution-of-india-json"
LEGAL_PATTERNS = ["in_*_legislation.parquet", "in_*_regulations.parquet"]
JUDGMENT_PATTERNS = ["in_*_judgments.parquet"]
CONSTITUTION_FILES = ["articles.jsonl", "schedules.jsonl", "appendices.jsonl", "CONSTITUTION_DATASET.json"]


def download_datasets(include_judgments: bool = False) -> dict:
    OPEN_INDIA_LAW_DIR.mkdir(parents=True, exist_ok=True)
    CONSTITUTION_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    patterns = LEGAL_PATTERNS + (JUDGMENT_PATTERNS if include_judgments else [])
    print(f"Downloading Open India Law files: {patterns}", flush=True)
    try:
        open_path = snapshot_download(
            repo_id=OPEN_REPO, repo_type="dataset", allow_patterns=patterns,
            local_dir=str(OPEN_INDIA_LAW_DIR)
        )
    except Exception as exc:
        raise RuntimeError(
            "Open India Law download failed. Check internet, run `hf auth login`, "
            "and confirm your Hugging Face account has read access to the dataset. "
            "The download is resumable. Original error: " + str(exc)
        ) from exc

    print("Downloading structured Constitution files...", flush=True)
    downloaded = []
    for filename in CONSTITUTION_FILES:
        try:
            local = hf_hub_download(
                repo_id=CONSTITUTION_REPO, repo_type="dataset", filename=filename,
                local_dir=str(CONSTITUTION_DIR)
            )
            downloaded.append(str(local))
        except Exception as exc:
            raise RuntimeError(f"Could not download Constitution file {filename}: {exc}") from exc

    manifest = {
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "open_india_law_repo": OPEN_REPO,
        "open_india_law_patterns": patterns,
        "constitution_repo": CONSTITUTION_REPO,
        "constitution_files": CONSTITUTION_FILES,
        "judgments_included": bool(include_judgments),
        "open_india_law_local_path": str(open_path),
        "constitution_local_files": downloaded,
        "notes": "Point-in-time third-party datasets. Verify operative law against official sources."
    }
    (DATABASE_PATH.parent / "download_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def setup_all(include_judgments: bool = False, progress: Callable[[str], None] | None = None) -> dict:
    manifest = download_datasets(include_judgments=include_judgments)
    if progress: progress("Downloads complete. Building local SQLite FTS5 index...")
    stats = build_index(OPEN_INDIA_LAW_DIR, CONSTITUTION_DIR, DATABASE_PATH, progress=progress)
    manifest["index_stats"] = stats
    (DATABASE_PATH.parent / "download_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"manifest": manifest, "stats": stats}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Download and index Nyaya Mitra legal datasets")
    sub = parser.add_subparsers(dest="command", required=True)
    p_setup = sub.add_parser("setup", help="Download nationwide legislation/regulations + Constitution and index them")
    p_setup.add_argument("--include-judgments", action="store_true", help="Also download all judgment Parquet files (tens of GB)")
    p_download = sub.add_parser("download", help="Download datasets without indexing")
    p_download.add_argument("--include-judgments", action="store_true")
    sub.add_parser("index", help="Rebuild the local index from already downloaded files")
    sub.add_parser("status", help="Show local database and downloaded-file status")
    args = parser.parse_args(argv)
    try:
        if args.command == "setup":
            result = setup_all(args.include_judgments, progress=lambda msg: print(msg, flush=True))
            print(json.dumps(result["stats"], indent=2))
        elif args.command == "download":
            print(json.dumps(download_datasets(args.include_judgments), indent=2))
        elif args.command == "index":
            print(json.dumps(build_index(OPEN_INDIA_LAW_DIR, CONSTITUTION_DIR, DATABASE_PATH, progress=lambda m: print(m, flush=True)), indent=2))
        elif args.command == "status":
            print(json.dumps(database_stats(DATABASE_PATH, OPEN_INDIA_LAW_DIR, CONSTITUTION_DIR), indent=2))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
