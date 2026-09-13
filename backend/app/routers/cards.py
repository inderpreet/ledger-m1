from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.engine import cycles_to_insert, generate_cycles, parse_date
from app.models import Account, CreditCardConfig, StatementCycle
from app.schemas import (
    CreditCardOut,
    FundingUpdate,
    StatementCycleCreate,
    StatementCycleOut,
    StatementCycleUpdate,
)
from app.services import get_settings
from app.validation import get_account_or_404, validate_funding_account

router = APIRouter()


@router.get("/credit-cards", response_model=list[CreditCardOut])
def list_credit_cards(db: Session = Depends(get_db)):
    cards = db.query(Account).filter(Account.account_type == "credit_card").order_by(Account.id).all()
    out = []
    for card in cards:
        funding = card.credit_card_config
        out.append(
            CreditCardOut(
                id=card.id,
                name=card.name,
                funding_account_id=funding.funding_account_id if funding else None,
                funding_account_name=funding.funding_account.name if funding else None,
            )
        )
    return out


@router.put("/credit-cards/{account_id}/funding", response_model=CreditCardOut)
def update_funding(account_id: int, payload: FundingUpdate, db: Session = Depends(get_db)):
    account = get_account_or_404(db, account_id)
    if account.account_type != "credit_card":
        raise HTTPException(status_code=422, detail="Account is not a credit card")
    funding_account = validate_funding_account(db, payload.funding_account_id)
    if account.credit_card_config:
        account.credit_card_config.funding_account_id = payload.funding_account_id
    else:
        db.add(
            CreditCardConfig(
                account_id=account.id,
                funding_account_id=payload.funding_account_id,
            )
        )
    db.commit()
    db.refresh(account)
    return CreditCardOut(
        id=account.id,
        name=account.name,
        funding_account_id=payload.funding_account_id,
        funding_account_name=funding_account.name,
    )


@router.get("/statement-cycles", response_model=list[StatementCycleOut])
def list_cycles(account_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(StatementCycle)
    if account_id is not None:
        q = q.filter(StatementCycle.account_id == account_id)
    return q.order_by(StatementCycle.account_id, StatementCycle.statement_from).all()


@router.post("/statement-cycles", response_model=StatementCycleOut, status_code=201)
def create_cycle(payload: StatementCycleCreate, db: Session = Depends(get_db)):
    account = get_account_or_404(db, payload.account_id)
    if account.account_type != "credit_card":
        raise HTTPException(status_code=422, detail="Cycles can only be created for credit cards")
    existing = (
        db.query(StatementCycle)
        .filter(
            StatementCycle.account_id == payload.account_id,
            StatementCycle.statement_from == payload.statement_from,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=422, detail="A cycle with this statement_from already exists")
    cycle = StatementCycle(
        account_id=payload.account_id,
        statement_from=payload.statement_from,
        statement_to=payload.statement_to,
        payment_due=payload.payment_due,
        is_generated=False,
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return cycle


@router.post("/statement-cycles/{account_id}/generate", response_model=list[StatementCycleOut])
def generate_account_cycles(account_id: int, db: Session = Depends(get_db)):
    account = get_account_or_404(db, account_id)
    if account.account_type != "credit_card":
        raise HTTPException(status_code=422, detail="Cycles can only be generated for credit cards")
    existing = (
        db.query(StatementCycle)
        .filter(StatementCycle.account_id == account_id)
        .order_by(StatementCycle.statement_from)
        .all()
    )
    if not existing:
        raise HTTPException(
            status_code=400,
            detail="Enter a starting statement cycle before generating",
        )
    anchor = existing[0]
    settings = get_settings(db)
    model_end = parse_date(settings["model_end_date"])
    frm = parse_date(anchor.statement_from)
    to = parse_date(anchor.statement_to)
    due = parse_date(anchor.payment_due)
    if not frm or not to or not due or not model_end:
        raise HTTPException(status_code=422, detail="Anchor cycle has invalid dates")
    generated = generate_cycles(account_id, frm, to, due, model_end)
    for frm, to, due in cycles_to_insert(existing, generated):
        db.add(
            StatementCycle(
                account_id=account_id,
                statement_from=frm.isoformat(),
                statement_to=to.isoformat(),
                payment_due=due.isoformat(),
                is_generated=True,
            )
        )
    db.commit()
    return (
        db.query(StatementCycle)
        .filter(StatementCycle.account_id == account_id)
        .order_by(StatementCycle.statement_from)
        .all()
    )


@router.put("/statement-cycles/{cycle_id}", response_model=StatementCycleOut)
def update_cycle(cycle_id: int, payload: StatementCycleUpdate, db: Session = Depends(get_db)):
    cycle = db.get(StatementCycle, cycle_id)
    if cycle is None:
        raise HTTPException(status_code=404, detail="Statement cycle not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(cycle, key, value)
    cycle.is_generated = False
    db.commit()
    db.refresh(cycle)
    return cycle


@router.delete("/statement-cycles/{cycle_id}", status_code=204)
def delete_cycle(cycle_id: int, db: Session = Depends(get_db)):
    cycle = db.get(StatementCycle, cycle_id)
    if cycle is None:
        raise HTTPException(status_code=404, detail="Statement cycle not found")
    db.delete(cycle)
    db.commit()


@router.delete("/credit-cards/{account_id}/statement-cycles", status_code=204)
def delete_account_cycles(account_id: int, db: Session = Depends(get_db)):
    account = get_account_or_404(db, account_id)
    if account.account_type != "credit_card":
        raise HTTPException(status_code=422, detail="Account is not a credit card")
    db.query(StatementCycle).filter(StatementCycle.account_id == account_id).delete(
        synchronize_session=False
    )
    db.commit()
