# Contributing to RiskTrack

Everyone's commits are evidence for the contribution record (report §6.2), so commit your own work under your own GitHub account.

## Branches and pull requests

- `main` is always deployable and deploys to production on Vercel. **Only the technical lead (Ocen) merges into `main`.**
- Work on a branch: `feat/<area>`, `fix/<area>` or `docs/<area>`, e.g. `feat/csv-import`.
- Open a pull request early; CI (lint and tests on SQLite and PostgreSQL) must pass before review.
- Reviews: Ocen reviews Emmanuel, Ouabo and Kelechi; Emmanuel reviews frontend-facing changes from Ocen.
- Teammates' branches may not get Vercel preview deploys (single-owner Hobby account). Test locally on SQLite instead.

## Commit messages

Short imperative subject, optional body explaining *why*:

```
feat(scoring): add band and appetite calculation
fix(import): reject rows with likelihood outside 1-5
test(acceptance): cover CISO/CRO failover
docs(readme): add PostgreSQL test instructions
```

## Definition of done (every feature)

- The rule is enforced in the API and covered by a pytest test (and listed against a test ID in `docs/test-cases.md` where one applies).
- The screen works in light and dark mode and at phone width *(frontend phases)*.
- Important actions write an audit entry.
- Docs are updated if behaviour changed.

## Security checklist before every commit

Adapted from the Guardian project's guidelines:

- [ ] No hardcoded secrets: no passwords, connection strings, tokens or keys in code, tests, docs or screenshots.
- [ ] `.env` is not staged (`git status` shows nothing under `.env`).
- [ ] Every input is validated (Pydantic schemas, database constraints).
- [ ] Database access goes through the ORM or bound parameters only, never string-built SQL.
- [ ] Output is escaped (React does this by default; never use `dangerouslySetInnerHTML`).
- [ ] State-changing endpoints check the session, the CSRF token and the user's permission on the server.
- [ ] Error messages don't leak internals (stack traces, SQL, hostnames).
- [ ] New dependencies are pinned and justified in the PR.

If you find a security problem: stop, tell the technical lead privately (not in the group chat), and if a secret was exposed, it gets rotated before anything else.

## Local checks

```bash
cd backend && source .venv/bin/activate
ruff check . && ruff format --check . && pytest
```
