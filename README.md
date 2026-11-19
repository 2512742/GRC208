# RiskTrack

Cyber Risk Register and Treatment Management Platform, built by ICDFA GRC208 Group 1 for the fictional Lagos fintech **The Alajo**.

> Status: **in development** (backend complete (phases P0 to P6): every brief feature is available through the API; the React frontend is next). Sections marked *(later)* are filled in as each phase lands. The full plan is in the project folder's `PLAN.md`.

## Stack

- **Backend:** Python 3.12+ (3.13 locally), FastAPI, SQLModel/SQLAlchemy 2, Alembic
- **Database:** SQLite by default; PostgreSQL (Neon) when hosted
- **Frontend:** React 19 + Vite 7 + TypeScript + Tailwind 3 (Guardian "Deep Intel" design system), TanStack Query; Node 20.19+
- **Hosting:** Vercel (API as a Python function, region `cle1`) + Neon PostgreSQL (us-east-2)

## Run it locally (SQLite, nothing else to install)

Prerequisites: Python 3.12 or newer, Git. Node 20+ is needed once the frontend lands.

```bash
git clone <repository-url> risktrack
cd risktrack

# 1. Settings
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # paste the output as SECRET_KEY in .env

# 2. Backend environment
cd backend
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# 3. Database with The Alajo demo data (in-project SQLite file backend/data/risktrack.sqlite3)
alembic upgrade head
python -m app.cli seed-demo --reset
#   (or, for an empty register: python -m app.cli load-reference
#    and python -m app.cli create-user --username admin --full-name "Admin" --role admin)

# 4. Build the web app once (FastAPI serves it, so everything is on one URL)
cd ../frontend
npm ci
npm run build
cd ../backend

# 5. Run
uvicorn app.main:app
```

Open http://127.0.0.1:8000 and sign in with one of the demo accounts below. The API health check is at http://127.0.0.1:8000/api/health and the interactive API docs at http://127.0.0.1:8000/api/docs.

**Developing the frontend:** run `uvicorn app.main:app --reload` in `backend/` and `npm run dev` in `frontend/`, then open http://localhost:5173 (Vite forwards `/api` to port 8000, so cookies work as in production). `/kitchen-sink` shows every shared component on mock data; toggle the theme and narrow the window to check both themes and the phone layout. After an API change, refresh the TypeScript types with `python -m app.cli export-openapi` (in `backend/`) and `npm run gen:api` (in `frontend/`).

### Demo accounts (local SQLite demo only)

`seed-demo` creates these fictional personas of The Alajo, all with the password **`Alajo-Demo-2026!`** when seeding a local SQLite database. For a remote database the command asks for a different password, which is never written down in the repository.

| Username | Persona | Role |
|---|---|---|
| `admin` | System Administrator | admin |
| `omotayo` | Omotayo Akinola, GRC Analyst | analyst |
| `emmanuel` | Emmanuel Teye Adjei, Head of Engineering | risk owner |
| `anita` | Anita Ojimba, Head of Investment Operations | risk owner |
| `gilbert` | Gilbert Obichere, Head of Customer Support | risk owner |
| `adeola` | Adeola Bamigboye, CISO | approver (also owns R-015) |
| `kelechi` | Kelechi Kenneth Nwankwo, CRO | approver |
| `ernestina` | Ernestina Lamiorkor Tawiah, Internal Auditor | auditor (read-only) |

The demo data lives in `sample_data/` as CSV: `alajo_assets.csv` (18 assets in 3 services), `alajo_risks.csv` (22 scored risks), `alajo_decisions.csv` (treatment strategy per risk) and `alajo_treatments.csv` (18 actions with owners, due dates relative to today, costs in ₦ and framework controls). The seed also sets up each state the brief asks to demonstrate: an overdue action (T-003), an expired acceptance (R-014), a completed action awaiting reassessment (R-002), a reassessed risk with history (R-013, 12 then 4), a valid acceptance (R-010) and two pending requests (R-015, the CISO's own risk that only the CRO may decide, and R-022). Evidence files are small PDFs marked "fictional demo evidence". Edit them in a spreadsheet and re-run `seed-demo --reset`; invalid rows are reported with their row numbers. Dates are relative to the day you seed.

> If your `.env` sets `DATABASE_URL`, these commands act on **that** database. CLI commands print the target and ask before touching a remote one.

## Tests and checks

From `backend/` with the virtual environment active:

```bash
ruff check . && ruff format --check .
pytest --cov=app
```

Tests always use a throwaway SQLite file, even if your `.env` points at Neon. To run them against PostgreSQL instead, set `TEST_DATABASE_URL`, e.g. with a local container:

```bash
docker run -d --rm --name risktrack-pg -e POSTGRES_USER=risktrack -e POSTGRES_PASSWORD=risktrack \
  -e POSTGRES_DB=risktrack_test -p 55432:5432 docker.io/library/postgres:18
TEST_DATABASE_URL=postgresql://risktrack:risktrack@localhost:55432/risktrack_test pytest
docker stop risktrack-pg
```

Against the team's Neon server (database `risktrack_test`, never production; needs the Neon URLs in `.env`). Slower, because every query crosses the network; run it before merging or deploying:

```bash
TEST_DB=neon pytest
```

The suite refuses to run on any PostgreSQL database whose name doesn't contain "test".

Frontend checks, from `frontend/`:

```bash
npm run typecheck && npm test && npm run build
```

GitHub Actions runs the backend on SQLite and on a `postgres:18` container, and the frontend typecheck, tests, build and `npm audit`, on every push and pull request (`.github/workflows/ci.yml`); CI never receives Neon credentials.

## Signing in (API)

- `POST /api/auth/login` with `{"username", "password"}` sets two cookies: an HttpOnly session cookie and a readable CSRF cookie. The response includes `csrf_token`.
- Every `POST`, `PATCH`, `PUT` and `DELETE` must send that token in the `X-CSRF-Token` header, or it is refused with 403 (and audited).
- Sessions end after 2 idle hours or 12 hours in total. Five failed sign-ins for a username lock it for 15 minutes (counted from the audit log, so the limit holds across serverless instances).
- Try it in the interactive docs at `/api/docs`.

## The required demonstration through the API

| Brief step | Endpoint |
|---|---|
| Create a risk with L4 × I5 = 20 | `POST /api/risks` with `initial_assessment` |
| Assign a treatment action and upload evidence | `POST /api/risks/{id}/actions`, `POST /api/evidence` |
| Complete the action without the score changing | `POST /api/actions/{id}/complete` (note + file); the risk becomes *awaiting reassessment* |
| Justified residual reassessment | `POST /api/risks/{id}/reassessments` (scores + rationale + file) |
| Acceptance request approved by a different user | `POST /api/risks/{id}/acceptances`, then `POST /api/acceptances/{id}/decision` |
| Overdue actions, expired acceptance and the updated management report | `GET /api/actions?overdue=true`, `GET /api/acceptances?expired=true`, `GET /api/dashboard`, `GET /api/reports/management.pdf` (or `.csv`) |
| Unauthorised users refused | any change by the auditor, or an owner deciding their own acceptance: 403 and a `DENIED` audit entry |

`tests/test_treatment_api.py::test_brief_required_demonstration` runs all of these in order.

## CSV import

1. Download a template: `GET /api/imports/templates/assets.csv` or `risks.csv`.
2. Upload: `POST /api/imports/assets` (or `risks`) with the file. You get a **preview**: every row marked `valid`, `rejected` (with reasons, e.g. `service_code: no business service 'S9'`) or `duplicate` (already in the register, or repeated earlier in the file). Nothing is created yet; the file is kept as evidence.
3. `POST /api/imports/{id}/commit` creates the valid rows (re-checked at that moment), or `/cancel`.

Try it with `sample_data/assets_import_valid.csv` and `sample_data/assets_import_with_errors.csv` (one row of each kind of error). Analysts import assets and risks; admins import assets only (risks may carry scores, and admins don't assess).

## Management commands

From `backend/` (`python -m app.cli --help`):

| Command | What it does |
|---|---|
| `seed-demo [--reset]` | Load The Alajo demo data (`--reset` erases and rebuilds first) |
| `load-reference` | Add or update framework controls and regulatory obligations |
| `create-user` | Create a user (e.g. the first admin) |
| `verify-audit` | Recompute the audit hash chain; exit code 1 if broken |
| `export-backup [--out DIR] [--no-with-evidence]` | Write every table to one JSON file in `backups/` (git-ignored; contains personal data and password hashes) |
| `reset-password --username NAME` | Offline recovery (e.g. a lost admin password): prints a temporary password that must be changed at the next sign-in, and ends that account's sessions |
| `export-openapi` | Write `openapi.json`, from which the frontend generates its types (`npm run gen:api`) |

Every command prints the database it is about to use and asks before changing a remote one.

## Account security

RiskTrack sends no email, so account recovery follows the design of the team lead's Sentinel project:

- **My account** (avatar in the top bar, or More on a phone): edit your profile, choose the display time zone and theme, change your password (needs the current one; your other sessions are signed out), see and sign out your sessions, and review your recent sign-ins and failed attempts.
- **Recovery code:** generate a one-time code under My account (you confirm your password first). It is shown once, stored only as an Argon2 hash, and replaced by any newer code. "Forgot password?" on the sign-in page takes your username, the code and a new password; the code is then used up and every session ends.
- **Administrator resets:** a password set by an administrator (new account or reset) is temporary. The user can do nothing else until they replace it, so the administrator never knows a working password. Administrators also see each account's security status (lockout, sessions, whether a recovery code exists, never the code) and can sign an account out everywhere.
- **Lockout (defaults, set in `.env`):** 5 wrong passwords or recovery codes within 15 minutes pause sign-in for that username (20 per network address); it lifts by itself. Every attempt is in the audit log.
- **Lost administrator password:** `python -m app.cli reset-password --username admin` on the server.

## Configuration

All settings come from environment variables or `.env` (real environment variables win). See `.env.example`.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `SECRET_KEY` | yes | none | 32+ characters. The app refuses to start without it |
| `DEBUG` | no | `false` | Never `true` on Vercel |
| `DATABASE_URL` | no | `backend/data/risktrack.sqlite3` | On Vercel: Neon **pooled** URL |
| `DATABASE_URL_DIRECT` | no | `DATABASE_URL` | Neon **direct** URL, used only for migrations |
| `ORG_TIMEZONE` | no | `Africa/Lagos` | Deadlines and expiry are evaluated in this zone |
| `LOG_FILE` | no | none | Local runs only |
| `SESSION_HOURS` / `SESSION_IDLE_MINUTES` | no | `12` / `120` | Absolute and idle session limits |
| `LOGIN_MAX_FAILURES` / `LOGIN_LOCKOUT_MINUTES` | no | `5` / `15` | Per-username sign-in lockout |
| `TRUST_PROXY_HEADERS` | no | `false` | Use `X-Forwarded-For` for client IPs (automatic on Vercel; set `true` behind a VPS reverse proxy) |

## Deployment (Vercel + Neon)

Owned and run by the technical lead. Summary *(full steps later)*:

1. In Vercel, import the GitHub repository; set the environment variables above for Production (pooled Neon URL as `DATABASE_URL`, a new random `SECRET_KEY`).
2. From a developer machine whose `.env` holds the Neon URLs: `alembic upgrade head`, then `python -m app.cli load-reference` (migrations use `DATABASE_URL_DIRECT`).
3. Deploy `main`; Vercel builds `frontend/` into static files (served by its CDN with the same security headers as the API, see `vercel.json`) and runs the API as a Python function. Check `https://<project>.vercel.app/api/health`, then sign in.

Secrets live only in `.env` (git-ignored) and in Vercel's settings. If a connection string is ever exposed, reset the password in Neon.

## Project structure

```
api/index.py            Vercel entry point (imports the FastAPI app)
backend/app/main.py     FastAPI application factory
backend/app/core/       settings, security headers, logging
backend/app/db.py       database engine (SQLite / PostgreSQL)
backend/app/models/     tables (SQLModel) with database-level rules
backend/app/reference/  framework controls and regulatory obligations catalogue
backend/app/cli.py      management commands (python -m app.cli --help)
backend/alembic/        migrations
backend/app/core/auth.py        sessions, CSRF check, permission dependencies
backend/app/core/permissions.py role table, ownership and separation-of-duties rules
backend/app/services/   scoring, clock (WAT), workflow, audit chain, evidence checks, users
backend/app/routers/    API routes: health, auth (+ recover), account (my profile, password,
                        recovery code, sessions, activity), users, register (services, assets,
                        obligations, controls), risks (+ initial assessment),
                        treatment (decisions, actions, completion, reassessment,
                        acceptances), evidence (upload, list, download),
                        reports (dashboard, management report JSON/CSV/PDF),
                        admin (CSV import, audit log + verify + CSV, settings)
sample_data/            The Alajo demo data in CSV import format (owned by WS2)
backend/app/frontend.py serves frontend/dist for single-URL local and VPS runs
backend/tests/          pytest suite
frontend/src/api/       fetch client (CSRF header, errors), generated OpenAPI types, queries
frontend/src/auth/      session, permissions and display time-zone preference
frontend/src/components/ design system: ui, modal, toast, risk badges, heat map, dialogs
frontend/src/layout/    app shell, role-based navigation, theme and time-zone controls
frontend/src/pages/     one file per screen (dashboard, register, risk detail, actions,
                        acceptances, assets, reports, import, audit, users, settings)
frontend/src/lib/       time-zone formatting and number/label helpers
vercel.json             Vercel config (region, static build, rewrites, headers)
```

## Team

GRC208 Group 1 (17 members). Roles and contributions are documented in the project report.
