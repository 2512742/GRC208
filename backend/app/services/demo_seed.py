"""`seed-demo` v1 (P4): The Alajo's people, services, 18 assets and 22 scored risks.

Data comes from `app/sample_data/alajo_assets.csv` and `alajo_risks.csv` (owned and refined by
WS2), validated by the same row models as the CSV import. Records are created through the same
register functions as the API, so every rule and audit entry applies.

All dates are relative to the day the seed runs (PLAN.md §4): initial assessments are recorded
45 days ago, so review dates and (in P5) overdue actions still hold on demo day.
v2 (P5) adds treatment decisions, actions, evidence placeholders and acceptances.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from pydantic import ValidationError
from sqlmodel import Session, func, select

from app.core.config import REPO_DIR
from app.models import Asset, BusinessService, Obligation, Risk, User
from app.models.enums import AssessmentType, Role
from app.schemas.rows import AssetRow, RiskRow
from app.services import audit, clock
from app.services import register as reg
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
    report = SeedReport()
    report.reference_added = load_reference_data(session).added

    start = clock.now_utc() - timedelta(days=BACKDATE_DAYS)
    with clock.frozen(start):
        users = _people(session, password, report)
        analyst = users["omotayo"]
        by = audit.AuditActor(analyst.id, analyst.username, analyst.role, ip=None)
        services = _services(session, users, by, report)
        assets = _assets(session, asset_rows, users, services, by, report)
        _risks(session, risk_rows, users, assets, by, report)
    session.flush()
    return report


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
) -> None:
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
