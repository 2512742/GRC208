# Organisation profile, appetite statement and governance roles

## 1. Organisation profile
The Alajo is a fictional Lagos based digital savings and investment platform, founded in 2021. Customers save automatically, lock funds toward goals, and invest in mutual funds and treasury bills through a mobile app and website. The platform is cloud hosted, and partner banks hold customer funds.

Registered customers: 650,000
Monthly active customers: 180,000
Customer funds under management: ₦85 billion
Annual revenue: ₦6 billion
Capital reserves: ₦3 billion
Staff: 140
Growth goal: 1 million customers within two years

Regulatory context: NDPA 2023 (personal data), SEC Nigeria (investment products), CBN requirements through partner banks and payment providers, and PCI DSS (card payments).

Scope: three business services and 18 assets. Market risk, credit risk and physical premises risk are out of scope, because they are not cyber risks.

Savings and Wallets (owner Emmanuel Teye Adjei, Head of Engineering): mobile app, web app, wallet ledger, savings engine, payment gateway integration, customer database.
Investments (owner Anita Ojimba): investment platform, portfolio management system, fund manager API, market pricing feed, investment admin portal, reporting database.
Customer Onboarding and Support (owner Gilbert Obichere): KYC and BVN verification service, onboarding portal, customer support platform, identity document storage, email and SMS notification service, fraud monitoring tool.

Business objectives: protect customer funds and personal data, keep the platform available for deposits, withdrawals and investments, stay compliant with Nigerian regulators and card standards, grow to 1 million customers, and launch new products quickly and safely.

Current weakness: risks are held in separate spreadsheets, scoring is inconsistent, deadlines are missed, and management cannot see risks above appetite. RiskTrack addresses this.

## 2. Risk appetite statement
The Alajo has a low appetite for loss of customer funds, exposure of customer data and regulatory breach. Any risk scoring 10 or more (likelihood times impact, each rated 1 to 5) is above appetite and must be treated or formally accepted by an authorised approver, with a justification and an expiry date. Risks scoring below 10 may be managed by the risk owner within the review cycle for their band.

## 3. Governance roles
Board and management: receive the dashboard and management report and set the appetite.
GRC analyst (Omotayo Akinola): runs the register, creates and assesses risks, performs reassessments with evidence, and imports data.
Risk owners (Emmanuel Teye Adjei, Anita Ojimba, Gilbert Obichere): own the risks and treatment actions for their service and complete actions with evidence.
Approvers (CISO Adeola Bamigboye and CRO Kelechi Kenneth Nwankwo): decide risk acceptances. An approver never decides on a risk they own or a request they made. When the CISO owns the risk, the CRO decides.
Internal auditor (Ernestina Lamiorkor Tawiah): read only access to all records and the audit log, and can verify the log's integrity.
System administrator: manages users and settings.
