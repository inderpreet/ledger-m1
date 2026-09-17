import os
from datetime import date
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
        settings_tbl = conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='settings'")
        ).fetchone()
        if settings_tbl:
            has_start = conn.execute(
                text("SELECT 1 FROM settings WHERE key='model_start_date'")
            ).fetchone()
            if not has_start:
                conn.execute(
                    text("INSERT INTO settings (key, value) VALUES ('model_start_date', :v)"),
                    {"v": date.today().isoformat()},
                )
        cats_tbl = conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='budget_categories'")
        ).fetchone()
        if cats_tbl:
            count = conn.execute(text("SELECT COUNT(*) FROM budget_categories")).scalar()
            if not count:
                names = {
                    str(row[0]).strip()
                    for row in conn.execute(
                        text(
                            "SELECT DISTINCT category FROM recurring_items "
                            "WHERE category IS NOT NULL AND TRIM(category) != '' "
                            "UNION "
                            "SELECT DISTINCT category FROM one_off_items "
                            "WHERE category IS NOT NULL AND TRIM(category) != ''"
                        )
                    ).fetchall()
                    if row[0]
                }
                for name in sorted(names):
                    conn.execute(
                        text("INSERT INTO budget_categories (name) VALUES (:name)"),
                        {"name": name},
                    )
            cat_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(budget_categories)"))]
            if cat_cols and "amount" not in cat_cols:
                conn.execute(text("ALTER TABLE budget_categories ADD COLUMN amount REAL"))
            if cat_cols and "period" not in cat_cols:
                conn.execute(
                    text(
                        "ALTER TABLE budget_categories ADD COLUMN period TEXT NOT NULL DEFAULT 'monthly'"
                    )
                )
            ddl = conn.execute(
                text(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name='budget_categories'"
                )
            ).fetchone()
            ddl_sql = ddl[0] if ddl and ddl[0] else ""
            if "biweekly" not in ddl_sql and (
                "ck_budget_period" in ddl_sql or "'yearly'" in ddl_sql
            ):
                conn.execute(
                    text(
                        """
                        CREATE TABLE budget_categories_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL UNIQUE,
                            amount REAL,
                            period TEXT NOT NULL DEFAULT 'monthly',
                            CHECK (period IN ('monthly','biweekly','yearly'))
                        )
                        """
                    )
                )
                conn.execute(
                    text(
                        "INSERT INTO budget_categories_new (id, name, amount, period) "
                        "SELECT id, name, amount, COALESCE(period, 'monthly') "
                        "FROM budget_categories"
                    )
                )
                conn.execute(text("DROP TABLE budget_categories"))
                conn.execute(text("ALTER TABLE budget_categories_new RENAME TO budget_categories"))
