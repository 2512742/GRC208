# GRC208 Capstone Brief (transcribed)

Transcribed from the E-Campus assignment page (campus.icdfa.edu.ng, assignment id 119) and the screenshots in `GRC208 Capstone Project.docx`. This is the source of truth for requirements; `PLAN.md` maps every item to features, tests and owners.

**GRC208 · Capstone Project · Governed Evidence Submission · Semester 2.** Submission type: mixed. Group 1: individual submissions, shared group grade.

**Cyber Risk Register and Treatment Management Platform**

**Overview.** Design and build a working web application that helps an organisation identify, assess, prioritise and manage cybersecurity risks. The organisation currently uses separate spreadsheets to record risks. Risk owners miss treatment deadlines, assessments use inconsistent scoring, and management cannot clearly identify risks that exceed its approved risk appetite. The solution must address these problems through a central risk management platform.

**Objective.** Develop a platform that connects business services, assets, cyber risks, treatment actions, supporting evidence and approval decisions. It must support practical GRC decision-making and provide traceable records for management and audit review.

**Required features**
1. **Asset and risk register.** Record assets, business services, risk descriptions, threats, vulnerabilities, business impacts, responsible owners and review dates. Link each risk to the relevant assets.
2. **Risk assessment and scoring.** Implement defined likelihood and impact scales from 1 to 5. Calculate the risk score as likelihood × impact. Document the rating bands and risk appetite thresholds, and show users how each score was calculated.
3. **Risk treatment management.** Support decisions to reduce, accept, transfer or avoid a risk. Create treatment actions with responsible owners, deadlines, status, estimated cost and supporting evidence.
4. **Residual risk assessment.** Keep the original assessment and subsequent reassessments. Completing a treatment action must not automatically reduce the risk score. Require a documented reassessment supported by evidence.
5. **Approval and exceptions.** Require an authorised reviewer to approve risk acceptance. Record the justification, decision date and expiry date. A risk owner must not approve their own acceptance request.
6. **Dashboard and reporting.** Display a risk heat map, risks above appetite, overdue treatment actions and upcoming reviews. Support filtering and export of a management risk report.
7. **Access control and audit history.** Provide separate permissions for risk analysts, risk owners, approvers and read-only auditors. Record who created, changed, reviewed or approved important records, and when.
8. **Data import.** Provide a CSV import template for assets or risks. Validate imported information, explain rejected rows and prevent unintended duplicates.

**Minimum demonstration data (fictional):** at least 15 assets across three business services; at least 20 cybersecurity risks; at least 12 treatment actions; one overdue treatment action; one expired risk acceptance; one completed treatment awaiting reassessment; and risks that exceed the organisation's defined appetite.

**Required demonstration**
- Create a risk with likelihood 4 and impact 5, producing a score of 20.
- Assign a treatment action and upload supporting evidence.
- Complete the action without the risk score changing automatically.
- Perform and record a justified residual risk reassessment.
- Submit a risk acceptance request and have a different authorised user approve it.
- Show overdue actions, the expired acceptance and the updated management report.
- Show that an unauthorised user cannot approve or modify protected records.

**Expected deliverables**
1. A working application with persistent database storage.
2. Source code and clear installation instructions, including database setup and demonstration accounts.
3. A documented scoring methodology, risk appetite thresholds and approval workflow.
4. Test cases showing expected results, actual results and corrections made.
5. A sample management risk report.
6. A contribution record showing each group member's responsibilities and completed work.

**E-Campus submission requirements**
- **Abstract:** problem, proposed solution, implementation approach and main results in about 200 to 300 words.
- **Project documentation:** a PDF covering requirements, architecture, database design, workflows, screenshots, security controls, testing, limitations and deployment instructions, with an accessible source-code link.
- **Demonstration video:** a link to an 8 to 12 minute walkthrough of the working application. Do not upload the video file to the portal.
- **Presentation slides:** about 10 to 12 slides covering the problem, solution, implementation, testing and business value.
- Save the required items and complete final submission through E-Campus.

**Defence preparation.** Be prepared to explain the scoring assumptions, approval controls, treatment decisions and the evidence supporting residual risk assessments. Each member should understand the overall application and be able to explain their own contribution.

**Supervisor:** Directorate of Training (abubakar.salisu@icdfa.edu.ng). **Defence assessors:** Aminu Idris, Dr. Sarah James, Lilly Adjei. Presentation date and Microsoft Teams session: to be confirmed on E-Campus.

**Portal facts:** one attempt; due and final close 15 Dec 2026, 11:59 PM WAT; final submission charges NGN 1,000 from each member's wallet (drafts are free); a non-submitter stays "not submitted" even after the group is graded. Field-by-field map: `docs/submission-guide.md`.
