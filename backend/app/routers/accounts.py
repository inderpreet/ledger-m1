from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, CreditCardConfig, OneOffItem, RecurringItem, StatementCycle
from app.schemas import AccountCreate, AccountOut, AccountUpdate
from app.validation import get_account_or_404, validate_funding_account

from app.security import current_user

router = APIRouter(dependencies=[Depends(current_user)])


def _to_out(account: Account) -> AccountOut:
    funding_id = account.credit_card_config.funding_account_id if account.credit_card_config else None
    return AccountOut(
        id=account.id,
        name=account.name,
        account_type=account.account_type,
        opening_balance=account.opening_balance,
        opening_balance_date=account.opening_balance_date,
        funding_account_id=funding_id,
    )


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    return [_to_out(a) for a in db.query(Account).order_by(Account.id).all()]


@router.post("/accounts", response_model=AccountOut, status_code=201)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    if db.query(Account).filter(Account.name == payload.name).first():
        raise HTTPException(status_code=422, detail="Account name already exists")
    account = Account(
        name=payload.name,
        account_type=payload.account_type,
        opening_balance=payload.opening_balance if payload.account_type == "bank" else None,
        opening_balance_date=payload.opening_balance_date
        if payload.account_type == "bank"
        else None,
    )
    if payload.account_type == "bank" and payload.opening_balance is not None and not account.opening_balance_date:
        account.opening_balance_date = date.today().isoformat()
    db.add(account)
    db.flush()
    if payload.account_type == "credit_card" and payload.funding_account_id is not None:
        validate_funding_account(db, payload.funding_account_id)
        db.add(
            CreditCardConfig(
                account_id=account.id,
                funding_account_id=payload.funding_account_id,
            )
        )
    db.commit()
    db.refresh(account)
    return _to_out(account)


@router.get("/accounts/{account_id}", response_model=AccountOut)
def get_account(account_id: int, db: Session = Depends(get_db)):
    return _to_out(get_account_or_404(db, account_id))


@router.put("/accounts/{account_id}", response_model=AccountOut)
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)):
    account = get_account_or_404(db, account_id)
    if payload.name is not None:
        clash = db.query(Account).filter(Account.name == payload.name, Account.id != account_id).first()
        if clash:
            raise HTTPException(status_code=422, detail="Account name already exists")
        account.name = payload.name
    if account.account_type == "bank":
        if payload.opening_balance is not None:
            account.opening_balance = payload.opening_balance
            account.opening_balance_date = payload.opening_balance_date or date.today().isoformat()
        elif payload.opening_balance_date is not None:
            account.opening_balance_date = payload.opening_balance_date
    if payload.funding_account_id is not None:
        if account.account_type != "credit_card":
            raise HTTPException(status_code=422, detail="funding_account_id is only valid for credit cards")
        validate_funding_account(db, payload.funding_account_id)
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
    return _to_out(account)


@router.delete("/accounts/{account_id}", status_code=204)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = get_account_or_404(db, account_id)
    if db.query(RecurringItem).filter(RecurringItem.target_account_id == account_id).first():
        raise HTTPException(status_code=422, detail="Account has recurring items")
    if db.query(OneOffItem).filter(OneOffItem.target_account_id == account_id).first():
        raise HTTPException(status_code=422, detail="Account has one-off items")
    if db.query(CreditCardConfig).filter(CreditCardConfig.funding_account_id == account_id).first():
        raise HTTPException(status_code=422, detail="Account funds a credit card")
    if db.query(StatementCycle).filter(StatementCycle.account_id == account_id).first():
        raise HTTPException(status_code=422, detail="Account has statement cycles")
    if account.credit_card_config:
        db.delete(account.credit_card_config)
    db.delete(account)
    db.commit()
