"""CSV imports, the audit log with its integrity check, and governance settings."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlmodel import Session, col, func, select

from app.core.auth import AuthContext, ensure, get_auth, require
from app.core.permissions import Perm
from app.db import get_session
from app.models import AuditLog, Evidence, ImportBatch, User
from app.models.enums import AuditAction, Band, ImportType
from app.routers.evidence import read_upload
from app.schemas.admin import (
    AuditEntryOut,
    AuditPage,
    BandRule,
    ChainReportOut,
    ImportBatchOut,
    ImportRowResult,
    Methodology,
    ScaleLevel,
    SettingsOut,
    SettingsUpdate,
)
from app.services import audit, governance, importer
from app.services import treatment as tr
from app.services.clock import now_utc
from app.services.evidence import EvidenceRejected, check_evidence
from app.services.report import safe_cell
from app.services.scoring import BAND_LABELS, IMPACT_LABELS, LIKELIHOOD_LABELS

router = APIRouter(tags=["imports, audit and settings"])


# ── CSV import ─────────────────────────────────────────────────────────────────────────────


def _batch_out(db: Session, batch: ImportBatch) -> ImportBatchOut:
    uploader = db.get(User, batch.uploaded_by_id)
    file_name = db.exec(
        select(Evidence.original_name).where(Evidence.id == batch.evidence_id)
    ).first()
    return ImportBatchOut(
        id=batch.id,
        import_type=batch.import_type,
        status=batch.status,  # type: ignore[arg-type]
        uploaded_by=uploader.full_name if uploader else "?",
        uploaded_at=batch.uploaded_at,
        committed_at=batch.committed_at,
        file_name=file_name,
        evidence_id=batch.evidence_id,
        total_rows=batch.total_rows,
        valid_rows=batch.valid_rows,
        rejected_rows=batch.rejected_rows,
        duplicate_rows=batch.duplicate_rows,
        rows=[
            ImportRowResult(**{k: v for k, v in r.items() if k != "data"})
            for r in batch.row_results or []
        ],
    )


def _batch(db: Session, batch_id: int) -> ImportBatch:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Import not found.")
    return batch


def _check_import_rights(db: Session, ctx: AuthContext, kind: ImportType, scored: bool) -> None:
    ensure(db, ctx, Perm.IMPORT_CSV, object_type="import")
    if kind == ImportType.RISKS:
        ensure(db, ctx, Perm.CREATE_RISK, object_type="import")
        if scored:
            ensure(db, ctx, Perm.ASSESS_RISK, object_type="import")


@router.get("/imports/templates/{kind}.csv")
def import_template(kind: ImportType, _: AuthContext = Depends(get_auth)) -> Response:
    return Response(
        importer.template_csv(kind).encode("utf-8-sig"),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="risktrack-{kind.value}-template.csv"'
        },
    )


@router.get("/imports", response_model=list[ImportBatchOut])
def list_imports(
    _: AuthContext = Depends(require(Perm.IMPORT_CSV)), db: Session = Depends(get_session)
) -> list[ImportBatchOut]:
    return [_batch_out(db, b) for b in importer.batches(db)]


@router.get("/imports/{batch_id}", response_model=ImportBatchOut)
def get_import(
    batch_id: int,
    _: AuthContext = Depends(require(Perm.IMPORT_CSV)),
    db: Session = Depends(get_session),
) -> ImportBatchOut:
    return _batch_out(db, _batch(db, batch_id))


@router.post("/imports/{kind}", response_model=ImportBatchOut, status_code=status.HTTP_201_CREATED)
def preview_import(
    kind: ImportType,
    file: UploadFile = File(description="CSV in the template format, UTF-8"),
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> ImportBatchOut:
    """Step 1: validate and preview. Nothing is created until the batch is committed."""
    _check_import_rights(db, ctx, kind, scored=False)
    try:
        content = read_upload(file)
        if not (file.filename or "").lower().endswith(".csv"):
            raise EvidenceRejected("Upload a .csv file (download the template to start).")
        checked = check_evidence(file.filename or "", content)
        batch = importer.preview(db, ctx.audit_actor, kind, checked, content)
    except (EvidenceRejected, importer.ImportFileError) as exc:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    db.commit()
    return _batch_out(db, batch)


@router.post("/imports/{batch_id}/commit", response_model=ImportBatchOut)
def commit_import(
    batch_id: int, ctx: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> ImportBatchOut:
    """Step 2: create the valid rows (re-checked now); rejected and duplicate rows are skipped."""
    batch = _batch(db, batch_id)
    _check_import_rights(
        db, ctx, ImportType(batch.import_type), scored=importer.has_scores(batch.row_results or [])
    )
    try:
        importer.commit(db, ctx.audit_actor, batch)
    except tr.TreatmentError as exc:
        db.rollback()
        raise HTTPException(exc.status, str(exc)) from exc
    db.commit()
    return _batch_out(db, batch)


@router.post("/imports/{batch_id}/cancel", response_model=ImportBatchOut)
def cancel_import(
    batch_id: int,
    ctx: AuthContext = Depends(require(Perm.IMPORT_CSV)),
    db: Session = Depends(get_session),
) -> ImportBatchOut:
    batch = _batch(db, batch_id)
    try:
        importer.cancel(db, ctx.audit_actor, batch)
    except tr.TreatmentError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    db.commit()
    return _batch_out(db, batch)


# ── Audit log ──────────────────────────────────────────────────────────────────────────────


def _audit_query(
    action: AuditAction | None,
    username: str | None,
    object_type: str | None,
    object_id: str | None,
    since: datetime | None,
    until: datetime | None,
):  # type: ignore[no-untyped-def]
    query = select(AuditLog)
    if action is not None:
        query = query.where(AuditLog.action == action.value)
    if username:
        query = query.where(AuditLog.username == username.strip().lower())
    if object_type:
        query = query.where(AuditLog.object_type == object_type)
    if object_id:
        query = query.where(AuditLog.object_id == object_id)
    if since is not None:
        query = query.where(col(AuditLog.occurred_at) >= since)
    if until is not None:
        query = query.where(col(AuditLog.occurred_at) <= until)
    return query


def _entry(row: AuditLog) -> AuditEntryOut:
    return AuditEntryOut.model_validate(row, from_attributes=True)


@router.get("/audit", response_model=AuditPage)
def audit_log(
    action: AuditAction | None = None,
    username: str | None = Query(default=None, max_length=50),
    object_type: str | None = Query(default=None, max_length=40),
    object_id: str | None = Query(default=None, max_length=40),
    since: datetime | None = None,
    until: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _: AuthContext = Depends(require(Perm.VIEW_AUDIT)),
    db: Session = Depends(get_session),
) -> AuditPage:
    """Newest first. Filter by action, user, record, or time window (ISO 8601 with zone)."""
    query = _audit_query(action, username, object_type, object_id, since, until)
    total = db.exec(select(func.count()).select_from(query.subquery())).one()
    rows = db.exec(
        query.order_by(col(AuditLog.id).desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return AuditPage(items=[_entry(r) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/audit/verify", response_model=ChainReportOut)
def verify_audit(
    _: AuthContext = Depends(require(Perm.VIEW_AUDIT)), db: Session = Depends(get_session)
) -> ChainReportOut:
    """Recompute every link of the hash chain (test T22)."""
    report = audit.verify_chain(db)
    head = db.exec(select(AuditLog.hash).order_by(col(AuditLog.id).desc()).limit(1)).first()
    return ChainReportOut(
        ok=report.ok,
        entries_checked=report.entries_checked,
        first_broken_id=report.first_broken_id,
        problem=report.problem,
        head_hash=head,
    )


@router.get("/audit.csv")
def audit_csv(
    action: AuditAction | None = None,
    username: str | None = Query(default=None, max_length=50),
    object_type: str | None = Query(default=None, max_length=40),
    object_id: str | None = Query(default=None, max_length=40),
    since: datetime | None = None,
    until: datetime | None = None,
    ctx: AuthContext = Depends(require(Perm.VIEW_AUDIT)),
    db: Session = Depends(get_session),
) -> Response:
    """Times in UTC (auditors compare against UTC)."""
    query = _audit_query(action, username, object_type, object_id, since, until)
    rows = db.exec(query.order_by(col(AuditLog.id))).all()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        [
            "id",
            "occurred_at_utc",
            "username",
            "role",
            "action",
            "object_type",
            "object_id",
            "detail",
            "ip",
            "before",
            "after",
            "prev_hash",
            "hash",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                safe_cell(v)
                for v in (
                    r.id,
                    f"{r.occurred_at:%Y-%m-%dT%H:%M:%S.%fZ}",
                    r.username,
                    r.role,
                    r.action,
                    r.object_type,
                    r.object_id,
                    r.detail,
                    r.ip,
                    json.dumps(r.before, sort_keys=True) if r.before else "",
                    json.dumps(r.after, sort_keys=True) if r.after else "",
                    r.prev_hash,
                    r.hash,
                )
            ]
        )
    audit.record(
        db,
        AuditAction.EXPORT,
        ctx.audit_actor,
        object_type="audit_log",
        detail=f"Audit log CSV export ({len(rows)} entries)",
    )
    db.commit()
    return Response(
        out.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="audit-log-{now_utc():%Y%m%d-%H%M}.csv"',
            "Cache-Control": "private, no-store",
        },
    )


# ── Settings ───────────────────────────────────────────────────────────────────────────────

SETTING_FIELDS = tuple(SettingsOut.model_fields.keys() - {"updated_at", "updated_by"})


def _settings_out(db: Session) -> SettingsOut:
    row = governance.app_setting(db)
    by = db.get(User, row.updated_by_id) if row.updated_by_id else None
    likelihood, impact = governance.level_definitions(row)
    values = {f: getattr(row, f) for f in SETTING_FIELDS}
    values.update(likelihood_definitions=likelihood, impact_definitions=impact)
    return SettingsOut(**values, updated_at=row.updated_at, updated_by=by.full_name if by else None)


@router.get("/methodology", response_model=Methodology)
def methodology(
    _: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> Methodology:
    """The documented scoring method (brief feature 2): scales with their definitions, rating
    bands with remediation deadlines and review cycles, and the appetite threshold."""
    row = governance.app_setting(db)
    policy = governance.policy(db)
    likelihood, impact = governance.level_definitions(row)
    ranges = {Band.LOW: (1, 4), Band.MEDIUM: (5, 9), Band.HIGH: (10, 14), Band.CRITICAL: (15, 25)}
    return Methodology(
        formula="Risk score = likelihood × impact (each 1 to 5), giving 1 to 25.",
        appetite_threshold=policy.appetite_threshold,
        appetite_statement=(
            "The Alajo has a low appetite for loss of customer funds, exposure of customer data "
            f"and regulatory breach. Any score of {policy.appetite_threshold} or more is above "
            "appetite and must be treated or formally accepted; lower scores may be managed by "
            "the risk owner."
        ),
        likelihood=[
            ScaleLevel(level=i, label=LIKELIHOOD_LABELS[i], definition=likelihood[i - 1])
            for i in range(1, 6)
        ],
        impact=[
            ScaleLevel(level=i, label=IMPACT_LABELS[i], definition=impact[i - 1])
            for i in range(1, 6)
        ],
        bands=[
            BandRule(
                band=band.value,
                label=BAND_LABELS[band],
                min_score=low,
                max_score=high,
                above_appetite=low >= policy.appetite_threshold,
                remediation_days=policy.sla_days(band),
                review_days=policy.review_days(band),
            )
            for band, (low, high) in sorted(ranges.items(), key=lambda kv: -kv[1][0])
        ],
        review_warning_days=policy.review_warning_days,
        org_timezone=row.org_timezone,
    )


@router.get("/settings", response_model=SettingsOut)
def get_settings_row(
    _: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> SettingsOut:
    return _settings_out(db)


@router.patch("/settings", response_model=SettingsOut)
def change_settings(
    body: SettingsUpdate,
    ctx: AuthContext = Depends(require(Perm.MANAGE_SETTINGS)),
    db: Session = Depends(get_session),
) -> SettingsOut:
    """Changes apply to *new* assessments and actions; stored assessments keep the threshold in
    force when they were made (it is recorded on each row)."""
    row = governance.app_setting(db)
    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    before = {k: getattr(row, k) for k in changes}
    for field, value in changes.items():
        setattr(row, field, value)
    row.updated_at = now_utc()
    row.updated_by_id = ctx.user.id
    db.add(row)
    audit.record(
        db,
        AuditAction.SETTING,
        ctx.audit_actor,
        object_type="settings",
        object_id=1,
        before=before,
        after=changes,
    )
    db.commit()
    return _settings_out(db)
