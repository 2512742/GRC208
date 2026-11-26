# Demonstration video: recording script (draft)

Owner: Farida Baberin-Yor Beacher (WS5). Target 10 minutes (the brief allows 8 to 12). Every step of the brief's required demonstration appears in order, marked **[REQUIRED]**.

## Before recording

- **Where:** record on the live site, https://thealajo.tinex.tech, so the video also shows it is hosted. Ask Ocen to reset the demo data first (`seed-demo --reset` on the server, `deploy/vps/README.md`), and again after recording.
- **Password:** the shared demo password (sent privately). It must never appear on screen: type it with the field hidden, and never open the file or message it came in.
- **Screen:** 1080p, browser zoom 110 to 125%, light theme (dark theme shown once), one browser window, notifications off. Use a private window per persona, or sign out between them.
- **Speakers:** each speaker says their name and role when they start. Keep each line short; the screen carries the detail.

## Script

| Time | Speaker | Signed in as | On screen | Say (about) |
|---|---|---|---|---|
| 0:00 to 0:45 | Deborah or Daniella | (sign-in page) | Sign-in page, then the slide 1 title | "We are GRC208 Group 1. RiskTrack replaces The Alajo's separate risk spreadsheets with one governed register. The Alajo is a fictional Lagos savings and investment company." Name the speakers. |
| 0:45 to 1:45 | Emmanuel | `omotayo` (analyst) | Dashboard: tiles, heat map, click the cell L1 × I4 (R-013), switch Residual (current) to Inherent, above-appetite list, overdue panel, acceptances, reviews due. Toggle dark theme once and back. | "Management sees 14 risks above appetite, one overdue action and one expired acceptance at a glance. The heat map shows where R-013 started and where it is now." |
| 1:45 to 3:00 | Omotayo | `omotayo` | Risk register → New risk. Title "Insider abuse of the wallet adjustment tool", owner Emmanuel, threat, vulnerability, impact, description, asset A-003 Wallet ledger. Likelihood **4**, impact **5**; point at the live preview; rationale; Create risk. **[REQUIRED: create a risk with L4 × I5 = 20]** | "The score is calculated, never typed: 4 times 5 is 20, Critical, above our appetite of 10, so it must be fixed within 30 days. The explanation is stored with the assessment." |
| 3:00 to 4:15 | Ocen | `emmanuel` (risk owner) | On the new risk: Treatment tab → Record decision (Reduce, target 2 × 4). Add action (title, owner, cost in ₦, a control). Complete with evidence: note plus a PDF. Show the risk: **still 20**, "Awaiting reassessment". **[REQUIRED: assign an action, upload evidence, complete without the score changing]** | "Finishing the work does not lower the risk. The score stays at 20 until an analyst reassesses it with evidence. That is the brief's residual-risk rule." |
| 4:15 to 5:15 | Omotayo | `omotayo` | In the Awaiting reassessment notice click Reassess now: the form lists the completed action and its evidence; open View scoring rubric. Likelihood 2, impact 4, rationale, evidence file. Score box: Inherent 20, Residual 8. History: Inherent assessment 20, then Residual reassessment 1: 8 (was 20), after the completed action, each with who and when. **[REQUIRED: justified reassessment]** | "The inherent assessment is never edited. The residual score comes only from an evidenced reassessment, linked to the action it followed." |
| 5:15 to 6:45 | Ocen | `emmanuel` (owner), then `adeola` (CISO) | As `emmanuel`, on the new risk (now 8, within appetite), Acceptance tab → Request risk acceptance for the residual risk (justification of at least 30 characters, expiry date). As `adeola` open Acceptances: R-015, her own risk, is blocked with "You own this risk, so another approver must decide." She approves Emmanuel's request with a comment. Optionally show `kelechi` (CRO) deciding R-015. **[REQUIRED: acceptance approved by a different authorised user]** | "Nobody approves their own risk. When the CISO owns the risk, the decision fails over to the CRO. The server enforces this, not just the screen." |
| 6:45 to 7:45 | Emmanuel | `kelechi` | Treatment actions → Overdue (T-003, days overdue). Risk R-014: acceptance expired banner. Reports: filters, preview, download the PDF and open it. **[REQUIRED: overdue actions, the expired acceptance, the updated management report]** | "Deadlines are judged in Lagos time for everyone. The report is stamped with who generated it and when, and the export is logged." |
| 7:45 to 8:45 | Ernestina | `ernestina` (auditor) | No edit or approve buttons anywhere; open Users to show "Not available for your role". Audit log: filter by DENIED, open an entry, Verify integrity: "Chain intact". **[REQUIRED: an unauthorised user cannot approve or modify protected records]** | "As the auditor I can read everything and change nothing. The API refuses these requests too, and each refusal is in the audit log. Editing any log entry would break the hash chain." |
| 8:45 to 9:30 | Ouabo | `omotayo` | CSV import: download template, upload `assets_import_with_errors.csv`: 1 valid, 5 rejected, 3 duplicates, each with its reason. Commit the valid row. | "Every bad row is explained before anything is created, and duplicates are blocked, even when the same file is uploaded twice." |
| 9:30 to 10:15 | Ebere | (slides) | Slide 10 (tests), then slide 11 (value, limits, next steps) | "All 32 planned tests pass on SQLite and PostgreSQL; 480 automated tests in total. Limitations and next steps are in the report." Close with thanks. |

## After recording

- Trim to 8 to 12 minutes, add speaker names as captions if possible, upload to an approved host (OneDrive, SharePoint or unlisted YouTube).
- Check the link from a signed-out browser, then fill in `demo-video-link.md`.
- Ask Ocen to reset the live demo data again.
