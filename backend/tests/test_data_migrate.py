import sqlite3
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.data_migrate import LedgerDataError, migrate_ledger_data
from app.database import Base
from app.models import Account, AuthUser, RecurringItem, Setting


def _dest_session(path: Path) -> Session:
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _source_with_term(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            account_type TEXT NOT NULL,
            opening_balance REAL,
            opening_balance_date TEXT
        );
        CREATE TABLE credit_card_config (
            account_id INTEGER PRIMARY KEY,
            funding_account_id INTEGER NOT NULL
        );
        CREATE TABLE statement_cycles (
            id INTEGER PRIMARY KEY,
            account_id INTEGER NOT NULL,
            statement_from TEXT NOT NULL,
            statement_to TEXT NOT NULL,
            payment_due TEXT NOT NULL,
            is_generated INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE recurring_items (
            id INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            item_type TEXT NOT NULL,
            amount REAL,
            day_of_month INTEGER,
            start_date TEXT,
            end_date TEXT,
            target_account_id INTEGER NOT NULL,
            category TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            term TEXT NOT NULL DEFAULT 'monthly'
        );
        CREATE TABLE one_off_items (
            id INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            item_type TEXT NOT NULL,
            amount REAL NOT NULL,
            item_date TEXT NOT NULL,
            target_account_id INTEGER NOT NULL,
            category TEXT
        );
        CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        INSERT INTO accounts VALUES (1, 'Imported Bank', 'bank', 250.25, '2026-09-01');
        INSERT INTO accounts VALUES (2, 'Imported Card', 'credit_card', NULL, NULL);
        INSERT INTO credit_card_config VALUES (2, 1);
        INSERT INTO statement_cycles VALUES (10, 2, '2026-08-05', '2026-09-03', '2026-09-24', 0);
        INSERT INTO recurring_items VALUES (
            5, 'Imported Salary', 'income', 1000, 17, NULL, NULL, 1, 'Income', 1, 'monthly'
        );
        INSERT INTO one_off_items VALUES (3, 'Imported Tax', 'expense', 99.5, '2026-09-17', 1, 'Tax');
        INSERT INTO settings VALUES ('low_balance_threshold', '1234');
        INSERT INTO settings VALUES ('model_end_date', '2027-06-30');
        """
    )
    conn.commit()
    conn.close()


def _source_without_term(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            account_type TEXT NOT NULL,
            opening_balance REAL,
            opening_balance_date TEXT
        );
        CREATE TABLE recurring_items (
            id INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            item_type TEXT NOT NULL,
            amount REAL,
            day_of_month INTEGER,
            start_date TEXT,
            end_date TEXT,
            target_account_id INTEGER NOT NULL,
            category TEXT,
            active INTEGER NOT NULL DEFAULT 1
        );
        INSERT INTO accounts VALUES (1, 'Legacy Bank', 'bank', 10, NULL);
        INSERT INTO recurring_items VALUES (
            1, 'Legacy Bill', 'expense', 40, 1, NULL, NULL, 1, 'Utilities', 1
        );
        """
    )
    conn.commit()
    conn.close()


def test_migrate_replaces_ledger_rows_and_keeps_login(tmp_path: Path):
    dest = tmp_path / "dest.db"
    source = tmp_path / "source.db"
    _source_with_term(source)
    db = _dest_session(dest)
    db.add(AuthUser(username="keepme", password_hash="hashed"))
    db.add(Account(name="Old Bank", account_type="bank", opening_balance=1))
    db.add(Setting(key="low_balance_threshold", value="6000"))
    db.add(Setting(key="model_end_date", value="2026-12-31"))
    db.commit()

    imported = migrate_ledger_data(source, dest)
    db.expire_all()

    assert imported["accounts"] == 2
    assert imported["recurring_items"] == 1
    assert imported["one_off_items"] == 1
    assert imported["statement_cycles"] == 1
    assert db.query(AuthUser).filter_by(username="keepme").one()
    assert db.query(Account).filter_by(name="Imported Bank").one().opening_balance == 250.25
    assert db.query(Account).filter_by(name="Old Bank").first() is None
    assert db.query(Setting).filter_by(key="low_balance_threshold").one().value == "1234"
    assert db.query(Setting).filter_by(key="model_end_date").one().value == "2027-06-30"
    db.close()


def test_migrate_fills_missing_term_column(tmp_path: Path):
    dest = tmp_path / "dest.db"
    source = tmp_path / "legacy.db"
    _source_without_term(source)
    db = _dest_session(dest)
    imported = migrate_ledger_data(source, dest)
    db.expire_all()
    assert imported["recurring_items"] == 1
    item = db.query(RecurringItem).one()
    assert item.term == "monthly"
    assert item.description == "Legacy Bill"
    db.close()


def test_migrate_rejects_non_sqlite(tmp_path: Path):
    dest = tmp_path / "dest.db"
    junk = tmp_path / "notes.txt"
    junk.write_text("not a sqlite database file")
    _dest_session(dest).close()
    try:
        migrate_ledger_data(junk, dest)
        raise AssertionError("expected LedgerDataError")
    except LedgerDataError as exc:
        assert "SQLite" in str(exc)
