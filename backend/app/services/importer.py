"""CSV import for assets and risks (brief feature 8; tests T24-T26).

Two steps, so nothing is written by surprise:
1. preview: normalise headers, validate every row (same row models as `seed-demo`), resolve
   references, detect duplicates against the database *and* within the file, and store a
   row-by-row result with plain-language reasons. The uploaded file is kept as evidence.
2. commit: re-check each valid row (the database may have changed since the preview) and create
   it through the same register functions as the API. Rejected rows are never written.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from pydantic import ValidationError
from sqlmodel import Session, func, select

from app.models import Asset, BusinessService, ImportBatch, Obligation, Risk, User
from app.models.enums import AssessmentType, AuditAction, EvidenceTarget, ImportStatus, ImportType
from app.schemas.rows import AssetRow, RiskRow
from app.services import audit
from app.services import register as reg
from app.services import treatment as tr
from app.services.clock import now_utc
from app.services.evidence import CheckedFile

MAX_ROWS = 1000
VALID, REJECTED, DUPLICATE = "valid", "rejected", "duplicate"

TEMPLATES: dict[ImportType, tuple[list[str], list[str]]] = {
    ImportType.ASSETS: (
        [
            "asset_code",
            "name",
            "asset_type",
            "service_code",
            "owner_username",
            "classification",
            "obligations",
            "description",
        ],
        [
            "",
            "Loyalty points engine",
            "application",
            "S1",
            "emmanuel",
            "confidential",
            "NDPA-02",
            "Leave asset_code empty to have one assigned",
        ],
    ),
    ImportType.RISKS: (
        [
            "risk_code",
            "title",
            "asset_codes",
            "owner_username",
            "likelihood",
            "impact",
            "category",
            "obligations",
            "threat",
            "vulnerability",
            "business_impact",
            "rationale",
            "description",
        ],
        [
            "",
            "Loyalty points fraud through API abuse",
            "A-001;A-004",
            "emmanuel",
            "3",
            "3",
            "fraud",
            "NDPA-02",
            "Bots farming referral points",
            "No rate limits on referral API",
            "Financial loss and customer complaints",
            "Seen in two peer fintechs this year; our API has the same gap.",
            "",
        ],
    ),
}
MODELS: dict[ImportType, type[AssetRow] | type[RiskRow]] = {
    ImportType.ASSETS: AssetRow,
    ImportType.RISKS: RiskRow,
}


class ImportFileError(ValueError):
    """The file as a whole can't be read (wrong columns, empty, too many rows)."""


def template_csv(kind: ImportType) -> str:
    header, example = TEMPLATES[kind]
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(header)
    writer.writerow(example)
    return out.getvalue()


def _normalise_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def parse_csv(kind: ImportType, content: bytes) -> list[dict[str, str]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ImportFileError("The file is empty: the first row must contain the column names.")
    headers = [_normalise_header(h) for h in reader.fieldnames]
    allowed = TEMPLATES[kind][0]
    unknown = [h for h in headers if h and h not in allowed]
    if unknown:
        raise ImportFileError(
            f"Unknown column(s): {', '.join(unknown)}. Expected: "
            f"{', '.join(allowed)}. Download the template to compare."
        )
    model = MODELS[kind]
    required = [name for name, f in model.model_fields.items() if f.is_required()]
    missing = [r for r in required if r not in headers]
    if missing:
        raise ImportFileError(f"Missing required column(s): {', '.join(missing)}.")
    rows = []
    for raw in reader:
        row = {_normalise_header(k): (v or "") for k, v in raw.items() if k is not None}
        if any(value.strip() for value in row.values()):
            rows.append(row)
    if not rows:
        raise ImportFileError("The file has column names but no data rows.")
    if len(rows) > MAX_ROWS:
        raise ImportFileError(f"The file has {len(rows)} rows; the limit is {MAX_ROWS} per import.")
    return rows


def _pydantic_reasons(exc: ValidationError) -> list[str]:
    reasons = []
    for error in exc.errors():
        field = ".".join(str(p) for p in error["loc"]) or "row"
        message = error["msg"].removeprefix("Value error, ")
        blank = error.get("input") in ("", None)
        if error["type"] == "missing" or (blank and error["type"] == "string_too_short"):
            message = "is required"
        reasons.append(f"{field}: {message}")
    return reasons


# ── Row checks ─────────────────────────────────────────────────────────────────────────────


class _Lookups:
    """Reference data loaded once per import."""

    def __init__(self, session: Session) -> None:
        self.services = {s.code.upper(): s.id for s in session.exec(select(BusinessService))}
        self.users = {u.username: u for u in session.exec(select(User))}
        self.obligations = dict(session.exec(select(Obligation.reference, Obligation.id)).all())
        self.assets = dict(session.exec(select(Asset.asset_code, Asset.id)).all())
        self.asset_keys = {
            (n.lower(), sid) for n, sid in session.exec(select(Asset.name, Asset.service_id))
        }
        self.risk_codes = set(session.exec(select(Risk.risk_code)))
        self.risk_titles = {t.lower() for t in session.exec(select(Risk.title))}


def _check_asset(
    row: AssetRow, look: _Lookups, seen: set[Any]
) -> tuple[str, list[str], dict[str, Any]]:
    reasons: list[str] = []
    service_id = look.services.get(row.service_code.upper())
    if service_id is None:
        reasons.append(f"service_code: no business service '{row.service_code}'")
    owner_id = None
    if row.owner_username:
        owner = look.users.get(row.owner_username.lower())
        if owner is None or not owner.is_active:
            reasons.append(f"owner_username: no active user '{row.owner_username}'")
        else:
            owner_id = owner.id
    unknown = [o for o in row.obligations if o not in look.obligations]
    if unknown:
        reasons.append(f"obligations: unknown reference(s) {', '.join(unknown)}")
    if reasons:
        return REJECTED, reasons, {}

    key = (row.name.lower(), service_id)
    if row.asset_code and row.asset_code in look.assets:
        return DUPLICATE, [f"asset_code {row.asset_code} already exists"], {}
    if key in look.asset_keys:
        return DUPLICATE, [f"an asset named '{row.name}' already exists in {row.service_code}"], {}
    if key in seen or (row.asset_code and row.asset_code in seen):
        return DUPLICATE, ["repeats an earlier row in this file"], {}
    seen.add(key)
    if row.asset_code:
        seen.add(row.asset_code)
    data = {
        "asset_code": row.asset_code,
        "name": row.name,
        "asset_type": row.asset_type.value,
        "service_id": service_id,
        "owner_id": owner_id,
        "classification": row.classification.value,
        "description": row.description,
        "obligation_ids": [look.obligations[o] for o in row.obligations],
    }
    return VALID, [], data


def _check_risk(
    row: RiskRow, look: _Lookups, seen: set[Any]
) -> tuple[str, list[str], dict[str, Any]]:
    reasons: list[str] = []
    owner = look.users.get(row.owner_username.lower())
    if owner is None or not owner.is_active:
        reasons.append(f"owner_username: no active user '{row.owner_username}'")
    elif owner.role not in reg.OWNER_ROLES:
        reasons.append(f"owner_username: '{row.owner_username}' is not a risk owner or approver")
    missing_assets = [c for c in row.asset_codes if c not in look.assets]
    if missing_assets:
        reasons.append(f"asset_codes: unknown asset(s) {', '.join(missing_assets)}")
    unknown = [o for o in row.obligations if o not in look.obligations]
    if unknown:
        reasons.append(f"obligations: unknown reference(s) {', '.join(unknown)}")
    if reasons:
        return REJECTED, reasons, {}

    title_key = row.title.lower()
    if row.risk_code and row.risk_code in look.risk_codes:
        return DUPLICATE, [f"risk_code {row.risk_code} already exists"], {}
    if title_key in look.risk_titles:
        return DUPLICATE, [f"a risk titled '{row.title}' already exists"], {}
    if title_key in seen or (row.risk_code and row.risk_code in seen):
        return DUPLICATE, ["repeats an earlier row in this file"], {}
    seen.add(title_key)
    if row.risk_code:
        seen.add(row.risk_code)
    data = {
        "risk_code": row.risk_code,
        "title": row.title,
        "description": row.description or row.title,
        "threat": row.threat,
        "vulnerability": row.vulnerability,
        "business_impact": row.business_impact,
        "category": row.category,
        "owner_id": owner.id,  # type: ignore[union-attr]
        "asset_ids": [look.assets[c] for c in row.asset_codes],
        "obligation_ids": [look.obligations[o] for o in row.obligations],
        "likelihood": row.likelihood,
        "impact": row.impact,
        "rationale": row.rationale,
    }
    return VALID, [], data


def check_rows(
    session: Session, kind: ImportType, raw_rows: list[dict[str, str]]
) -> list[dict[str, Any]]:
    look = _Lookups(session)
    seen: set[Any] = set()
    model = MODELS[kind]
    results = []
    for number, raw in enumerate(raw_rows, start=2):  # row 1 is the header
        try:
            parsed = model.model_validate(raw)
        except ValidationError as exc:
            results.append(
                {
                    "row": number,
                    "status": REJECTED,
                    "reasons": _pydantic_reasons(exc),
                    "values": raw,
                    "data": None,
                }
            )
            continue
        checker = _check_asset if kind == ImportType.ASSETS else _check_risk
        status, reasons, data = checker(parsed, look, seen)  # type: ignore[arg-type]
        results.append(
            {
                "row": number,
                "status": status,
                "reasons": reasons,
                "values": raw,
                "data": data or None,
            }
        )
    return results


def _count(batch: ImportBatch, results: list[dict[str, Any]]) -> None:
    batch.total_rows = len(results)
    batch.valid_rows = sum(1 for r in results if r["status"] == VALID)
    batch.rejected_rows = sum(1 for r in results if r["status"] == REJECTED)
    batch.duplicate_rows = sum(1 for r in results if r["status"] == DUPLICATE)


def has_scores(results: list[dict[str, Any]]) -> bool:
    return any(r["data"] and r["data"].get("likelihood") for r in results)


# ── Preview and commit ─────────────────────────────────────────────────────────────────────


def preview(
    session: Session, by: audit.AuditActor, kind: ImportType, checked: CheckedFile, content: bytes
) -> ImportBatch:
    raw_rows = parse_csv(kind, content)
    results = check_rows(session, kind, raw_rows)
    batch = ImportBatch(
        import_type=kind.value,
        uploaded_by_id=by.user_id,  # type: ignore[arg-type]
        row_results=results,
    )
    _count(batch, results)
    session.add(batch)
    session.flush()
    evidence = tr.store_evidence(
        session,
        by,
        EvidenceTarget.IMPORT_BATCH,
        batch.id,
        checked,  # type: ignore[arg-type]
        content,
        description=f"Uploaded {kind.value} import file",
    )
    batch.evidence_id = evidence.id
    session.add(batch)
    audit.record(
        session,
        AuditAction.IMPORT,
        by,
        object_type="import_batch",
        object_id=batch.id,
        after={
            "type": kind.value,
            "status": "previewed",
            "total": batch.total_rows,
            "valid": batch.valid_rows,
            "rejected": batch.rejected_rows,
            "duplicates": batch.duplicate_rows,
        },
        detail=checked.original_name,
    )
    return batch


def commit(session: Session, by: audit.AuditActor, batch: ImportBatch) -> ImportBatch:
    if batch.status != ImportStatus.PREVIEWED.value:
        raise tr.TreatmentError(f"This import is already {batch.status}.", 409)
    kind = ImportType(batch.import_type)
    # Re-check against the database as it is now, using the original cells.
    results = check_rows(session, kind, [r["values"] for r in batch.row_results or []])
    for result in results:
        if result["status"] != VALID:
            continue
        data = dict(result["data"])
        savepoint = session.begin_nested()
        try:
            if kind == ImportType.ASSETS:
                obligation_ids = data.pop("obligation_ids")
                created = reg.create_asset(session, by, obligation_ids, **data)
                result["created"] = created.asset_code
            else:
                scores = {k: data.pop(k) for k in ("likelihood", "impact", "rationale")}
                risk = reg.create_risk(session, by, **data)
                if scores["likelihood"] is not None:
                    reg.record_assessment(
                        session,
                        by,
                        risk,
                        likelihood=scores["likelihood"],
                        impact=scores["impact"],
                        rationale=scores["rationale"],
                        assessment_type=AssessmentType.INITIAL,
                    )
                result["created"] = risk.risk_code
            savepoint.commit()
        except reg.RegisterError as exc:
            savepoint.rollback()
            result["status"] = DUPLICATE if exc.status == 409 else REJECTED
            result["reasons"] = [str(exc)]
    batch.row_results = results
    _count(batch, results)
    batch.status = ImportStatus.COMMITTED.value
    batch.committed_at = now_utc()
    session.add(batch)
    audit.record(
        session,
        AuditAction.IMPORT,
        by,
        object_type="import_batch",
        object_id=batch.id,
        after={
            "type": kind.value,
            "status": "committed",
            "created": batch.valid_rows,
            "rejected": batch.rejected_rows,
            "duplicates": batch.duplicate_rows,
        },
    )
    return batch


def cancel(session: Session, by: audit.AuditActor, batch: ImportBatch) -> ImportBatch:
    if batch.status != ImportStatus.PREVIEWED.value:
        raise tr.TreatmentError(f"This import is already {batch.status}.", 409)
    batch.status = ImportStatus.CANCELLED.value
    session.add(batch)
    audit.record(
        session,
        AuditAction.IMPORT,
        by,
        object_type="import_batch",
        object_id=batch.id,
        after={"status": "cancelled"},
    )
    return batch


def batches(session: Session) -> list[ImportBatch]:
    return list(session.exec(select(ImportBatch).order_by(func.coalesce(ImportBatch.id, 0).desc())))
