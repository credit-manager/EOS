from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from . import reports
from .auth.security import Principal, require_principal
from .db import get_db
from .export import format_export_response
from .tenant import require_tenant

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/dashboard")
def get_dashboard(
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    return reports.get_dashboard_stats(db, tenant_id=tenant_id)


@router.get("/financial/summary")
def get_financial_summary(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    return reports.get_financial_summary(
        db, tenant_id=tenant_id, start_date=start_date, end_date=end_date
    )


@router.get("/financial/profit-loss")
def get_profit_loss(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    format: str = Query("json", pattern="^(json|csv|xlsx|pdf)$"),
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Response:
    data = reports.get_profit_loss_report(
        db, tenant_id=tenant_id, start_date=start_date, end_date=end_date
    )
    
    if format == "json":
        return data
    
    flat_data = []
    for item in data["revenue"]["details"]:
        flat_data.append({"type": "Revenue", **item})
    for item in data["expenses"]["details"]:
        flat_data.append({"type": "Expense", **item})
    
    content, mime, filename = format_export_response(
        flat_data, format, title="Profit & Loss Report",
        headers={"type": "Type", "account_code": "Code", "account_name": "Account", "net": "Amount"},
    )
    
    return Response(
        content=content,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/financial/trial-balance")
def get_trial_balance(
    as_of_date: datetime | None = Query(None),
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    return reports.get_trial_balance(db, tenant_id=tenant_id, as_of_date=as_of_date)


@router.get("/financial/account-balances")
def get_account_balances(
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    return {"accounts": reports.get_account_balances(db, tenant_id=tenant_id)}
