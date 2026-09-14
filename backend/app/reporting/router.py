import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.security import Principal, require_principal
from ..db import get_db
from ..rules.schemas import Condition
from ..tenant import require_tenant
from .models import AnalyticsReport, ReportRun
from .schemas import (
    AnalyticsReportCreate,
    AnalyticsReportResponse,
    AnalyticsReportUpdate,
    ReportRunResponse,
    WorkspaceFeed,
)
from .service import home_feed, run_and_record

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def _conditions(report: AnalyticsReport) -> list[Condition]:
    if not report.conditions_json:
        return []
    return [Condition(**condition) for condition in json.loads(report.conditions_json)]


def _response(report: AnalyticsReport) -> AnalyticsReportResponse:
    return AnalyticsReportResponse(
        id=report.id,
        code=report.code,
        name=report.name,
        entity_code=report.entity_code,
        metric=report.metric,
        field=report.field,
        conditions=_conditions(report),
        group_by=report.group_by,
        created_by=report.created_by,
        created_at=report.created_at,
    )


def _get_report(db: Session, tenant_id: UUID, code: str) -> AnalyticsReport:
    report = db.scalar(
        select(AnalyticsReport).where(AnalyticsReport.tenant_id == tenant_id, AnalyticsReport.code == code)
    )
    if report is None:
        raise HTTPException(status_code=404, detail="analytics report not found")
    return report


@router.post("/reports", response_model=AnalyticsReportResponse, status_code=201)
def create_report(
    payload: AnalyticsReportCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> AnalyticsReportResponse:
    existing = db.scalar(
        select(AnalyticsReport).where(
            AnalyticsReport.tenant_id == tenant_id, AnalyticsReport.code == payload.code
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="analytics report code already exists")
    report = AnalyticsReport(
        tenant_id=tenant_id,
        code=payload.code,
        name=payload.name,
        entity_code=payload.entity_code,
        metric=payload.metric,
        field=payload.field,
        conditions_json=json.dumps([condition.model_dump(mode="json") for condition in payload.conditions]),
        group_by=payload.group_by,
        created_by=request.state.user_id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _response(report)


@router.get("/reports", response_model=list[AnalyticsReportResponse])
def list_reports(
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[AnalyticsReportResponse]:
    rows = db.scalars(
        select(AnalyticsReport)
        .where(AnalyticsReport.tenant_id == tenant_id)
        .order_by(AnalyticsReport.created_at.desc())
    ).all()
    return [_response(report) for report in rows]


@router.get("/reports/{code}", response_model=AnalyticsReportResponse)
def get_report(
    code: str,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> AnalyticsReportResponse:
    return _response(_get_report(db, tenant_id, code))


@router.patch("/reports/{code}", response_model=AnalyticsReportResponse)
def update_report(
    code: str,
    payload: AnalyticsReportUpdate,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> AnalyticsReportResponse:
    report = _get_report(db, tenant_id, code)
    if payload.name is not None:
        report.name = payload.name
    if payload.metric is not None:
        report.metric = payload.metric
    if payload.field is not None:
        report.field = payload.field
    if payload.conditions is not None:
        report.conditions_json = json.dumps(
            [condition.model_dump(mode="json") for condition in payload.conditions]
        )
    if payload.group_by is not None:
        report.group_by = payload.group_by
    db.commit()
    db.refresh(report)
    return _response(report)


@router.delete("/reports/{code}", status_code=204)
def delete_report(
    code: str,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> None:
    report = _get_report(db, tenant_id, code)
    db.delete(report)
    db.commit()


@router.post("/reports/{code}/run", response_model=ReportRunResponse)
def run_report(
    code: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    report = _get_report(db, tenant_id, code)
    return run_and_record(
        db,
        tenant_id=tenant_id,
        role=request.state.role,
        user_id=request.state.user_id,
        report=report,
        request_id=request.state.request_id,
    )


@router.get("/reports/{code}/runs", response_model=list[ReportRunResponse])
def report_run_history(
    code: str,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[dict]:
    report = _get_report(db, tenant_id, code)
    runs = db.scalars(
        select(ReportRun)
        .where(ReportRun.tenant_id == tenant_id, ReportRun.report_id == report.id)
        .order_by(ReportRun.created_at.desc())
        .limit(20)
    ).all()
    return [
        {
            "run_id": run.id,
            "report_code": report.code,
            "result": run.result_json,
            "created_at": run.created_at,
        }
        for run in runs
    ]


@router.get("/home", response_model=WorkspaceFeed)
def workspace_feed(
    request: Request,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    return home_feed(
        db,
        tenant_id=tenant_id,
        role=request.state.role,
        user_id=request.state.user_id,
    )