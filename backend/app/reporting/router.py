import csv
import io
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
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
from .service import execute_report, home_feed, run_and_record

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


@router.delete("/reports/{code}", status_code=204, response_model=None)
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


# ---------------------------------------------------------------------------
# CSV / PDF Export endpoints
# ---------------------------------------------------------------------------

@router.get("/reports/{code}/export/csv")
def export_report_csv(
    code: str,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    report = _get_report(db, tenant_id, code)
    result = execute_report(db, tenant_id=tenant_id, role=principal.role, report=report)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    if result.get("series"):
        writer.writerow(["key", "value"])
        for item in result["series"]:
            writer.writerow([item["key"], item["value"]])
    else:
        writer.writerow(["metric", "value", "count"])
        writer.writerow([result.get("metric", ""), result.get("value", ""), result.get("count", 0)])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={code}_report.csv"},
    )


@router.get("/reports/{code}/export/pdf")
def export_report_pdf(
    code: str,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    report = _get_report(db, tenant_id, code)
    result = execute_report(db, tenant_id=tenant_id, role=principal.role, report=report)

    # Generate a simple text-based PDF-like content
    lines = [
        f"Report: {result.get('report_name', code)}",
        f"Entity: {result.get('entity_code', '')}",
        f"Metric: {result.get('metric', '')}",
        f"Value: {result.get('value', '')}",
        f"Count: {result.get('count', 0)}",
        "",
        "Breakdown:",
    ]
    for item in result.get("series", []):
        lines.append(f"  {item['key']}: {item['value']}")

    content = "\n".join(lines)
    output = io.BytesIO(content.encode("utf-8"))
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={code}_report.pdf"},
    )


# ---------------------------------------------------------------------------
# Scheduled Reports
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field as PydanticField


class ScheduledReportCreate(BaseModel):
    report_code: str
    name: str
    frequency: str = PydanticField(pattern="^(daily|weekly|monthly)$")
    day_of_week: int | None = PydanticField(default=None, ge=0, le=6)
    day_of_month: int | None = PydanticField(default=None, ge=1, le=31)
    hour: int = PydanticField(default=8, ge=0, le=23)
    minute: int = PydanticField(default=0, ge=0, le=59)
    export_format: str = PydanticField(default="csv", pattern="^(csv|pdf)$")
    recipients: list[str] = PydanticField(default_factory=list)


class ScheduledReportResponse(BaseModel):
    id: UUID
    report_code: str
    name: str
    frequency: str
    export_format: str
    is_active: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime


@router.get("/scheduled", response_model=list[ScheduledReportResponse])
def list_scheduled_reports(
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    from .models import ScheduledReport, AnalyticsReport
    from sqlalchemy import select

    scheduled = db.scalars(
        select(ScheduledReport).where(ScheduledReport.tenant_id == tenant_id)
    ).all()

    result = []
    for s in scheduled:
        report = db.get(AnalyticsReport, s.report_id)
        result.append(ScheduledReportResponse(
            id=s.id,
            report_code=report.code if report else "",
            name=s.name,
            frequency=s.frequency,
            export_format=s.export_format,
            is_active=s.is_active,
            last_run_at=s.last_run_at,
            next_run_at=s.next_run_at,
            created_at=s.created_at,
        ))
    return result


@router.post("/scheduled", response_model=ScheduledReportResponse, status_code=201)
def create_scheduled_report(
    payload: ScheduledReportCreate,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    from .models import ScheduledReport, AnalyticsReport
    from sqlalchemy import select
    from datetime import timedelta

    report = db.scalar(
        select(AnalyticsReport).where(
            AnalyticsReport.tenant_id == tenant_id,
            AnalyticsReport.code == payload.report_code,
        )
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    from datetime import UTC, datetime
    now = datetime.now(UTC)
    next_run = now + timedelta(days=1)

    scheduled = ScheduledReport(
        tenant_id=tenant_id,
        report_id=report.id,
        name=payload.name,
        frequency=payload.frequency,
        day_of_week=payload.day_of_week,
        day_of_month=payload.day_of_month,
        hour=payload.hour,
        minute=payload.minute,
        export_format=payload.export_format,
        recipients_json=json.dumps(payload.recipients),
        created_by=principal.user_id,
        next_run_at=next_run,
    )
    db.add(scheduled)
    db.commit()
    db.refresh(scheduled)

    return ScheduledReportResponse(
        id=scheduled.id,
        report_code=payload.report_code,
        name=scheduled.name,
        frequency=scheduled.frequency,
        export_format=scheduled.export_format,
        is_active=scheduled.is_active,
        last_run_at=scheduled.last_run_at,
        next_run_at=scheduled.next_run_at,
        created_at=scheduled.created_at,
    )


@router.delete("/scheduled/{scheduled_id}", status_code=204, response_model=None)
def delete_scheduled_report(
    scheduled_id: UUID,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    from .models import ScheduledReport
    from sqlalchemy import select

    scheduled = db.scalar(
        select(ScheduledReport).where(
            ScheduledReport.id == scheduled_id,
            ScheduledReport.tenant_id == tenant_id,
        )
    )
    if not scheduled:
        raise HTTPException(status_code=404, detail="Scheduled report not found")
    db.delete(scheduled)
    db.commit()
