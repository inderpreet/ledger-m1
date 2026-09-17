from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Account, BudgetCategory


def get_account_or_404(db: Session, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


def require_bank(account: Account, field: str = "target_account_id") -> Account:
    if account.account_type != "bank":
        raise HTTPException(
            status_code=422,
            detail=f"{field} must reference a bank account",
        )
    return account


def validate_item_target(db: Session, item_type: str, target_account_id: int) -> Account:
    account = get_account_or_404(db, target_account_id)
    if item_type == "income":
        require_bank(account, "target_account_id")
    return account


def validate_funding_account(db: Session, funding_account_id: int) -> Account:
    account = get_account_or_404(db, funding_account_id)
    return require_bank(account, "funding_account_id")


def normalize_category_name(name: str) -> str:
    cleaned = " ".join(name.split())
    if not cleaned:
        raise HTTPException(status_code=422, detail="Budget category name is required")
    return cleaned


def validate_category(db: Session, category: str | None) -> str | None:
    if category is None:
        return None
    raw = str(category).strip()
    if raw == "":
        return None
    name = normalize_category_name(raw)
    row = (
        db.query(BudgetCategory)
        .filter(func.lower(BudgetCategory.name) == name.lower())
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=422,
            detail="Unknown budget category. Add it under Budgets on the Expenses page first.",
        )
    return row.name
