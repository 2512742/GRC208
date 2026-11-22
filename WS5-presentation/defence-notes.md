# Defence notes (draft)

Owner: Farida Baberin-Yor Beacher (WS5). Short answers for the questions the brief says assessors will ask ("scoring assumptions, approval controls, treatment decisions and the evidence supporting residual risk assessments"), with where to show each one. Every member should be able to give these answers and explain their own contribution (report section 6.2).

## Scoring

**Why 1 to 5 scales and these bands?**
The brief fixes the 1 to 5 scales. Five points are easy to agree on in a workshop and give 25 cells, enough to separate risks without false precision. Bands: Low 1 to 4, Medium 5 to 9, High 10 to 14, Critical 15 to 25 (report 2.5). Code: `WS1-development/app/backend/app/services/scoring.py`; all 25 combinations are tested (T03).

**Why is the appetite threshold 10?**
The Alajo has a low appetite for loss of customer funds, exposure of customer data and regulatory breach. Ten is where High begins, so every High and Critical risk must be treated or formally accepted, while Low and Medium can be managed by the owner. The boundary is tested both ways: 9 is within, 10 is above (T04). It is an admin setting; changes are audited and old assessments keep the threshold that applied.

**How does a user know how a score was calculated?**
Every assessment stores its explanation, for example "Likelihood 4 (Likely) × Impact 5 (Severe) = 20 → Critical. Above appetite (threshold 10). Remediation due within 30 days." Show it on any risk page.

## Treatment and residual risk

**Why does completing an action not lower the score?**
Finishing work is not proof that the risk fell. Completion needs an evidence file and moves the risk to "Awaiting reassessment"; only an analyst's reassessment with its own evidence and rationale changes the score (T08 to T10). Show: complete an action, the score stays 20.

**What evidence supports a residual score, and why trust it?**
Each reassessment requires a file. Files are type-checked by their content (a renamed `.exe` is refused), capped at 4 MB, stored with a SHA-256 fingerprint, never deleted, and replaced only by a new version that supersedes the old one (T27, T28). Code: `WS1-development/app/backend/app/services/evidence.py`.

**Can someone quietly change an old assessment?**
No. There is no edit or delete route, and database triggers reject an UPDATE or DELETE even from a direct SQL session (T11). Code: the baseline migration in `WS1-development/app/backend/alembic/versions/`.

## Approval controls

**How is self-approval prevented, and where?**
On the server, in one permission policy: an approver can never decide a risk they own or a request they made. Refusals return 403 and write a DENIED entry to the audit log (T12). Code: `WS1-development/app/backend/app/core/permissions.py` (`authorize`). The screen only shows the server's reason.

**What happens when the CISO owns the risk?**
The CRO decides (R-015 in the demo data). The CISO sees "You own this risk, so another approver must decide." (T14).

**What makes an acceptance valid?**
A justification of at least 30 characters, an expiry date in the future, and an independent approver. After expiry the acceptance shows as expired and the risk is flagged for review (T15, T16; R-014 in the demo).

## Audit and access

**How is tampering with the audit log detected?**
Each entry stores a hash of its content plus the previous entry's hash. Editing or deleting any entry breaks the chain; "Verify integrity" names the first broken entry (T22). Note the newest hash after each check: it also reveals entries cut from the end. Code: `WS1-development/app/backend/app/services/audit.py`.

**Who can do what?**
Analyst, risk owner, approver, auditor (read-only) and administrator (report 2.4). The API checks every request, so hiding a button is never the only control (T19 to T21).

## Import

**How are duplicate CSV rows detected?**
Against the register (same asset name in the same service, or an existing code) and within the file itself. A preview lists every row's result with reasons; commit re-checks each row, so uploading the same file twice creates nothing twice (T24 to T26). Code: `WS1-development/app/backend/app/services/importer.py`.

## Technology choices

**Why FastAPI and React instead of Django?**
Emmanuel's prototype was already React, and FastAPI gives typed validation and an API contract the frontend types are generated from. The cost was building authentication and permissions ourselves, which we designed as one tested policy table.

**Why SQLite and PostgreSQL?**
SQLite needs no setup for graders and suits one server; PostgreSQL (Neon) suits multi-instance hosting. The same code and all tests run on both.

**Why no automatic vulnerability scanning?**
Out of the brief's scope and time. A future adapter could turn scanner findings into proposed risks through the same validation as CSV import.

**What would you do next?**
Reminders by email or Teams, single sign-on and multi-factor authentication, risk quantified in ₦, and scanner or SIEM adapters (report 6.1).

## Possible tough questions

- *Is the hosted data real?* No. The Alajo and all its people and data are fictional; personas are named after group members.
- *Did you use AI?* Yes, declared in the report (6.3) and in `docs/ai-use-log.md`; each member declares their own use on E-Campus. Results in the report come from test runs, not from the tool's claims.
- *What if the server goes down?* Daily backups; the app also runs locally from the README in minutes, and a Vercel plus Neon configuration is ready.
