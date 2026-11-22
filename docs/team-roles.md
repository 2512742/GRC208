# GRC208 Group 1: Team Roles and Workstreams

Project: Cyber Risk Register and Treatment Management Platform
Demo organisation: The Alajo, a fictional Lagos digital savings and investment platform (decided). Risk appetite: scores of 10 or more are above appetite (decided).
Stack: FastAPI + SQLite backend, React frontend (see `PLAN.md` §1)
Due: 15 Dec 2026, 11:59 PM WAT. Group target for every final submission: 14 Dec 2026.
Status: DRAFT for group agreement. Swaps are open until 21 Nov 2026.

## 1. How roles were assigned

- **Adopted from work already done:**
  - Ocen Richard volunteered as the full-stack developer and technical lead.
  - Emmanuel Teye Adjei built and shared the React prototype, so he joins development.
  - Omotayo Akinola wrote the org profile, the improved structure and the documentation draft, so he leads risk framework and analysis.
- **Everyone else (14 members)** was placed by a reproducible random draw: Python `random.Random(208).shuffle()` over the alphabetical list, then dealt into the open slots in workstream order.
- **Swaps:** any two members may swap by telling the coordinator before 21 Nov. Anyone drawn into Development who is not comfortable coding should swap into QA or Documentation. Coding experience is not assumed.

## 2. Group roster and assignments

| # | Name | Reg. number | Workstream | Role | How assigned |
|---|---|---|---|---|---|
| 1 | Abdullahi Murtala Kawu | 2025/GCR/12893 | WS4 Documentation | Report sections 4 and 5, references | Random |
| 2 | Adeola Bamigboye | 2025/GRC/10068 | WS2 Risk framework | Risk criteria and scoring methodology | Random |
| 3 | Anita Ojimba | 2025/GRC/10120 | WS3 QA and testing | Functional and demo-step testing | Random |
| 4 | Daniella Edinam Nyaletey | 2025/GCR/12679 | WS5 Presentation | Slides | Random |
| 5 | Deborah Orimikoya | 2025/GRC/10963 | WS5 Presentation | Abstract, slides support, defence rehearsal | Random (moved from WS6 on 22 Nov) |
| 6 | Ebere Emilia Ikechukwu | 2025/GCR/12707 | WS3 QA and testing | QA lead, test catalogue and results | Random |
| 7 | Edna Moraa Maburi | 2025/GCR/12688 | WS2 Risk framework | Risk identification and analysis (register sheet) | Random |
| 8 | Emmanuel Teye Adjei | 2025/GCR/12765 | WS1 Development | Front-end, dashboard and reporting | Adopted (prototype) |
| 9 | Ernestina Lamiorkor Tawiah | 2025/GCR/12776 | WS3 QA and testing | Security and access-control testing, evidence register | Random |
| 10 | Farida Baberin-Yor Beacher | 2025/GCR/12741 | WS5 Presentation | Workstream lead; demo video and defence preparation | Random (lead from 22 Nov) |
| 11 | Gilbert Obichere | 2025/GCR/12646 | WS4 Documentation | Report sections 2 and 3, diagrams | Random |
| 12 | Kelechi Kenneth Nwankwo | 2025/GCR/12814 | WS1 Development | Demo data, fixtures, automated tests | Random |
| 13 | Maria Nalima | 2025/GRC/10582 | WS2 Risk framework | Treatment plan and regulatory/control mapping | Random |
| 14 | Ocen Richard | 2025/GCR/12742 | WS1 Development | Technical lead, full-stack developer | Adopted (volunteered) |
| 15 | Omotayo Akinola | 2025/GCR/12813 | WS2 Risk framework; WS6 | Group coordinator (schedules and chairs meetings); WS2 lead | Adopted (planning PDFs; coordinates in practice) |
| 16 | Ouabo Kamdem Derrick Arnaud | 2025/GCR/12778 | WS1 Development | CSV import feature | Random |
| 17 | Ponsel Iliya | 2025/GCR/12779 | WS4 Documentation | Report editor, section 1 and final PDF | Random |

Registration numbers were copied from the E-Campus group list. Some use `GRC` and some use `GCR`, and they are copied exactly as shown there.

## 3. Workstreams

### WS1 Development (lead: Ocen Richard)
Builds the FastAPI backend and React frontend described in `PLAN.md`. Work in weekly sprints (`PLAN.md` §5).

| Member | Responsibilities | Done when |
|---|---|---|
| Ocen Richard | Repository, CI and setup, FastAPI backend: data model, auth and sessions, scoring engine, treatment/reassessment/acceptance workflows, segregation of duties on the server, evidence upload, hash-chained audit log, integration, README, deployment | Every step of the required demonstration works end to end |
| Emmanuel Teye Adjei | Port the prototype to the real React app on the shared design system, wired to the API: dashboard (heat map, KPI tiles, above appetite, overdue, upcoming reviews, regulatory exposure), register list and filters, management report page and print layout, approvals and audit screens | Dashboard and report show correct data from the database |
| Ouabo Kamdem Derrick Arnaud | CSV import (backend endpoint and React wizard): downloadable templates, validation, row-by-row rejection reasons, duplicate blocking, preview and commit; sample valid and error CSVs | A bad file is rejected with clear reasons and nothing is duplicated |
| Kelechi Kenneth Nwankwo | `seed-demo` CLI command loading WS2's sheets (dates relative to today), control and obligation fixtures, pytest API tests with WS3 | Seeded data meets every minimum in the brief and the tests pass |

### WS2 Risk framework and analysis (lead: Omotayo Akinola)
This is the paperwork phase (Phase A in the Improved Structure, built on NIST SP 800-39 Frame, Assess, Respond, Monitor). Its sheets feed the demo data. Deliver them as CSV files in the import template format, so they also exercise the CSV import feature.

| Member | Responsibilities | Output |
|---|---|---|
| Omotayo Akinola | A1 org profile (done), A2 capacity, appetite and tolerance statement, A9 governance roles, approval rules and reporting; final owner of the methodology document | `docs/org-profile.md`, `docs/methodology.md` (sections 1 and 4) |
| Adeola Bamigboye | A3 risk criteria: likelihood and impact scales (impact in ₦), rating bands, appetite threshold, remediation deadlines and review cycles per band | `docs/methodology.md` (sections 2 and 3) |
| Edna Moraa Maburi | A4 to A6: at least 22 risk scenarios with asset(s), threat, vulnerability, business impact, owner, L, I, score, band and decision. Start from the 12 scenarios in Emmanuel's prototype | `WS1-development/app/sample_data/alajo_risks.csv` and the assets sheet |
| Maria Nalima | A7 and A8: at least 14 treatment actions with owner, deadline, cost (₦), status and evidence; the special cases (overdue, expired acceptance, awaiting reassessment, above appetite); mapping to NDPA 2023, CBN, SEC Nigeria, PCI DSS v4.0 and to NIST CSF 2.0 / ISO 27001 control IDs | `WS1-development/app/sample_data/alajo_treatments.csv`, `docs/regulatory-mapping.md` |

### WS3 QA and testing (lead: Ebere Emilia Ikechukwu)
| Member | Responsibilities | Output |
|---|---|---|
| Ebere Emilia Ikechukwu | Test plan; expected results for T01 to T25 written before features land; records actual results and corrections (brief deliverable 4) | `docs/test-cases.md` |
| Anita Ojimba | Runs the required-demonstration steps after each build phase and logs defects as GitHub issues with steps to reproduce | Issues; demo-step checklist in `docs/test-cases.md` |
| Ernestina Lamiorkor Tawiah | Security and access-control tests: auditor write attempts, self-approval, IDOR, upload abuse, audit-log tamper check; keeps the numbered screenshot evidence register E01 onwards | `docs/test-cases.md` (security section), `screenshots/` |

### WS4 Documentation (lead: Ponsel Iliya)
Writes the report in the ICDFA template. Plain styling with no em-dashes, and only results that were actually observed.

| Member | Responsibilities | Template sections |
|---|---|---|
| Ponsel Iliya | Editor: cover page and team table, section 1 (problem, objectives, scope, requirements, comparison with existing tools), consistency pass, final PDF export | Cover, 1, final assembly |
| Gilbert Obichere | Section 2 (approach, architecture and ER diagrams with WS1, technology decisions, security design, project risks) and section 3 (implementation, screenshots, decisions, challenges) | 2, 3 |
| Abdullahi Murtala Kawu | Section 4 (from WS3 results), section 5 (installation steps verified on a clean machine, user guide per role, delivery inventory), references (APA, direct links), appendices | 4, 5, references |

### WS5 Presentation, video and defence (lead: Farida Baberin-Yor Beacher)
| Member | Responsibilities | Output |
|---|---|---|
| Daniella Edinam Nyaletey | 10 to 12 slides following `PLAN.md` §6.2 and the template's presentation outline | `WS5-presentation/slides/` |
| Farida Baberin-Yor Beacher | Video script (`PLAN.md` §6.3) and speaker list, recording coordination, upload and viewing-access check; defence Q&A bank and rehearsal | `WS5-presentation/video/demo-video-link.md`, `WS5-presentation/defence-notes.md` |

### WS6 Coordination and submission (Omotayo Akinola, with Ocen Richard)
*Updated 22 Nov: Omotayo coordinates the group in practice, scheduling and chairing meetings; Ocen is co-coordinator for gender balance. Every workstream now has at least one of the nine most active members, and an active member as lead (so WS5 is led by Farida).*
- **Ocen Richard:** co-coordinator; supports Omotayo and follows up technical tasks.
- **Omotayo Akinola:** schedules and chairs Teams meetings and check-ins, keeps the task tracker.
- **Both coordinators:** the record-keeping below. (Deborah Orimikoya moved to WS5 on 22 Nov to balance group sizes.)
- Maintains `docs/contributions.md` (brief deliverable 6, report section 6.2) and consolidates `docs/ai-use-log.md`.
- Finalises the abstract with the workstream leads.
- Checks every member's folder under `WS<n>-<workstream>/members/` is complete and consistent with section 6.2. Before 14 Dec, chases each member's final submission and records their receipt.

## 4. In-app personas are not project roles

The demo app uses seven members' names as fictional staff of The Alajo, taken from the org profile. These are **demo accounts only** and are separate from project roles. For example, Kelechi is the CRO persona in the app but a developer on the project.

| Persona in app | Member | App role |
|---|---|---|
| GRC Analyst | Omotayo Akinola | Risk analyst |
| Head of Engineering | Emmanuel Teye Adjei | Risk owner |
| Head of Investment Operations | Anita Ojimba | Risk owner |
| Head of Customer Support | Gilbert Obichere | Risk owner |
| CISO | Adeola Bamigboye | Approver |
| CRO | Kelechi Kenneth Nwankwo | Approver |
| Internal Auditor | Ernestina Lamiorkor Tawiah | Auditor (read-only) |

## 5. Timeline and hand-offs

| Date | Milestone | Owner |
|---|---|---|
| 21 Nov | Roles confirmed, swaps closed; repository created, developers invited; P0 Foundations done | WS6, Ocen |
| 24 Nov | Database schema and domain logic done (P1, P2); design-system components on mock data (U0) | Ocen, Kelechi, Emmanuel |
| 25 Nov | Methodology draft, risk register sheet and treatment sheet v1 handed to WS1; expected results T01 to T32 written | WS2, WS3 |
| 28 Nov | Auth and register API done (P3, P4); app shell with login, theme and time-zone selector (U1) | Ocen, Kelechi, Emmanuel |
| 2 Dec | Treatment and governance API done (P5); register screens (U2); report sections 1 and 2 drafted | WS1, WS4 |
| 5 Dec | Reporting, import and admin API done; **API frozen** (P6) | Ocen, Ouabo, Kelechi |
| 7 Dec | All screens done (U3, U4) | Emmanuel, Ouabo |
| 8 Dec | Methodology frozen | WS2 |
| 10 Dec | Deployed to Vercel + Neon, security checks done, tag `v1.0`; final test run with actual results; screenshots final (P7) | Ocen, WS3 |
| 11 Dec | Video recorded; slides final; report sections 3 to 6 drafted | WS5, WS4 |
| 12 Dec | Final report PDF; every member's `submission.md` filled in | WS4, everyone |
| 13 Dec | Defence rehearsal: each member explains the whole app and their own part | WS5 |
| 14 Dec | Every member completes Final submit on E-Campus and confirms their receipt | Everyone, WS6 checks |

Development phase details: `PLAN.md` §5.1.

## 6. Rules for everyone

- Each member does and records **their own** work. Developers commit under their own GitHub account. Non-coders keep their drafts under their own name in the shared drive or the repository, because these are the evidence for section 6.2.
- Each member writes their own "Additional information / your contribution" text and AI-use declaration in `WS<n>-<workstream>/members/<your folder>/submission.md`. These must match your row in section 6.2 of the report.
- Every member submits on E-Campus individually. A non-submitter's status stays "not submitted" even if the group is graded. Final submission charges NGN 1,000 from each member's portal wallet, so check your balance early.
- Never put passwords or secret keys in the report, slides, video or repository.
