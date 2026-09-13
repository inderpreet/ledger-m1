from datetime import date

from sqlalchemy.orm import Session

from app.database import SessionLocal, ensure_schema
from app import models
from app.engine import cycles_to_insert, generate_cycles, parse_date

SEED_SETTINGS = {
    "low_balance_threshold": "6000",
    "model_end_date": "2026-12-31",
}

ACCOUNTS = [
    {"name": "Scotia", "account_type": "bank", "opening_balance": None},
    {"name": "TD GK", "account_type": "bank", "opening_balance": None},
    {"name": "BMO CC", "account_type": "credit_card"},
    {"name": "Scotia CC", "account_type": "credit_card"},
    {"name": "CIBC CC", "account_type": "credit_card"},
    {"name": "TD CC", "account_type": "credit_card"},
]

CC_FUNDING = [
    {"account": "BMO CC", "funding_account": "Scotia"},
    {"account": "Scotia CC", "funding_account": "Scotia"},
    {"account": "CIBC CC", "funding_account": "Scotia"},
    {"account": "TD CC", "funding_account": "TD GK"},
]

RECURRING = [
    {"description": "Salary IP", "item_type": "income", "amount": 4546.21, "day_of_month": 17, "target_account": "Scotia", "category": "Income"},
    {"description": "Salary GP", "item_type": "income", "amount": 2710.36, "day_of_month": 17, "target_account": "TD GK", "category": "Income"},
    {"description": "Rent Lau", "item_type": "income", "amount": 3000, "day_of_month": 5, "target_account": "Scotia", "category": "Income"},
    {"description": "Rent Mol", "item_type": "income", "amount": None, "day_of_month": None, "target_account": "Scotia", "category": "Income"},
    {"description": "Mortgage BMO", "item_type": "expense", "amount": 5273.89, "day_of_month": 1, "target_account": "Scotia", "category": "Housing & Debt"},
    {"description": "Mortgage National", "item_type": "expense", "amount": 5561.23, "day_of_month": 8, "target_account": "Scotia", "category": "Housing & Debt"},
    {"description": "Alectra", "item_type": "expense", "amount": 150, "day_of_month": 23, "target_account": "Scotia", "category": "Utilities"},
    {"description": "Enbridge", "item_type": "expense", "amount": 70, "day_of_month": 20, "target_account": "Scotia", "category": "Utilities"},
    {"description": "Enercare", "item_type": "expense", "amount": None, "day_of_month": None, "target_account": "Scotia", "category": "Utilities"},
    {"description": "Gas", "item_type": "expense", "amount": None, "day_of_month": None, "target_account": "Scotia", "category": "Utilities"},
    {"description": "Life Insurance", "item_type": "expense", "amount": 87.69, "day_of_month": 10, "target_account": "Scotia", "category": "Insurance"},
    {"description": "Coop Auto Insurance", "item_type": "expense", "amount": 448.09, "day_of_month": 30, "target_account": "Scotia", "category": "Insurance"},
    {"description": "Coop House Insurance", "item_type": "expense", "amount": 338.23, "day_of_month": 15, "target_account": "Scotia", "category": "Insurance"},
    {"description": "Oxford", "item_type": "expense", "amount": 395, "day_of_month": 1, "target_account": "Scotia", "category": "Subscriptions"},
    {"description": "Rogers", "item_type": "expense", "amount": 62.15, "day_of_month": 9, "target_account": "Scotia", "category": "Subscriptions"},
    {"description": "Freedom", "item_type": "expense", "amount": 56, "day_of_month": 8, "target_account": "Scotia", "category": "Subscriptions"},
]

ONE_OFFS = [
    {
        "description": "Property Tax",
        "item_type": "expense",
        "amount": 3000,
        "item_date": "2026-09-17",
        "target_account": "TD GK",
        "category": "Housing & Debt",
    },
]

CYCLE_ANCHORS = [
    {"account": "TD CC", "statement_from": "2026-08-05", "statement_to": "2026-09-03", "payment_due": "2026-09-24"},
    {"account": "Scotia CC", "statement_from": "2026-07-12", "statement_to": "2026-08-11", "payment_due": "2026-09-01"},
]


def seed(db: Session) -> None:
    ensure_schema()

    if db.query(models.Account).count() > 0:
        return

    by_name: dict[str, models.Account] = {}
    for row in ACCOUNTS:
        account = models.Account(
            name=row["name"],
            account_type=row["account_type"],
            opening_balance=row.get("opening_balance"),
            opening_balance_date=None,
        )
        db.add(account)
        db.flush()
        by_name[account.name] = account

    for row in CC_FUNDING:
        db.add(
            models.CreditCardConfig(
                account_id=by_name[row["account"]].id,
                funding_account_id=by_name[row["funding_account"]].id,
            )
        )

    for row in RECURRING:
        db.add(
            models.RecurringItem(
                description=row["description"],
                item_type=row["item_type"],
                amount=row["amount"],
                day_of_month=row["day_of_month"],
                target_account_id=by_name[row["target_account"]].id,
                category=row["category"],
                active=True,
                term=row.get("term", "monthly"),
            )
        )

    for row in ONE_OFFS:
        db.add(
            models.OneOffItem(
                description=row["description"],
                item_type=row["item_type"],
                amount=row["amount"],
                item_date=row["item_date"],
                target_account_id=by_name[row["target_account"]].id,
                category=row["category"],
            )
        )

    model_end = parse_date(SEED_SETTINGS["model_end_date"])
    assert model_end is not None

    for row in CYCLE_ANCHORS:
        account = by_name[row["account"]]
        db.add(
            models.StatementCycle(
                account_id=account.id,
                statement_from=row["statement_from"],
                statement_to=row["statement_to"],
                payment_due=row["payment_due"],
                is_generated=True,
            )
        )
        db.flush()
        generated = generate_cycles(
            account.id,
            date.fromisoformat(row["statement_from"]),
            date.fromisoformat(row["statement_to"]),
            date.fromisoformat(row["payment_due"]),
            model_end,
        )
        existing = (
            db.query(models.StatementCycle)
            .filter(models.StatementCycle.account_id == account.id)
            .all()
        )
        for frm, to, due in cycles_to_insert(existing, generated):
            db.add(
                models.StatementCycle(
                    account_id=account.id,
                    statement_from=frm.isoformat(),
                    statement_to=to.isoformat(),
                    payment_due=due.isoformat(),
                    is_generated=True,
                )
            )
            db.flush()

    for key, value in SEED_SETTINGS.items():
        db.add(models.Setting(key=key, value=value))

    db.commit()


def main() -> None:
    ensure_schema()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
