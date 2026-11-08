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
        {"act_id":"A2","chunk_id":"A2_s103","title":"Bharatiya Nyaya Sanhita","section_number":"103","section_title":"Punishment for murder","text":"Punishment for murder and criminal offence","jurisdiction":"central","state":"central","act_status":"in_force","in_force":True,"year":2023.0,"source_url":"https://example.org/bns","source_publisher":"India Code","legal_subject":["criminal_law"]},
        {"act_id":"A3","chunk_id":"A3_assam","title":"Assam Tenancy Example Act","section_number":"7","text":"Assam landlord tenancy security deposit dispute","jurisdiction":"Assam","state":"Assam","act_status":"in_force","year":2020,"source_url":"https://example.org/assam"},
        {"act_id":"A4","chunk_id":"A4_wb","title":"West Bengal Tenancy Example Act","section_number":"8","text":"West Bengal landlord tenancy security deposit dispute","jurisdiction":"West Bengal","state":"West Bengal","act_status":"in_force","year":2020,"source_url":"https://example.org/wb"},
        {"act_id":"A5","chunk_id":"A5_reg","title":"West Bengal Tenancy Regulation Example","section_number":"9","text":"West Bengal landlord tenancy security deposit regulation","jurisdiction":"West Bengal","state":"West Bengal","act_status":"in_force","year":2020,"source_url":"https://example.org/wb-reg"},
        {"act_id":"A6","chunk_id":"A6_trai","title":"TRAI DTH Tariff Order","section_number":"4","text":"Cable television subscriber security deposit and tariff charges","jurisdiction":"central","state":"central","act_status":"in_force","year":2013,"source_url":"https://example.org/trai"},
        {"act_id":"A7","chunk_id":"A7_rbi","title":"RBI Management of Advances Circular","section_number":"5","text":"Bank advances borrower loan security deposit and collateral requirements","jurisdiction":"central","state":"central","act_status":"in_force","year":2023,"source_url":"https://example.org/rbi"}
    ]
    monkeypatch.setattr("src.database._parquet_records", lambda path: iter(rows))
    (constitution / "articles.jsonl").write_text(json.dumps({"article_number":"21","article_title":"Protection of life and personal liberty","part_number":"III","text":"No person shall be deprived of life or personal liberty except according to procedure established by law."})+"\n", encoding="utf-8")
    db = tmp_path / "test.sqlite3"
    stats = build_index(legal, constitution, db)
    assert stats["indexed_rows"] == 8
    consumer = search_sources("consumer refund defective goods", db, 5)
    assert consumer and consumer[0]["title"] == "Consumer Protection Act"
    art = search_sources("Article 21 personal liberty", db, 5)
    assert any(x["source_type"] == "constitution" for x in art)

    assam = search_sources("landlord tenancy security deposit", db, 10, "assam")
    assert any(x["title"] == "Assam Tenancy Example Act" for x in assam)
    assert not any("West Bengal" in x["title"] for x in assam)

    national = search_sources("landlord tenancy security deposit", db, 10, national_only=True)
    assert not any("Assam" in x["title"] or "West Bengal" in x["title"] for x in national)

    relevant = search_sources(
        "My landlord is withholding my security deposit",
        db,
        10,
        "assam",
        strict_relevance=True,
    )
    assert any("Assam Tenancy" in x["title"] for x in relevant)
    assert not any("TRAI" in x["title"] or "RBI" in x["title"] for x in relevant)

    # When location is unknown, national-only filtering plus topic relevance
    # must not let generic RBI/TRAI uses of "deposit" appear as tenancy law.
    unknown_location = search_sources(
        "My landlord is withholding my security deposit",
        db,
        10,
        national_only=True,
        strict_relevance=True,
    )
    assert not any("TRAI" in x["title"] or "RBI" in x["title"] for x in unknown_location)
    assert not any("Assam Tenancy" in x["title"] for x in unknown_location)


def test_no_files_raises_clear_error(tmp_path: Path):
    (tmp_path/"legal").mkdir(); (tmp_path/"constitution").mkdir()
    try:
        build_index(tmp_path/"legal", tmp_path/"constitution", tmp_path/"db.sqlite3")
    except RuntimeError as exc:
        assert "No dataset files found" in str(exc)
    else:
        raise AssertionError("Expected missing-dataset error")
