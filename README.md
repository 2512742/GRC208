# RiskTrack

Cyber Risk Register and Treatment Management Platform, built by ICDFA GRC208 Group 1 for the fictional Lagos fintech **The Alajo**.

> Status: **in development** (phases P0 Foundations and P1 Database complete). Sections marked *(later)* are filled in as each phase lands. The full plan is in the project folder's `PLAN.md`.

## Stack

- **Backend:** Python 3.12+ (3.13 locally), FastAPI, SQLModel/SQLAlchemy 2, Alembic
- **Database:** SQLite by default; PostgreSQL (Neon) when hosted
- **Frontend:** React + Vite + TypeScript + Tailwind *(later)*
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

# 3. Database (local SQLite file backend/risktrack.sqlite3)
alembic upgrade head
python -m app.cli load-reference

# 4. Run
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/api/health (expect `"status": "ok"`) and the interactive API docs at http://127.0.0.1:8000/api/docs.

Demo data and demo accounts *(later: `python -m app.cli seed-demo`)*.

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

GitHub Actions runs both variants on every push and pull request (`.github/workflows/ci.yml`).

## Configuration

All settings come from environment variables or `.env` (real environment variables win). See `.env.example`.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `SECRET_KEY` | yes | none | 32+ characters. The app refuses to start without it |
| `DEBUG` | no | `false` | Never `true` on Vercel |
| `DATABASE_URL` | no | local SQLite file | On Vercel: Neon **pooled** URL |
| `DATABASE_URL_DIRECT` | no | `DATABASE_URL` | Neon **direct** URL, used only for migrations |
| `ORG_TIMEZONE` | no | `Africa/Lagos` | Deadlines and expiry are evaluated in this zone |
| `LOG_FILE` | no | none | Local runs only |

## Deployment (Vercel + Neon)

Owned and run by the technical lead. Summary *(full steps later)*:

1. In Vercel, import the GitHub repository; set the environment variables above for Production (pooled Neon URL as `DATABASE_URL`, a new random `SECRET_KEY`).
2. From a developer machine whose `.env` holds the Neon URLs: `alembic upgrade head`, then `python -m app.cli load-reference` (migrations use `DATABASE_URL_DIRECT`).
3. Deploy `main`; check `https://<project>.vercel.app/api/health`.

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
backend/app/routers/    API routes (currently: health)
backend/tests/          pytest suite
vercel.json             Vercel config (region, rewrites)
```

## Team

GRC208 Group 1 (17 members). Roles and contributions are documented in the project report.
