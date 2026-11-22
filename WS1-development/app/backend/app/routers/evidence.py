"""Evidence: upload to a record, list, and permission-checked download.

Files are never edited or deleted (a database trigger enforces it); a mistake is fixed by
uploading a new file that supersedes the old one. Downloads are only for signed-in users and are
always served as attachments, never rendered inline (no stored XSS through an uploaded file).
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlmodel import Session

from app.core.auth import AuthContext, ensure, get_auth
from app.core.permissions import Perm, Target
from app.db import get_session
from app.models import (
    AcceptanceRequest,
    Evidence,
    Risk,
    RiskAssessment,
    TreatmentAction,
    TreatmentDecision,
    User,
)
from app.models.enums import EvidenceTarget
from app.models.records import EVIDENCE_MAX_BYTES
from app.schemas.register import PersonRef
from app.schemas.treatment import EvidenceOut
from app.services import treatment as tr
from app.services.evidence import EvidenceRejected, check_evidence

router = APIRouter(prefix="/evidence", tags=["evidence"])

# Uploads through this generic route; imports attach their own files (P6).
UPLOADABLE = (
    EvidenceTarget.RISK,
    EvidenceTarget.ACTION,
    EvidenceTarget.ASSESSMENT,
    EvidenceTarget.DECISION,
    EvidenceTarget.ACCEPTANCE,
)


def read_upload(file: UploadFile) -> bytes:
    """Read at most limit + 1 bytes, so an oversized upload is refused without being buffered
    whole (the size check itself is in check_evidence)."""
    return file.file.read(EVIDENCE_MAX_BYTES + 1)


def evidence_out(db: Session, row: Evidence, superseded_by: int | None = None) -> EvidenceOut:
    uploader = db.get(User, row.uploaded_by_id)
    return EvidenceOut(
        id=row.id,
        target_type=row.target_type,
        target_id=row.target_id,  # type: ignore[arg-type]
        original_name=row.original_name,
        mime_type=row.mime_type,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        description=row.description,
        supersedes_id=row.supersedes_id,
        superseded_by_id=superseded_by,
        uploaded_by=PersonRef.model_validate(uploader),
        uploaded_at=row.uploaded_at,
        download_url=f"/api/evidence/{row.id}/download",
    )


def target_context(db: Session, target_type: EvidenceTarget, target_id: int) -> Target:
    """Who owns the record, for the permission check. 404 if it doesn't exist."""

    def missing() -> HTTPException:
        return HTTPException(
            status.HTTP_404_NOT_FOUND, f"No {target_type.value} with id {target_id}."
        )

    if target_type == EvidenceTarget.RISK:
        risk = db.get(Risk, target_id)
        if risk is None:
            raise missing()
        return Target(risk_owner_id=risk.owner_id, evidence_on=target_type.value)
    if target_type == EvidenceTarget.ACTION:
        action = db.get(TreatmentAction, target_id)
        if action is None:
            raise missing()
        risk = db.get(Risk, action.risk_id)
        return Target(
            risk_owner_id=risk.owner_id if risk else None,
            action_owner_id=action.owner_id,
            evidence_on=target_type.value,
        )
    parent_model = {
        EvidenceTarget.ASSESSMENT: RiskAssessment,
        EvidenceTarget.DECISION: TreatmentDecision,
        EvidenceTarget.ACCEPTANCE: AcceptanceRequest,
    }.get(target_type)
    if parent_model is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Evidence can't be uploaded to a {target_type.value} here.",
        )
    parent = db.get(parent_model, target_id)
    if parent is None:
        raise missing()
    risk = db.get(Risk, parent.risk_id)  # type: ignore[attr-defined]
    return Target(risk_owner_id=risk.owner_id if risk else None, evidence_on=target_type.value)


@router.get("", response_model=list[EvidenceOut])
def list_evidence(
    target_type: EvidenceTarget,
    target_id: int,
    _: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> list[EvidenceOut]:
    rows = tr.evidence_for(db, target_type.value, target_id)
    superseded = {r.supersedes_id: r.id for r in rows if r.supersedes_id}
    return [evidence_out(db, r, superseded.get(r.id)) for r in rows]


@router.post("", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED)
def upload_evidence(
    target_type: EvidenceTarget = Form(),
    target_id: int = Form(),
    description: str | None = Form(default=None, max_length=500),
    supersedes_id: int | None = Form(default=None),
    file: UploadFile = File(
        description=f"PDF, PNG, JPG, CSV, TXT, XLSX or DOCX, max "
        f"{EVIDENCE_MAX_BYTES // 1_048_576} MB"
    ),
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> EvidenceOut:
    if target_type not in UPLOADABLE:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Evidence can't be uploaded to a {target_type.value} here.",
        )
    target = target_context(db, target_type, target_id)
    ensure(
        db, ctx, Perm.UPLOAD_EVIDENCE, target, object_type=target_type.value, object_id=target_id
    )
    try:
        content = read_upload(file)
        checked = check_evidence(file.filename or "", content)
        row = tr.store_evidence(
            db,
            ctx.audit_actor,
            target_type,
            target_id,
            checked,
            content,
            description=description,
            supersedes_id=supersedes_id,
        )
    except (EvidenceRejected, tr.TreatmentError) as exc:
        db.rollback()
        raise HTTPException(getattr(exc, "status", 422), str(exc)) from exc
    db.commit()
    return evidence_out(db, row)


@router.get("/{evidence_id}/download")
def download_evidence(
    evidence_id: int, _: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> Response:
    row = db.get(Evidence, evidence_id)
    if row is None or row.content is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence not found.")
    ascii_name = row.original_name.encode("ascii", "replace").decode().replace('"', "'")
    return Response(
        content=row.content,
        media_type=row.mime_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_name}"; '
                f"filename*=UTF-8''{quote(row.original_name)}"
            ),
            "Cache-Control": "private, no-store",
            "X-Evidence-SHA256": row.sha256,
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )
