# backend/data

Home of the in-project SQLite database, `risktrack.sqlite3` (git-ignored: data never goes into git).

Used when `DATABASE_URL` is not set in `.env`: local development, graders' installs, and a
possible VPS deployment, where this folder is the one to back up and keep on persistent disk.

Create or update it from `app/backend`:

    alembic upgrade head
    python -m app.cli load-reference
