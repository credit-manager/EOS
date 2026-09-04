"""P30 Document Management Router — tenant-safe folders, documents, versions and tags."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.auth_adapter import get_current_user
from core.document_engine import DocumentEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic", tags=["Document Management"])


def _err(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"status": "error", "error": {"code": code, "message": message}})


def _get_engine(db: Session = Depends(get_db)) -> DocumentEngine:
    return DocumentEngine(db)


def _require_company(db: Session, company_id: str, tenant_id: str) -> None:
    row = db.execute(text("SELECT id FROM dbp_companies WHERE id=:cid AND tenant_id=:tid"), {"cid": company_id, "tid": tenant_id}).fetchone()
    if not row:
        raise _err(404, "COMPANY_NOT_FOUND", "Company not found in current tenant")


def _require_document(db: Session, document_id: str, tenant_id: str) -> None:
    row = db.execute(text("SELECT id FROM dbp_documents WHERE id=:did AND tenant_id=:tid"), {"did": document_id, "tid": tenant_id}).fetchone()
    if not row:
        raise _err(404, "NOT_FOUND", "Document not found")


def _require_folder(db: Session, folder_id: str, tenant_id: str) -> None:
    row = db.execute(text("SELECT id FROM dbp_doc_folders WHERE id=:fid AND tenant_id=:tid"), {"fid": folder_id, "tid": tenant_id}).fetchone()
    if not row:
        raise _err(404, "NOT_FOUND", "Folder not found")


@router.get("/companies/{cid}/doc-folders", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_doc_folders(cid: str, parent_id: Optional[str] = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db), engine: DocumentEngine = Depends(_get_engine)):
    _require_company(db, cid, user["tenant_id"])
    if parent_id:
        _require_folder(db, parent_id, user["tenant_id"])
    return {"status": "success", "data": engine.list_folders(cid, tenant_id=user["tenant_id"], parent_id=parent_id)}


@router.post("/companies/{cid}/doc-folders", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_doc_folder(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db), engine: DocumentEngine = Depends(_get_engine)):
    tenant_id = user["tenant_id"]
    _require_company(db, cid, tenant_id)
    name = body.get("name")
    if not name:
        raise _err(400, "MISSING", "name is required")
    parent_id = body.get("parent_id")
    if parent_id:
        _require_folder(db, parent_id, tenant_id)
        parent_company = db.execute(text("SELECT company_id FROM dbp_doc_folders WHERE id=:fid AND tenant_id=:tid"), {"fid": parent_id, "tid": tenant_id}).scalar()
        if parent_company != cid:
            raise _err(400, "INVALID_PARENT", "Parent folder belongs to another company")
    fid = engine.create_folder(tenant_id, cid, name, parent_id, user.get("id") or user.get("user_id"))
    db.commit()
    return {"status": "success", "data": {"id": fid, "name": name}}


@router.delete("/doc-folders/{fid}", dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def delete_doc_folder(fid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db), engine: DocumentEngine = Depends(_get_engine)):
    _require_folder(db, fid, user["tenant_id"])
    result = engine.delete_folder(fid, tenant_id=user["tenant_id"])
    if not result.get("success"):
        raise _err(404 if result.get("code") == "NOT_FOUND" else 400, result.get("code", "CONFLICT"), result.get("error", "Folder operation failed"))
    db.commit()
    return {"status": "success", "message": "Folder deleted"}


@router.get("/companies/{cid}/documents", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_documents(cid: str, folder_id: Optional[str] = None, doc_type: Optional[str] = None, search: Optional[str] = None, tag: Optional[str] = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db), engine: DocumentEngine = Depends(_get_engine)):
    tenant_id = user["tenant_id"]
    _require_company(db, cid, tenant_id)
    if folder_id:
        _require_folder(db, folder_id, tenant_id)
    return {"status": "success", "data": engine.list_documents(cid, tenant_id=tenant_id, folder_id=folder_id, doc_type=doc_type, search=search, tag=tag)}


@router.post("/companies/{cid}/documents", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_document(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db), engine: DocumentEngine = Depends(_get_engine)):
    tenant_id = user["tenant_id"]
    _require_company(db, cid, tenant_id)
    title = body.get("title")
    if not title:
        raise _err(400, "MISSING", "title is required")
    folder_id = body.get("folder_id")
    if folder_id:
        _require_folder(db, folder_id, tenant_id)
        if db.execute(text("SELECT company_id FROM dbp_doc_folders WHERE id=:fid AND tenant_id=:tid"), {"fid": folder_id, "tid": tenant_id}).scalar() != cid:
            raise _err(400, "INVALID_FOLDER", "Folder belongs to another company")
    did = engine.create_document(tenant_id, cid, title, folder_id=folder_id, description=body.get("description"), doc_type=body.get("doc_type"), file_name=body.get("file_name"), file_size=body.get("file_size"), mime_type=body.get("mime_type"), reference_type=body.get("reference_type"), reference_id=body.get("reference_id"), access_level=body.get("access_level", "private"), created_by=user.get("id") or user.get("user_id"))
    db.commit()
    return {"status": "success", "data": {"id": did, "title": title}}


@router.get("/documents/{did}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_document(did: str, user: dict = Depends(get_current_user), engine: DocumentEngine = Depends(_get_engine)):
    doc = engine.get_document(did, tenant_id=user["tenant_id"])
    if not doc:
        raise _err(404, "NOT_FOUND", "Document not found")
    return {"status": "success", "data": doc}


@router.put("/documents/{did}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_document(did: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db), engine: DocumentEngine = Depends(_get_engine)):
    tenant_id = user["tenant_id"]
    _require_document(db, did, tenant_id)
    if body.get("folder_id"):
        _require_folder(db, body["folder_id"], tenant_id)
        doc_company = db.execute(text("SELECT company_id FROM dbp_documents WHERE id=:did AND tenant_id=:tid"), {"did": did, "tid": tenant_id}).scalar()
        folder_company = db.execute(text("SELECT company_id FROM dbp_doc_folders WHERE id=:fid AND tenant_id=:tid"), {"fid": body["folder_id"], "tid": tenant_id}).scalar()
        if doc_company != folder_company:
            raise _err(400, "INVALID_FOLDER", "Folder belongs to another company")
    updates = {k: body[k] for k in ("title", "description", "folder_id", "doc_type", "access_level", "status") if k in body}
    if not updates:
        raise _err(400, "NO_FIELDS", "No valid fields to update")
    result = engine.update_document(did, tenant_id=tenant_id, updated_by=user.get("id") or user.get("user_id"), **updates)
    if not result.get("success"):
        raise _err(404, "NOT_FOUND", result.get("error", "Document not found"))
    db.commit()
    return {"status": "success", "message": "Document updated"}


@router.delete("/documents/{did}", dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def delete_document(did: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db), engine: DocumentEngine = Depends(_get_engine)):
    _require_document(db, did, user["tenant_id"])
    result = engine.delete_document(did, tenant_id=user["tenant_id"])
    if not result.get("success"):
        raise _err(404, "NOT_FOUND", result.get("error", "Document not found"))
    db.commit()
    return {"status": "success", "message": "Document deleted"}


@router.get("/documents/{did}/versions", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_versions(did: str, user: dict = Depends(get_current_user), engine: DocumentEngine = Depends(_get_engine)):
    if not engine.get_document(did, tenant_id=user["tenant_id"]):
        raise _err(404, "NOT_FOUND", "Document not found")
    return {"status": "success", "data": engine.get_versions(did, tenant_id=user["tenant_id"])}


@router.post("/documents/{did}/versions", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def add_version(did: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db), engine: DocumentEngine = Depends(_get_engine)):
    if not engine.get_document(did, tenant_id=user["tenant_id"]):
        raise _err(404, "NOT_FOUND", "Document not found")
    file_name = body.get("file_name")
    if not file_name:
        raise _err(400, "MISSING", "file_name is required")
    vid = engine.add_version(did, file_name=file_name, file_size=body.get("file_size"), change_notes=body.get("change_notes"), uploaded_by=user.get("id") or user.get("user_id"), tenant_id=user["tenant_id"])
    db.commit()
    return {"status": "success", "data": {"id": vid, "document_id": did, "file_name": file_name}}


@router.post("/documents/{did}/tags", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def add_tag(did: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db), engine: DocumentEngine = Depends(_get_engine)):
    if not engine.get_document(did, tenant_id=user["tenant_id"]):
        raise _err(404, "NOT_FOUND", "Document not found")
    tag = str(body.get("tag", "")).strip()
    if not tag:
        raise _err(400, "MISSING", "tag is required")
    engine.add_tag(did, tag, tenant_id=user["tenant_id"])
    db.commit()
    return {"status": "success", "data": {"document_id": did, "tag": tag}}


@router.delete("/documents/{did}/tags/{tag}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def remove_tag(did: str, tag: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db), engine: DocumentEngine = Depends(_get_engine)):
    if not engine.get_document(did, tenant_id=user["tenant_id"]):
        raise _err(404, "NOT_FOUND", "Document not found")
    result = engine.remove_tag(did, tag, tenant_id=user["tenant_id"])
    if not result.get("success"):
        raise _err(404, "TAG_NOT_FOUND", result.get("error", "Tag not found on document"))
    db.commit()
    return {"status": "success", "message": f"Tag '{tag}' removed"}
