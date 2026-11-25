# GRC208 Capstone Plan: Cyber Risk Register and Treatment Management Platform

> **Repository layout changed on 22 Nov 2026:** the project is now one repository with a folder per workstream (`WS1-development` with the app in `WS1-development/app`, up to `WS5-presentation`). The root `README.md` is the current map; older path names below refer to the same files in their new folders.

Working name: **RiskTrack** (rename freely). Demo organisation: **The Alajo** (fictional Lagos digital savings and investment fintech).
Due **15 Dec 2026, 11:59 PM WAT**; group target for all 17 final submissions: **14 Dec**.
This file is the single plan and context document (it absorbed the former `HANDOVER.md`). Also read: `docs/brief.md` (the assignment brief), `docs/team-roles.md` (who does what), `docs/submission-guide.md` (E-Campus field map).

Revision 3 (19 Nov 2026): hosting decided as **Vercel + Neon PostgreSQL** (project already created); HANDOVER merged in here. Revision 2 (same day): stack changed from Django to **FastAPI + React**, demo organisation changed to The Alajo, appetite threshold changed to **score ≥ 10**, design system and conventions adopted from the user's Guardian project (`/home/tinex/ance/projects/pita/guardian/`).

**Status: planning. No code yet; don't start coding until the user says so.**

---

## A. Project context

### A.1 Who and what
- **Lead student:** Ocen Richard, 2025/GCR/12742 (portal ID ICDFA12742), ICDFA Uganda, batch B2025, Level 1 / Semester 2. Technical lead and full-stack developer.
- **Course:** GRC208 Capstone Project, 100 marks, one attempt, due **15 Dec 2026, 11:59 PM WAT**.
- **Group:** Group 1, 17 members, individual submissions, shared grade. Roster and roles: `docs/team-roles.md` (draft; swaps open until 21 Nov 2026).
- **Project:** *Cyber Risk Register and Treatment Management Platform*, a working web app with persistent database storage. Brief: `docs/brief.md`.

### A.2 Files in this folder
| Path | What it is |
|---|---|
| `PLAN.md` | This file |
| `docs/brief.md` | The assignment brief, transcribed (the original `GRC208 Capstone Project.docx` is screenshots only) |
| `ICDFA-Technical-Project-and-Seminar-Template.docx` / `.pdf` | Required report template (sections 1 to 6, references, appendices, final checklist) |
| `WS2-risk-framework/planning-sources/` | Omotayo's org profile, improved structure (NIST SP 800-39) and documentation draft; `emmanuel_prototype_extracted.html` (source of Emmanuel's React mockup, live at https://sites.google.com/view/the-alajo-enter-cyber-risk/full-page-embed; client-only, no persistence) |
| `docs/team-roles.md`, `docs/contributions.md` | Roster, workstreams, timeline; master contribution record (report §6.2) |
| `deliverables/` | Everything submitted on E-Campus: `shared/` and `members/<NN-name>/submission.md` |

### A.3 Related coursework worth reusing
- `../../phase 1/grc103/wk3/3.1/GRC_Lab3_Phishing_Risk_Analysis.xlsx`: SLE × ARO = ALE and control ROI, plus an executive briefing. Reuse for the optional cost-benefit fields on actions and as a model for the management report layout. Known bug: in the Step 7 confidence-interval and sample-size rows, Campaign A uses `'INPUT DATA'!B18` (MFA cost) instead of `B8` (credentials submitted); its $652.5M ALE is unrealistic, so cap ARO if reused.
- `../../phase 1/grc103/wk1/`: scanning lab (Nmap, Nikto, Nuclei → risk assessment); shows where vulnerability inputs come from.
- `../GRC206/GRC206_Northbridge_Security-Awareness-Program.docx`: the former demo organisation, reference only.
- `../AWS/`: IAM and S3 labs (not needed for Vercel + Neon).
- `/home/tinex/ance/icdfa/note.txt`: the user's rough notes on input sources and roles.
- `/home/tinex/ance/projects/pita/guardian/`: design system, security headers, conventions and Vercel deployment experience (§1.3, §2.6).

### A.4 Decision log (don't re-litigate)
1. **Governance and workflow system, not a scanner.** Scanner output arrives only as evidence attachments or an optional findings import.
2. **Upload facts, type judgements.** Assets by CSV or form; scores, rationales, decisions and approvals typed by an accountable person; source documents attached and hashed as evidence, **never parsed**.
3. **Evidence required** to complete an action and to submit a reassessment (plus written justification). Evidence can't be edited or deleted; mistakes are superseded by a new file.
4. **Scoring:** L and I 1 to 5, score = L × I; bands 1-4 Low, 5-9 Medium, 10-14 High, 15-25 Critical; **appetite: score ≥ 10 is above appetite** (19 Nov, adopted from the group). Calculation always shown. ALE may appear beside the score, never instead of it.
5. **Assessments are never overwritten**; the current score is the latest row; completing an action only flags "Awaiting reassessment".
6. **Roles:** analyst, owner, approver, auditor (read-only), admin. Owners never approve their own acceptance; approvers are CISO and CRO with failover; justification ≥ 30 characters and a future expiry. Enforced on the server (403 + audit entry).
7. **Audit log:** append-only, SHA-256 hash chain, "Verify integrity" check.
8. **CSV import:** fixed templates (optional column mapping); normalise, validate, duplicate check by natural key, preview with reasons, commit only valid rows; file kept as evidence.
9. **Framework mapping (bonus):** NIST CSF 2.0, CIS v8.1, ISO 27001:2022 Annex A as IDs + our own short titles; plus regulatory obligations (NDPA 2023, CBN, SEC Nigeria, PCI DSS v4.0). Descriptive only, never drives the score.
10. **Optional extra:** Nessus CSV findings into a triage list; findings never become risks automatically.
11. **Demo organisation:** The Alajo (19 Nov, chosen so the whole group feels included).
12. **Stack:** FastAPI + SQLModel + Alembic; SQLite by default; React + Vite + TypeScript + Tailwind; Guardian design system and conventions (19 Nov, user's decision). See §1.
13. **Hosting:** **Vercel + Neon PostgreSQL** (19 Nov, user's decision; Neon project created). See §1.2.
14. **Accounts:** the GitHub repository and the Vercel project are both owned by Ocen's personal accounts (19 Nov). Teammates join the GitHub repo as collaborators; only Ocen has Vercel dashboard access. See §5 for how teammates' work still deploys.
15. **VPS fallback kept open (19 Nov):** the user owns the domain `tinex.tech` and a shared VPS already running another project (`/home/tinex/sentinel/`). If Vercel misbehaves, deploy as one long-running service on that VPS with the in-project SQLite file (`backend/data/` on persistent disk, backed up) behind the existing web server, e.g. a `risktrack.tinex.tech` subdomain. No code change is needed: only `DATABASE_URL` differs.

### A.5 Machine and environment
- Parrot OS, Python 3.13.5, Node 20.20 / npm 10.8, `git`, `psql`, `docker`; VS Code with Claude Code. Backend venv at `app/backend/.venv`.
- Not a git repository yet. **Confirm with the user before creating a GitHub remote or pushing**; the instructor needs access to the source link.

### A.6 Working preferences
- Report follows the ICDFA template styles; content has no em-dashes and no decoration. References in APA with direct links. The user reviews drafts.
- Honest AI-use declaration (template §6.3): keep `docs/ai-use-log.md` of what Claude generated and how it was checked.
- Never invent test results; report only what was actually run.
- Never put secrets (database URL with password, `SECRET_KEY`, demo passwords for the hosted instance) in the repository, report, slides or video.

### A.7 Open questions
1. Group confirmation of the draft roles (swaps close 21 Nov).
2. GitHub visibility. Recommendation: **private while building, made public before 12 Dec** (when the report's source link is frozen), so graders open it without an invite. Before going public, run `gitleaks` over the full history and confirm no `.env`, connection string or demo password was ever committed. The alternative is to stay private and invite the instructor as a read-only collaborator, but the brief asks for an "accessible" link and the instructor's GitHub username is unknown.
3. Teammates' GitHub usernames (Emmanuel, Ouabo, Kelechi first; non-coders only if they will commit docs directly), collected by WS6.

---

## 0. Everything we must hand in

| # | Deliverable | Source in brief | Where it lives | Owner (see team-roles) |
|---|---|---|---|---|
| D1 | Working app with persistent database | Deliverable 1 | `app/` | WS1 |
| D2 | Source code and README (install, database setup, demo accounts) | Deliverable 2 | `app/README.md`, GitHub | Ocen |
| D3 | Scoring methodology, appetite thresholds, approval workflow | Deliverable 3 | `docs/methodology.md`, report §2 | WS2 |
| D4 | Test cases: expected, actual, corrections | Deliverable 4 | `docs/test-cases.md`, `app/backend/tests/` | WS3 |
| D5 | Sample management risk report (exported by the app) | Deliverable 5 | `WS4-documentation/report/sample-management-report.pdf` | WS1 |
| D6 | Contribution record | Deliverable 6 | `docs/contributions.md`, report §6.2, each member's `submission.md` | WS6 |
| D7 | Abstract (200 to 300 words) | E-Campus | `WS5-presentation/abstract.md` | WS6 |
| D8 | Project documentation PDF in the ICDFA template | E-Campus | `WS4-documentation/report/GRC208_Group1_Project_Documentation.pdf` | WS4 |
| D9 | 8 to 12 minute demo video (link only) | E-Campus | `WS5-presentation/video/demo-video-link.md` | WS5 |
| D10 | 10 to 12 presentation slides | E-Campus | `WS5-presentation/slides/GRC208_Group1_Slides.pdf` | WS5 |
| D11 | Defence preparation notes | Defence | `WS5-presentation/defence-notes.md` | WS5 |
| D12 | Personal portal fields (contribution text, AI-use declaration, receipt) × 17 | E-Campus | `WS<n>-<workstream>/members/<NN-name>/submission.md` | Each member |

---

## 1. Stack and hosting

### 1.1 Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | **Python 3.13, FastAPI**, Pydantic v2, `pydantic-settings` | User's choice; typed request/response schemas; automatic OpenAPI docs at `/api/docs` for the report and for the frontend team |
| ORM and migrations | **SQLModel** (SQLAlchemy 2.0) + **Alembic** | One model layer for SQLite and PostgreSQL; switching is only the `DATABASE_URL` value |
| Database | **SQLite** by default (dev, tests, local demo, grader install). PostgreSQL only where the host has no persistent disk (see §1.2) | User's choice; zero setup for graders |
| Auth | Server-side sessions: opaque token in an `HttpOnly; Secure; SameSite=Lax` cookie, session rows in the DB; passwords hashed with **Argon2** (`pwdlib[argon2]`); CSRF double-submit token header on every state-changing request | Works across serverless instances; no JWT revocation problems |
| Rate limiting | Sign-in throttling counted from the audit log's `LOGIN_FAILED` entries (5 per username, 20 per IP, per 15 minutes) | Changed in P3 from `slowapi`: its counters live in each instance's memory, which doesn't hold across Vercel's serverless instances; the database is shared |
| Frontend | **React 18 + Vite + TypeScript** (`allowJs` on, so Emmanuel's prototype JSX can be ported file by file), **Tailwind CSS 3** (built, not the CDN), React Router, TanStack Query | Emmanuel already works in React + Tailwind; TypeScript types generated from the FastAPI OpenAPI schema (`openapi-typescript`) keep frontend and backend in sync |
| Icons | **Heroicons** (`@heroicons/react`) first, **Lucide** (`lucide-react`) as fallback | Guardian convention; the prototype already uses Lucide |
| Charts | Heat map as a plain CSS grid; small bar charts with Recharts | No heavy chart library needed; drop the prototype's unused three.js |
| Report export | CSV from the API; **PDF generated server-side with `fpdf2`** (pure Python, runs on serverless); plus an A4 print stylesheet on the report page (Guardian's printable report pattern) | WeasyPrint needs system libraries that serverless hosts lack |
| Tests | **pytest** + `httpx` TestClient + `pytest-cov` (backend); **Vitest** + Testing Library for key components | Guardian TDD skill |
| Quality and security tooling | `ruff` (lint + format), `mypy` (backend, non-blocking at first), `pip-audit`, `bandit`, `npm audit`, `gitleaks` | Guardian verification loop |
| CLI | `python -m app.cli` (Typer): `seed-demo`, `create-user`, `verify-audit`, `export-backup` | Replaces Django management commands |

What we lose by leaving Django, and how we cover it: no built-in admin panel (admin users are created with the CLI, plus a small Users page for the admin role), no built-in auth (built once in `core/security.py` and tested hard), no migrations framework (Alembic).

### 1.2 Hosting: Vercel + Neon PostgreSQL (decided 19 Nov 2026)

**Neon project (created by the user):** project `GRC208`, branch `production` (default, expires never), region **AWS US East 2 (Ohio)**, PostgreSQL 18, free plan, database `neondb`, role `neondb_owner`, scale-to-zero compute (0.25 to 2 CU). The connection string lives **only** in the local `.env` and in Vercel's environment variables, never in git or documents. If the password is ever exposed (screenshot, chat, commit), reset it in Neon.

**How the app connects:**

| Setting | Value / rule | Why |
|---|---|---|
| `DATABASE_URL` (runtime, Vercel) | Neon **pooled** endpoint (`...-pooler...`), `sslmode=require&channel_binding=require` | Serverless functions open many short connections; the pooler absorbs them |
| `DATABASE_URL_DIRECT` (migrations only) | Neon **direct** endpoint (same host without `-pooler`) | Alembic migrations need a session-level connection, not the transaction pooler |
| Driver | `psycopg[binary]` v3; config normalises `postgresql://` to `postgresql+psycopg://` | Supports `channel_binding`; one driver for app and migrations |
| Pooling in the app | SQLAlchemy `NullPool` on Vercel; `prepare_threshold=None` for the pooled URL | Don't hold connections in frozen functions; the pooler runs in transaction mode, which breaks server-side prepared statements |
| Vercel function region | `cle1` (Cleveland), set in `vercel.json` | Same area as Neon us-east-2, so each query isn't a long round trip |
| Migrations | Run `alembic upgrade head` against the direct URL from the developer machine or a GitHub Action before deploying, **not** in the Vercel build | Guardian ran `migrate` inside the Vercel build; separating it avoids half-applied migrations on a failed build |
| Local development | In-project SQLite file `app/backend/data/risktrack.sqlite3` (default when `DATABASE_URL` is unset); created 19 Nov, migrated and loaded | Nothing to install; graders use this path; also the database for a VPS deployment |
| Tests | Temporary SQLite file per run (fast, default). `TEST_DB=neon pytest` runs the same suite on the Neon database **`risktrack_test`** (created 19 Nov; same server, never `neondb`; about 5 minutes because of the Uganda to Ohio round trips). CI runs a `postgres:18` service container and never receives Neon credentials. The suite refuses any PostgreSQL database whose name lacks "test" | Catches SQLite-vs-PostgreSQL differences before they reach production |
| Neon databases | `neondb` on branch `production` = the hosted demo (migrated to head and reference-loaded on 19 Nov); `risktrack_test` = automated tests only. A `dev` child branch can be added if the team needs a shared online playground | Never experiment on the demo data |
| Evidence files | Stored in PostgreSQL as bytes, max 4 MB each | Vercel request bodies are capped at about 4.5 MB; the free plan's storage (about 0.5 GB) easily holds demo evidence. Neon's Object storage (visible in the project sidebar) is a fallback if files ever outgrow this |
| Cold start | First request after idle can take a second or two (Neon compute wakes, Vercel function starts) | Open the site once before recording the video or the live demo |
| Backups | `python -m app.cli export-backup` (JSON of all tables) before any schema change; Neon's 6-hour history allows point-in-time restore as a second net | Guardian's runbook lesson |

Not used from Neon: Neon Auth / Better Auth, Data API, Functions, AI Gateway. Our own auth is part of what the project demonstrates.

#### Why the database must be PostgreSQL when hosted (background for the report §3 decisions table)

The brief's first deliverable is **persistent database storage**. On Vercel and Heroku the filesystem is temporary: Vercel functions can only write to `/tmp`, which is wiped and not shared between instances, and Heroku dynos lose local files on every restart (at least daily). A SQLite file or uploaded evidence stored there **will disappear**. Guardian already hit this: it runs on Vercel with its database on Render PostgreSQL and its media on Cloudinary (`MEDIA_ROOT` is `/tmp` on Vercel), and Render's free PostgreSQL expires, which is why `RENDER_DB_MIGRATION_RUNBOOK.md` exists.

So a hosted serverless demo is the "something specifically requires PostgreSQL" case. Options:

| Option | Database | Evidence files | Effort | Notes |
|---|---|---|---|---|
| **A. Vercel + Neon (recommended)** | Neon free PostgreSQL via `DATABASE_URL` | Stored **in the database** as bytes (max 4 MB per file) | Low: no code change beyond the env var, because of SQLModel | Matches Guardian's Vercel experience; Neon's free tier doesn't expire like Render's. Vercel limits request bodies to about 4.5 MB, which sets the 4 MB evidence cap |
| B. One container with a persistent volume (Fly.io or Railway) | SQLite file on the volume | Files on the volume | Low: one Dockerfile | Keeps pure SQLite everywhere, but it's a small always-on server, not serverless, and usually needs a card on file |
| C. Local only | SQLite | Local disk | None | Valid for the brief (the demo video and graders run it locally) but no public URL |

**Chosen: option A.** The code still runs on all three (only `DATABASE_URL` differs): SQLite stays the default for development, tests and the README install, and the demo video can fall back to a local run if the hosted site misbehaves. Storing evidence in the database also makes backups a single step and keeps file integrity with the record.

### 1.3 Conventions borrowed from Guardian

- `.env` + committed `.env.example`; settings read explicitly through `pydantic-settings` (Guardian's runbook lesson: `dj_database_url.config()` silently preferred the OS variable over `.env`; read one explicit variable, `DATABASE_URL`).
- Required secrets validated at startup: the app refuses to start without `SECRET_KEY` (Guardian raises `ImproperlyConfigured`). `DEBUG` defaults to false.
- Security headers middleware copied from Guardian's `SecurityHeadersMiddleware` and tightened: `Content-Security-Policy` (self + Google Fonts only; no CDN scripts because Tailwind is built), `Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=()`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, HSTS when not in debug.
- Cookies `Secure` when not in debug, `SameSite=Lax`; CORS locked to the app's own origin (frontend and API are served from the same domain, so CORS is normally not needed at all).
- Logging: console handler always; file handler only when not serverless (Guardian's `if not VERCEL` pattern).
- Time zones: store UTC; each user picks a display zone (default: their device's system zone); business rules use The Alajo's official zone. Details in §2.7.
- `.gitignore` based on Guardian's (venvs, `.env*` except `.env.example`, `*.sqlite3`, `*.sql`, `*.dump`, `media/`, logs, coverage, `node_modules/`, `dist/`, `.vercel/`).
- Pre-commit security checklist from Guardian's `skills/Security_Guidelines.md` goes into `CONTRIBUTING.md`: no hardcoded secrets, inputs validated, parameterised queries only, output escaped, CSRF on, authz verified, rate limiting, error messages that don't leak internals.
- Backup and restore: `python -m app.cli export-backup` writes a JSON dump of every table, the equivalent of Guardian's `dumpdata` approach, so a database move never depends on `pg_dump` versions.
- Not adopted: Guardian's random URL prefixes (security by obscurity), the Tailwind CDN in production, and `!important` dark-mode overrides (replaced by CSS variables, §2.6).

---

## 2. Functional design

### 2.1 Roles and permissions (enforced on the server; the UI only mirrors them)

| Action | Admin | Risk analyst | Risk owner | Approver | Auditor |
|---|---|---|---|---|---|
| Manage users and roles | ✔ | | | | |
| Create/edit services, assets, obligations | ✔ | ✔ | | | |
| Import CSV (assets, risks) | ✔ | ✔ | | | |
| Create/edit risk details | | ✔ | own risks: description and review date only | | |
| Record initial assessment or reassessment | | ✔ | | | |
| Choose treatment strategy, create treatment actions | | ✔ | ✔ (own risks) | | |
| Update/complete an action (with evidence) | | ✔ | ✔ (if assigned) | | |
| Upload evidence | | ✔ | ✔ (own records) | ✔ (on decisions) | |
| Request acceptance | | | ✔ (own risks) | | |
| Approve/reject acceptance | | | | ✔ never for a risk they own or requested | |
| View everything, download evidence, export reports | ✔ | ✔ | ✔ | ✔ | ✔ |
| View audit log, run integrity check | ✔ | | | ✔ | ✔ |

Every refused attempt returns **403** and writes an audit entry (`action=DENIED`). The frontend hides buttons the user can't use, but every rule is checked in the API, and tests call the API directly to prove it.

### 2.2 Data model (SQLModel tables)

| Model | Key fields |
|---|---|
| `User` | username, full_name, email, password_hash, role (admin, analyst, owner, approver, auditor), job_title, department, is_active, display_timezone (`system` or an IANA zone from the allow-list in §2.7; default `system`) |
| `Session` | token_hash, user, created_at, expires_at, last_seen_at, ip |
| `BusinessService` | code (S1), name, description, owner (User), criticality 1-5 |
| `Asset` | asset_id (A-001), name, type (application, API, database, SaaS, endpoint, network, data store, third-party service), service (FK), owner, classification (public, internal, confidential, restricted), status. **Natural key: name + service** |
| `Obligation` | regime (NDPA 2023, CBN, SEC Nigeria, PCI DSS v4.0), reference, short_title. Linked M2M to assets and risks. Descriptive only; never drives the score |
| `Control` | framework (NIST CSF 2.0, ISO/IEC 27001:2022 Annex A, CIS v8.1), control_id, short_title (our own wording; ISO text is copyrighted) |
| `Risk` | risk_id (R-001), title, description, threat, vulnerability, business_impact, category, assets (M2M, at least 1), obligations (M2M), owner (User), status, next_review_date, created_by, created_at |
| `RiskAssessment` | risk, type (initial, reassessment), likelihood 1-5, impact 1-5, score, band, above_appetite, rationale (required), assessed_by, assessed_at, evidence (required for reassessment). **Insert only: no update or delete route exists, and a DB trigger blocks it** |
| `TreatmentDecision` | risk, strategy (reduce, accept, transfer, avoid), justification, target_likelihood, target_impact (planned residual, labelled "target", never used as the current score), decided_by, decided_at |
| `TreatmentAction` | action_id (T-001), risk, title, description, owner, due_date (defaults from the band's remediation SLA), status (not started, in progress, completed, cancelled), estimated_cost_ngn, completed_at, completed_by, controls (M2M). Optional: sle, aro, effectiveness → ALE before/after, ROI |
| `AcceptanceRequest` | risk, requested_by, justification (≥ 30 characters), proposed_expiry (future, ≤ 12 months), status (pending, approved, rejected), decided_by, decision_date, decision_comment, expiry_date. "Expired" is computed at read time (approved and expiry_date < today), so no scheduler is needed on serverless |
| `Evidence` | target type + id, original_name, mime_type, size, sha256, content (bytes, ≤ 4 MB) or storage_path (volume option), uploaded_by, uploaded_at, description, supersedes (FK self). **No edit or delete** |
| `AuditLog` | seq, timestamp, user, role, action (CREATE, UPDATE, ASSESS, APPROVE, REJECT, IMPORT, LOGIN, LOGOUT, DENIED, EXPORT, SETTING), object type/id, before/after JSON, ip, prev_hash, hash |
| `ImportBatch` | type, file (as Evidence), uploaded_by, totals (valid, rejected, duplicates), status (previewed, committed, cancelled), row results JSON |
| `AppSetting` | appetite_threshold (10), review warning days (30), SLA days per band, org_timezone (`Africa/Lagos`). Every change audited |

The current score of a risk is its **latest assessment**; the original is the earliest `initial` row.

**Audit chain on concurrent serverless instances:** appends are serialised (`BEGIN IMMEDIATE` on SQLite, a row lock on a single chain-head row on PostgreSQL), so two instances can never write the same `prev_hash`.

### 2.3 Workflows and statuses

**Risk status:** `Open` → `Treatment in progress` → `Awaiting reassessment` (set automatically when an action is completed) → back to `Open` or `Treatment in progress` after a reassessment; or `Accepted` (acceptance approved) → `Acceptance expired` (computed once past expiry) → re-review; or `Closed` (strategy avoid, after a reassessment shows the risk was removed).

**Action completion:** the owner clicks Complete → evidence and a completion note are required → status Completed → risk flagged Awaiting reassessment → **the score doesn't change**.

**Reassessment:** analyst only → new L and I, rationale and evidence required → new `RiskAssessment` row → history shows original, target and residual side by side.

**Acceptance (separation of duties, adopted from the group's design):**
1. The owner requests acceptance with a justification (≥ 30 characters) and a proposed expiry date (in the future).
2. Approvers are the **CISO and the CRO**. The server rejects a decision by anyone who is the risk owner or the requester (403 + `DENIED` audit entry).
3. Dual-approver failover: when the CISO owns a risk, only the CRO can decide on it, and the reverse.
4. The decision date is stored automatically; the expiry shows on the dashboard; once expired the risk reopens for review.

### 2.4 Scoring methodology (`docs/methodology.md`, owned by WS2; report §2)

**Likelihood scale**

| Score | Label | Guide |
|---|---|---|
| 1 | Rare | Less than once in 5 years; no known exposure |
| 2 | Unlikely | Once in 2 to 5 years; hard to exploit |
| 3 | Possible | About once a year; some exposure or past attempts |
| 4 | Likely | Several times a year; exposed and actively targeted |
| 5 | Almost certain | Expected monthly or already happening; public exploit or on the CISA KEV list |

**Impact scale** (financial values in Naira; WS2 to confirm the amounts)

| Score | Label | Financial | Operational | Customer data / regulatory |
|---|---|---|---|---|
| 1 | Negligible | < ₦5m | < 1 hour disruption | No personal data |
| 2 | Minor | ₦5m to ₦50m | < 1 day | Internal data, contained |
| 3 | Moderate | ₦50m to ₦250m | 1 to 3 days for one service | Limited personal data; internal report |
| 4 | Major | ₦250m to ₦1bn | > 3 days or several services | BVN/NIN or financial data exposed; NDPC notification likely |
| 5 | Severe | > ₦1bn | Savings or investments stopped | Mass PII exposure, loss of customer funds, regulator sanction or licence risk |

**Bands and governance tiers** (from the group's Capstone_Project_Ver2)

| Score | Band | Appetite | Requirement | Remediation SLA (default action due date) | Review cycle |
|---|---|---|---|---|---|
| 1-4 | Low | Within | Managed routinely by the risk owner | none | 365 days |
| 5-9 | Medium | Within | Owner monitors with periodic control reviews | 180 days | 180 days |
| 10-14 | High | **Above** | Treatment plan (reduce, transfer, avoid) **or** formal acceptance by CISO/CRO with justification and expiry | 90 days | 90 days |
| 15-25 | Critical | **Above** | Immediate escalation, compensating controls, time-bound remediation; acceptance only by CISO/CRO | 30 days | 30 days |

**Appetite statement (The Alajo):** low appetite for loss of customer funds, exposure of customer data or regulatory breach. **Any score of 10 or more is above appetite** and must be treated or formally accepted. Scores below 10 may be managed by the risk owner. The threshold is stored in `AppSetting` and every change is audited.

**Display:** "Likelihood 4 (Likely) × Impact 5 (Severe) = 20 → Critical. Above appetite (threshold 10). Remediation due within 30 days."

All scoring lives in one pure function module, `services/scoring.py`, tested for all 25 combinations.

### 2.5 Screens (React routes)

Ported from Emmanuel's prototype tabs, now backed by the API:

| Route | Screen | Source |
|---|---|---|
| `/login` | Login | new |
| `/` | Executive dashboard: KPI tiles (total, above appetite, pending approvals, overdue actions, expired acceptances), 5×5 heat map (current vs original toggle, dashed appetite boundary, click a cell to filter the register), upcoming reviews (30 days), risks by service, regulatory exposure | prototype "Executive GRC Dashboard" |
| `/risks`, `/risks/:id` | Register with search and filters (service, owner, band, status, obligation, above appetite); risk detail with calculation, assets, obligations, assessment history, decisions, actions, evidence, acceptance, audit trail for that record | prototype "Cyber Risk Register" |
| `/actions` | Treatment actions, overdue first; "my actions" for owners | new |
| `/approvals` | Acceptance queue with the SoD banner; approve/reject with comment and expiry | prototype "Approvals & SoD Workflow" |
| `/assets` | 18-asset inventory by service with obligations and highest linked score | prototype "18 Assets & Compliance" |
| `/reports` | Management report (filters → preview → PDF/CSV export), A4 print layout | Guardian printable report |
| `/imports` | CSV template download, upload, row-by-row preview, commit | new |
| `/audit` | Audit log with filters and "Verify integrity" | prototype "Immutable Audit Trail" |
| `/users` | Admin only | new |

Removed from the prototype: the header "switch active user" dropdown (replaced by real login), client-side SoD checks (now server-side), hard-coded audit entries.

### 2.6 Design system (adopted from Guardian's "Deep Intel", `guardian/design.md`)

> **Colours changed on 26 Nov 2026:** colleagues disliked the green/teal, so the app now uses the Sentinel dashboard's light and dark palettes (neutral greys, blue accent `#0078D4` light / `#3f9cff` dark, red only for critical). Risk-band colours stay as data colours. The token values below are historical; the live values are in `WS1-development/app/frontend/src/theme/tokens.css`.

- **Character:** minimalist, high-contrast, clinical. No gradients, no shadows, **0px corners** on cards, inputs, buttons and modals. Depth from 1px borders and tonal fills only.
- **Font:** Inter only (Google Fonts, weights 400/500/600/700). Type scale: display 48/700, h1 32/700, h2 24/600, h3 20/600, body-lg 16/400, body-md 14/400, `label-caps` 12/700 uppercase with 0.08em tracking (table headers, field labels, metadata), `mono-data` 13/500 tabular numerals (IDs, scores, hashes, timestamps).
- **Spacing:** 4px base unit (4, 8, 16, 24, 48); 12-column grid, 24px gutter; dense tables for analytics views.
- **Colour tokens** as CSS variables, switched by `html.dark` (Tailwind `darkMode: 'class'`), instead of Guardian's `!important` overrides:

| Token | Light | Dark |
|---|---|---|
| `--bg` (page) | `#f9f9f9` | `#0d1615` |
| `--surface` (cards, inputs) | `#ffffff` | `#1a2423` |
| `--surface-container` | `#eeeeee` | `#1a2423` |
| `--hover` (row hover) | `#f5f5f5` | `#1e2c2b` |
| `--text` | `#1a1c1c` | `#dce4e2` |
| `--text-muted` | `#3f4947` | `#8bb5b1` |
| `--outline` | `#6f7977` | `#2b3e3c` |
| `--outline-variant` | `#bfc9c6` | `#2b3e3c` |
| `--primary` (headings accent, primary buttons) | `#003732` / container `#005049` | `#7ecfc5` / container `#002724` |
| `--accent` (links, focus ring, active nav) | `#005049` | `#4db8aa` |
| `--error` | `#ba1a1a` | `#ffb4ab` |
| `--footer` | `#1a1c1c` | `#050c0b` |

- **Risk band colours** (new, not in Guardian; always paired with the text label so colour is never the only signal): Low `#2e7d32` / dark `#81c784`; Medium `#9a6b00` / `#ffd54f`; High `#c75b00` / `#ffb74d`; Critical `#ba1a1a` / `#ffb4ab`. Heat map cells use a 15% tint of the band colour with the count in `mono-data`.
- **Components:** primary button solid teal with white text; secondary white with 1px border; ghost teal text. Inputs 1px border, 2px teal on focus, label above in `label-caps`. Status chips: critical or blocked = solid dark with white text, normal = 1px light border. Cards: 1px light border, header separated by a 1px rule. Tables: 1px row separators, hovered row tinted; on small screens rows become stacked cards with `data-label` captions (Guardian `mob-cards`).
- **Dark/light mode:** a tiny inline script in `index.html` runs before paint, reading `localStorage['risktrack-theme']` and falling back to `prefers-color-scheme` (Guardian's no-flash pattern); toggle button with a Heroicons moon/sun in the top bar.
- **Feedback:** toast at bottom-right (success teal, error red, fade/slide 250 ms) instead of `alert()`; confirmation through an in-page modal (Guardian `gConfirmOverlay`) instead of `confirm()`.
- **Accessibility:** visible 2px focus ring, `aria-label` on icon-only buttons, contrast checked in both themes.

### 2.7 Time and time zones

The team works across zones: Ocen is in Uganda (EAT, UTC+3) and most colleagues are in WAT (UTC+1). The list below also covers neighbouring zones in case some members are elsewhere; WS6 confirms each member's zone and the list is adjusted if needed. Everyone must see times they understand, while the rules stay identical for everyone.

**Storage and API**
- Every timestamp is stored in UTC (`timestamptz` on PostgreSQL; UTC-normalised on SQLite) and sent by the API as ISO 8601 with `Z`.
- Calendar dates (due dates, review dates, acceptance expiry) are stored as plain dates, with no time and no zone.

**Business rules use one official zone**
- "Today" for overdue actions, expired acceptances and upcoming reviews is computed in **The Alajo's official zone, `AppSetting.org_timezone` = `Africa/Lagos` (WAT)**, never in the viewer's zone. So an action due on 5 Dec becomes overdue at 00:00 WAT on 6 Dec for every user, wherever they are (test T32).
- Server code never calls `date.today()` directly; it uses one helper, `services/clock.py` (`now_utc()`, `org_today()`), which tests can freeze.

**Display preference (per user)**
- A time-zone dropdown in the top bar, next to the theme toggle, also in the user's profile menu:

| Option | Zone | Offset |
|---|---|---|
| **System (default)** | Detected from the device with `Intl.DateTimeFormat().resolvedOptions().timeZone`; label shows the detected zone, e.g. "System (Africa/Kampala)" | device |
| WAT: Lagos, Nigeria | `Africa/Lagos` | UTC+1 |
| WAT: Douala, Cameroon | `Africa/Douala` | UTC+1 |
| EAT: Kampala, Uganda | `Africa/Kampala` | UTC+3 |
| EAT: Nairobi, Kenya | `Africa/Nairobi` | UTC+3 |
| GMT: Accra, Ghana | `Africa/Accra` | UTC+0 |
| UTC | `UTC` | UTC+0 |

- The server only accepts `system` or a zone from this allow-list.
- Before login the choice is kept in `localStorage['risktrack-tz']`; after login it is saved to `User.display_timezone`, so it follows the user to any device.
- The frontend formats all times with one helper (`formatDateTime(isoUtc)`) using `Intl.DateTimeFormat` with the chosen zone, and always prints the zone abbreviation, e.g. "5 Dec 2026, 14:30 WAT". Calendar dates are shown as-is, with no zone conversion.
- Deadlines on the dashboard carry a hint, e.g. "Due 5 Dec (overdue after midnight WAT)", so EAT and GMT users understand the cut-off.

**Exports and audit**
- PDF/CSV reports show times in the generating user's chosen zone and state it in the header ("Times shown in EAT, UTC+3; deadlines evaluated in WAT"). The CSV also includes a UTC column.
- The audit log shows the chosen zone, with the exact UTC value in a tooltip and in the CSV export, because auditors compare against UTC.

---

## 3. Repository layout

```
GRC208/
├── PLAN.md
├── WS2-risk-framework/planning-sources/                 teammates' PDFs + emmanuel_prototype_extracted.html (reference for the port)
├── app/                           git repository root
│   ├── README.md                  install, run, demo accounts, troubleshooting
│   ├── CONTRIBUTING.md            branch/PR flow, commit rules, Guardian security checklist
│   ├── .env.example, .gitignore, vercel.json, Dockerfile (option B)
│   ├── api/index.py               Vercel entry point (imports the FastAPI app)
│   ├── backend/
│   │   ├── pyproject.toml         deps + ruff/pytest config
│   │   ├── alembic/               migrations
│   │   ├── app/
│   │   │   ├── main.py            FastAPI app, middleware, routers, serves frontend build locally
│   │   │   ├── core/              config.py (settings), security.py (sessions, passwords, CSRF), headers.py, permissions.py
│   │   │   ├── db.py, models/, schemas/
│   │   │   ├── routers/           auth, services, assets, risks, assessments, treatments, actions, acceptances, evidence, imports, reports, audit, users, settings
│   │   │   ├── services/          scoring.py, audit.py (hash chain), evidence.py, importer.py, report_pdf.py
│   │   │   ├── fixtures/          controls (CSF 2.0, ISO Annex A IDs, CIS v8.1), obligations (NDPA, CBN, SEC, PCI DSS)
│   │   │   └── cli.py             seed-demo, create-user, verify-audit, export-backup
│   │   └── tests/                 pytest: unit (scoring), API (permissions, workflows), audit chain, import
│   ├── frontend/
│   │   ├── package.json, vite.config.ts (proxy /api → :8000), tailwind.config.js, index.html (theme script)
│   │   └── src/                   api/ (generated types + client), components/, pages/, theme/ (tokens.css), hooks/
│   └── sample_data/               CSV templates; alajo_assets.csv, alajo_risks.csv, alajo_treatments.csv (from WS2); *_with_errors.csv
├── docs/                          brief, team-roles, contributions, methodology, regulatory-mapping, data-model (Mermaid ER), test-cases, ai-use-log, defence-notes
├── screenshots/                   numbered E01, E02... for the evidence register
└── deliverables/                  E-Campus submissions (see docs/submission-guide.md)
```

Local run for graders (SQLite, one terminal after install): `cd frontend && npm ci && npm run build`, then `cd ../backend && alembic upgrade head && python -m app.cli seed-demo && uvicorn app.main:app`. FastAPI serves the built frontend, so it's one URL. During development: `uvicorn --reload` plus `npm run dev` with the Vite proxy.

---

## 4. Demo data (The Alajo)

`python -m app.cli seed-demo` resets and seeds the database. **All dates are relative to the day it runs**, so the overdue and expired examples still hold on demo day. WS2 owns and refines the sheets below in `WS1-development/app/sample_data/`; the seed command loads them through the same validation code as the CSV import, so every WS2 refinement is a re-seed, not a code change.

### 4.1 Services, assets and owners (from the org profile)

| S1 Savings and Wallets (owner: Emmanuel Teye Adjei, Head of Engineering) | S2 Investments (owner: Anita Ojimba, Head of Investment Operations) | S3 Customer Onboarding and Support (owner: Gilbert Obichere, Head of Customer Support) |
|---|---|---|
| A-001 Mobile app | A-007 Investment platform | A-013 KYC and BVN verification service |
| A-002 Web app | A-008 Portfolio management system | A-014 Onboarding portal |
| A-003 Wallet ledger | A-009 Fund manager API | A-015 Customer support platform |
| A-004 Savings engine | A-010 Market pricing feed | A-016 Identity document storage |
| A-005 Payment gateway integration | A-011 Investment admin portal | A-017 Email and SMS notification service |
| A-006 Customer database | A-012 Reporting database | A-018 Fraud monitoring tool |

### 4.2 Starter risk register (22 risks; WS2 refines wording and scores)

Built from the scenarios in Emmanuel's prototype and Capstone_Project_Ver2, plus fillers to reach the required states. Score ≥ 10 = above appetite.

| ID | Risk (asset) | L × I | Owner | Strategy | Demo state |
|---|---|---|---|---|---|
| R-001 | Wallet ledger race condition allowing double-spend (A-003) | 4×5=20 | Emmanuel | Reduce | **Above appetite**, actions in progress |
| R-002 | Payment gateway webhook spoofing crediting wallets without settlement (A-005) | 4×5=20 | Emmanuel | Reduce | **Completed action awaiting reassessment** (HMAC verification done) |
| R-003 | KYC/BVN images exposed from misconfigured identity document storage (A-016) | 3×5=15 | Gilbert | Reduce | **Overdue action** (block public access and encryption) |
| R-004 | Fund manager API credential leak enabling unauthorised redemption (A-009) | 3×5=15 | Anita | Reduce | Above appetite |
| R-005 | BOLA/IDOR on savings-goal endpoints in the mobile app (A-001) | 4×4=16 | Emmanuel | Reduce | Above appetite |
| R-006 | Poisoned or stale market pricing feed mispricing T-bill yields (A-010) | 3×4=12 | Anita | Reduce | In progress |
| R-007 | Account takeover through social engineering of support agents (A-015) | 4×4=16 | Gilbert | Reduce | Above appetite |
| R-008 | Card data captured in web app storage or error logs (A-002) | 2×5=10 | Emmanuel | Avoid | Move to hosted tokenisation fields; decommission action |
| R-009 | Insider abuse of the investment admin portal without maker-checker (A-011) | 3×4=12 | Anita | Reduce | In progress |
| R-010 | SMS OTP interception or delay through a single SMS aggregator (A-017) | 3×3=9 | Gilbert | Accept | **Approved acceptance (valid)** |
| R-011 | Unmasked PII in the reporting database replica (A-012) | 2×4=8 | Anita | Reduce | Open, within appetite |
| R-012 | Smurfing through structured micro-deposits evading fraud rules (A-018) | 4×4=16 | Gilbert | Reduce + Transfer | Above appetite; crime insurance |
| R-013 | Credential stuffing and BVN lookup abuse on the KYC API (A-013) | 3×4=12 | Gilbert | Reduce | **Reassessed** (shows original 12 → residual 4 history) |
| R-014 | Fund manager API downtime delaying unit allocations (A-009) | 3×4=12 | Anita | Accept | **Expired acceptance** |
| R-015 | Privileged insider manipulation of ledger balances (A-003) | 2×5=10 | **Adeola (CISO)** | Accept | **Pending acceptance; only the CRO may decide** (dual-approver failover) |
| R-016 | Ransomware encrypting the customer database and backups (A-006) | 3×5=15 | Emmanuel | Reduce | Above appetite |
| R-017 | DDoS against the mobile and web apps during peak savings hours (A-001, A-002) | 3×3=9 | Emmanuel | Transfer | DDoS protection service contract |
| R-018 | Bot-driven fake account creation with synthetic identities (A-014) | 3×3=9 | Gilbert | Reduce | Open |
| R-019 | Customer support SaaS vendor data breach (A-015) | 2×4=8 | Gilbert | Transfer | Contract clauses + cyber insurance |
| R-020 | Sender-ID spoofing of Alajo SMS/email used to phish customers (A-017) | 4×3=12 | Gilbert | Reduce | In progress |
| R-021 | Savings engine scheduled-debit failure causing missed or double debits (A-004) | 2×4=8 | Emmanuel | Reduce | Open |
| R-022 | Stale portfolio data in the portfolio management system after a failed sync (A-008) | 2×3=6 | Anita | Accept | **Pending acceptance**, for the live demo |

The live demo creates a **new** risk with L4 × I5 = 20 (brief requirement); R-001 and R-002 already show the same score in seeded data.

At least 14 treatment actions, e.g. ledger row locking and idempotency keys, HMAC webhook verification (**completed with evidence**), block public bucket access and KMS encryption (**overdue**), Vault-managed fund API tokens, UUIDs and object-level authorisation, ±2.5% price circuit breaker, maker-checker on admin portal, remove Tier-1 2FA override with a 24-hour cooling-off period, velocity-based AML rules, API rate limiting and WAF bot protection, immutable offline backups, hosted card fields, sender-ID registration and DMARC. Costs in ₦. Each linked to NIST CSF 2.0 and ISO 27001 control IDs and to the relevant obligations.

### 4.3 Demo accounts (fictional personas; see `docs/team-roles.md` §4)

| Username | Persona | Role |
|---|---|---|
| `admin` | System administrator | admin |
| `omotayo` | Omotayo Akinola, GRC Analyst | analyst |
| `emmanuel` | Emmanuel Teye Adjei, Head of Engineering | owner |
| `anita` | Anita Ojimba, Head of Investment Operations | owner |
| `gilbert` | Gilbert Obichere, Head of Customer Support | owner |
| `adeola` | Adeola Bamigboye, CISO | approver (also owns R-015) |
| `kelechi` | Kelechi Kenneth Nwankwo, CRO | approver |
| `ernestina` | Ernestina Lamiorkor Tawiah, Internal Auditor | auditor |

One shared demo password set by `seed-demo` and printed in the README (local demo only; the hosted instance uses a different password shared privately with the instructor, never in the report, slides or video).

---

## 5. Way of working (agile)

- **Short phases instead of fixed sprints** (§5.1): each phase is a few days long and ends in a merged, tested chunk. Teams check-ins on Mon and Thu, run by WS6, show the group whatever phase just finished.
- **Planning stays live:** WS2 keeps refining the methodology, register and treatment sheets throughout. Changes arrive as edited files in `docs/` and `WS1-development/app/sample_data/`, reviewed by Omotayo, then picked up by a re-seed. Code changes are only needed if a *rule* changes, and every rule change goes through a GitHub issue first.
- **GitHub flow:** `main` is always deployable; feature branches `feat/<area>`, pull requests reviewed by another developer (Ocen reviews Emmanuel, Ouabo and Kelechi; Emmanuel reviews Ocen's frontend-facing changes). CI (GitHub Actions) runs ruff, pytest, frontend build and Vitest on each PR.
- **Deploys on a single-owner Vercel account:** Vercel is connected to Ocen's GitHub repo. Production deploys only from `main`, and only Ocen merges into `main`. Teammates' branches may not get automatic preview deploys, because Vercel's free Hobby plan can refuse to build commits whose author isn't on the Vercel account. If that happens, teammates test locally (SQLite) and Ocen reviews the PR before merging. If merged commits are still refused, deploy from a GitHub Action using the Vercel CLI with a `VERCEL_TOKEN` repository secret. Environment variables (`DATABASE_URL`, `SECRET_KEY`, the hosted demo password) are set by Ocen in the Vercel dashboard and never shared in chat.
- **Contract first:** backend routers and Pydantic schemas land before the screens that use them; the frontend regenerates types from `/api/openapi.json`. Emmanuel builds the design system on mock data first (U0), then wires each screen group once its API phase is done (§5.1).
- **Definition of done** for any feature: API rule enforced and tested, screen working in both themes and on a phone-width screen, audit entries written, docs touched if behaviour changed.

### 5.1 Development phases (backend and database first, then frontend)

The build goes bottom-up in eleven phases: foundations, then database, domain logic, API, and only then the screens. Each phase is a small chunk that ends in something runnable and tested, merged to `main`. A phase starts only when the one before it is done, with one exception: the **frontend lane** (Emmanuel) starts design-system work early against static mock data, then switches to the real API once the contract it needs exists.

```
P0 Foundations ─► P1 Database ─► P2 Domain logic ─► P3 Auth & access API ─► P4 Register API ─► P5 Treatment & governance API ─► P6 Reporting, import & admin API
                                                         │                       │                     │                                │
Frontend lane:  U0 Design system port (mock data) ───────┴─► U1 App shell & auth ─┴─► U2 Register screens ┴─► U3 Treatment & governance UI ┴─► U4 Dashboard, reports, import ─► P7 Integration, deploy & freeze
```

#### Backend and database

**P0 Foundations** (20 to 21 Nov; Ocen)
- Repo layout per §3; `.gitignore`, `.env.example`, `CONTRIBUTING.md` (Guardian security checklist, branch and commit rules).
- `backend/pyproject.toml` with pinned dependencies; ruff, pytest and coverage config.
- `core/config.py` (pydantic-settings; refuses to start without `SECRET_KEY`; reads `DATABASE_URL`, `DATABASE_URL_DIRECT`, `DEBUG`, `ORG_TIMEZONE`); `postgresql://` normalised to `postgresql+psycopg://`; NullPool on Vercel.
- `main.py` with the security-headers middleware, structured logging and a `/api/health` endpoint that runs `SELECT 1`.
- GitHub Actions CI: ruff, pytest on SQLite, and pytest again on a `postgres:18` service container.
- Vercel skeleton (`api/index.py`, `vercel.json` with region `cle1`), deployed once against the Neon `production` branch to prove the pipeline.
- **Done when:** CI passes on both databases; the hosted `/api/health` answers from Neon; the app refuses to start without `SECRET_KEY`.

**P1 Database schema and migrations** (22 to 23 Nov; Ocen, Kelechi)
- All SQLModel tables from §2.2, with constraints in the database, not just in code: L and I `CHECK 1..5`; unique natural keys (asset name + service, risk_id, action_id, control framework + id); foreign keys with `RESTRICT`; not-null rationale; evidence size ≤ 4 MB.
- Insert-only protection: triggers that reject `UPDATE`/`DELETE` on `risk_assessment`, `evidence` and `audit_log` (PostgreSQL and SQLite versions in the same Alembic migration).
- Alembic baseline migration; reference fixtures for controls and obligations loaded by a data migration.
- `WS1-development/docs/data-model.md` with the Mermaid ER diagram (handed to Gilbert for report §2).
- **Done when:** `alembic upgrade head` works on an empty SQLite file and on Neon; a direct SQL `UPDATE` on an assessment fails on both (basis for T11).

**P2 Domain logic, no HTTP** (23 to 24 Nov; Ocen)
- Pure, unit-tested modules that every later phase calls:
  - `services/scoring.py`: score, band, appetite flag, explanation text, SLA due date.
  - `services/clock.py`: `now_utc()`, `org_today()` in `Africa/Lagos`; freezable in tests.
  - `services/audit.py`: hash-chain append with serialised writes; verify.
  - `services/workflow.py`: allowed risk/action/acceptance status transitions.
  - `core/permissions.py`: a single policy table (§2.1) answering "may user X do action Y on record Z?", including SoD and CISO/CRO failover.
  - `services/evidence.py`: type allow-list by content sniffing, size check, SHA-256.
- **Done when:** unit tests cover all 25 L × I combinations, the 9/10 boundary, every allowed and forbidden status transition, every row of the permission table, and the tamper-detection case (T03, T04, T22 at unit level, T32 with a frozen clock).

**P3 Auth and access API** (25 to 26 Nov; Ocen)
- Login/logout, DB-backed sessions, Argon2 passwords, CSRF double-submit, rate limit on login (slowapi).
- `GET /api/me` (user, role, permissions list, `display_timezone`); `PATCH /api/me/preferences` (timezone from the allow-list, theme).
- FastAPI dependencies `current_user` and `require(permission)`; every refusal returns 401/403 and writes a `DENIED` audit entry.
- `python -m app.cli create-user`; minimal admin user CRUD API.
- **Freezes the auth contract** in OpenAPI so the frontend lane can wire up login.
- **Done when:** T19, T20, T23 and the timezone allow-list validation pass as API tests.

**P4 Register API** (26 to 28 Nov; Ocen, Kelechi)
- CRUD for services, assets, obligations and risks, with filters (service, owner, band, status, obligation, above appetite), search and pagination.
- Assessments: create initial or reassessment; no update or delete routes; history endpoint returning original, target and current.
- Every write audited, with before/after JSON.
- `seed-demo` v1 (Kelechi): services, 18 assets, users, risks and initial assessments from WS2's sheets v1 (due 25 Nov). It goes through the same validation code the CSV import will use.
- **Done when:** T01, T02, T05, T11 and T21 (for risks) pass; the seeded register reproduces §4.2. *(Changed 19 Nov: reassessment and T10 moved to P5, because the brief requires evidence for every reassessment and evidence upload arrives in P5. P4 records the initial assessment only.)*

**P5 Treatment and governance API** (28 Nov to 2 Dec; Ocen)
- Treatment decisions (with target residual); treatment actions with SLA-defaulted due dates; computed overdue flag.
- Evidence upload, download and supersede: permission-checked download, never public, bytes stored in the DB.
- Complete-action flow (evidence required → risk becomes Awaiting reassessment, score unchanged); reassessment with evidence and rationale.
- Acceptance: request, approve and reject, with SoD, failover, justification ≥ 30 characters, future expiry; computed expired state.
- `seed-demo` v2 (Kelechi): actions, evidence placeholders, the valid, expired and pending acceptances, the overdue action, and the completed-awaiting-reassessment case.
- **Done when:** T06 to T16, T21, T27 and T28 pass as API tests; every step of the brief's required demonstration can be performed with API calls alone (a scripted `pytest` scenario).

**P6 Reporting, import and admin API** (2 to 5 Dec; Ocen, Ouabo, Kelechi)
- Dashboard aggregate endpoint: heat-map counts (current and original), above-appetite list, overdue actions, expired acceptances, upcoming reviews, totals by band and service, regulatory exposure.
- Management report: filtered JSON, CSV (with a UTC column) and PDF (fpdf2), stamped with generator, zone and time.
- CSV import (Ouabo): template download, upload, normalise, validate, duplicate check, preview with row reasons, commit, file kept as evidence, audited.
- Audit log query endpoint and integrity verification; `AppSetting` read/update (audited); `verify-audit` and `export-backup` CLI commands.
- **Done when:** T17, T18, T22, T24 to T26 and T29 pass; `seed-demo` final passes T30. **The backend is feature-complete and the API is frozen**: only fixes from here.
- *Built 19 Nov.* Notes: imports are two-step (preview, then commit with a re-check); admins may import assets but not risks, because imported risks can carry scores and admins don't assess; report CSVs neutralise spreadsheet formulas; `/api/audit/verify` also returns the newest entry's hash so Internal Audit can note it and later detect truncation, the one tampering a hash chain alone can't reveal. Tests that need The Alajo seed it once per test file, which keeps the Neon run practical.

#### Frontend

**U0 Design system port, mock data** (from 22 Nov, in parallel with P1 and P2; Emmanuel)
- Vite + React + TypeScript (allowJs) + Tailwind; `theme/tokens.css` with the light and dark variables (§2.6); the no-flash theme script in `index.html`.
- Shared components: buttons, inputs, select, chips, band badge, cards, data table with mobile cards, modal and confirm dialog, toast, empty and error states, page header.
- Port the prototype's layouts (dashboard tiles, heat map grid, register table, approvals queue) as components fed by static mock JSON.
- **Done when:** a `/kitchen-sink` page shows every component in both themes and at phone width.

**U1 App shell and auth** (26 to 28 Nov, after P3; Emmanuel with Ocen)
- `api/` client with types generated from `/api/openapi.json`; CSRF header and 401 handling; TanStack Query setup.
- Login page; route guards by role; top bar with the theme toggle, the time-zone dropdown (§2.7) and the user menu; side navigation per role.
- `formatDateTime`/`formatDate` helpers wired to the user's zone.
- **Done when:** each demo user logs in and sees only their menu; the theme and zone choices persist across reloads and logins (T31, UI part).

**U2 Register screens** (29 Nov to 1 Dec, after P4; Emmanuel)
- Risk register with filters and search; risk detail (calculation panel, assets, obligations, assessment history); create/edit risk; assessment form with live calculation preview; assets inventory by service.
- **Done when:** the demo step "create a risk with L4 × I5 = 20" works in the browser and shows the explanation text.

**U3 Treatment and governance UI** (1 to 4 Dec, after P5; Emmanuel, Ocen)
- Decisions and actions on the risk detail page; "My actions" list with overdue first; complete-with-evidence dialog; evidence list with download and supersede.
- Reassessment form; approvals queue with the SoD banner, approve/reject dialog and a disabled state with the reason ("You own this risk").
- **Done when:** every required demonstration step works by clicking, logged in as the right persona.

**U4 Dashboard, reports, import, admin** (4 to 7 Dec, after P6; Emmanuel, Ouabo)
- Dashboard: KPI tiles, heat map with current/original toggle, dashed appetite boundary and click-to-filter; overdue, expired and upcoming panels.
- Report page with filters, preview, print CSS and PDF/CSV download.
- Import wizard (Ouabo); audit log page with integrity check; users and settings pages (admin).
- Accessibility and responsive pass.
- **Done when:** T17 and T18 pass in the UI; the dashboard numbers match the API.
- *U0 to U4 built 19 Nov by Ocen (AI-assisted), ahead of the planned dates, so Emmanuel's role shifts from building to reviewing, refining the screens against his prototype, and owning UI fixes.* Notes: one `npm run build` and FastAPI serves the app on the same URL (local and VPS); on Vercel the CDN serves it with the same security headers, kept identical to the API's by a backend test. The no-flash theme script is an external file, because the CSP allows scripts from `'self'` only. Risk pages are addressed by code (`/risks/R-013`), so dashboard and report links are readable. Permission checks in the UI only hide controls; the server still decides, and a disabled "Approve or reject" shows the server's reason ("You own this risk, so another approver must decide."). Verified by 22 Vitest tests and a scripted Chromium walkthrough of the whole required demonstration (create L4 × I5 = 20, owner completes with evidence, analyst reassesses, CISO blocked on her own risk, CRO decides it, auditor verifies the chain and exports the PDF, CSV import with reasons), in both themes and at phone width.
- *Added 19 Nov at the team lead's request:* a phone layout following Guardian (teal bar, bottom tab bar with a More sheet, `mob-cards`, no sideways-scrolling tables anywhere: tables become cards below 1280 px and always print as tables), and **account security** borrowed from the Sentinel project because there is no email: My account (profile, preferences, password change that ends other sessions, sessions list with sign-out, recent sign-in activity), a one-time recovery code with a "Forgot password?" flow, a forced change after any administrator-set password, the admin's account-security view with "sign out everywhere", and an offline `reset-password` CLI. One new migration (`account_security`).
- *Added 19 Nov:* dark mode without glare (deep, muted fills for buttons, toasts and alert chips, checked by a script that flags bright fills on every screen) and a **PWA**: manifest, icons, shortcuts, a hand-written service worker that precaches only the app's files and never `/api`, an offline screen, an update bar and an install button (Add to Home Screen steps on iPhone). Verified installable by Chrome's own checks.

#### Integration

**P7 Integration, deploy and freeze** (7 to 10 Dec; Ocen, with WS3)
- *Deployed 19 Nov to the team lead's shared VPS instead of Vercel (the planned fallback): https://thealajo.tinex.tech, Docker Compose behind the server's shared Caddy (automatic Let's Encrypt HTTPS), SQLite in a Docker volume, 384 MB limit, daily backups at 03:30 kept 14 days, hosted demo password shared privately. Vercel + Neon stays configured as the alternative. Steps in `app/deploy/vps/README.md`. Still to do for P7: security scans, WS3 testing on the live site, `v1.0` tag.*
- Migrate Neon `production` with the direct URL; seed it; set the Vercel env vars; deploy `main`.
- Smoke-test the hosted site, including cold start and evidence upload near the 4 MB cap.
- Security checks: `pip-audit`, `npm audit`, `bandit`, `gitleaks`, header check (T29), IDOR checks, `DEBUG` off.
- Clean-clone README test on SQLite by a non-developer from WS4.
- Fix only what WS3 reports; tag `v1.0` on 10 Dec. Screenshots and the sample management report are taken from `v1.0`.
- **Done when:** WS3 has recorded actual results for T01 to T32 against `v1.0`, and the hosted and local runs both pass the required demonstration.

#### Phase calendar

| Dates | Backend and database | Frontend lane | Non-coding workstreams |
|---|---|---|---|
| 20 to 21 Nov | P0 Foundations | Read the prototype source; set up Node | Roles confirmed (21 Nov); WS2 methodology draft; WS3 test plan skeleton |
| 22 to 24 Nov | P1 Database, P2 Domain logic | U0 Design system port | WS2 sheets v1 due 25 Nov; WS3 expected results T01 to T32 |
| 25 to 28 Nov | P3 Auth API, P4 Register API | U1 Shell and auth (from 26 Nov) | WS4 drafts report §1 |
| 28 Nov to 2 Dec | P5 Treatment and governance API | U2 Register screens | WS3 tests P3/P4 via API; WS4 drafts §2 |
| 2 to 5 Dec | P6 Reporting, import, admin API (API frozen 5 Dec) | U3 Treatment and governance UI | WS3 tests P5; WS5 starts slides |
| 4 to 7 Dec | Fixes | U4 Dashboard, reports, import | WS2 methodology frozen 8 Dec |
| 7 to 10 Dec | P7 Integration, deploy, freeze; tag `v1.0` 10 Dec | Fixes | WS3 final test run; screenshots |
| 11 to 12 Dec | Fixes only, no features | | Video (11 Dec), report final (12 Dec), sample report exported |
| 13 to 14 Dec | | | Rehearsal (13 Dec); all 17 final submissions by 14 Dec |

If a phase slips, cut in this order: bonus items (ALE/ROI, coverage report, Nessus import), then the users/settings pages (keep the CLI), then the original-vs-current heat map toggle. Never cut a brief feature (F1 to F8 in `docs/brief.md`) or a test.

---

## 6. Test catalogue (automate where possible; report actual results only)

| ID | Req | Test | Expected |
|---|---|---|---|
| T01 | F2 | Create a risk with L=4, I=5 | Score 20, Critical, above appetite (≥ 10), calculation shown |
| T02 | F2 | L=0 or L=6 entered (UI and direct API) | Rejected with a validation message (422) |
| T03 | F2 | Every L × I combination | Band and appetite flag match the methodology table |
| T04 | F2 | Boundary: score 9 vs score 10 | 9 is within appetite; 10 is above appetite |
| T05 | F1 | Save a risk with no linked asset | Rejected |
| T06 | F3 | Create an action with owner, due date and cost | Saved; due date defaults from the band SLA; appears on the owner's list |
| T07 | F3 | Mark an action complete without evidence | Rejected |
| T08 | F4 | Complete an action with evidence | Status Completed; **risk score unchanged**; risk Awaiting reassessment |
| T09 | F4 | Reassess without evidence or rationale | Rejected |
| T10 | F4 | Valid reassessment | New row; original kept; history shows both |
| T11 | F4 | Try to edit or delete an assessment through the API | No such route (405); a direct DB update is blocked by the trigger |
| T12 | F5 | Owner approves their own acceptance request | 403 and an audit DENIED entry |
| T13 | F5 | Different approver approves | Approved; decision date and expiry stored; audited |
| T14 | F5 | CISO-owned risk (R-015): CISO tries to approve, then CRO approves | CISO 403; CRO succeeds |
| T15 | F5 | Justification under 30 characters, or expiry in the past | Rejected |
| T16 | F5 | Acceptance past its expiry date | Shown as expired on the dashboard; risk flagged for review |
| T17 | F6 | Dashboard with demo data | Heat map counts match the database; overdue, above-appetite, expired and upcoming reviews listed |
| T18 | F6 | Filter and export the PDF/CSV report | File generated; content matches filters; generator and time stamped |
| T19 | F7 | Auditor tries to edit a risk or approve (direct API calls) | 403 for each |
| T20 | F7 | Analyst tries to approve an acceptance | 403 |
| T21 | F7 | Change a record ID in the URL/API to another owner's action | 403 |
| T22 | F7 | Tamper with an audit row in the database, then verify | Integrity check reports the broken entry |
| T23 | F7 | State-changing request without the CSRF token, or without a session | 403 / 401 |
| T24 | F8 | Import a valid assets CSV | All rows committed; audit entry; file stored as evidence |
| T25 | F8 | Import a CSV with bad values, missing fields and a duplicate | Preview lists each rejected row with its reason; only valid rows committed |
| T26 | F8 | Import the same file twice | Second run detects duplicates; nothing duplicated |
| T27 | Sec | Upload a `.exe`, a renamed executable, or a file over 4 MB | Rejected |
| T28 | Sec | Open an evidence download while logged out | 401, no file |
| T29 | Sec | Response headers on any page | CSP, nosniff, frame denial, Permissions-Policy present; HSTS when deployed |
| T30 | Data | Run `seed-demo` | At least 15 assets in 3 services, 20 risks, 12 actions; every required demo state present |
| T31 | Time | Switch display zone System → EAT → WAT → GMT on the same record | Displayed times shift by the right offset with the zone label shown; stored UTC values, overdue and expired flags don't change; choice persists after logout/login |
| T32 | Time | Action due today (Lagos date), checked at 23:30 EAT (21:30 WAT) | Not yet overdue; becomes overdue only after midnight Lagos time |

Record each failure and its fix as "corrections made", which the brief asks for explicitly.

---

## 7. Non-code deliverables

### 7.1 Report (ICDFA template → PDF), owner WS4
Fill in `WS4-documentation/report/GRC208_Group1_Project_Documentation.docx`, delete the guidance text, keep its styles, avoid em-dashes, export to PDF.

| Template section | Content |
|---|---|
| Cover page | Title, programme and course, Group 1, B2025 L1/S2, supervisor, date and version, **team table of all 17 members** |
| Abstract and project links | Final abstract; GitHub link and tag `v1.0`; video link; slides filename |
| 1 Problem and requirements | The spreadsheet problem at The Alajo; regulatory context (NDPA 2023, CBN, SEC Nigeria, PCI DSS); objectives with acceptance criteria; scope (no scanning, fictional data); requirements R01 to R08 mapped to test IDs; comparison with existing tools (Excel registers, Eramba, SimpleRisk, ServiceNow IRM) |
| 2 Technical approach and design | NIST SP 800-39 Frame/Assess/Respond/Monitor as the method; development phases P0 to P7 and U0 to U4 (§5.1); architecture diagram; ER diagram; technology table with trade-offs; security design (roles, SoD, evidence, audit chain, threats: IDOR, self-approval, upload abuse, tampering, CSRF); **scoring methodology, appetite and approval workflow (D3)**; project risks |
| 3 Implementation | Environment and versions; work completed per feature with screenshots; decisions table (FastAPI vs Django, SQLite vs PostgreSQL and the hosting constraint, append-only assessments, hash chain, evidence in DB, no automatic scanning); challenges; evidence register E01 onwards |
| 4 Testing and results | Approach; test table T01 to T32 with actual results and corrections (D4); security checks; acceptance against objectives; limitations |
| 5 Handover | Installation steps (from the README); operating guide per role; delivery inventory; references (APA, direct links); appendices (screenshots, sample report D5, CSV templates, meeting notes) |
| 6 Conclusions | Outcome vs objectives; future work (SIEM/scanner adapters, SSO/MFA, expiry reminders, FAIR/Monte Carlo quantification in ₦); **contribution record (D6)**; authorship and AI-use statement consistent with every member's E-Campus declaration |

### 7.2 Slides (11 to 12), owner Daniella
1. Title, team and workstreams
2. The problem: spreadsheets, missed deadlines, inconsistent scoring, appetite blind spot (The Alajo context)
3. Objectives and the eight required features
4. Architecture and stack (FastAPI, SQLite/PostgreSQL, React)
5. Data model and workflow (risk → assessment → treatment → evidence → reassessment → acceptance)
6. Scoring, bands, appetite ≥ 10 and SLAs (heat map image)
7. Key screens: dashboard, register, risk detail
8. Governance controls: roles, SoD with CISO/CRO failover, evidence, hash-chained audit log
9. Data import with validation
10. Testing results (pass/fail summary, corrections made)
11. Business value, limitations and next steps
12. Contributions and questions

### 7.3 Demo video (target 10 minutes), owner Farida
| Time | Segment | Suggested speaker |
|---|---|---|
| 0:00 to 0:45 | Introduction: project, speakers, The Alajo scenario | WS6 / WS5 |
| 0:45 to 1:45 | Log in as analyst; dashboard tour (heat map, above appetite, overdue, upcoming reviews); theme toggle | Emmanuel |
| 1:45 to 3:00 | Create a risk with L4 × I5 = 20, linked to assets and obligations; show the calculation | Omotayo |
| 3:00 to 4:15 | Owner adds a treatment action, uploads evidence, completes it; **score still 20** | Ocen |
| 4:15 to 5:15 | Analyst reassesses with evidence and justification; history shows original vs residual | Omotayo |
| 5:15 to 6:45 | Owner requests acceptance; owner's own approval blocked; CRO approves; CISO-owned risk failover | Ocen |
| 6:45 to 7:45 | Overdue action, expired acceptance, updated management report and PDF export | Emmanuel |
| 7:45 to 8:45 | Auditor tries to edit or approve (403); audit log and integrity check | Ernestina |
| 8:45 to 9:30 | CSV import with rejected rows explained | Ouabo |
| 9:30 to 10:15 | Tests passing; limitations and conclusion | Ebere |

Reset with `seed-demo` before recording; 1080p capture, browser zoom 110 to 125%, clear audio.

### 7.4 Abstract, contribution record, AI-use log
- Abstract: written last from real results (`WS5-presentation/abstract.md`).
- `docs/contributions.md` + each member's `WS<n>-<workstream>/members/<NN-name>/submission.md` must agree. Developers commit under their own GitHub accounts.
- `docs/ai-use-log.md`: date, member, AI tool (e.g. Claude Code, Gemini for the prototype), purpose, what was generated, how it was checked. Feeds report §6.3; each member's own declaration covers only their own use.
- **Ideas adopted from teammates** (for §6.2 and the defence): The Alajo org profile, people and appetite statement (Omotayo); NIST SP 800-39 phased structure (Omotayo); governance tiers, CISO/CRO dual approver, justification and expiry rules, regulatory mapping (Capstone_Project_Ver2, group); screen structure, risk scenarios and dashboard ideas (Emmanuel's prototype).

### 7.5 Defence notes (`WS5-presentation/defence-notes.md`), owner Farida
Short answers for: why 1 to 5 scales and these bands; why appetite 10 (low appetite for funds, data, regulatory loss; catches all High and Critical); why completing an action doesn't lower the score; how self-approval is prevented and where in the code; CISO/CRO failover; what makes evidence trustworthy (SHA-256, no delete, supersede only); how audit tampering is detected; how CSV duplicates are detected; why FastAPI + React instead of Django; why SQLite locally but PostgreSQL when hosted; why no automatic scanning; what next.

---

## 8. Project risks

| Risk | Effect | Mitigation and owner |
|---|---|---|
| 17-person group, uneven availability | Weak contribution record; uneven defence | Clear workstreams; WS6 tracks tasks and evidence weekly (Deborah) |
| Only two confident developers | Core features late | Ocen owns the critical backend path; bonuses only after P6; Kelechi and Ouabo get self-contained tasks (seed/tests, import) |
| FastAPI has no built-in auth/admin | Security mistakes | Permissions designed as one policy table in P2 and auth built in P3 with tests T19 to T23 first; reuse Guardian's header and checklist (Ocen) |
| Serverless host wipes SQLite/evidence | Data loss on the hosted demo | §1.2 option A or B; local SQLite demo as fallback; `export-backup` before any change (Ocen) |
| Vercel 4.5 MB request limit | Evidence upload fails | 4 MB cap enforced and tested (T27) |
| Free PostgreSQL expiry (Guardian's Render experience) | Hosted demo dies before grading | Use Neon (no expiry) or option B; keep `export-backup` JSON (Ocen) |
| Scope creep from bonus features | Core features unfinished | Brief features F1 to F8 first; bonuses (ALE/ROI, coverage report, scanner import) only after P6, cut first if a phase slips (§5.1) |
| Planning refinements arrive late | Demo data or methodology out of date | Sheets loaded by re-seed; methodology freeze 8 Dec (Omotayo) |
| Demo dates going stale | Overdue/expired examples disappear | Relative dates; re-seed before recording |
| Lost work | Missed deadline | Push daily; report copy outside the repo |
| Late E-Campus submission or empty wallet | Zero marks for that member | Submit by 14 Dec; NGN 1,000 balance check; WS6 records receipts |

---

## 9. Change backlog (feedback of 22 to 26 Nov 2026)

Raised by Omotayo Akinola (gaps against the brief), Emmanuel's updated prototype (`WS1-development/prototype/`, live preview https://sites.google.com/view/alajocyberriskreg/full-page-embed) and colleagues' design feedback. Status: **open** unless marked done.

### 9.1 Decisions needed first (WS2, Adeola Bamigboye with Omotayo Akinola)

| # | Decision | Options | Affects |
|---|---|---|---|
| D-1 | Where the Critical band starts | 15 (app now) or 16 (prototype) | Scoring code, heat map, report 2.6, slides |
| D-2 | Top impact label | "Severe" (app now) or "Catastrophic" (prototype) | Scales, explanations, report, slides |
| D-3 | Definitions for the 5 likelihood and 5 impact levels | Start from the prototype's (probability %, outage hours, loss ranges); convert $ ranges to ₦ | Rubric, report 2.6 |

### 9.2 Application changes (WS1, Ocen Richard with Emmanuel Teye Adjei)

**A. Inherent and residual risk (priority 1). Done 26 Nov.** The app already keeps the first assessment and every reassessment (insert-only); the gap is naming and presentation.
- Rename "Original" to **Inherent risk** and "Current" to **Residual risk** once a reassessment exists (before that: "Inherent, not yet reassessed"); "Target" stays.
- Show inherent and residual side by side with the reduction (e.g. "Inherent 20 Critical → Residual 8 Medium, −12") on the risk page, the register, the management report (PDF and CSV columns) and the dashboard heat-map toggle (Inherent / Residual).
- Label the history: first entry **Inherent**, then **Residual reassessment 1, 2, …**

**B. Documented scoring methodology (priority 2). Done 26 Nov:** the definitions are editable by the administrator in Settings, so WS2's final wording and ₦ ranges (D-3) need no code change.
- Store and show the definition of each likelihood and impact level (after D-3).
- Add a **"View scoring rubric"** button on the register and in the assessment forms, and a **"How scoring works"** page (scales, bands, appetite, deadlines, the four governance controls).

**C. Residual reassessment workflow (priority 3). Done 26 Nov** (migration `84070bc4c4e0`, table `assessment_action`, insert-only). Already enforced: completion needs evidence and leaves the score unchanged ("Awaiting reassessment"); reassessment needs new likelihood and impact, a justification and evidence; the previous assessment is kept; only an analyst can reassess.
- Link each reassessment to the completed action(s) it follows ("Reassessed after T-001 was completed"); this is the one data-model addition (new migration).
- A **"Reassess now"** button inside the "Awaiting reassessment" notice; list the completed actions and their evidence in the reassessment form.
- Show the change in the result ("Residual 8, was 20").

**D. Design (done 26 Nov, commit `3028cd8`).** Sentinel palette in light and dark mode; teal removed. Open: decide whether the Low band stays green or becomes blue like Sentinel's "OK".

### 9.3 Knock-on work

| Item | Owner | When |
|---|---|---|
| Push local commits to GitHub | Ocen Richard | Now |
| Delete the leftover `dev` branch on GitHub | Ocen Richard | Now |
| Collect GitHub usernames and add collaborators | Coordinators | Before 27 Nov |
| Redeploy https://thealajo.tinex.tech after the app changes (backup first; `deploy/vps/README.md`) | Ocen Richard | After 9.2 |
| Re-seed so the demo history reads inherent → residual (R-001, R-013) | Ocen Richard | With the redeploy |
| Retake screenshots E01 to E20 in the new colours and wording | Ernestina Lamiorkor Tawiah with Ocen | After the redeploy |
| Update report sections 2.4 to 2.6 and 4 (inherent/residual wording, scale definitions, ₦ ranges, screenshots) | WS4 (Ponsel Iliya) | After D-1 to D-3 and the screenshots |
| Update slides 5 to 7 and 10 | WS5 (Daniella Edinam Nyaletey) | Same |
| Contributions uploaded to workstream folders | Everyone | 27 Nov, before the 29 Nov meeting |

**Order:** WS2 decisions (9.1) → app changes A, then C, then B → redeploy and re-seed → screenshots → report and slides.

---

## 10. Developer workflow (local)

`.env` points at the Neon **production** database, so every local command overrides it with the in-project SQLite file.

**Check the built app** (one address):

```bash
cd "WS1-development/app/frontend" && npm run build
cd ../backend
DATABASE_URL="sqlite:///$PWD/data/risktrack.sqlite3" DATABASE_URL_DIRECT="" COOKIE_SECURE=false \
  .venv/bin/uvicorn app.main:app --port 8000
```

Open http://127.0.0.1:8000. If the old look appears, the installed-app cache is serving the previous version: click **Reload** on the "new version" bar or press Ctrl+Shift+R.

**Develop with live reload** (two terminals):

```bash
# Terminal 1: API
cd "WS1-development/app/backend"
DATABASE_URL="sqlite:///$PWD/data/risktrack.sqlite3" DATABASE_URL_DIRECT="" COOKIE_SECURE=false \
  .venv/bin/uvicorn app.main:app --reload --port 8000

# Terminal 2: interface
cd "WS1-development/app/frontend" && npm run dev
```

Open http://localhost:5173; interface changes appear instantly.

**Useful commands:**
- Free port 8000: find the process with `ss -ltnp | grep :8000`, then `kill <pid>`.
- Reset the demo data: `DATABASE_URL="sqlite:///$PWD/data/risktrack.sqlite3" DATABASE_URL_DIRECT="" .venv/bin/python -m app.cli seed-demo --reset --yes` (in `backend/`; demo password `Alajo-Demo-2026!`, local only).
- Tests: `.venv/bin/pytest` in `backend/`, `npm test` in `frontend/`. Deadlines are judged in Lagos time (WAT), so tests take "today" in Africa/Lagos.
- After moving the folder, recreate the Python environment: `rm -rf .venv && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.

