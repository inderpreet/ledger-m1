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

### Docker (local, builds on the machine)

```bash
docker compose up -d --build
docker compose exec api python set_password.py
```

App: http://localhost:3000 (Caddy on the host port, default 3000). SQLite lives in the `ledger-data` volume. Do not bake a password into the image.

```bash
docker compose exec api python set_password.py --username alex
docker compose down
```

### VPS (build on your PC, copy images)

Oracle Cloud and similar hosts often cannot build comfortably. Build and export on a machine with Docker, then load on the VPS. Use `-p ledger` so the image names stay `ledger-api` and `ledger-web`.

**1. On your PC** (repo root; stop the local app first with `.\stop.ps1` if you will also copy `backend/app.db`):

```powershell
docker compose -p ledger build
docker save ledger-api ledger-web -o ledger-images.tar
scp -i YOUR_SSH_KEY .\ledger-images.tar ubuntu@YOUR_HOST:~/ledger-m1/
scp -i YOUR_SSH_KEY .\backend\app.db ubuntu@YOUR_HOST:~/ledger-m1/app.db
```

Create `~/ledger-m1` on the VPS first (`mkdir -p ~/ledger-m1`) or `scp` fails.

**2. On the VPS**, load the images:

```bash
cd ~/ledger-m1
docker load -i ledger-images.tar
```

**3. Write `~/ledger-m1/docker-compose.yml`** (this uses the loaded images; no build, no Caddyfile):

```yaml
services:
  api:
    image: ledger-api
    environment:
      LEDGER_DB_PATH: /data/app.db
    volumes:
      - ledger-data:/data
    restart: unless-stopped

  web:
    image: ledger-web
    ports:
      - "80:3000"
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped

volumes:
  ledger-data:
```

**4. Start, then put the database into the volume** (not into the git folder):

```bash
cd ~/ledger-m1
docker compose -p ledger up -d
docker compose -p ledger stop api
docker compose -p ledger cp ./app.db api:/data/app.db
docker compose -p ledger exec -u root api chown ledger:ledger /data/app.db
docker compose -p ledger exec -u root api chmod 664 /data/app.db
docker compose -p ledger start api
```

If you skip `chown`, login fails: the API can read the file but cannot write a session (`attempt to write a readonly database`).

**5. Open port 80 in two places** (Oracle Compute). The app can be healthy on the VM and still time out from the internet.

On the VM:

```bash
sudo iptables -I INPUT 5 -p tcp -m state --state NEW --dport 80 -j ACCEPT
sudo sh -c 'iptables-save > /etc/iptables/rules.v4'
```

In the Oracle console: **Compute → Instances → your instance → Subnet → Security Lists → Default Security List → Add Ingress Rules**. Source CIDR `0.0.0.0/0`, TCP, destination port `80`. If the instance uses a Network security group, add the same ingress rule there.

Leave `LEDGER_SECURE_COOKIES` unset (or `0`) while the site is plain HTTP. Set it to `1` only after HTTPS is in front.

**6. Sign in.** Use the same username and password as on your PC. If that password is lost, rotate on the VPS (prints once):

```bash
docker compose -p ledger exec api python set_password.py
```

Default username is `ledger`. Running it again signs everyone out.

You can also move data later from **Setup → Download data / Upload database** (upload asks you to confirm overwrite; the VPS login is kept).

App: `http://YOUR_HOST`. Check `docker compose -p ledger ps` and `docker logs ledger-api-1` if something fails.

### Login (required)

One local username. A script generates a long random password and stores **only a bcrypt hash** in SQLite. The plaintext is printed once.

```bash
./set-password.sh                  # Linux VPS
./set-password.sh --username alex  # optional name (default: ledger)
```

```powershell
.\set-password.ps1
.\set-password.ps1 --username alex
```

Running it again rotates the password and signs everyone out.

On a VPS put HTTPS in front (nginx/Caddy) and:

```bash
export LEDGER_SECURE_COOKIES=1
```

Sessions are httpOnly cookies (14 days). Login is rate-limited. `/api/health` stays public; every other `/api` route requires a session.

Backend tests:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests -q
```

## Pages

| Nav | Route | What it shows |
|---|---|---|
| Dashboard | `/` | Bank balances, low-balance banner, bank-flow chart, expenses by category |
| Bank Account Flow | `/bank-flow` | Daily bank balances and activity |
| Credit Cards | `/credit-cards` | Card-targeted charges and due-date payments |
| Expenses | `/expenses` | Recurring and one-off items |
| Setup | `/setup` | Opening balances, model start/end, card funding, statement cycles |
| — | `/login` | Single-user sign-in |

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
- `GET /daily-cashflow?start=&end=` — omitted dates use Setup `model_start_date` / `model_end_date`
- `GET /cc-cashflow?start=&end=`
- `GET /dashboard`
- `GET /health` (public)
- `GET /auth/status` (public), `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`

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

On first empty database, `backend/app/seed.py` loads accounts, funding, recurring/one-off rows, Scotia CC and TD CC cycle anchors (then generates through `model_end_date`), and settings (`low_balance_threshold` 6000, `model_start_date` today at first run, `model_end_date` 2026-12-31). Change the projection window in Setup; it is stored and does not jump to today on each visit.

- Opening balances start unset — enter them in Setup.
- Rent Mol, Enercare, and Gas are incomplete (`amount` / `day_of_month` null).
- BMO CC and CIBC CC have no cycle anchors until you add one in Setup.

## Account colors

| Account | Color |
|---|---|
| Scotia / Scotia CC | Red `#c42b2b` |
| TD GK / TD CC | Green `#187a3c` |
