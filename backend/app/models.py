from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    account_type: Mapped[str] = mapped_column(String, nullable=False)
    opening_balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    opening_balance_date: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("account_type IN ('bank','credit_card')", name="ck_accounts_type"),
    )

    credit_card_config: Mapped["CreditCardConfig | None"] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        uselist=False,
        foreign_keys="CreditCardConfig.account_id",
    )
    funded_cards: Mapped[list["CreditCardConfig"]] = relationship(
        back_populates="funding_account",
        foreign_keys="CreditCardConfig.funding_account_id",
    )
    statement_cycles: Mapped[list["StatementCycle"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )
    recurring_items: Mapped[list["RecurringItem"]] = relationship(back_populates="target_account")
    one_off_items: Mapped[list["OneOffItem"]] = relationship(back_populates="target_account")


class CreditCardConfig(Base):
    __tablename__ = "credit_card_config"

    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    funding_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)

    account: Mapped[Account] = relationship(
        back_populates="credit_card_config",
        foreign_keys=[account_id],
    )
    funding_account: Mapped[Account] = relationship(
        back_populates="funded_cards",
        foreign_keys=[funding_account_id],
    )


class StatementCycle(Base):
    __tablename__ = "statement_cycles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    statement_from: Mapped[str] = mapped_column(String, nullable=False)
    statement_to: Mapped[str] = mapped_column(String, nullable=False)
    payment_due: Mapped[str] = mapped_column(String, nullable=False)
    is_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (UniqueConstraint("account_id", "statement_from", name="uq_cycle_account_from"),)

    account: Mapped[Account] = relationship(back_populates="statement_cycles")


class RecurringItem(Base):
    __tablename__ = "recurring_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    item_type: Mapped[str] = mapped_column(String, nullable=False)
    # Nullable so incomplete seed rows (unknown amount / day) can be stored.
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_date: Mapped[str | None] = mapped_column(String, nullable=True)
    end_date: Mapped[str | None] = mapped_column(String, nullable=True)
    target_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    term: Mapped[str] = mapped_column(String, nullable=False, default="monthly")

    __table_args__ = (
        CheckConstraint("item_type IN ('income','expense')", name="ck_recurring_type"),
        CheckConstraint(
            "day_of_month IS NULL OR (day_of_month BETWEEN 1 AND 31)",
            name="ck_recurring_dom",
        ),
        CheckConstraint("term IN ('monthly','biweekly')", name="ck_recurring_term"),
    )

    target_account: Mapped[Account] = relationship(back_populates="recurring_items")


class OneOffItem(Base):
    __tablename__ = "one_off_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    item_type: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    item_date: Mapped[str] = mapped_column(String, nullable=False)
    target_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (CheckConstraint("item_type IN ('income','expense')", name="ck_oneoff_type"),)

    target_account: Mapped[Account] = relationship(back_populates="one_off_items")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)


class BudgetCategory(Base):
    __tablename__ = "budget_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    period: Mapped[str] = mapped_column(String, nullable=False, default="monthly")

    __table_args__ = (
        CheckConstraint("period IN ('monthly','biweekly','yearly')", name="ck_budget_period"),
    )


class AuthUser(Base):
    __tablename__ = "auth_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    expires_at: Mapped[str] = mapped_column(String, nullable=False)
