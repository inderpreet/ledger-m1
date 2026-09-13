"""Pure cash-flow calculation engine. No FastAPI or SQLAlchemy imports."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Any, Iterable

from dateutil.relativedelta import relativedelta


def parse_date(value: date | str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def add_months(d: date, n: int) -> date:
    return d + relativedelta(months=n)


def each_day(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _attr(obj: Any, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _normalize_term(value: Any) -> str:
    raw = str(value or "monthly").lower().replace("-", "").replace(" ", "")
    if raw == "biweekly":
        return "biweekly"
    return "monthly"


def recurring_item_fires_on(item: Any, d: date) -> bool:
    """True if a recurring item posts on calendar date d.

    Monthly: day-of-month match, overflow clamped to the last day of the month.
    Bi-weekly: every 14 days from start_date (the first payday).
    """
    if _attr(item, "active", True) is False:
        return False
    amount = _attr(item, "amount")
    if amount is None:
        return False

    start = parse_date(_attr(item, "start_date"))
    end = parse_date(_attr(item, "end_date"))
    if start and d < start:
        return False
    if end and d > end:
        return False

    if _normalize_term(_attr(item, "term", "monthly")) == "biweekly":
        if start is None:
            return False
        return (d - start).days % 14 == 0

    day_of_month = _attr(item, "day_of_month")
    if day_of_month is None:
        return False
    days_in_month = calendar.monthrange(d.year, d.month)[1]
    effective_day = min(int(day_of_month), days_in_month)
    return d.day == effective_day


def generate_cycles(
    account_id: int,
    anchor_from: date,
    anchor_to: date,
    anchor_due: date,
    model_end_date: date,
) -> list[tuple[date, date, date]]:
    cycles: list[tuple[date, date, date]] = []
    n = 0
    while True:
        frm = add_months(anchor_from, n)
        to = add_months(anchor_to, n)
        due = add_months(anchor_due, n)
        if frm > model_end_date:
            break
        cycles.append((frm, to, due))
        n += 1
    return cycles


def cycles_to_insert(
    existing: Iterable[Any],
    generated: Iterable[tuple[date, date, date]],
) -> list[tuple[date, date, date]]:
    """Return generated cycles that are not already present.

    Existing rows (including hand-edited is_generated=0) are never replaced.
    Identity is statement_from, matching UNIQUE(account_id, statement_from).
    """
    existing_froms = {parse_date(_attr(c, "statement_from")) for c in existing}
    return [triple for triple in generated if triple[0] not in existing_froms]


def statement_total(
    account: Any,
    statement_from: date,
    statement_to: date,
    recurring_items: Iterable[Any],
    one_off_items: Iterable[Any],
) -> float:
    """Amount owed on the card for this cycle. Positive = debit on due date."""
    account_id = _attr(account, "id")
    total = 0.0
    for item in recurring_items:
        if _attr(item, "target_account_id") != account_id:
            continue
        for d in each_day(statement_from, statement_to):
            if recurring_item_fires_on(item, d):
                amount = float(_attr(item, "amount"))
                total += amount if _attr(item, "item_type") == "expense" else -amount
    for item in one_off_items:
        if _attr(item, "target_account_id") != account_id:
            continue
        item_date = parse_date(_attr(item, "item_date"))
        if item_date is None:
            continue
        if statement_from <= item_date <= statement_to:
            amount = float(_attr(item, "amount"))
            total += amount if _attr(item, "item_type") == "expense" else -amount
    return total


def daily_cashflow(
    accounts: Iterable[Any],
    recurring_items: Iterable[Any],
    one_off_items: Iterable[Any],
    cycles: Iterable[Any],
    statement_totals: dict[int, float],
    funding_by_card: dict[int, int],
    start_date: date,
    end_date: date,
) -> list[dict]:
    account_list = list(accounts)
    bank_accounts = [a for a in account_list if _attr(a, "account_type") == "bank"]
    names = {_attr(a, "id"): _attr(a, "name") for a in account_list}
    balances: dict[int, float] = {}
    for a in bank_accounts:
        opening = _attr(a, "opening_balance")
        balances[_attr(a, "id")] = float(opening) if opening is not None else 0.0

    rows: list[dict] = []
    d = start_date
    while d <= end_date:
        movements: list[dict] = []
        for item in recurring_items:
            target = _attr(item, "target_account_id")
            if target in balances and recurring_item_fires_on(item, d):
                sign = 1 if _attr(item, "item_type") == "income" else -1
                delta = sign * float(_attr(item, "amount"))
                balances[target] += delta
                movements.append(
                    {
                        "account_id": target,
                        "description": _attr(item, "description") or "",
                        "amount": delta,
                        "kind": "recurring",
                    }
                )
        for item in one_off_items:
            target = _attr(item, "target_account_id")
            item_date = parse_date(_attr(item, "item_date"))
            if target in balances and item_date == d:
                sign = 1 if _attr(item, "item_type") == "income" else -1
                delta = sign * float(_attr(item, "amount"))
                balances[target] += delta
                movements.append(
                    {
                        "account_id": target,
                        "description": _attr(item, "description") or "",
                        "amount": delta,
                        "kind": "one_off",
                    }
                )
        for cycle in cycles:
            due = parse_date(_attr(cycle, "payment_due"))
            if due == d:
                card_id = _attr(cycle, "account_id")
                funding_id = funding_by_card.get(card_id)
                total = statement_totals[_attr(cycle, "id")]
                if funding_id in balances and total:
                    balances[funding_id] -= total
                    card_name = names.get(card_id) or "Credit card"
                    movements.append(
                        {
                            "account_id": funding_id,
                            "description": f"{card_name} payment",
                            "amount": -float(total),
                            "kind": "cc_payment",
                        }
                    )
        row = {"date": d, "movements": movements, **{a_id: balances[a_id] for a_id in balances}}
        rows.append(row)
        d += timedelta(days=1)
    return rows


def daily_cc_cashflow(
    accounts: Iterable[Any],
    recurring_items: Iterable[Any],
    one_off_items: Iterable[Any],
    start_date: date,
    end_date: date,
    cycles: Iterable[Any] | None = None,
    statement_totals: dict[int, float] | None = None,
) -> list[dict]:
    """Running amount owed on each card.

    Card-targeted expenses increase the balance on the charge date. On each
    cycle's payment_due, the statement total is subtracted — the same lump
    that hits the funding bank — so a fully paid cycle returns to zero
    (newer-cycle charges stay).

    Walks from the earliest statement_from so unpaid charges before the
    visible window still sit on the card at start_date.
    """
    cards = [a for a in accounts if _attr(a, "account_type") == "credit_card"]
    names = {_attr(a, "id"): _attr(a, "name") for a in cards}
    balances = {_attr(a, "id"): 0.0 for a in cards}
    cycle_list = list(cycles or [])
    totals = statement_totals or {}

    first_from: dict[int, date] = {}
    walk_from = start_date
    for cycle in cycle_list:
        frm = parse_date(_attr(cycle, "statement_from"))
        if frm is None:
            continue
        card_id = _attr(cycle, "account_id")
        if card_id not in first_from or frm < first_from[card_id]:
            first_from[card_id] = frm
        if frm < walk_from:
            walk_from = frm

    rows: list[dict] = []
    for d in each_day(walk_from, end_date):
        movements: list[dict] = []
        for item in recurring_items:
            target = _attr(item, "target_account_id")
            card_start = first_from.get(target, start_date)
            if target in balances and d >= card_start and recurring_item_fires_on(item, d):
                sign = 1 if _attr(item, "item_type") == "expense" else -1
                delta = sign * float(_attr(item, "amount"))
                balances[target] += delta
                if d >= start_date:
                    movements.append(
                        {
                            "account_id": target,
                            "description": _attr(item, "description") or "",
                            "amount": delta,
                            "kind": "recurring",
                        }
                    )
        for item in one_off_items:
            target = _attr(item, "target_account_id")
            card_start = first_from.get(target, start_date)
            item_date = parse_date(_attr(item, "item_date"))
            if target in balances and d >= card_start and item_date == d:
                sign = 1 if _attr(item, "item_type") == "expense" else -1
                delta = sign * float(_attr(item, "amount"))
                balances[target] += delta
                if d >= start_date:
                    movements.append(
                        {
                            "account_id": target,
                            "description": _attr(item, "description") or "",
                            "amount": delta,
                            "kind": "one_off",
                        }
                    )
        for cycle in cycle_list:
            due = parse_date(_attr(cycle, "payment_due"))
            if due != d:
                continue
            card_id = _attr(cycle, "account_id")
            total = totals.get(_attr(cycle, "id"), 0.0)
            if card_id in balances and total:
                balances[card_id] -= total
                if d >= start_date:
                    card_name = names.get(card_id) or "Credit card"
                    movements.append(
                        {
                            "account_id": card_id,
                            "description": f"{card_name} payment",
                            "amount": -float(total),
                            "kind": "cc_payment",
                        }
                    )
        if d >= start_date:
            row = {"date": d, "movements": movements, **{a_id: balances[a_id] for a_id in balances}}
            rows.append(row)
    return rows


def first_low_balance_date(
    daily_rows: Iterable[dict],
    account_id: int | str,
    threshold: float,
) -> date | None:
    for row in daily_rows:
        if row[account_id] < threshold:
            return row["date"]
    return None


def combined_daily_rows(daily_rows: Iterable[dict], bank_ids: Iterable[int]) -> list[dict]:
    bank_ids = list(bank_ids)
    out: list[dict] = []
    for row in daily_rows:
        combined = sum(row[i] for i in bank_ids)
        out.append({**row, "combined": combined})
    return out


def expenses_by_category(
    recurring_items: Iterable[Any],
    one_off_items: Iterable[Any],
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Sum projected expenses in the window, grouped by category.

    Recurring items are expanded with the same fire rules as cashflow
    (monthly / bi-weekly). Card payments are not added again — the
    underlying expense rows already carry the category.
    """
    totals: dict[str, float] = {}
    for item in recurring_items:
        if _attr(item, "item_type") != "expense":
            continue
        amount = _attr(item, "amount")
        if amount is None:
            continue
        for d in each_day(start_date, end_date):
            if recurring_item_fires_on(item, d):
                category = (_attr(item, "category") or "Uncategorized").strip() or "Uncategorized"
                totals[category] = totals.get(category, 0.0) + float(amount)
    for item in one_off_items:
        if _attr(item, "item_type") != "expense":
            continue
        item_date = parse_date(_attr(item, "item_date"))
        if item_date is None or not (start_date <= item_date <= end_date):
            continue
        category = (_attr(item, "category") or "Uncategorized").strip() or "Uncategorized"
        totals[category] = totals.get(category, 0.0) + float(_attr(item, "amount"))
    return [
        {"category": name, "amount": round(amount, 2)}
        for name, amount in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    ]
