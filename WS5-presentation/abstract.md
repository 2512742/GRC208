# Abstract (shared, about 200 to 300 words)

Owner: Deborah Orimikoya with the workstream leads. Write it **last**, from real results only.
The same text goes into the PDF (Abstract section) and into each member's E-Campus abstract field.

Cover, in this order: the problem (spreadsheet registers, missed deadlines, inconsistent scoring, appetite blind spot), the proposed solution, the implementation approach (stack and key controls), and the main results (tests passed, demonstration steps achieved).

## Final text

*Draft v0.1 (19 Nov 2026), written from observed results only. WS6 and the workstream leads review it; freeze with the report on 12 Dec.*

Organisations that manage cyber risk in separate spreadsheets struggle with missed treatment deadlines, inconsistent scoring and no clear view of risks that exceed the approved appetite. Group 1 built RiskTrack, a web-based cyber risk register and treatment management platform, for The Alajo, a fictional Lagos savings and investment company subject to the Nigeria Data Protection Act 2023, Central Bank of Nigeria cybersecurity requirements, SEC Nigeria rules and PCI DSS.

RiskTrack connects business services, assets, risks, treatment actions, evidence and approval decisions in one database. Risks are scored as likelihood times impact on 1 to 5 scales, placed in documented bands, and flagged when the score reaches the appetite threshold of 10, with the calculation shown to the user. Completing a treatment action never lowers a score: only a reassessment backed by evidence does, and the original assessment is kept. Risk acceptance requires an independent approver, a justification and an expiry date, and the server blocks self-approval. A dashboard shows the heat map, risks above appetite, overdue actions and upcoming reviews, and management reports export to PDF and CSV. Separate roles for analysts, owners, approvers, auditors and administrators are enforced on the server, and every important change is recorded in a tamper-evident, hash-chained audit log. CSV import explains each rejected row and prevents duplicates.

The application uses FastAPI, SQLite or PostgreSQL, and a React interface that also installs as a phone app. It is hosted with HTTPS at thealajo.tinex.tech. All 32 planned test cases pass, within 467 automated tests run on both databases, and every step of the brief's required demonstration works in the hosted application.

Word count: 265
