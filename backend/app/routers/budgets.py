from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BudgetCategory, OneOffItem, RecurringItem
from app.schemas import BudgetCategoryCreate, BudgetCategoryOut, BudgetCategoryUpdate
from app.security import current_user
from app.validation import normalize_category_name

router = APIRouter(dependencies=[Depends(current_user)])


def _by_name_ci(db: Session, name: str, skip_id: int | None = None) -> BudgetCategory | None:
    query = db.query(BudgetCategory).filter(func.lower(BudgetCategory.name) == name.lower())
    if skip_id is not None:
        query = query.filter(BudgetCategory.id != skip_id)
    return query.first()


@router.get("/budget-categories", response_model=list[BudgetCategoryOut])
def list_budget_categories(db: Session = Depends(get_db)):
    return db.query(BudgetCategory).order_by(BudgetCategory.name).all()


@router.post("/budget-categories", response_model=BudgetCategoryOut, status_code=201)
def create_budget_category(payload: BudgetCategoryCreate, db: Session = Depends(get_db)):
    name = normalize_category_name(payload.name)
    if _by_name_ci(db, name):
        raise HTTPException(status_code=422, detail="A budget category with that name already exists")
    row = BudgetCategory(name=name, amount=payload.amount, period=payload.period)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/budget-categories/{category_id}", response_model=BudgetCategoryOut)
def update_budget_category(
    category_id: int,
    payload: BudgetCategoryUpdate,
    db: Session = Depends(get_db),
):
    row = db.get(BudgetCategory, category_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Budget category not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        name = normalize_category_name(data["name"])
        if _by_name_ci(db, name, skip_id=row.id):
            raise HTTPException(status_code=422, detail="A budget category with that name already exists")
        old = row.name
        row.name = name
        if old != name:
            db.query(RecurringItem).filter(RecurringItem.category == old).update(
                {RecurringItem.category: name},
                synchronize_session=False,
            )
            db.query(OneOffItem).filter(OneOffItem.category == old).update(
                {OneOffItem.category: name},
                synchronize_session=False,
            )
    if "amount" in data:
        row.amount = data["amount"]
    if "period" in data and data["period"] is not None:
        row.period = data["period"]
    db.commit()
    db.refresh(row)
    return row


@router.delete("/budget-categories/{category_id}", status_code=204)
def delete_budget_category(category_id: int, db: Session = Depends(get_db)):
    row = db.get(BudgetCategory, category_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Budget category not found")
    db.query(RecurringItem).filter(RecurringItem.category == row.name).update(
        {RecurringItem.category: None},
        synchronize_session=False,
    )
    db.query(OneOffItem).filter(OneOffItem.category == row.name).update(
        {OneOffItem.category: None},
        synchronize_session=False,
    )
    db.delete(row)
    db.commit()
