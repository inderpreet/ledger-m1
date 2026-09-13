from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OneOffItem, RecurringItem
from app.schemas import (
    OneOffItemCreate,
    OneOffItemOut,
    OneOffItemUpdate,
    RecurringItemCreate,
    RecurringItemOut,
    RecurringItemUpdate,
)
from app.validation import validate_item_target

router = APIRouter()


@router.get("/recurring-items", response_model=list[RecurringItemOut])
def list_recurring(db: Session = Depends(get_db)):
    return db.query(RecurringItem).order_by(RecurringItem.id).all()


@router.post("/recurring-items", response_model=RecurringItemOut, status_code=201)
def create_recurring(payload: RecurringItemCreate, db: Session = Depends(get_db)):
    validate_item_target(db, payload.item_type, payload.target_account_id)
    item = RecurringItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/recurring-items/{item_id}", response_model=RecurringItemOut)
def update_recurring(item_id: int, payload: RecurringItemUpdate, db: Session = Depends(get_db)):
    item = db.get(RecurringItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Recurring item not found")
    data = payload.model_dump(exclude_unset=True)
    item_type = data.get("item_type", item.item_type)
    target_id = data.get("target_account_id", item.target_account_id)
    start = data.get("start_date", item.start_date)
    end = data.get("end_date", item.end_date)
    term = data.get("term", item.term)
    if start and end and end < start:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    if term == "biweekly" and not start:
        raise HTTPException(status_code=422, detail="bi-weekly items need a start_date (first payday)")
    validate_item_target(db, item_type, target_id)
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/recurring-items/{item_id}", status_code=204)
def delete_recurring(item_id: int, db: Session = Depends(get_db)):
    item = db.get(RecurringItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Recurring item not found")
    db.delete(item)
    db.commit()


@router.get("/one-off-items", response_model=list[OneOffItemOut])
def list_one_off(db: Session = Depends(get_db)):
    return db.query(OneOffItem).order_by(OneOffItem.item_date, OneOffItem.id).all()


@router.post("/one-off-items", response_model=OneOffItemOut, status_code=201)
def create_one_off(payload: OneOffItemCreate, db: Session = Depends(get_db)):
    validate_item_target(db, payload.item_type, payload.target_account_id)
    item = OneOffItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/one-off-items/{item_id}", response_model=OneOffItemOut)
def update_one_off(item_id: int, payload: OneOffItemUpdate, db: Session = Depends(get_db)):
    item = db.get(OneOffItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="One-off item not found")
    data = payload.model_dump(exclude_unset=True)
    item_type = data.get("item_type", item.item_type)
    target_id = data.get("target_account_id", item.target_account_id)
    validate_item_target(db, item_type, target_id)
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/one-off-items/{item_id}", status_code=204)
def delete_one_off(item_id: int, db: Session = Depends(get_db)):
    item = db.get(OneOffItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="One-off item not found")
    db.delete(item)
    db.commit()
