import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

_default_db = Path(__file__).resolve().parent.parent / "app.db"
DB_PATH = Path(os.environ.get("LEDGER_DB_PATH", _default_db))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema() -> None:
    from app import models  # noqa: F401 — register tables on Base.metadata

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(recurring_items)"))]
        if cols and "term" not in cols:
            conn.execute(
                text("ALTER TABLE recurring_items ADD COLUMN term TEXT NOT NULL DEFAULT 'monthly'")
            )
