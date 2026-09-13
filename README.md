# Ledger — Cash Flow Tracker

Projects daily bank and credit-card balances from today through a configurable end date. Replaces `Fin-model-v3.xlsx`. The FastAPI backend owns every balance calculation; the Next.js frontend only renders API data.

## Run

From the repo root:

```powershell
.\start.ps1
```

- Web app: http://localhost:3000
- API: http://127.0.0.1:8000 (`/api/*` is rewritten from the Next.js app)

Stop only this project's API, Next.js, and launcher windows:

```powershell
.\stop.ps1
.\stop.ps1 -ListOnly   # preview
```

Or start each side alone: `.\start-backend.ps1`, `.\start-frontend.ps1`.

Backend tests:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests\test_engine.py -q
```

## Pages

| Nav | Route | What it shows |
|---|---|---|
| Dashboard | `/` | Bank balances, low-balance banner, bank-flow chart, expenses by category |
| Bank Account Flow | `/bank-flow` | Daily bank balances and activity |
| Credit Cards | `/credit-cards` | Card-targeted charges and due-date payments |
| Expenses | `/expenses` | Recurring and one-off items |
| Setup | `/setup` | Opening balances, model window, card funding, statement cycles |

Old routes redirect: `/cashflow` → `/bank-flow`, `/cc-cashflow` → `/credit-cards`, `/recurring` and `/one-off` → `/expenses`, `/settings` → `/setup`.

Scotia is shown in red, TD GK in green.

## How money moves

- Amounts are stored **positive**. Direction comes from `item_type` (`income` / `expense`), never from sign.
- Bank-targeted income adds on the fire date; bank-targeted expense subtracts that day.
- **Card-targeted** expenses do **not** move a bank on the charge date. They increase the card balance owed.
- On each cycle's `payment_due`, the statement total leaves the **funding bank** and the same lump is subtracted on the **card**. Newer-cycle charges stay on the card (it does not wipe the full running balance).
- Recurring `term`: `monthly` (day of month, overflow clamped to month-end) or `biweekly` (every 14 days from `start_date`).

## Stack

```
frontend/          Next.js App Router, TypeScript, Tailwind, Recharts
backend/           FastAPI, SQLAlchemy, SQLite (`backend/app.db`)
start.ps1          Launch API + web app
stop.ps1           Kill this project's processes
```

- Recompute balances on every request. Do not cache them in SQLite.
- `recurring_items.amount` and `day_of_month` are nullable so incomplete seed rows can exist.
- `recurring_items.term` is `monthly` or `biweekly`.

## API (`/api/`)

CRUD: `accounts`, `recurring-items`, `one-off-items`, `settings`.

Cards and cycles:

- `GET /credit-cards`, `PUT /credit-cards/{id}/funding`
- `GET/POST /statement-cycles`, `PUT/DELETE /statement-cycles/{id}`
- `POST /statement-cycles/{account_id}/generate` — insert missing cycles through `model_end_date`; never overwrite `is_generated=0`
- `DELETE /credit-cards/{id}/statement-cycles` — delete all cycles for a card

Computed (read-only):

- `GET /cc-statement-totals`
- `GET /daily-cashflow?start=&end=`
- `GET /cc-cashflow?start=&end=`
- `GET /dashboard`
- `GET /health`

Income rows must target a bank (422 otherwise). Card funding must be a bank. Amounts must be > 0 when set.

## Engine (`backend/app/engine.py`)

Pure functions, no FastAPI/SQLAlchemy imports. Unit tests in `backend/tests/test_engine.py`.

**Monthly fire:** clamp `day_of_month` to the last day of the month (day 31 in April → 30th, not May 1).

**Bi-weekly fire:** `(d - start_date).days % 14 == 0`. `start_date` is required; `day_of_month` is ignored.

**Statement totals:** expenses add, refunds/income subtract. Positive total = amount owed / bank debit on due date.

**Bank cashflow:** opening balances, then each day recurring → one-off → CC payments. Card-targeted items never touch a bank except via the due-date lump.

**Card cashflow:** starts from each card's earliest `statement_from` (charges before that are ignored). Charges raise the owed balance; `payment_due` subtracts that cycle's statement total.

**Generate cycles:** add calendar months with `dateutil.relativedelta`. Identity is `(account_id, statement_from)`.

## Seed

On first empty database, `backend/app/seed.py` loads accounts, funding, recurring/one-off rows, Scotia CC and TD CC cycle anchors (then generates through `model_end_date`), and settings (`low_balance_threshold` 6000, `model_end_date` 2026-12-31).

- Opening balances start unset — enter them in Setup.
- Rent Mol, Enercare, and Gas are incomplete (`amount` / `day_of_month` null).
- BMO CC and CIBC CC have no cycle anchors until you add one in Setup.

## Account colors

| Account | Color |
|---|---|
| Scotia / Scotia CC | Red `#c42b2b` |
| TD GK / TD CC | Green `#187a3c` |
