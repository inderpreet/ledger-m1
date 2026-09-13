from datetime import date

from sqlalchemy.orm import Session

from app import models
from app.engine import (
    combined_daily_rows,
    daily_cashflow,
    daily_cc_cashflow,
    expenses_by_category,
    first_low_balance_date,
    parse_date,
    statement_total,
)


def get_setting(db: Session, key: str, default: str) -> str:
    row = db.get(models.Setting, key)
    return row.value if row else default


def get_settings(db: Session) -> dict:
    return {
        "low_balance_threshold": float(get_setting(db, "low_balance_threshold", "6000")),
        "model_end_date": get_setting(db, "model_end_date", "2026-12-31"),
    }


def upsert_setting(db: Session, key: str, value: str) -> None:
    row = db.get(models.Setting, key)
    if row:
        row.value = value
    else:
        db.add(models.Setting(key=key, value=value))


def funding_map(db: Session) -> dict[int, int]:
    rows = db.query(models.CreditCardConfig).all()
    return {row.account_id: row.funding_account_id for row in rows}


def compute_statement_totals(db: Session) -> list[dict]:
    accounts = {a.id: a for a in db.query(models.Account).all()}
    recurring = db.query(models.RecurringItem).filter(models.RecurringItem.active.is_(True)).all()
    one_offs = db.query(models.OneOffItem).all()
    cycles = db.query(models.StatementCycle).order_by(models.StatementCycle.payment_due).all()
    out = []
    for cycle in cycles:
        account = accounts[cycle.account_id]
        frm = parse_date(cycle.statement_from)
        to = parse_date(cycle.statement_to)
        assert frm and to
        total = statement_total(account, frm, to, recurring, one_offs)
        out.append(
            {
                "cycle_id": cycle.id,
                "account_id": cycle.account_id,
                "account_name": account.name,
                "statement_from": cycle.statement_from,
                "statement_to": cycle.statement_to,
                "payment_due": cycle.payment_due,
                "is_generated": cycle.is_generated,
                "total": round(total, 2),
            }
        )
    return out


def compute_daily_cashflow(db: Session, start: date | None, end: date | None) -> dict:
    settings = get_settings(db)
    start_date = start or date.today()
    end_date = end or date.fromisoformat(settings["model_end_date"])
    accounts = db.query(models.Account).all()
    bank_accounts = [a for a in accounts if a.account_type == "bank"]
    recurring = db.query(models.RecurringItem).filter(models.RecurringItem.active.is_(True)).all()
    one_offs = db.query(models.OneOffItem).all()
    cycles = db.query(models.StatementCycle).all()
    totals_rows = compute_statement_totals(db)
    totals = {row["cycle_id"]: row["total"] for row in totals_rows}

    rows = daily_cashflow(
        accounts,
        recurring,
        one_offs,
        cycles,
        totals,
        funding_map(db),
        start_date,
        end_date,
    )
    bank_ids = [a.id for a in bank_accounts]
    rows = combined_daily_rows(rows, bank_ids)
    names = {a.id: a.name for a in bank_accounts}
    serialized = []
    for row in rows:
        out_row = {"date": row["date"].isoformat()}
        for a in bank_accounts:
            out_row[str(a.id)] = round(row[a.id], 2)
        out_row["combined"] = round(row["combined"], 2)
        out_row["movements"] = [
            {
                "account_id": m["account_id"],
                "account_name": names.get(m["account_id"], ""),
                "description": m["description"],
                "amount": round(m["amount"], 2),
                "kind": m["kind"],
            }
            for m in row.get("movements", [])
        ]
        serialized.append(out_row)

    return {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "accounts": [{"id": a.id, "name": a.name} for a in bank_accounts],
        "rows": serialized,
    }


def compute_cc_cashflow(db: Session, start: date | None, end: date | None) -> dict:
    settings = get_settings(db)
    start_date = start or date.today()
    end_date = end or date.fromisoformat(settings["model_end_date"])
    accounts = db.query(models.Account).all()
    cards = [a for a in accounts if a.account_type == "credit_card"]
    recurring = db.query(models.RecurringItem).filter(models.RecurringItem.active.is_(True)).all()
    one_offs = db.query(models.OneOffItem).all()
    cycles = db.query(models.StatementCycle).all()
    totals = {row["cycle_id"]: row["total"] for row in compute_statement_totals(db)}

    rows = daily_cc_cashflow(
        accounts,
        recurring,
        one_offs,
        start_date,
        end_date,
        cycles,
        totals,
    )
    card_ids = [a.id for a in cards]
    rows = combined_daily_rows(rows, card_ids)
    names = {a.id: a.name for a in cards}
    serialized = []
    for row in rows:
        out_row = {"date": row["date"].isoformat()}
        for a in cards:
            out_row[str(a.id)] = round(row[a.id], 2)
        out_row["combined"] = round(row["combined"], 2)
        out_row["movements"] = [
            {
                "account_id": m["account_id"],
                "account_name": names.get(m["account_id"], ""),
                "description": m["description"],
                "amount": round(m["amount"], 2),
                "kind": m["kind"],
            }
            for m in row.get("movements", [])
        ]
        serialized.append(out_row)

    return {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "accounts": [{"id": a.id, "name": a.name} for a in cards],
        "rows": serialized,
    }


def compute_dashboard(db: Session) -> dict:
    settings = get_settings(db)
    threshold = settings["low_balance_threshold"]
    today = date.today()
    end = date.fromisoformat(settings["model_end_date"])
    payload = compute_daily_cashflow(db, today, end)
    accounts = {a.id: a for a in db.query(models.Account).filter(models.Account.account_type == "bank").all()}
    rows = payload["rows"]

    def as_float_rows():
        converted = []
        for row in rows:
            item = {"date": date.fromisoformat(row["date"]), "combined": row["combined"]}
            for key, value in row.items():
                if key not in ("date", "combined", "movements"):
                    item[int(key)] = value
            converted.append(item)
        return converted

    numeric = as_float_rows()
    account_summaries = []
    for account_id, account in accounts.items():
        current = numeric[0][account_id] if numeric else (account.opening_balance or 0.0)
        low = first_low_balance_date(numeric, account_id, threshold)
        account_summaries.append(
            {
                "id": account.id,
                "name": account.name,
                "opening_balance": account.opening_balance,
                "current_balance": round(current, 2) if account.opening_balance is not None else None,
                "first_low_balance_date": low.isoformat() if low else None,
            }
        )

    combined_current = numeric[0]["combined"] if numeric else 0.0
    combined_low = first_low_balance_date(
        [{"date": r["date"], "combined": r["combined"]} for r in numeric],
        "combined",
        threshold,
    )
    any_unset = any(a.opening_balance is None for a in accounts.values())
    recurring = db.query(models.RecurringItem).filter(models.RecurringItem.active.is_(True)).all()
    one_offs = db.query(models.OneOffItem).all()

    return {
        "as_of": today.isoformat(),
        "threshold": threshold,
        "model_end_date": settings["model_end_date"],
        "opening_balances_set": not any_unset,
        "accounts": account_summaries,
        "combined": {
            "current_balance": None if any_unset else round(combined_current, 2),
            "first_low_balance_date": combined_low.isoformat() if combined_low else None,
        },
        "expenses_by_category": expenses_by_category(recurring, one_offs, today, end),
    }
