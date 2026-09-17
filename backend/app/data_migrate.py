"""Copy ledger tables from an uploaded SQLite file into the live database."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from app.database import DB_PATH, engine

SQLITE_HEADER = b"SQLite format 3\x00"
MAX_UPLOAD_BYTES = 32 * 1024 * 1024

# Auth tables stay on this server so an upload cannot lock the current user out.
DATA_TABLES = (
    "accounts",
    "credit_card_config",
    "statement_cycles",
    "budget_categories",
    "recurring_items",
    "one_off_items",
    "settings",
)
DELETE_ORDER = (
    "statement_cycles",
    "credit_card_config",
    "recurring_items",
    "one_off_items",
    "budget_categories",
    "settings",
    "accounts",
)
INSERT_ORDER = (
    "accounts",
    "credit_card_config",
    "statement_cycles",
    "budget_categories",
    "recurring_items",
    "one_off_items",
    "settings",
)
COLUMN_DEFAULTS: dict[tuple[str, str], str] = {
    ("recurring_items", "term"): "'monthly'",
    ("recurring_items", "active"): "1",
    ("statement_cycles", "is_generated"): "1",
    ("budget_categories", "period"): "'monthly'",
}

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class LedgerDataError(ValueError):
    """Uploaded file is not a usable Ledger database."""


def _ident(name: str) -> str:
    if not _IDENT.fullmatch(name):
        raise LedgerDataError("Database contains an invalid table or column name")
    return name


def is_sqlite_file(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(16) == SQLITE_HEADER
    except OSError:
        return False


def _table_columns(conn: sqlite3.Connection, schema: str, table: str) -> list[str]:
    schema = _ident(schema)
    table = _ident(table)
    rows = conn.execute(f"PRAGMA {schema}.table_info({table})").fetchall()
    return [str(row[1]) for row in rows]


def _incoming_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM incoming.sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def _copy_table(conn: sqlite3.Connection, table: str, source_tables: set[str]) -> int:
    table = _ident(table)
    dest_cols = _table_columns(conn, "main", table)
    if not dest_cols:
        return 0
    if table not in source_tables:
        return 0
    source_cols = set(_table_columns(conn, "incoming", table))
    insert_cols: list[str] = []
    select_exprs: list[str] = []
    for col in dest_cols:
        col = _ident(col)
        if col in source_cols:
            insert_cols.append(col)
            select_exprs.append(col)
        elif (table, col) in COLUMN_DEFAULTS:
            insert_cols.append(col)
            select_exprs.append(COLUMN_DEFAULTS[(table, col)])
    if not insert_cols:
        return 0
    conn.execute(
        f"INSERT INTO main.{table} ({', '.join(insert_cols)}) "
        f"SELECT {', '.join(select_exprs)} FROM incoming.{table}"
    )
    row = conn.execute(f"SELECT COUNT(*) FROM main.{table}").fetchone()
    return int(row[0]) if row else 0


def _sync_sequences(conn: sqlite3.Connection, source_tables: set[str]) -> None:
    id_tables = ("accounts", "statement_cycles", "recurring_items", "one_off_items", "budget_categories")
    has_seq = conn.execute(
        "SELECT 1 FROM main.sqlite_master WHERE type = 'table' AND name = 'sqlite_sequence'"
    ).fetchone()
    if not has_seq:
        return
    conn.execute(
        "DELETE FROM sqlite_sequence WHERE name IN ({})".format(
            ", ".join(f"'{_ident(name)}'" for name in id_tables)
        )
    )
    if "sqlite_sequence" not in source_tables:
        for table in id_tables:
            table = _ident(table)
            row = conn.execute(f"SELECT MAX(id) FROM main.{table}").fetchone()
            max_id = row[0] if row else None
            if max_id is not None:
                conn.execute(
                    "INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)",
                    (table, int(max_id)),
                )
        return
    conn.execute(
        "INSERT INTO sqlite_sequence (name, seq) "
        "SELECT name, seq FROM incoming.sqlite_sequence "
        "WHERE name IN ({})".format(", ".join(f"'{_ident(name)}'" for name in id_tables))
    )


def migrate_ledger_data(source_path: Path, dest_path: Path | None = None) -> dict[str, int]:
    source = Path(source_path)
    dest = Path(dest_path) if dest_path is not None else DB_PATH
    if not source.is_file() or source.stat().st_size < 16:
        raise LedgerDataError("Uploaded file is empty")
    if not is_sqlite_file(source):
        raise LedgerDataError("File is not a SQLite database")
    if dest.resolve() == source.resolve():
        raise LedgerDataError("Source and destination databases are the same file")
    if dest_path is None:
        engine.dispose()

    conn = sqlite3.connect(str(dest), timeout=60, isolation_level=None)
    counts: dict[str, int] = {}
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("ATTACH DATABASE ? AS incoming", (str(source.resolve()),))
        source_tables = _incoming_tables(conn)
        if "accounts" not in source_tables:
            raise LedgerDataError("File is not a Ledger database (missing accounts table)")
        conn.execute("BEGIN")
        for table in DELETE_ORDER:
            conn.execute(f"DELETE FROM main.{_ident(table)}")
        for table in INSERT_ORDER:
            counts[table] = _copy_table(conn, table, source_tables)
        _sync_sequences(conn, source_tables)
        conn.execute("PRAGMA foreign_keys = ON")
        mismatches = conn.execute("PRAGMA foreign_key_check").fetchall()
        if mismatches:
            raise LedgerDataError("Uploaded database failed foreign-key checks")
        conn.commit()
        return counts
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            conn.execute("DETACH DATABASE incoming")
        except sqlite3.Error:
            pass
        conn.close()
