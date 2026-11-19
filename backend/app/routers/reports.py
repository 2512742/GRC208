"""Dashboard and the management risk report (brief feature 6; tests T17, T18)."""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session

from app.core.auth import AuthContext, get_auth, require
from app.core.permissions import Perm
from app.db import get_session
from app.models.enums import AuditAction, Band, RiskStatus
from app.services import audit, governance
from app.services.clock import now_utc
from app.services.dashboard import Overview, overview
from app.services.report import Stamp, to_csv, to_pdf
from app.services.risk_views import RiskFilters

router = APIRouter(tags=["dashboard and reports"])


def report_filters(
    q: str | None = Query(default=None, max_length=100),
    service_id: int | None = None,
    owner_id: int | None = None,
    obligation_id: int | None = None,
    band: Band | None = None,
    risk_status: RiskStatus | None = Query(default=None, alias="status"),
    above_appetite: bool | None = None,
) -> RiskFilters:
    return RiskFilters(
        q=q,
        service_id=service_id,
        owner_id=owner_id,
        obligation_id=obligation_id,
        band=band,
        status=risk_status,
        above_appetite=above_appetite,
    )


def _describe(filters: RiskFilters) -> str:
    parts = [
        f"{k}={v.value if hasattr(v, 'value') else v}"
        for k, v in vars(filters).items()
        if v is not None
    ]
    return ", ".join(parts)


def _display_zone(ctx: AuthContext, db: Session, tz: str | None) -> str:
    """The zone for printed times: ?tz= (the browser's resolved zone when the user picked
    'System'), else the user's saved choice, else the organisation's zone."""
    for candidate in (tz, ctx.user.display_timezone):
        if candidate and candidate != "system":
            try:
                ZoneInfo(candidate)
                return candidate
            except (ZoneInfoNotFoundError, ValueError):
                continue
    return governance.app_setting(db).org_timezone


@router.get("/dashboard", response_model=Overview)
def dashboard(
    filters: RiskFilters = Depends(report_filters),
    _: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> Overview:
    data = overview(db, filters)
    data.risks = []  # the dashboard needs the aggregates, not the whole register
    return data


@router.get("/reports/management", response_model=Overview)
def management_report(
    filters: RiskFilters = Depends(report_filters),
    _: AuthContext = Depends(require(Perm.EXPORT_REPORTS)),
    db: Session = Depends(get_session),
) -> Overview:
    return overview(db, filters)


def _export(
    kind: str, filters: RiskFilters, ctx: AuthContext, db: Session, tz: str | None
) -> tuple[Overview, Stamp]:
    data = overview(db, filters)
    stamp = Stamp(
        generated_by=f"{ctx.user.full_name} ({ctx.user.role})",
        generated_at_utc=now_utc(),
        display_zone=_display_zone(ctx, db, tz),
        org_zone=governance.app_setting(db).org_timezone,
        filters=_describe(filters),
    )
    audit.record(
        db,
        AuditAction.EXPORT,
        ctx.audit_actor,
        object_type="report",
        object_id=kind,
        detail=f"Management report ({kind}); filters: "
        f"{stamp.filters or 'none'}; {len(data.risks)} risks",
    )
    db.commit()
    return data, stamp


def _filename(extension: str) -> str:
    return f"alajo-management-risk-report-{now_utc():%Y%m%d-%H%M}.{extension}"


@router.get("/reports/management.csv")
def management_report_csv(
    filters: RiskFilters = Depends(report_filters),
    tz: str | None = Query(default=None, max_length=64),
    ctx: AuthContext = Depends(require(Perm.EXPORT_REPORTS)),
    db: Session = Depends(get_session),
) -> Response:
    data, stamp = _export("csv", filters, ctx, db, tz)
    return Response(
        to_csv(data, stamp).encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{_filename("csv")}"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/reports/management.pdf")
def management_report_pdf(
    filters: RiskFilters = Depends(report_filters),
    tz: str | None = Query(default=None, max_length=64),
    ctx: AuthContext = Depends(require(Perm.EXPORT_REPORTS)),
    db: Session = Depends(get_session),
) -> Response:
    data, stamp = _export("pdf", filters, ctx, db, tz)
    return Response(
        to_pdf(data, stamp),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{_filename("pdf")}"',
            "Cache-Control": "private, no-store",
        },
    )
