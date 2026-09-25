from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth.security import Principal, require_principal
from .construction.models import Project
from .db import get_db
from .export import format_export_response
from .tenant import require_tenant

router = APIRouter(prefix="/api/v1/export", tags=["export"])


@router.get("/construction/projects")
def export_projects(
    format: str = Query("csv", pattern="^(csv|json|xlsx|pdf)$"),
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Response:
    projects = db.scalars(
        select(Project).where(Project.tenant_id == tenant_id)
    ).all()
    
    data = [
        {
            "code": p.code,
            "name": p.name,
            "status": p.status,
            "budget": str(p.budget) if p.budget else "",
            "client_name": p.client_name or "",
            "location": p.location or "",
            "created_at": p.created_at.isoformat() if p.created_at else "",
        }
        for p in projects
    ]
    
    headers_map = {
        "code": "Code",
        "name": "Name",
        "status": "Status",
        "budget": "Budget",
        "client_name": "Client",
        "location": "Location",
        "created_at": "Created",
    }
    
    content, mime, filename = format_export_response(
        data, format, title="Construction Projects", headers=headers_map
    )
    
    return Response(
        content=content,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
