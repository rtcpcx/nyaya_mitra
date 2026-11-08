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
        {"act_id":"A7","chunk_id":"A7_rbi","title":"RBI Management of Advances Circular","section_number":"5","text":"Bank advances borrower loan security deposit and collateral requirements","jurisdiction":"central","state":"central","act_status":"in_force","year":2023,"source_url":"https://example.org/rbi"},
        {"act_id":"A8","chunk_id":"A8_delhi","title":"Delhi Rent Control Act","section_number":"14","text":"Delhi landlord tenant tenancy eviction premises","jurisdiction":"central","state":"central","act_status":"in_force","year":1958,"source_url":"https://example.org/delhi"},
        {"act_id":"A9","chunk_id":"A9_punjab","title":"Punjab Tenancy Act","section_number":"62","text":"Punjab landlord tenant tenancy rent","jurisdiction":"central","state":"central","act_status":"in_force","year":1887,"source_url":"https://example.org/punjab"}
    ]
    monkeypatch.setattr("src.database._parquet_records", lambda path: iter(rows))
    (constitution / "articles.jsonl").write_text(json.dumps({"article_number":"21","article_title":"Protection of life and personal liberty","part_number":"III","text":"No person shall be deprived of life or personal liberty except according to procedure established by law."})+"\n", encoding="utf-8")
    db = tmp_path / "test.sqlite3"
    stats = build_index(legal, constitution, db)
    assert stats["indexed_rows"] == 10
    consumer = search_sources("consumer refund defective goods", db, 5)
    assert consumer and consumer[0]["title"] == "Consumer Protection Act"
    art = search_sources("Article 21 personal liberty", db, 5)
    assert any(x["source_type"] == "constitution" for x in art)

    assam = search_sources("landlord tenancy security deposit", db, 10, "assam", strict_relevance=True)
    assert any(x["title"] == "Assam Tenancy Example Act" for x in assam)
    assert not any("West Bengal" in x["title"] for x in assam)
    assert not any("Delhi" in x["title"] or "Punjab" in x["title"] for x in assam)

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

    banking = search_sources(
        "bank loan security deposit collateral",
        db,
        10,
        national_only=True,
        strict_relevance=True,
    )
    assert any("RBI" in x["title"] for x in banking)

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



def test_rental_search_rejects_generic_deposit_match_without_shared_tenancy_term(tmp_path, monkeypatch):
    legal = tmp_path / "legal"; legal.mkdir()
    constitution = tmp_path / "constitution"; constitution.mkdir()
    (legal / "in_central_regulations.parquet").write_bytes(b"fixture")
    rows = [
        {"act_id":"T1","chunk_id":"T1","title":"Telecom Security Deposit Regulation","section_number":"10","text":"Security deposit for subscriber premises and equipment charges","jurisdiction":"central","act_status":"in_force","year":2020},
        {"act_id":"R1","chunk_id":"R1","title":"Assam Rental Deposit Provision","section_number":"4","text":"Landlord shall return tenant security deposit after lease termination","jurisdiction":"Assam","act_status":"in_force","year":2020},
    ]
    monkeypatch.setattr("src.database._parquet_records", lambda path: iter(rows))
    db = tmp_path / "db.sqlite3"
    build_index(legal, constitution, db)
    results = search_sources("My landlord has not returned my security deposit", db, 10, "assam", strict_relevance=True)
    assert any("Assam Rental" in item["title"] for item in results)
    assert not any("Telecom" in item["title"] for item in results)
