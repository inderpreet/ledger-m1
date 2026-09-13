from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

def normalize_term(value: str | None) -> str:
    raw = str(value or "monthly").lower().replace("-", "").replace(" ", "")
    if raw == "biweekly":
        return "biweekly"
    if raw == "monthly":
        return "monthly"
    raise ValueError("term must be 'monthly' or 'biweekly'")


class AccountCreate(BaseModel):
    name: str
    account_type: str
    opening_balance: float | None = None
    opening_balance_date: str | None = None
    funding_account_id: int | None = None

    @field_validator("account_type")
    @classmethod
    def account_type_ok(cls, v: str) -> str:
        if v not in ("bank", "credit_card"):
            raise ValueError("account_type must be 'bank' or 'credit_card'")
        return v


class AccountUpdate(BaseModel):
    name: str | None = None
    opening_balance: float | None = None
    opening_balance_date: str | None = None
    funding_account_id: int | None = None


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    account_type: str
    opening_balance: float | None
    opening_balance_date: str | None
    funding_account_id: int | None = None


class RecurringItemCreate(BaseModel):
    description: str
    item_type: str
    amount: float | None = None
    day_of_month: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    target_account_id: int
    category: str | None = None
    active: bool = True
    term: str = "monthly"

    @field_validator("item_type")
    @classmethod
    def item_type_ok(cls, v: str) -> str:
        if v not in ("income", "expense"):
            raise ValueError("item_type must be 'income' or 'expense'")
        return v

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("amount must be greater than 0")
        return v

    @field_validator("day_of_month")
    @classmethod
    def day_ok(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 31):
            raise ValueError("day_of_month must be between 1 and 31")
        return v

    @field_validator("term")
    @classmethod
    def term_ok(cls, v: str) -> str:
        return normalize_term(v)

    @model_validator(mode="after")
    def dates_ordered(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.term == "biweekly" and not self.start_date:
            raise ValueError("bi-weekly items need a start_date (first payday)")
        return self


class RecurringItemUpdate(BaseModel):
    description: str | None = None
    item_type: str | None = None
    amount: float | None = None
    day_of_month: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    target_account_id: int | None = None
    category: str | None = None
    active: bool | None = None
    term: str | None = None

    @field_validator("item_type")
    @classmethod
    def item_type_ok(cls, v: str | None) -> str | None:
        if v is not None and v not in ("income", "expense"):
            raise ValueError("item_type must be 'income' or 'expense'")
        return v

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("amount must be greater than 0")
        return v

    @field_validator("day_of_month")
    @classmethod
    def day_ok(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 31):
            raise ValueError("day_of_month must be between 1 and 31")
        return v

    @field_validator("term")
    @classmethod
    def term_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return normalize_term(v)


class RecurringItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    item_type: str
    amount: float | None
    day_of_month: int | None
    start_date: str | None
    end_date: str | None
    target_account_id: int
    category: str | None
    active: bool
    term: str


class OneOffItemCreate(BaseModel):
    description: str
    item_type: str
    amount: float = Field(gt=0)
    item_date: str
    target_account_id: int
    category: str | None = None

    @field_validator("item_type")
    @classmethod
    def item_type_ok(cls, v: str) -> str:
        if v not in ("income", "expense"):
            raise ValueError("item_type must be 'income' or 'expense'")
        return v


class OneOffItemUpdate(BaseModel):
    description: str | None = None
    item_type: str | None = None
    amount: float | None = Field(default=None, gt=0)
    item_date: str | None = None
    target_account_id: int | None = None
    category: str | None = None

    @field_validator("item_type")
    @classmethod
    def item_type_ok(cls, v: str | None) -> str | None:
        if v is not None and v not in ("income", "expense"):
            raise ValueError("item_type must be 'income' or 'expense'")
        return v


class OneOffItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    item_type: str
    amount: float
    item_date: str
    target_account_id: int
    category: str | None


class SettingsOut(BaseModel):
    low_balance_threshold: float
    model_end_date: str


class SettingsUpdate(BaseModel):
    low_balance_threshold: float | None = None
    model_end_date: str | None = None


class FundingUpdate(BaseModel):
    funding_account_id: int


class CreditCardOut(BaseModel):
    id: int
    name: str
    funding_account_id: int | None
    funding_account_name: str | None = None


class StatementCycleCreate(BaseModel):
    account_id: int
    statement_from: str
    statement_to: str
    payment_due: str


class StatementCycleUpdate(BaseModel):
    statement_from: str | None = None
    statement_to: str | None = None
    payment_due: str | None = None


class StatementCycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    statement_from: str
    statement_to: str
    payment_due: str
    is_generated: bool


class LoginIn(BaseModel):
    username: str
    password: str


class AuthStatusOut(BaseModel):
    configured: bool


class AuthMeOut(BaseModel):
    username: str
