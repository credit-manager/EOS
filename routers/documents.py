"""
P30 Document Management Router — folders, documents, versions, tags
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from core.auth import get_current_user, require_permission
from core.rate_limit import read_limiter, write_limiter
from core.document_engine import DocumentEngine


router = APIRouter(
    prefix="/api/v1/dynamic",
    tags=["Document Management"]
)


def _err(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={
        "status": "error",
        "error": {"code": code, "message": message},
    })


def _get_engine(db: Session = Depends(get_db)) -> DocumentEngine:
    return DocumentEngine(db)


# ──────────────────────────────────────────────────────────────
# FOLDERS
# ──────────────────────────────────────────────────────────────

@router.get(
    "/companies/{cid}/doc-folders",
    dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)],
)
async def list_doc_folders(
    cid: str,
    parent_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
    engine: DocumentEngine = Depends(_get_engine),
):
    """List document folders for a company (optionally by parent)."""
    tenant_id = user.get("tenant_id")
    folders = engine.list_folders(cid, tenant_id=tenant_id, parent_id=parent_id)
    return {"status": "success", "data": folders}


@router.post(
    "/companies/{cid}/doc-folders",
    dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)],
)
async def create_doc_folder(
    cid: str,
    body: dict,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    engine: DocumentEngine = Depends(_get_engine),
):
    """Create a document folder."""
    tenant_id = user.get("tenant_id")
    name = body.get("name")
    if not name:
        raise _err(400, "MISSING", "name is required")

    parent_id = body.get("parent_id")
    if parent_id:
        parent = [f for f in engine.list_folders(cid, tenant_id=tenant_id)
                  if f["id"] == parent_id]
        if not parent:
            raise _err(404, "NOT_FOUND", "Parent folder not found")

    fid = engine.create_folder(
        tenant_id=tenant_id, company_id=cid, name=name,
        parent_id=parent_id,
        created_by=user.get("id") or user.get("user_id"),
    )
    db.commit()
    return {"status": "success", "data": {"id": fid, "name": name}}


@router.delete(
    "/doc-folders/{fid}",
    dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)],
)
async def delete_doc_folder(
    fid: str,
    db: Session = Depends(get_db),
    engine: DocumentEngine = Depends(_get_engine),
):
    """Delete a folder (only when empty of documents)."""
    result = engine.delete_folder(fid)
    if not result.get("success"):
        if result.get("code") == "NOT_FOUND":
            raise _err(404, "NOT_FOUND", result["error"])
        raise _err(400, result.get("code", "CONFLICT"), result["error"])
    db.commit()
    return {"status": "success", "message": "Folder deleted"}


# ──────────────────────────────────────────────────────────────
# DOCUMENTS
# ──────────────────────────────────────────────────────────────

@router.get(
    "/companies/{cid}/documents",
    dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)],
)
async def list_documents(
    cid: str,
    folder_id: Optional[str] = None,
    doc_type: Optional[str] = None,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    user: dict = Depends(get_current_user),
    engine: DocumentEngine = Depends(_get_engine),
):
    """List documents with optional filters and title/description search."""
    tenant_id = user.get("tenant_id")
    docs = engine.list_documents(
        cid, tenant_id=tenant_id, folder_id=folder_id,
        doc_type=doc_type, search=search, tag=tag,
    )
    return {"status": "success", "data": docs}


@router.post(
    "/companies/{cid}/documents",
    dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)],
)
async def create_document(
    cid: str,
    body: dict,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    engine: DocumentEngine = Depends(_get_engine),
):
    """Create a document (auto-creates version 1)."""
    tenant_id = user.get("tenant_id")
    title = body.get("title")
    if not title:
        raise _err(400, "MISSING", "title is required")

    folder_id = body.get("folder_id")
    if folder_id:
        folder = [f for f in engine.list_folders(cid, tenant_id=tenant_id)
                  if f["id"] == folder_id]
        if not folder:
            raise _err(404, "NOT_FOUND", "Folder not found")

    did = engine.create_document(
        tenant_id=tenant_id, company_id=cid, title=title,
        folder_id=folder_id,
        description=body.get("description"),
        doc_type=body.get("doc_type"),
        file_name=body.get("file_name"),
        file_size=body.get("file_size"),
        mime_type=body.get("mime_type"),
        reference_type=body.get("reference_type"),
        reference_id=body.get("reference_id"),
        access_level=body.get("access_level", "private"),
        created_by=user.get("id") or user.get("user_id"),
    )
    db.commit()
    return {"status": "success", "data": {"id": did, "title": title}}


@router.get(
    "/documents/{did}",
    dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)],
)
async def get_document(
    did: str,
    user: dict = Depends(get_current_user),
    engine: DocumentEngine = Depends(_get_engine),
):
    """Get a single document with tags and latest version."""
    doc = engine.get_document(did, tenant_id=user.get("tenant_id"))
    if not doc:
        raise _err(404, "NOT_FOUND", "Document not found")
    return {"status": "success", "data": doc}


@router.put(
    "/documents/{did}",
    dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)],
)
async def update_document(
    did: str,
    body: dict,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    engine: DocumentEngine = Depends(_get_engine),
):
    """Update document metadata."""
    updates = {k: body[k] for k in ("title", "description", "folder_id",
                                    "doc_type", "access_level", "status")
               if k in body}
    if not updates:
        raise _err(400, "NO_FIELDS", "No valid fields to update")

    result = engine.update_document(
        did, updated_by=user.get("id") or user.get("user_id"), **updates)
    if not result.get("success"):
        raise _err(404, "NOT_FOUND", result.get("error", "Document not found"))
    db.commit()
    return {"status": "success", "message": "Document updated"}


@router.delete(
    "/documents/{did}",
    dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)],
)
async def delete_document(
    did: str,
    db: Session = Depends(get_db),
    engine: DocumentEngine = Depends(_get_engine),
):
    """Delete a document with its versions and tags."""
    result = engine.delete_document(did)
    if not result.get("success"):
        raise _err(404, "NOT_FOUND", result.get("error", "Document not found"))
    db.commit()
    return {"status": "success", "message": "Document deleted"}


# ──────────────────────────────────────────────────────────────
# VERSIONS
# ──────────────────────────────────────────────────────────────

@router.get(
    "/documents/{did}/versions",
    dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)],
)
async def list_versions(
    did: str,
    user: dict = Depends(get_current_user),
    engine: DocumentEngine = Depends(_get_engine),
):
    """List version history of a document."""
    doc = engine.get_document(did, tenant_id=user.get("tenant_id"))
    if not doc:
        raise _err(404, "NOT_FOUND", "Document not found")
    versions = engine.get_versions(did)
    return {"status": "success", "data": versions}


@router.post(
    "/documents/{did}/versions",
    dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)],
)
async def add_version(
    did: str,
    body: dict,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    engine: DocumentEngine = Depends(_get_engine),
):
    """Add a new version to a document."""
    file_name = body.get("file_name")
    if not file_name:
        raise _err(400, "MISSING", "file_name is required")

    doc = engine.get_document(did, tenant_id=user.get("tenant_id"))
    if not doc:
        raise _err(404, "NOT_FOUND", "Document not found")

    vid = engine.add_version(
        did, file_name=file_name, file_size=body.get("file_size"),
        change_notes=body.get("change_notes"),
        uploaded_by=user.get("id") or user.get("user_id"),
    )
    db.commit()
    return {"status": "success", "data": {"id": vid, "document_id": did,
                                          "file_name": file_name}}


# ──────────────────────────────────────────────────────────────
# TAGS
# ──────────────────────────────────────────────────────────────

@router.post(
    "/documents/{did}/tags",
    dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)],
)
async def add_tag(
    did: str,
    body: dict,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    engine: DocumentEngine = Depends(_get_engine),
):
    """Add a tag to a document (duplicates ignored)."""
    tag = body.get("tag")
    if not tag or not str(tag).strip():
        raise _err(400, "MISSING", "tag is required")

    doc = engine.get_document(did, tenant_id=user.get("tenant_id"))
    if not doc:
        raise _err(404, "NOT_FOUND", "Document not found")

    engine.add_tag(did, str(tag).strip())
    db.commit()
    return {"status": "success", "data": {"document_id": did, "tag": str(tag).strip()}}


@router.delete(
    "/documents/{did}/tags/{tag}",
    dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)],
)
async def remove_tag(
    did: str,
    tag: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    engine: DocumentEngine = Depends(_get_engine),
):
    """Remove a tag from a document."""
    doc = engine.get_document(did, tenant_id=user.get("tenant_id"))
    if not doc:
        raise _err(404, "NOT_FOUND", "Document not found")

    result = engine.remove_tag(did, tag)
    if not result.get("success"):
        raise _err(404, "TAG_NOT_FOUND", result.get("error", "Tag not found on document"))
    db.commit()
    return {"status": "success", "message": f"Tag '{tag}' removed"}
