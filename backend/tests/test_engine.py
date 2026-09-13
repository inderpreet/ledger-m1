from dataclasses import dataclass
from datetime import date

from app.engine import (
    cycles_to_insert,
    daily_cashflow,
    daily_cc_cashflow,
    expenses_by_category,
    first_low_balance_date,
    generate_cycles,
    recurring_item_fires_on,
    statement_total,
)


@dataclass
class Item:
    description: str = ""
    item_type: str = "expense"
    amount: float | None = 0.0
    day_of_month: int | None = 1
    start_date: date | None = None
    end_date: date | None = None
    target_account_id: int = 0
    active: bool = True
    item_date: date | None = None
    term: str = "monthly"
    category: str | None = None


@dataclass
class Account:
    id: int
    name: str
    account_type: str
    opening_balance: float | None = 0.0


@dataclass
class Cycle:
    id: int
    account_id: int
    statement_from: date
    statement_to: date
    payment_due: date
    is_generated: bool = True


def test_sign_convention_expense_minus_refund():
    card = Account(id=10, name="TD CC", account_type="credit_card")
    items_recurring = [
        Item(item_type="expense", amount=100.0, day_of_month=5, target_account_id=10),
    ]
    items_one_off = [
        Item(item_type="income", amount=20.0, item_date=date(2026, 8, 20), target_account_id=10),
    ]
    total = statement_total(
        card,
        date(2026, 8, 5),
        date(2026, 9, 3),
        items_recurring,
        items_one_off,
    )
    assert total == 80.0


def test_month_spanning_cycle_captures_both_months_without_double_count():
    card = Account(id=10, name="Scotia CC", account_type="credit_card")
    day_20 = Item(item_type="expense", amount=40.0, day_of_month=20, target_account_id=10)
    day_10 = Item(item_type="expense", amount=25.0, day_of_month=10, target_account_id=10)

    spanning = statement_total(
        card,
        date(2026, 1, 15),
        date(2026, 2, 14),
        [day_20, day_10],
        [],
    )
    # Jan 20 + Feb 10, each once
    assert spanning == 65.0

    within_january = statement_total(
        card,
        date(2026, 1, 1),
        date(2026, 1, 31),
        [day_20, day_10],
        [],
    )
    # day 10 and day 20 each fire once in January — no double-count
    assert within_january == 65.0


def test_day_of_month_overflow_clamps_to_month_end():
    item = Item(day_of_month=31, amount=10.0, item_type="expense", target_account_id=1)

    assert recurring_item_fires_on(item, date(2026, 4, 30)) is True
    assert recurring_item_fires_on(item, date(2026, 5, 1)) is False
    assert recurring_item_fires_on(item, date(2026, 4, 1)) is False

    # 2026 is not a leap year
    assert recurring_item_fires_on(item, date(2026, 2, 28)) is True
    assert recurring_item_fires_on(item, date(2026, 3, 1)) is False

    # 2024 is a leap year
    assert recurring_item_fires_on(item, date(2024, 2, 29)) is True
    assert recurring_item_fires_on(item, date(2024, 3, 1)) is False


def test_start_end_date_bounds():
    ending = Item(
        day_of_month=10,
        amount=50.0,
        item_type="expense",
        target_account_id=1,
        end_date=date(2026, 6, 15),
    )
    assert recurring_item_fires_on(ending, date(2026, 6, 10)) is True
    assert recurring_item_fires_on(ending, date(2026, 7, 10)) is False

    starting = Item(
        day_of_month=10,
        amount=50.0,
        item_type="expense",
        target_account_id=1,
        start_date=date(2026, 8, 1),
    )
    assert recurring_item_fires_on(starting, date(2026, 7, 10)) is False
    assert recurring_item_fires_on(starting, date(2026, 8, 10)) is True


def test_biweekly_fires_every_14_days_from_start():
    item = Item(
        description="Salary IP",
        item_type="income",
        amount=4546.21,
        start_date=date(2026, 9, 4),
        term="biweekly",
        target_account_id=1,
    )
    assert recurring_item_fires_on(item, date(2026, 9, 4)) is True
    assert recurring_item_fires_on(item, date(2026, 9, 18)) is True
    assert recurring_item_fires_on(item, date(2026, 10, 2)) is True
    assert recurring_item_fires_on(item, date(2026, 9, 5)) is False
    assert recurring_item_fires_on(item, date(2026, 9, 17)) is False
    assert recurring_item_fires_on(item, date(2026, 9, 3)) is False

    ended = Item(
        description="Salary IP",
        item_type="income",
        amount=4546.21,
        start_date=date(2026, 9, 4),
        end_date=date(2026, 9, 10),
        term="biweekly",
        target_account_id=1,
    )
    assert recurring_item_fires_on(ended, date(2026, 9, 4)) is True
    assert recurring_item_fires_on(ended, date(2026, 9, 18)) is False

    no_anchor = Item(amount=100.0, term="biweekly", target_account_id=1)
    assert recurring_item_fires_on(no_anchor, date(2026, 9, 4)) is False


def test_biweekly_counted_in_statement_total():
    card = Account(id=10, name="Scotia CC", account_type="credit_card")
    item = Item(
        description="Card spend",
        item_type="expense",
        amount=50.0,
        start_date=date(2026, 8, 7),
        term="biweekly",
        target_account_id=10,
    )
    # 2026-08-07 and 2026-08-21 fall in Aug 5–Sep 3; 2026-09-04 is after the cycle
    total = statement_total(card, date(2026, 8, 5), date(2026, 9, 3), [item], [])
    assert total == 100.0


def test_cc_isolation_bank_moves_only_on_payment_due():
    bank = Account(id=1, name="Scotia", account_type="bank", opening_balance=1000.0)
    card = Account(id=10, name="Scotia CC", account_type="credit_card")
    expense = Item(
        item_type="expense",
        amount=100.0,
        item_date=date(2026, 8, 20),
        target_account_id=10,
    )
    cycle = Cycle(
        id=1,
        account_id=10,
        statement_from=date(2026, 7, 12),
        statement_to=date(2026, 8, 11),
        payment_due=date(2026, 9, 1),
    )
    # Charge is on 2026-08-20, which is AFTER this cycle's statement_to.
    # Use a cycle that includes the charge date so the lump sum is $100.
    cycle = Cycle(
        id=1,
        account_id=10,
        statement_from=date(2026, 8, 5),
        statement_to=date(2026, 9, 3),
        payment_due=date(2026, 9, 24),
    )
    totals = {
        1: statement_total(card, cycle.statement_from, cycle.statement_to, [], [expense]),
    }
    assert totals[1] == 100.0

    rows = daily_cashflow(
        accounts=[bank, card],
        recurring_items=[],
        one_off_items=[expense],
        cycles=[cycle],
        statement_totals=totals,
        funding_by_card={10: 1},
        start_date=date(2026, 8, 19),
        end_date=date(2026, 9, 24),
    )
    by_date = {row["date"]: row[1] for row in rows}
    assert by_date[date(2026, 8, 20)] == 1000.0
    assert by_date[date(2026, 9, 23)] == 1000.0
    assert by_date[date(2026, 9, 24)] == 900.0
    due_row = next(row for row in rows if row["date"] == date(2026, 9, 24))
    assert due_row["movements"] == [
        {
            "account_id": 1,
            "description": "Scotia CC payment",
            "amount": -100.0,
            "kind": "cc_payment",
        }
    ]


def test_idempotent_cycle_generation_skips_existing_and_hand_edited():
    generated = generate_cycles(
        account_id=10,
        anchor_from=date(2026, 8, 5),
        anchor_to=date(2026, 9, 3),
        anchor_due=date(2026, 9, 24),
        model_end_date=date(2026, 12, 31),
    )
    assert generated[0] == (date(2026, 8, 5), date(2026, 9, 3), date(2026, 9, 24))
    assert all(frm <= date(2026, 12, 31) for frm, _, _ in generated)

    existing = [
        Cycle(
            id=1,
            account_id=10,
            statement_from=date(2026, 8, 5),
            statement_to=date(2026, 9, 3),
            payment_due=date(2026, 9, 24),
            is_generated=True,
        ),
        Cycle(
            id=2,
            account_id=10,
            statement_from=date(2026, 9, 5),
            statement_to=date(2026, 10, 3),
            payment_due=date(2026, 10, 24),
            is_generated=False,
        ),
    ]
    first_pass = cycles_to_insert(existing, generated)
    assert (date(2026, 8, 5), date(2026, 9, 3), date(2026, 9, 24)) not in first_pass
    assert (date(2026, 9, 5), date(2026, 10, 3), date(2026, 10, 24)) not in first_pass

    already_all = [
        Cycle(id=i, account_id=10, statement_from=frm, statement_to=to, payment_due=due)
        for i, (frm, to, due) in enumerate(generated, start=1)
    ]
    assert cycles_to_insert(already_all, generated) == []


def test_daily_cashflow_records_item_descriptions():
    bank = Account(id=1, name="Scotia", account_type="bank", opening_balance=1000.0)
    item = Item(
        description="Alectra",
        item_type="expense",
        amount=150.0,
        day_of_month=23,
        target_account_id=1,
    )
    rows = daily_cashflow(
        accounts=[bank],
        recurring_items=[item],
        one_off_items=[],
        cycles=[],
        statement_totals={},
        funding_by_card={},
        start_date=date(2026, 9, 23),
        end_date=date(2026, 9, 23),
    )
    assert rows[0][1] == 850.0
    assert rows[0]["movements"] == [
        {
            "account_id": 1,
            "description": "Alectra",
            "amount": -150.0,
            "kind": "recurring",
        }
    ]


def test_cc_cashflow_uses_card_items_only():
    bank = Account(id=1, name="Scotia", account_type="bank", opening_balance=5000.0)
    card = Account(id=10, name="Scotia CC", account_type="credit_card")
    bank_bill = Item(
        description="Rogers",
        item_type="expense",
        amount=62.15,
        day_of_month=15,
        target_account_id=1,
    )
    card_spend = Item(
        description="Gas",
        item_type="expense",
        amount=40.0,
        item_date=date(2026, 9, 15),
        target_account_id=10,
    )
    rows = daily_cc_cashflow(
        accounts=[bank, card],
        recurring_items=[bank_bill],
        one_off_items=[card_spend],
        start_date=date(2026, 9, 14),
        end_date=date(2026, 9, 15),
    )
    assert rows[0][10] == 0.0
    assert rows[1][10] == 40.0
    assert rows[1]["movements"] == [
        {
            "account_id": 10,
            "description": "Gas",
            "amount": 40.0,
            "kind": "one_off",
        }
    ]
    assert 1 not in rows[1]


def test_cc_payment_zeros_card_and_leaves_next_cycle():
    bank = Account(id=1, name="Scotia", account_type="bank", opening_balance=1000.0)
    card = Account(id=10, name="Scotia CC", account_type="credit_card")
    first = Item(
        description="Gas",
        item_type="expense",
        amount=100.0,
        item_date=date(2026, 8, 20),
        target_account_id=10,
    )
    second = Item(
        description="Groceries",
        item_type="expense",
        amount=40.0,
        item_date=date(2026, 9, 10),
        target_account_id=10,
    )
    cycle1 = Cycle(
        id=1,
        account_id=10,
        statement_from=date(2026, 8, 5),
        statement_to=date(2026, 9, 3),
        payment_due=date(2026, 9, 24),
    )
    cycle2 = Cycle(
        id=2,
        account_id=10,
        statement_from=date(2026, 9, 5),
        statement_to=date(2026, 10, 3),
        payment_due=date(2026, 10, 24),
    )
    totals = {
        1: statement_total(card, cycle1.statement_from, cycle1.statement_to, [], [first, second]),
        2: statement_total(card, cycle2.statement_from, cycle2.statement_to, [], [first, second]),
    }
    assert totals[1] == 100.0
    assert totals[2] == 40.0

    rows = daily_cc_cashflow(
        accounts=[bank, card],
        recurring_items=[],
        one_off_items=[first, second],
        start_date=date(2026, 8, 19),
        end_date=date(2026, 10, 24),
        cycles=[cycle1, cycle2],
        statement_totals=totals,
    )
    by_date = {row["date"]: row[10] for row in rows}
    assert by_date[date(2026, 8, 19)] == 0.0
    assert by_date[date(2026, 8, 20)] == 100.0
    assert by_date[date(2026, 9, 10)] == 140.0
    assert by_date[date(2026, 9, 23)] == 140.0
    assert by_date[date(2026, 9, 24)] == 40.0
    assert by_date[date(2026, 10, 23)] == 40.0
    assert by_date[date(2026, 10, 24)] == 0.0

    paid = next(row for row in rows if row["date"] == date(2026, 9, 24))
    assert {
        "account_id": 10,
        "description": "Scotia CC payment",
        "amount": -100.0,
        "kind": "cc_payment",
    } in paid["movements"]


def test_cc_opening_includes_unpaid_charges_before_window():
    card = Account(id=10, name="Scotia CC", account_type="credit_card")
    charge = Item(
        description="Gas",
        item_type="expense",
        amount=100.0,
        item_date=date(2026, 8, 20),
        target_account_id=10,
    )
    cycle = Cycle(
        id=1,
        account_id=10,
        statement_from=date(2026, 8, 5),
        statement_to=date(2026, 9, 3),
        payment_due=date(2026, 9, 24),
    )
    totals = {1: 100.0}
    rows = daily_cc_cashflow(
        accounts=[card],
        recurring_items=[],
        one_off_items=[charge],
        start_date=date(2026, 9, 10),
        end_date=date(2026, 9, 24),
        cycles=[cycle],
        statement_totals=totals,
    )
    assert rows[0]["date"] == date(2026, 9, 10)
    assert rows[0][10] == 100.0
    assert rows[0]["movements"] == []
    due = next(row for row in rows if row["date"] == date(2026, 9, 24))
    assert due[10] == 0.0


def test_cc_ignores_charges_before_cards_first_cycle():
    card = Account(id=10, name="TD CC", account_type="credit_card")
    other = Account(id=11, name="Scotia CC", account_type="credit_card")
    early = Item(
        description="Too early",
        item_type="expense",
        amount=50.0,
        item_date=date(2026, 7, 20),
        target_account_id=10,
    )
    in_cycle = Item(
        description="Gas",
        item_type="expense",
        amount=100.0,
        item_date=date(2026, 8, 20),
        target_account_id=10,
    )
    cycle = Cycle(
        id=1,
        account_id=10,
        statement_from=date(2026, 8, 5),
        statement_to=date(2026, 9, 3),
        payment_due=date(2026, 9, 24),
    )
    other_cycle = Cycle(
        id=2,
        account_id=11,
        statement_from=date(2026, 7, 12),
        statement_to=date(2026, 8, 11),
        payment_due=date(2026, 9, 1),
    )
    rows = daily_cc_cashflow(
        accounts=[card, other],
        recurring_items=[],
        one_off_items=[early, in_cycle],
        start_date=date(2026, 8, 19),
        end_date=date(2026, 8, 20),
        cycles=[cycle, other_cycle],
        statement_totals={1: 100.0, 2: 0.0},
    )
    assert rows[0][10] == 0.0
    assert rows[1][10] == 100.0


def test_expenses_by_category_clubs_recurring_and_one_off():
    recurring = [
        Item(
            description="Mortgage",
            item_type="expense",
            amount=1000.0,
            day_of_month=1,
            category="Housing & Debt",
        ),
        Item(
            description="Salary",
            item_type="income",
            amount=2000.0,
            day_of_month=1,
            category="Income",
        ),
        Item(
            description="Gas",
            item_type="expense",
            amount=40.0,
            start_date=date(2026, 9, 4),
            term="biweekly",
            category="Utilities",
        ),
    ]
    one_offs = [
        Item(
            description="Property Tax",
            item_type="expense",
            amount=300.0,
            item_date=date(2026, 9, 17),
            category="Housing & Debt",
        ),
    ]
    # Sept 1 + Oct 1 mortgages; Sept 4 + 18 gas; one property tax
    rows = expenses_by_category(recurring, one_offs, date(2026, 9, 1), date(2026, 10, 1))
    by_cat = {r["category"]: r["amount"] for r in rows}
    assert by_cat["Housing & Debt"] == 2300.0
    assert by_cat["Utilities"] == 80.0
    assert "Income" not in by_cat


def test_first_low_balance_date():
    rows = [
        {"date": date(2026, 9, 1), 1: 8000.0},
        {"date": date(2026, 9, 2), 1: 5500.0},
        {"date": date(2026, 9, 3), 1: 4000.0},
    ]
    assert first_low_balance_date(rows, 1, 6000.0) == date(2026, 9, 2)
    assert first_low_balance_date(rows, 1, 3000.0) is None
