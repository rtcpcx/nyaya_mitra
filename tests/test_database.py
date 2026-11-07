import json
import sqlite3
from pathlib import Path
from src.database import build_index, search_sources


def test_build_and_search_nationwide_and_constitution(tmp_path: Path, monkeypatch):
    legal = tmp_path / "legal"; legal.mkdir()
    constitution = tmp_path / "constitution"; constitution.mkdir()
    (legal / "in_central_legislation.parquet").write_bytes(b"fixture placeholder; rows are supplied by monkeypatch")
    rows = [
        {"act_id":"A1","chunk_id":"A1_s2","title":"Consumer Protection Act","section_number":"2","section_title":"Definitions","text":"Consumer complaint and refund of defective goods","jurisdiction":"central","state":"central","act_status":"in_force","in_force":True,"year":2019.0,"source_url":"https://example.org/consumer","source_publisher":"India Code","legal_subject":["consumer_law"]},
        {"act_id":"A2","chunk_id":"A2_s103","title":"Bharatiya Nyaya Sanhita","section_number":"103","section_title":"Punishment for murder","text":"Punishment for murder and criminal offence","jurisdiction":"central","state":"central","act_status":"in_force","in_force":True,"year":2023.0,"source_url":"https://example.org/bns","source_publisher":"India Code","legal_subject":["criminal_law"]}
    ]
    monkeypatch.setattr("src.database._parquet_records", lambda path: iter(rows))
    (constitution / "articles.jsonl").write_text(json.dumps({"article_number":"21","article_title":"Protection of life and personal liberty","part_number":"III","text":"No person shall be deprived of life or personal liberty except according to procedure established by law."})+"\n", encoding="utf-8")
    db = tmp_path / "test.sqlite3"
    stats = build_index(legal, constitution, db)
    assert stats["indexed_rows"] == 3
    consumer = search_sources("consumer refund defective goods", db, 5)
    assert consumer and consumer[0]["title"] == "Consumer Protection Act"
    art = search_sources("Article 21 personal liberty", db, 5)
    assert any(x["source_type"] == "constitution" for x in art)


def test_no_files_raises_clear_error(tmp_path: Path):
    (tmp_path/"legal").mkdir(); (tmp_path/"constitution").mkdir()
    try:
        build_index(tmp_path/"legal", tmp_path/"constitution", tmp_path/"db.sqlite3")
    except RuntimeError as exc:
        assert "No dataset files found" in str(exc)
    else:
        raise AssertionError("Expected missing-dataset error")
