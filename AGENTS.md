# Ledger agent notes

Read `README.md` before changing cash-flow math. The backend owns every balance. The frontend never recomputes running totals from source rows.

## Commands

- Start: `.\start.ps1` — API `http://127.0.0.1:8000`, app `http://localhost:3000`
- Stop this project only: `.\stop.ps1` (`-ListOnly` to preview)
- Engine / auth tests: `backend\.venv\Scripts\python -m pytest tests -q` from `backend/`
- Create or rotate the single login: `.\set-password.ps1` or `./set-password.sh` — never store the plaintext password in the repo

Uvicorn `--reload` can hang on Windows after a file change. If `/api` looks stale, `.\stop.ps1` then start again.

## Do not regress

- Amounts stored positive; sign from `item_type`.
- Card charges do not hit a bank on the charge date.
- On `payment_due`, the same statement total leaves the funding bank **and** pays down that card. Newer-cycle charges stay.
- Monthly day-of-month overflow clamps to month-end. Do not use `DATE(y, m, 31)` roll-forward.
- Bi-weekly uses `start_date` + 14 days, not day-of-month.
- Do not cache computed balances in SQLite.
- Do not guess opening balances in seed.
- One username; password is generated and bcrypt-hashed. Do not commit plaintext passwords or `.env`.
- Protect all `/api` routes except `/api/health` and `/api/auth/status`. Use httpOnly session cookies, not tokens in localStorage.

## Layout

| Path | Role |
|---|---|
| `backend/app/engine.py` | Pure calc |
| `backend/app/services.py` | DB → engine → JSON |
| `backend/app/routers/` | HTTP |
| `frontend/app/` | Pages |
| `frontend/components/` | UI |

Nav: Dashboard `/`, Bank Account Flow `/bank-flow`, Credit Cards `/credit-cards`, Expenses `/expenses`, Setup `/setup`. Old URLs redirect.

## UI

After changing a page, route, or shared state, verify in the browser (not a single screenshot). Scotia red `#c42b2b`, TD green `#187a3c`.
