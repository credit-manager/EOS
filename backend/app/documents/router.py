"""Document Intelligence router."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..db import get_db
from .schemas import (
    DocumentClassifyRequest,
    DocumentFieldResponse,
    DocumentLinkRequest,
    DocumentProcessingJobResponse,
    DocumentResponse,
    DocumentSearchResult,
    DocumentTemplateCreate,
    DocumentTemplateResponse,
    DocumentUpdate,
    DocumentUpload,
)
from .service import DocumentService
from ..tenant import require_tenant

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


# --- Static routes first (before /{document_id}) ---

@router.post("", response_model=DocumentResponse, status_code=201)
def create_document(
    payload: DocumentUpload,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    svc = DocumentService(db)
    doc = svc.create_document(str(tenant_id), payload.model_dump())
    return DocumentResponse.model_validate(doc)


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
    linked_entity_type: str | None = Query(default=None),
    linked_entity_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    svc = DocumentService(db)
    docs, _ = svc.list_documents(
        str(tenant_id),
        category=category,
        status=status,
        linked_entity_type=linked_entity_type,
        linked_entity_id=linked_entity_id,
        limit=limit,
        offset=offset,
    )
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get("/stats")
def get_document_stats(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    svc = DocumentService(db)
    return svc.get_document_stats(str(tenant_id))


@router.get("/search", response_model=DocumentSearchResult)
def search_documents(
    query: str | None = Query(default=None),
    category: str | None = Query(default=None),
    document_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    linked_entity_type: str | None = Query(default=None),
    linked_entity_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> DocumentSearchResult:
    svc = DocumentService(db)
    docs, total = svc.search_documents(
        str(tenant_id),
        query=query,
        category=category,
        document_type=document_type,
        status=status,
        linked_entity_type=linked_entity_type,
        linked_entity_id=linked_entity_id,
        limit=limit,
        offset=offset,
    )
    return DocumentSearchResult(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
        has_more=(offset + limit) < total,
    )


@router.post("/templates", response_model=DocumentTemplateResponse, status_code=201)
def create_template(
    payload: DocumentTemplateCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> DocumentTemplateResponse:
    svc = DocumentService(db)
    template = svc.create_template(str(tenant_id), payload.model_dump())
    return DocumentTemplateResponse.model_validate(template)


@router.get("/templates", response_model=list[DocumentTemplateResponse])
def list_templates(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[DocumentTemplateResponse]:
    svc = DocumentService(db)
    templates = svc.list_templates(str(tenant_id))
    return [DocumentTemplateResponse.model_validate(t) for t in templates]


@router.get("/templates/{template_id}", response_model=DocumentTemplateResponse)
def get_template(
    template_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> DocumentTemplateResponse:
    svc = DocumentService(db)
    template = svc.get_template(template_id, str(tenant_id))
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return DocumentTemplateResponse.model_validate(template)


@router.get("/jobs", response_model=list[DocumentProcessingJobResponse])
def list_jobs(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[DocumentProcessingJobResponse]:
    svc = DocumentService(db)
    jobs = svc.list_jobs(str(tenant_id), status=status, limit=limit)
    return [DocumentProcessingJobResponse.model_validate(j) for j in jobs]


# --- Dynamic routes after static ---

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    svc = DocumentService(db)
    doc = svc.get_document(document_id, str(tenant_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.patch("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: str,
    payload: DocumentUpdate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    svc = DocumentService(db)
    doc = svc.get_document(document_id, str(tenant_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(doc, key, value)
    from datetime import datetime
    doc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(doc)
    return DocumentResponse.model_validate(doc)


@router.post("/{document_id}/classify", response_model=DocumentResponse)
def classify_document(
    document_id: str,
    payload: DocumentClassifyRequest,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    svc = DocumentService(db)
    doc = svc.classify_document(document_id, str(tenant_id), payload.category, payload.confidence or 0.0)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.post("/{document_id}/extract", response_model=DocumentResponse)
def extract_document_data(
    document_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    svc = DocumentService(db)
    doc = svc.extract_document_data(document_id, str(tenant_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.post("/{document_id}/ocr", response_model=DocumentResponse)
def process_document_ocr(
    document_id: str,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """Process document with OCR (real extraction)."""
    svc = DocumentService(db)
    ocr_config = {}
    try:
        ocr_config = request.json() if hasattr(request, 'json') else {}
    except Exception:
        pass
    doc = svc.process_document_ocr(document_id, str(tenant_id), ocr_config)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.post("/{document_id}/link", response_model=DocumentResponse)
def link_document(
    document_id: str,
    payload: DocumentLinkRequest,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    svc = DocumentService(db)
    doc = svc.link_document(document_id, str(tenant_id), payload.entity_type, payload.entity_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.post("/{document_id}/archive", response_model=DocumentResponse)
def archive_document(
    document_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    svc = DocumentService(db)
    doc = svc.archive_document(document_id, str(tenant_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.get("/{document_id}/fields", response_model=list[DocumentFieldResponse])
def get_document_fields(
    document_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[DocumentFieldResponse]:
    svc = DocumentService(db)
    fields = svc.get_document_fields(document_id, str(tenant_id))
    return [DocumentFieldResponse.model_validate(f) for f in fields]


@router.post("/{document_id}/fields/{field_id}/validate", response_model=DocumentFieldResponse)
def validate_field(
    document_id: str,
    field_id: str,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> DocumentFieldResponse:
    svc = DocumentService(db)
    field = svc.validate_field(field_id, document_id, str(tenant_id), str(request.state.user_id))
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    return DocumentFieldResponse.model_validate(field)
