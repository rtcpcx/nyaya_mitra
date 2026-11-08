from __future__ import annotations
import json, re, sqlite3
from pathlib import Path
from typing import Any, Callable

TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./-]{1,}")
OFFICIAL_CONSTITUTION_URL = "https://www.legislative.gov.in/documents"

# Domain vocabulary is deliberately conservative: a document must contain a
# domain-specific legal term, not merely a generic word such as "deposit".
RENTAL_TERMS = {
    "landlord", "tenant", "tenancy", "rent", "rental", "lease", "lessor",
    "lessee", "eviction", "premises", "occupancy", "letting",
}
RENTAL_QUERY_EXPANSION = (
    "landlord tenant tenancy rent rental lease lessor lessee eviction premises occupancy"
)
STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "have", "what",
    "when", "where", "does", "under", "about", "into", "your", "are",
    "was", "were", "has", "had", "you", "my", "me", "can", "please",
    "who", "why", "how", "not", "but", "then", "they", "them",
}


def _query_domain(query: str) -> str | None:
    text = (query or "").casefold()
    tokens = set(TOKEN_RE.findall(text))
    if tokens & RENTAL_TERMS or "security deposit" in text:
        return "rental"
    return None


def _is_relevant_result(query: str, row: dict, domain: str | None) -> bool:
    source_text = " ".join(
        str(row.get(key) or "") for key in ("title", "section", "text", "legal_subject")
    ).casefold()
    source_tokens = set(TOKEN_RE.findall(source_text))
    query_tokens = set(TOKEN_RE.findall((query or "").casefold())) - STOPWORDS
    overlap = source_tokens & query_tokens
    if domain == "rental":
        # RBI/TRAI passages about generic "security deposits" fail this gate.
        # A tenancy-related source must contain a landlord/tenant/lease concept
        # and share at least one meaningful term with the user's account.
        return bool(source_tokens & RENTAL_TERMS) and bool(overlap)
    return len(overlap) >= 2


def connect(db_path: Path | str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS legal_fts USING fts5(
        doc_id UNINDEXED, title, section_number, text,
        jurisdiction UNINDEXED, source_url UNINDEXED, source_publisher UNINDEXED,
        year UNINDEXED, status UNINDEXED, source_type UNINDEXED, legal_subject UNINDEXED,
        tokenize='unicode61 remove_diacritics 2'
        )""")
    except sqlite3.OperationalError as exc:
        raise RuntimeError("This Python installation's SQLite does not include FTS5. Install a standard Python 3.11 build from python.org and retry.") from exc
    conn.execute("CREATE TABLE IF NOT EXISTS index_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.commit()


def _safe(value: Any, default: str = "") -> str:
    if value is None: return default
    if isinstance(value, (list, tuple)): return ", ".join(str(x) for x in value if x is not None)
    return str(value)


def _add_record(conn: sqlite3.Connection, record: dict, doc_id: str, source_type: str) -> None:
    title = _safe(record.get("title") or record.get("article_title") or record.get("schedule_title") or record.get("appendix_title") or record.get("section_title"), "Untitled")
    section = _safe(record.get("section_number") or record.get("article_number") or record.get("schedule_number") or record.get("appendix_number"))
    body = _safe(record.get("text"))
    if not body.strip(): return
    jurisdiction = _safe(record.get("state") or record.get("jurisdiction"), "India")
    source_url = _safe(record.get("source_url")) or (OFFICIAL_CONSTITUTION_URL if source_type == "constitution" else "")
    publisher = _safe(record.get("source_publisher"))
    if source_type == "constitution":
        publisher = "Structured transcription by GSMS-B; verify against Legislative Department official publication"
    year = _safe(record.get("year"))
    status = _safe(record.get("act_status"))
    if not status and record.get("in_force") is not None:
        status = "in_force" if record.get("in_force") else "not_marked_in_force"
    subject = _safe(record.get("legal_subject"))
    conn.execute("INSERT INTO legal_fts(doc_id,title,section_number,text,jurisdiction,source_url,source_publisher,year,status,source_type,legal_subject) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                 (doc_id, title, section, body, jurisdiction, source_url, publisher, year, status, source_type, subject))


def _parquet_records(path: Path, batch_size: int = 5000):
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("PyArrow is required to read the downloaded Parquet legal files. Run `pip install -r requirements.txt`.") from exc
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(batch_size=batch_size):
        for row in batch.to_pylist():
            yield row


def _jsonl_records(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip(): continue
            try: yield json.loads(line)
            except json.JSONDecodeError: continue


def build_index(legal_dir: Path | str, constitution_dir: Path | str, db_path: Path | str,
                progress: Callable[[str], None] | None = None) -> dict:
    legal_dir, constitution_dir = Path(legal_dir), Path(constitution_dir)
    parquet_files = sorted(legal_dir.glob("in_*_legislation.parquet")) + sorted(legal_dir.glob("in_*_regulations.parquet")) + sorted(legal_dir.glob("in_*_judgments.parquet"))
    jsonl_files = [constitution_dir / name for name in ("articles.jsonl", "schedules.jsonl", "appendices.jsonl") if (constitution_dir / name).exists()]
    if not parquet_files and not jsonl_files:
        raise RuntimeError(f"No dataset files found. Expected Parquet files in {legal_dir} and Constitution JSONL in {constitution_dir}. Run `python setup_database.py` first.")
    conn = connect(db_path)
    try:
        _create_schema(conn)
        conn.execute("DELETE FROM legal_fts")
        conn.commit()
        total = 0
        for path in parquet_files:
            source_type = "judgment_chunk" if "_judgments" in path.name else ("regulation" if "_regulations" in path.name else "legislation")
            count = 0
            if progress: progress(f"Indexing {path.name} ...")
            for row in _parquet_records(path):
                stable = _safe(row.get("chunk_id") or row.get("act_id") or row.get("case_id"))
                section = _safe(row.get("section_number"))
                doc_id = f"{path.name}:{stable or count}:{section}"
                _add_record(conn, row, doc_id, source_type)
                count += 1
                if count % 5000 == 0:
                    conn.commit()
                    if progress: progress(f"  {path.name}: processed {count:,} rows")
            conn.commit(); total += count
            if progress: progress(f"  {path.name}: finished {count:,} rows")
        # Add the Preamble from the full structured Constitution JSON, if present.
        master_path = constitution_dir / "CONSTITUTION_DATASET.json"
        if master_path.exists():
            try:
                master = json.loads(master_path.read_text(encoding="utf-8"))
                preamble = master.get("preamble") if isinstance(master, dict) else None
                if isinstance(preamble, dict) and preamble.get("text"):
                    preamble_record = dict(preamble)
                    preamble_record.setdefault("article_title", "Preamble to the Constitution of India")
                    preamble_record.setdefault("article_number", "Preamble")
                    _add_record(conn, preamble_record, "constitution:preamble", "constitution")
                    total += 1
            except (OSError, json.JSONDecodeError):
                if progress: progress("Warning: could not parse Constitution master JSON; continuing with JSONL files.")
        for path in jsonl_files:
            source_type = "constitution"
            count = 0
            if progress: progress(f"Indexing Constitution {path.name} ...")
            for row in _jsonl_records(path):
                key = _safe(row.get("article_number") or row.get("schedule_number") or row.get("appendix_number") or count)
                _add_record(conn, row, f"constitution:{path.name}:{key}", source_type)
                count += 1
            conn.commit(); total += count
        conn.execute("INSERT OR REPLACE INTO index_meta(key,value) VALUES('indexed_rows',?)", (str(total),))
        conn.execute("INSERT OR REPLACE INTO index_meta(key,value) VALUES('source_files',?)", (str(len(parquet_files)+len(jsonl_files)),))
        conn.commit()
        return {"indexed_rows": total, "parquet_files": len(parquet_files), "constitution_files": len(jsonl_files), "database_path": str(db_path)}
    finally:
        conn.close()


def _fts_query(query: str) -> str:
    tokens = []
    for token in TOKEN_RE.findall(query or ""):
        clean = token.replace('"', "").strip()
        if clean and clean.casefold() not in {"the", "and", "for", "with", "from", "that", "this", "have", "what", "when", "where", "does", "under", "about", "into", "your", "are", "was", "were", "has", "had", "you", "my", "me", "can"}:
            tokens.append('"' + clean + '"')
    return " OR ".join(dict.fromkeys(tokens[:18]))


def search_sources(
    query: str,
    db_path: Path | str,
    top_k: int = 8,
    jurisdiction_hint: str | None = None,
    national_only: bool = False,
    strict_relevance: bool = False,
) -> list[dict]:
    """Search legal passages with optional state or national jurisdiction isolation.

    A state-scoped search includes central/national and matching-state records.
    A national-only search excludes state-specific records until location is confirmed.
    The unrestricted default is retained for the manual source explorer.
    """
    if not Path(db_path).exists(): return []
    domain = _query_domain(query) if strict_relevance else None
    expanded_query = query
    if domain == "rental":
        expanded_query = f"{query} {RENTAL_QUERY_EXPANSION}"
    match = _fts_query(expanded_query)
    if not match: return []
    conn = connect(db_path)
    try:
        select_sql = """SELECT doc_id,title,section_number,text,jurisdiction,source_url,source_publisher,year,status,source_type,legal_subject,bm25(legal_fts, 0.0, 2.0, 4.0, 1.0) AS rank
                FROM legal_fts WHERE legal_fts MATCH ?"""
        limit = max(1, min(50, max(top_k * 3, top_k) if strict_relevance else top_k))
        if jurisdiction_hint:
            rows = conn.execute(
                select_sql + """ AND (
                    lower(trim(jurisdiction)) IN ('central', 'india')
                    OR lower(jurisdiction) LIKE ?
                ) ORDER BY rank LIMIT ?""",
                (match, "%" + jurisdiction_hint.casefold() + "%", limit),
            ).fetchall()
        elif national_only:
            rows = conn.execute(
                select_sql + """ AND (
                    lower(trim(jurisdiction)) IN ('central', 'india')
                    OR source_type = 'constitution'
                ) ORDER BY rank LIMIT ?""",
                (match, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                select_sql + " ORDER BY rank LIMIT ?",
                (match, limit),
            ).fetchall()
        results=[]
        for row in rows:
            (doc_id,title,section,body,jurisdiction,url,publisher,year,status,source_type,subject,rank)=row
            results.append({"doc_id":doc_id,"title":title,"section":section,"text":body[:9000],"jurisdiction":jurisdiction,
                            "source_url":url,"source_publisher":publisher,"year":year,"status":status,
                            "source_type":source_type,"legal_subject":subject,"retrieval_rank":round(float(rank),5)})
        if strict_relevance:
            results = [
                item for item in results
                if _is_relevant_result(query, item, domain)
            ][:max(1, min(20, top_k))]
        return results
    finally: conn.close()


def database_stats(db_path: Path | str, legal_dir: Path | str | None = None, constitution_dir: Path | str | None = None) -> dict:
    result={"database_exists":Path(db_path).exists(),"database_path":str(db_path)}
    if Path(db_path).exists():
        conn=connect(db_path)
        try:
            result["indexed_rows"]=conn.execute("SELECT count(*) FROM legal_fts").fetchone()[0]
            result["source_types"]={r[0]:r[1] for r in conn.execute("SELECT source_type,count(*) FROM legal_fts GROUP BY source_type")}
        finally: conn.close()
    if legal_dir is not None:
        d=Path(legal_dir)
        result["parquet_files"]=[p.name for p in sorted(d.glob("*.parquet"))] if d.exists() else []
    if constitution_dir is not None:
        d=Path(constitution_dir)
        result["constitution_files"]=[p.name for p in sorted(d.glob("*.jsonl"))] if d.exists() else []
    return result
