# E-Campus submission: Ocen Richard

| | |
|---|---|
| Registration number | 2025/GCR/12742 |
| Workstream | WS1 Development |
| Assigned role | Technical lead, full-stack developer |

Shared items (the same for everyone) are listed in `docs/submission-guide.md`. This file holds **your personal fields only**. Write them yourself, in your own words.

## 1. Additional information / your contribution

Paste into the E-Campus rich-text field. Describe your tasks, decisions and contribution. It must match your row in report section 6.2 and in `docs/contributions.md`.

*Draft prepared from the repository record (updated 26 Nov 2026). Rewrite it in your own words before pasting.*

**Tasks I was responsible for:**
- Technical lead and full-stack developer (WS1): architecture, repository, CI, backend, frontend integration, deployment.
- Planning document (`PLAN.md`): phases, requirements-to-test mapping, team roles and the deliverables map.

**Work I personally completed (with evidence: commit, file, test ID, report section, screenshot ID):**
- Backend in FastAPI: data model and migrations, scoring engine, treatment, reassessment and acceptance workflows, server-side segregation of duties, evidence handling, hash-chained audit log, dashboard and PDF/CSV reports, CSV import, account security (commits P0 to P6 and later in github.com/2512742/GRC208; tests T01 to T32).
- React frontend, phone layout and installable app (commits U0 to U4; screenshots E01 to E22); inherent and residual risk, reassessments linked to completed actions, scoring rubric and How scoring works page (PLAN.md 9.2; E10, E21, E22).
- 480 automated backend tests and 29 frontend tests, run on SQLite and PostgreSQL 18 (report section 4).
- Deployment to https://thealajo.tinex.tech with HTTPS, daily file backups and a daily full copy to Neon PostgreSQL with a tested restore (`deploy/vps/`; report 2.2, 3.1 and 5.1).
- First drafts of the report, slides, abstract, video script and defence notes for the group to edit.

**Decisions I made or influenced, and why:**
- FastAPI and React instead of Django: matched Emmanuel's prototype; permissions designed as one tested policy table.
- Insert-only assessments and a hash-chained audit log: residual-risk history can never be lost or silently edited.
- SQLite as the live database with Neon PostgreSQL as a remote backup: simple to run on one server, with an off-site copy in a second engine.
- Server-side segregation of duties with CISO to CRO failover: the brief forbids self-approval, so the UI is never the only control.
- Self-hosting on my VPS rather than Vercel: persistent storage, custom domain and no cold starts at no cost.

**What I can explain at the defence:**
- The architecture, scoring and appetite logic, the approval and residual-risk rules and where they are enforced in code, the audit chain, the test results and corrections, and the deployment.

## 2. AI-use declaration

- [x] I used an AI-enabled tool while preparing this work. (Tick only if true for **you**.)

**Tools used:** Claude Code (Anthropic Claude Opus 5.5), an AI coding assistant.

**How you used them** (purpose, what was produced, and how you checked the output):
*Draft; rewrite in your own words.* I used Claude Code to write and refine the application code, tests, deployment configuration and first drafts of the documentation, under my direction and review. I checked the output by running the automated tests on SQLite and PostgreSQL, clicking through every required demonstration step in a browser, testing the hosted site, and reviewing changes before committing them. Each use is logged in `docs/ai-use-log.md`.

Keep this consistent with report section 6.3 and `docs/ai-use-log.md`.

## 3. Pre-submission checklist

- [ ] Abstract pasted from `WS5-presentation/abstract.md` (frozen version)
- [ ] Project documentation PDF uploaded (frozen version)
- [ ] Section 1 above pasted into "Additional information / your contribution"
- [ ] Slides PDF uploaded
- [ ] Video HTTPS link pasted and opens for the instructor
- [ ] AI-use declaration completed (section 2 above)
- [ ] Draft saved and saved evidence reviewed on E-Campus
- [ ] Wallet has at least NGN 1,000

## 4. Submission receipt

| Final submitted (date, time WAT) | Receipt / reference | Checked by WS6 |
|---|---|---|
| | | |
