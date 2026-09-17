from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SettingsOut, SettingsUpdate
from app.services import (
    compute_cc_cashflow,
    compute_daily_cashflow,
    compute_dashboard,
    compute_statement_totals,
    get_settings,
    upsert_setting,
)

from app.security import current_user

router = APIRouter(dependencies=[Depends(current_user)])


def _parse_iso(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{field} must be YYYY-MM-DD") from None


@router.get("/settings", response_model=SettingsOut)
def read_settings(db: Session = Depends(get_db)):
    return get_settings(db)


@router.put("/settings", response_model=SettingsOut)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    if payload.low_balance_threshold is not None:
        upsert_setting(db, "low_balance_threshold", str(payload.low_balance_threshold))
    if payload.model_start_date is not None:
        _parse_iso(payload.model_start_date, "model_start_date")
        upsert_setting(db, "model_start_date", payload.model_start_date)
    if payload.model_end_date is not None:
        _parse_iso(payload.model_end_date, "model_end_date")
        upsert_setting(db, "model_end_date", payload.model_end_date)
    db.flush()
    settings = get_settings(db)
    if date.fromisoformat(settings["model_start_date"]) > date.fromisoformat(settings["model_end_date"]):
        raise HTTPException(
            status_code=422,
            detail="model_start_date must be on or before model_end_date",
        )
    db.commit()
    return get_settings(db)


@router.get("/cc-statement-totals")
def cc_statement_totals(db: Session = Depends(get_db)):
    return compute_statement_totals(db)


@router.get("/daily-cashflow")
def daily_cashflow_endpoint(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
):
    return compute_daily_cashflow(db, start, end)


@router.get("/cc-cashflow")
def cc_cashflow_endpoint(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
):
    return compute_cc_cashflow(db, start, end)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    return compute_dashboard(db)
