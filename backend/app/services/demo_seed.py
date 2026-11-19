"""`seed-demo` v1 (P4): The Alajo's people, services, 18 assets and 22 scored risks.

Data comes from `app/sample_data/alajo_assets.csv` and `alajo_risks.csv` (owned and refined by
WS2), validated by the same row models as the CSV import. Records are created through the same
register functions as the API, so every rule and audit entry applies.

All dates are relative to the day the seed runs (PLAN.md §4): initial assessments are recorded
45 days ago, so review dates and (in P5) overdue actions still hold on demo day.
v2 (P5) adds treatment decisions, 18 actions (one overdue, one completed awaiting
reassessment, one completed and reassessed), placeholder evidence PDFs, and acceptances
(valid, expired, and two pending, one of them on the CISO's own risk).
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from pydantic import ValidationError
from sqlmodel import Session, func, select

from app.core.config import REPO_DIR
from app.models import Asset, BusinessService, Control, Obligation, Risk, TreatmentAction, User
from app.models.enums import AssessmentType, Role
from app.schemas.rows import AssetRow, DecisionRow, RiskRow, TreatmentRow
from app.services import audit, clock, governance
from app.services import register as reg
from app.services import treatment as tr
from app.services.evidence import CheckedFile, check_evidence
from app.services.reference_data import load_reference_data
from app.services.users import create_user

SAMPLE_DIR = REPO_DIR / "sample_data"
BACKDATE_DAYS = 45

# PLAN.md §4.3: fictional personas played by group members in the demo.
PEOPLE = [
    ("admin", "System Administrator", Role.ADMIN, "System Administrator", "IT"),
    ("omotayo", "Omotayo Akinola", Role.ANALYST, "GRC Analyst", "Risk and Compliance"),
    ("emmanuel", "Emmanuel Teye Adjei", Role.OWNER, "Head of Engineering", "Engineering"),
    ("anita", "Anita Ojimba", Role.OWNER, "Head of Investment Operations", "Investments"),
    ("gilbert", "Gilbert Obichere", Role.OWNER, "Head of Customer Support", "Customer Operations"),
    (
        "adeola",
        "Adeola Bamigboye",
        Role.APPROVER,
        "Chief Information Security Officer",
        "Information Security",
    ),
    ("kelechi", "Kelechi Kenneth Nwankwo", Role.APPROVER, "Chief Risk Officer", "Risk"),
    ("ernestina", "Ernestina Lamiorkor Tawiah", Role.AUDITOR, "Internal Auditor", "Internal Audit"),
]

SERVICES = [
    (
        "S1",
        "Savings and Wallets",
        "emmanuel",
        5,
        "Daily and periodic thrift savings, goal-locked vaults and customer wallets",
    ),
    ("S2", "Investments", "anita", 4, "Mutual funds and treasury bills through fund managers"),
    (
        "S3",
        "Customer Onboarding and Support",
        "gilbert",
        4,
        "Identity verification, onboarding, support and customer notifications",
    ),
]


class SeedError(RuntimeError):
    """The seed can't run (e.g. data already present) or a sample row is invalid."""


@dataclass
class SeedReport:
    users: int = 0
    services: int = 0
    assets: int = 0
    risks: int = 0
    assessed: int = 0
    above_appetite: int = 0
    reference_added: int = 0
    decisions: int = 0
    actions: int = 0
    completed: int = 0
    reassessed: int = 0
    acceptances: int = 0
    evidence: int = 0
    problems: list[str] = field(default_factory=list)


def read_rows(path: Path, model: type[AssetRow] | type[RiskRow]) -> list:  # type: ignore[type-arg]
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    parsed, problems = [], []
    for number, raw in enumerate(rows, start=2):  # row 1 is the header
        try:
            parsed.append(model.model_validate(raw))
        except ValidationError as exc:
            reasons = "; ".join(
                f"{'.'.join(map(str, e['loc'])) or 'row'}: {e['msg']}" for e in exc.errors()
            )
            problems.append(f"{path.name} row {number}: {reasons}")
    if problems:
        raise SeedError("Invalid sample data:\n" + "\n".join(problems))
    return parsed


def seed_demo(session: Session, password: str, sample_dir: Path = SAMPLE_DIR) -> SeedReport:
    if session.exec(select(func.count()).select_from(Risk)).one():
        raise SeedError("The database already has risks. Use --reset to start from scratch.")
    asset_rows: list[AssetRow] = read_rows(sample_dir / "alajo_assets.csv", AssetRow)
    risk_rows: list[RiskRow] = read_rows(sample_dir / "alajo_risks.csv", RiskRow)
    decision_rows: list[DecisionRow] = read_rows(sample_dir / "alajo_decisions.csv", DecisionRow)
    action_rows: list[TreatmentRow] = read_rows(sample_dir / "alajo_treatments.csv", TreatmentRow)
    report = SeedReport()
    report.reference_added = load_reference_data(session).added

    now = clock.now_utc()
    demo_day = governance.org_today(session)  # due and expiry dates are relative to today

    def at(days_ago: int) -> AbstractContextManager[None]:
        return clock.frozen(now - timedelta(days=days_ago))

    with at(BACKDATE_DAYS):
        users = _people(session, password, report)
        by = actor(users["omotayo"])
        services = _services(session, users, by, report)
        assets = _assets(session, asset_rows, users, services, by, report)
        risks = _risks(session, risk_rows, users, assets, by, report)
    with at(44):
        _decisions(session, decision_rows, risks, by, report)
    _treatment_story(session, at, demo_day, action_rows, users, risks, report)
    session.flush()
    return report


def actor(user: User) -> audit.AuditActor:
    return audit.AuditActor(user.id, user.username, user.role, ip=None)


def placeholder_pdf(title: str, lines: list[str]) -> bytes:
    """A small, genuine PDF clearly marked as fictional demo evidence."""
    from fpdf import FPDF

    doc = FPDF()
    doc.set_title(title)
    doc.add_page()
    doc.set_font("Helvetica", "B", 13)
    doc.multi_cell(
        0, 8, "FICTIONAL DEMO EVIDENCE - The Alajo (GRC208 capstone)", new_x="LMARGIN", new_y="NEXT"
    )
    doc.set_font("Helvetica", size=11)
    for line in [title, *lines]:
        doc.multi_cell(0, 7, line, new_x="LMARGIN", new_y="NEXT")
    return bytes(doc.output())


def _evidence(title: str, lines: list[str]) -> tuple[CheckedFile, bytes]:
    content = placeholder_pdf(title, lines)
    return check_evidence(title.lower().replace(" ", "-") + ".pdf", content), content


def _decisions(
    session: Session,
    rows: list[DecisionRow],
    risks: dict[str, Risk],
    by: audit.AuditActor,
    report: SeedReport,
) -> None:
    for row in rows:
        if row.risk_code not in risks:
            raise SeedError(f"decision: unknown risk {row.risk_code}")
        tr.decide_treatment(
            session,
            by,
            risks[row.risk_code],
            strategy=row.strategy,
            justification=row.justification,
            target_likelihood=row.target_likelihood,
            target_impact=row.target_impact,
        )
        report.decisions += 1


def _treatment_story(
    session: Session,
    at: Callable[[int], AbstractContextManager[None]],
    demo_day: date,
    rows: list[TreatmentRow],
    users: dict[str, User],
    risks: dict[str, Risk],
    report: SeedReport,
) -> None:
    """Acceptances and actions in date order, so the audit log reads chronologically."""
    controls = {c.control_ref: c.id for c in session.exec(select(Control))}
    for code in ("R-002", "R-010", "R-013", "R-014", "R-015", "R-022"):
        if code not in risks:
            raise SeedError(f"the demo story needs risk {code} in alajo_risks.csv")

    # R-014: accepted 43 days ago, expired 14 days ago (brief: an expired acceptance).
    with at(44):
        expired = tr.request_acceptance(
            session,
            actor(users["anita"]),
            risks["R-014"],
            justification="T+1 reconciliation keeps customers whole while the fund manager "
            "improves availability.",
            proposed_expiry=demo_day - timedelta(days=14),
        )
    with at(43):
        tr.decide_acceptance(
            session,
            actor(users["kelechi"]),
            expired,
            approve=True,
            comment="Accepted for one month pending the vendor's fix.",
        )
    report.acceptances += 1

    actions: dict[str, TreatmentAction] = {}
    with at(40):
        for row in rows:
            where = f"action {row.action_code}"
            if row.risk_code not in risks:
                raise SeedError(f"{where}: unknown risk {row.risk_code}")
            missing = [c for c in row.controls if c not in controls]
            if missing:
                raise SeedError(f"{where}: unknown control(s) {', '.join(missing)}")
            actions[row.action_code] = tr.create_action(
                session,
                actor(users["omotayo"]),
                risks[row.risk_code],
                action_code=row.action_code,
                title=row.title,
                owner_id=_user_id(users, row.owner_username, where),  # type: ignore[arg-type]
                due_date=demo_day + timedelta(days=row.due_in_days),
                estimated_cost_ngn=row.estimated_cost_ngn,
                control_ids=[controls[c] for c in row.controls],
            )
            report.actions += 1

    # R-010: valid acceptance, decided by the CISO (the risk owner is Gilbert).
    with at(39):
        valid = tr.request_acceptance(
            session,
            actor(users["gilbert"]),
            risks["R-010"],
            justification="A second SMS aggregator costs more than the expected loss; OTP "
            "failures are rare and retried automatically.",
            proposed_expiry=demo_day + timedelta(days=150),
        )
    with at(38):
        tr.decide_acceptance(
            session,
            actor(users["adeola"]),
            valid,
            approve=True,
            comment="Accepted until the authenticator-app rollout next year.",
        )
    report.acceptances += 1

    with at(30):
        for row in rows:
            if row.status in ("in_progress", "completed"):
                action = actions[row.action_code]
                owner = session.get(User, action.owner_id)
                tr.update_action(session, actor(owner), action, {"status": "in_progress"})  # type: ignore[arg-type]

    def complete(code: str, days_ago: int) -> None:
        row = next(r for r in rows if r.action_code == code)
        action = actions[code]
        with at(days_ago):
            checked, content = _evidence(
                f"{code} completion evidence",
                [f"Action: {action.title}", f"Note: {row.completion_note}"],
            )
            tr.complete_action(
                session,
                actor(session.get(User, action.owner_id)),
                action,  # type: ignore[arg-type]
                note=row.completion_note or "",
                evidence=checked,
                content=content,
            )
        report.completed += 1
        report.evidence += 1

    # R-013: action completed, then reassessed with evidence (original 12, residual 4).
    if "T-011" in actions:
        complete("T-011", 6)
        with at(3):
            checked, content = _evidence(
                "R-013 reassessment evidence",
                [
                    "Two weeks of WAF logs: credential-stuffing bursts blocked at the edge.",
                    "BVN lookup volume back to the normal baseline.",
                ],
            )
            tr.reassess(
                session,
                actor(users["omotayo"]),
                risks["R-013"],
                likelihood=1,
                impact=4,
                rationale="Rate limiting and bot rules verified in two weeks "
                "of WAF logs; abuse attempts now blocked.",
                evidence=checked,
                content=content,
            )
        report.reassessed += 1
        report.evidence += 1

    # R-002: completed two days ago, awaiting reassessment (score still 20).
    if "T-002" in actions:
        complete("T-002", 2)

    # Pending: the CISO's own risk (only the CRO may decide) and one for the live demo.
    with at(2):
        tr.request_acceptance(
            session,
            actor(users["adeola"]),
            risks["R-015"],
            justification="Database access is limited to two named administrators with full "
            "query logging; PAM rollout is budgeted for next year.",
            proposed_expiry=demo_day + timedelta(days=180),
        )
    with at(1):
        tr.request_acceptance(
            session,
            actor(users["anita"]),
            risks["R-022"],
            justification="Stale holdings self-correct at the next sync and customers can "
            "refresh; impact is low.",
            proposed_expiry=demo_day + timedelta(days=120),
        )
    report.acceptances += 2


def _people(session: Session, password: str, report: SeedReport) -> dict[str, User]:
    existing = {u.username: u for u in session.exec(select(User))}
    users: dict[str, User] = {}
    for username, full_name, role, title, department in PEOPLE:
        if username in existing:
            users[username] = existing[username]
            continue
        users[username] = create_user(
            session,
            username=username,
            full_name=full_name,
            role=role,
            password=password,
            job_title=title,
            department=department,
        )
        report.users += 1
    return users


def _services(
    session: Session, users: dict[str, User], by: audit.AuditActor, report: SeedReport
) -> dict[str, BusinessService]:
    services = {}
    for code, name, owner, criticality, description in SERVICES:
        services[code] = reg.create_service(
            session,
            by,
            code=code,
            name=name,
            owner_id=users[owner].id,
            criticality=criticality,
            description=description,
        )
        report.services += 1
    return services


def _obligation_ids(session: Session, refs: list[str], where: str) -> list[int]:
    found = dict(session.exec(select(Obligation.reference, Obligation.id)).all())
    missing = [r for r in refs if r not in found]
    if missing:
        raise SeedError(f"{where}: unknown obligation reference(s) {', '.join(missing)}")
    return [found[r] for r in refs]


def _user_id(users: dict[str, User], username: str | None, where: str) -> int | None:
    if username is None:
        return None
    if username not in users:
        raise SeedError(f"{where}: unknown username '{username}'")
    return users[username].id


def _assets(
    session: Session,
    rows: list[AssetRow],
    users: dict[str, User],
    services: dict[str, BusinessService],
    by: audit.AuditActor,
    report: SeedReport,
) -> dict[str, Asset]:
    assets = {}
    for row in rows:
        where = f"asset {row.asset_code or row.name}"
        if row.service_code not in services:
            raise SeedError(f"{where}: unknown service {row.service_code}")
        asset = reg.create_asset(
            session,
            by,
            _obligation_ids(session, row.obligations, where),
            asset_code=row.asset_code,
            name=row.name,
            asset_type=row.asset_type.value,
            service_id=services[row.service_code].id,
            owner_id=_user_id(users, row.owner_username, where),
            classification=row.classification.value,
            description=row.description,
        )
        assets[asset.asset_code] = asset
        report.assets += 1
    return assets


def _risks(
    session: Session,
    rows: list[RiskRow],
    users: dict[str, User],
    assets: dict[str, Asset],
    by: audit.AuditActor,
    report: SeedReport,
) -> dict[str, Risk]:
    risks: dict[str, Risk] = {}
    for row in rows:
        where = f"risk {row.risk_code or row.title}"
        missing = [c for c in row.asset_codes if c not in assets]
        if missing:
            raise SeedError(f"{where}: unknown asset code(s) {', '.join(missing)}")
        risk = reg.create_risk(
            session,
            by,
            risk_code=row.risk_code,
            asset_ids=[assets[c].id for c in row.asset_codes],  # type: ignore[misc]
            obligation_ids=_obligation_ids(session, row.obligations, where),
            title=row.title,
            description=row.description or row.title,
            threat=row.threat,
            vulnerability=row.vulnerability,
            business_impact=row.business_impact,
            category=row.category,
            owner_id=_user_id(users, row.owner_username, where),
        )
        report.risks += 1
        if row.likelihood is not None and row.impact is not None:
            _, result = reg.record_assessment(
                session,
                by,
                risk,
                likelihood=row.likelihood,
                impact=row.impact,
                rationale=row.rationale or "",
                assessment_type=AssessmentType.INITIAL,
            )
            report.assessed += 1
            report.above_appetite += int(result.above_appetite)
        risks[risk.risk_code] = risk
    return risks
