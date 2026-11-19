"""Business services, assets, obligations and controls.

Reading: any signed-in user. Changing: analysts and admins (MANAGE_REGISTER).
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.auth import AuthContext, get_auth, require
from app.core.permissions import Perm
from app.db import get_session
from app.models import (
    Asset,
    AssetObligation,
    BusinessService,
    Control,
    Obligation,
    RiskAssessment,
    RiskAsset,
    User,
)
from app.models.enums import AuditAction, Framework, Regime
from app.schemas.register import (
    AssetCreate,
    AssetOut,
    AssetUpdate,
    ControlOut,
    ObligationCreate,
    ObligationOut,
    PersonRef,
    ServiceCreate,
    ServiceOut,
    ServiceUpdate,
)
from app.services import audit
from app.services import register as reg

router = APIRouter(tags=["register"])


def fail(exc: reg.RegisterError) -> HTTPException:
    return HTTPException(exc.status, str(exc))


def _person(db: Session, user_id: int | None) -> PersonRef | None:
    user = db.get(User, user_id) if user_id is not None else None
    return PersonRef.model_validate(user) if user else None


# ── Services ───────────────────────────────────────────────────────────────────────────────


def _service_out(db: Session, service: BusinessService) -> ServiceOut:
    asset_count = db.exec(
        select(func.count()).select_from(Asset).where(Asset.service_id == service.id)
    ).one()
    risk_count = db.exec(
        select(func.count(func.distinct(RiskAsset.risk_id)))
        .join(Asset, Asset.id == RiskAsset.asset_id)
        .where(Asset.service_id == service.id)
    ).one()
    return ServiceOut(
        id=service.id,
        code=service.code,
        name=service.name,  # type: ignore[arg-type]
        description=service.description,
        owner=_person(db, service.owner_id),
        criticality=service.criticality,
        asset_count=asset_count,
        risk_count=risk_count,
    )


@router.get("/services", response_model=list[ServiceOut])
def list_services(
    _: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> list[ServiceOut]:
    services = db.exec(select(BusinessService).order_by(col(BusinessService.code))).all()
    return [_service_out(db, s) for s in services]


@router.post("/services", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def add_service(
    body: ServiceCreate,
    ctx: AuthContext = Depends(require(Perm.MANAGE_REGISTER)),
    db: Session = Depends(get_session),
) -> ServiceOut:
    try:
        service = reg.create_service(db, ctx.audit_actor, **body.model_dump())
    except reg.RegisterError as exc:
        db.rollback()
        raise fail(exc) from exc
    db.commit()
    return _service_out(db, service)


@router.patch("/services/{service_id}", response_model=ServiceOut)
def change_service(
    service_id: int,
    body: ServiceUpdate,
    ctx: AuthContext = Depends(require(Perm.MANAGE_REGISTER)),
    db: Session = Depends(get_session),
) -> ServiceOut:
    service = db.get(BusinessService, service_id)
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found.")
    changes = body.model_dump(exclude_unset=True)
    try:
        if "owner_id" in changes:
            reg.check_optional_user(db, changes["owner_id"], "service owner")
        if (
            "name" in changes
            and db.exec(
                select(BusinessService.id).where(
                    func.lower(BusinessService.name) == changes["name"].lower(),
                    BusinessService.id != service_id,
                )
            ).first()
        ):
            raise reg.RegisterError("Another service already has that name.", 409)
    except reg.RegisterError as exc:
        raise fail(exc) from exc
    before = reg.snapshot(service, reg.SERVICE_FIELDS)
    for field, value in changes.items():
        setattr(service, field, value)
    db.add(service)
    audit.record(
        db,
        AuditAction.UPDATE,
        ctx.audit_actor,
        object_type="service",
        object_id=service.id,
        before=before,
        after=reg.snapshot(service, reg.SERVICE_FIELDS),
    )
    db.commit()
    return _service_out(db, service)


# ── Obligations and controls ───────────────────────────────────────────────────────────────


@router.get("/obligations", response_model=list[ObligationOut])
def list_obligations(
    regime: Regime | None = None,
    _: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> list[Obligation]:
    query = select(Obligation).order_by(col(Obligation.regime), col(Obligation.reference))
    if regime is not None:
        query = query.where(Obligation.regime == regime.value)
    return list(db.exec(query))


@router.post("/obligations", response_model=ObligationOut, status_code=status.HTTP_201_CREATED)
def add_obligation(
    body: ObligationCreate,
    ctx: AuthContext = Depends(require(Perm.MANAGE_REGISTER)),
    db: Session = Depends(get_session),
) -> Obligation:
    if db.exec(
        select(Obligation.id).where(
            Obligation.regime == body.regime.value, Obligation.reference == body.reference
        )
    ).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "That obligation reference already exists.")
    obligation = Obligation(**{**body.model_dump(), "regime": body.regime.value})
    db.add(obligation)
    db.flush()
    audit.record(
        db,
        AuditAction.CREATE,
        ctx.audit_actor,
        object_type="obligation",
        object_id=obligation.id,
        after=body.model_dump(),
    )
    db.commit()
    return obligation


@router.get("/controls", response_model=list[ControlOut])
def list_controls(
    framework: Framework | None = None,
    _: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> list[Control]:
    query = select(Control).order_by(col(Control.framework), col(Control.id))
    if framework is not None:
        query = query.where(Control.framework == framework.value)
    return list(db.exec(query))


# ── Assets ─────────────────────────────────────────────────────────────────────────────────


def _assets_out(db: Session, assets: list[Asset]) -> list[AssetOut]:
    if not assets:
        return []
    ids = [a.id for a in assets]
    services = {s.id: s for s in db.exec(select(BusinessService))}
    obligations: dict[int, list[ObligationOut]] = defaultdict(list)
    for asset_id, obligation in db.exec(
        select(AssetObligation.asset_id, Obligation)
        .join(Obligation, Obligation.id == AssetObligation.obligation_id)
        .where(col(AssetObligation.asset_id).in_(ids))
        .order_by(col(Obligation.regime), col(Obligation.reference))
    ):
        obligations[asset_id].append(ObligationOut.model_validate(obligation))
    risk_counts = dict(
        db.exec(
            select(RiskAsset.asset_id, func.count())
            .where(col(RiskAsset.asset_id).in_(ids))
            .group_by(RiskAsset.asset_id)
        ).all()
    )
    latest = (
        select(RiskAssessment.risk_id, func.max(RiskAssessment.id).label("aid"))
        .group_by(RiskAssessment.risk_id)
        .subquery()
    )
    highest = dict(
        db.exec(
            select(RiskAsset.asset_id, func.max(RiskAssessment.score))
            .join(latest, latest.c.risk_id == RiskAsset.risk_id)
            .join(RiskAssessment, RiskAssessment.id == latest.c.aid)
            .where(col(RiskAsset.asset_id).in_(ids))
            .group_by(RiskAsset.asset_id)
        ).all()
    )
    out = []
    for asset in assets:
        service = services[asset.service_id]
        out.append(
            AssetOut(
                id=asset.id,
                asset_code=asset.asset_code,
                name=asset.name,  # type: ignore[arg-type]
                asset_type=asset.asset_type,
                classification=asset.classification,  # type: ignore[arg-type]
                status=asset.status,
                description=asset.description,  # type: ignore[arg-type]
                service={"id": service.id, "code": service.code, "name": service.name},
                owner=_person(db, asset.owner_id),
                obligations=obligations.get(asset.id, []),  # type: ignore[arg-type]
                risk_count=risk_counts.get(asset.id, 0),
                highest_score=highest.get(asset.id),
            )
        )
    return out


@router.get("/assets", response_model=list[AssetOut])
def list_assets(
    service_id: int | None = None,
    q: str | None = Query(default=None, max_length=100),
    _: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> list[AssetOut]:
    query = select(Asset).order_by(col(Asset.asset_code))
    if service_id is not None:
        query = query.where(Asset.service_id == service_id)
    if q:
        needle = f"%{q.strip().lower()}%"
        query = query.where(
            func.lower(Asset.name).like(needle) | func.lower(Asset.asset_code).like(needle)
        )
    return _assets_out(db, list(db.exec(query)))


@router.get("/assets/{asset_id}", response_model=AssetOut)
def get_asset(
    asset_id: int, _: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> AssetOut:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found.")
    return _assets_out(db, [asset])[0]


@router.post("/assets", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def add_asset(
    body: AssetCreate,
    ctx: AuthContext = Depends(require(Perm.MANAGE_REGISTER)),
    db: Session = Depends(get_session),
) -> AssetOut:
    values = body.model_dump()
    obligation_ids = values.pop("obligation_ids")
    for key in ("asset_type", "classification", "status"):
        values[key] = values[key].value
    try:
        asset = reg.create_asset(db, ctx.audit_actor, obligation_ids, **values)
    except reg.RegisterError as exc:
        db.rollback()
        raise fail(exc) from exc
    db.commit()
    return _assets_out(db, [asset])[0]


@router.patch("/assets/{asset_id}", response_model=AssetOut)
def change_asset(
    asset_id: int,
    body: AssetUpdate,
    ctx: AuthContext = Depends(require(Perm.MANAGE_REGISTER)),
    db: Session = Depends(get_session),
) -> AssetOut:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found.")
    changes = body.model_dump(exclude_unset=True)
    obligation_ids = changes.pop("obligation_ids", None)
    try:
        if "name" in changes and reg.asset_name_taken(
            db, changes["name"], asset.service_id, except_id=asset.id
        ):
            raise reg.RegisterError("An asset with this name already exists in that service.", 409)
        if "owner_id" in changes:
            reg.check_optional_user(db, changes["owner_id"], "asset owner")
        before = {
            **reg.snapshot(asset, reg.ASSET_FIELDS),
            "obligation_ids": list(
                db.exec(
                    select(AssetObligation.obligation_id).where(
                        AssetObligation.asset_id == asset.id
                    )
                )
            ),
        }
        for field, value in changes.items():
            setattr(asset, field, getattr(value, "value", value))
        db.add(asset)
        after = reg.snapshot(asset, reg.ASSET_FIELDS)
        if obligation_ids is not None:
            new = reg.require_ids(db, Obligation, obligation_ids, "obligation")
            for link in db.exec(
                select(AssetObligation).where(AssetObligation.asset_id == asset.id)
            ):
                db.delete(link)
            db.flush()
            for obligation in new:
                db.add(AssetObligation(asset_id=asset.id, obligation_id=obligation.id))
            after["obligation_ids"] = [o.id for o in new]
    except reg.RegisterError as exc:
        db.rollback()
        raise fail(exc) from exc
    audit.record(
        db,
        AuditAction.UPDATE,
        ctx.audit_actor,
        object_type="asset",
        object_id=asset.id,
        before=before,
        after=after,
    )
    db.commit()
    return _assets_out(db, [asset])[0]
