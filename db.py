import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

ANALYTICS_DB = str(Path(__file__).resolve().parent / "analytics.db")


def compute_person_hash(post_author: str | None) -> str | None:
    if not post_author:
        return None
    normalized = post_author.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS parsed_cases (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id        INTEGER UNIQUE,
            message_date      TEXT,
            post_author       TEXT,
            person_hash       TEXT,
            raw_text          TEXT,
            source_type       TEXT,
            category          TEXT,
            case_type         TEXT,
            event_type        TEXT,
            receipt_date      TEXT,
            event_date        TEXT,
            days_processing   INTEGER,
            permit_valid_until TEXT,
            family_unit       INTEGER,
            confidence        TEXT,
            metadata          TEXT,
            parse_error       TEXT,
            parsed_at         TEXT
        );
        CREATE TABLE IF NOT EXISTS parse_cursor (
            id              INTEGER PRIMARY KEY CHECK (id = 1),
            last_message_id INTEGER DEFAULT 0
        );
    """)
    conn.commit()


def get_cursor(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT last_message_id FROM parse_cursor WHERE id=1"
    ).fetchone()
    return row[0] if row else 0


def update_cursor(conn: sqlite3.Connection, last_id: int) -> None:
    conn.execute(
        "INSERT INTO parse_cursor(id, last_message_id) VALUES(1,?) "
        "ON CONFLICT(id) DO UPDATE SET last_message_id=excluded.last_message_id",
        (last_id,),
    )
    conn.commit()


def insert_case(conn: sqlite3.Connection, data: dict, overwrite: bool = False) -> None:
    # Default conflict behavior lets --retry-errors fix bad rows without
    # clobbering good ones. overwrite=True is for deliberate full reprocessing.
    conflict_where = "" if overwrite else "WHERE parsed_cases.parse_error IS NOT NULL"
    sql = f"""INSERT INTO parsed_cases (
            message_id, message_date, post_author, person_hash, raw_text,
            source_type, category, case_type, event_type, receipt_date,
            event_date, days_processing, permit_valid_until, family_unit,
            confidence, metadata, parse_error, parsed_at
        ) VALUES (
            :message_id, :message_date, :post_author, :person_hash, :raw_text,
            :source_type, :category, :case_type, :event_type, :receipt_date,
            :event_date, :days_processing, :permit_valid_until, :family_unit,
            :confidence, :metadata, :parse_error, :parsed_at
        )
        ON CONFLICT(message_id) DO UPDATE SET
            message_date=excluded.message_date, post_author=excluded.post_author,
            person_hash=excluded.person_hash, raw_text=excluded.raw_text,
            source_type=excluded.source_type, category=excluded.category,
            case_type=excluded.case_type, event_type=excluded.event_type,
            receipt_date=excluded.receipt_date, event_date=excluded.event_date,
            days_processing=excluded.days_processing,
            permit_valid_until=excluded.permit_valid_until,
            family_unit=excluded.family_unit, confidence=excluded.confidence,
            metadata=excluded.metadata, parse_error=excluded.parse_error,
            parsed_at=excluded.parsed_at
        {conflict_where}"""
    conn.execute(sql, data)


def insert_noise_row(
    conn: sqlite3.Connection,
    row: dict,
    source_type: str,
    parse_error: str | None = None,
) -> None:
    insert_case(
        conn,
        {
            "message_id": row["message_id"],
            "message_date": row["date"],
            "post_author": row.get("post_author"),
            "person_hash": compute_person_hash(row.get("post_author")),
            "raw_text": row.get("message"),
            "source_type": source_type,
            "category": "NOISE",
            "case_type": None,
            "event_type": None,
            "receipt_date": None,
            "event_date": None,
            "days_processing": None,
            "permit_valid_until": None,
            "family_unit": None,
            "confidence": None,
            "metadata": "{}",
            "parse_error": parse_error,
            "parsed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
