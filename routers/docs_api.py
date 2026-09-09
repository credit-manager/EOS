"""
P71.3 Universal Document Manager — API
========================================
File metadata, folders, versions, cross-module linking.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from database import get_db
from sqlalchemy import text
from core.auth import get_current_user
from core.industry_security import (
    now, uid, check_permission, audit_log,
    success_response, list_response,
)

router = APIRouter(prefix="/docs", tags=["Document Manager"])


# ═══════════════════════════════════════════════════
# FOLDERS
# ═══════════════════════════════════════════════════

class FolderCreate(BaseModel):
    folder_name: str
    parent_id: Optional[str] = None
    description: Optional[str] = None
    source_module: Optional[str] = None

@router.post("/folders")
def create_folder(body: FolderCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    if body.parent_id:
        parent = db.execute(text("SELECT id FROM dbp_doc_folders WHERE id=:pid AND tenant_id=:t"),
                            {"pid": body.parent_id, "t": t}).fetchone()
        if not parent:
            raise HTTPException(400, detail="Parent folder not found")
    fid = uid()
    db.execute(text("INSERT INTO dbp_doc_folders (id,tenant_id,parent_id,folder_name,description,source_module,created_by) "
                    "VALUES (:id,:t,:pid,:fn,:d,:sm,:cb)"),
               {"id": fid, "t": t, "pid": body.parent_id, "fn": body.folder_name,
                "d": body.description, "sm": body.source_module, "cb": user["id"]})
    _log_doc(db, t, None, "folder_created", user["id"], f"Folder: {body.folder_name}")
    db.commit()
    return success_response("Folder created", {"id": fid})

@router.get("/folders")
def list_folders(parent_id: Optional[str] = None, source_module: Optional[str] = None,
                 user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t"
    params: Dict[str, Any] = {"t": t}
    if parent_id:
        where += " AND parent_id=:pid"
        params["pid"] = parent_id
    else:
        where += " AND parent_id IS NULL"
    if source_module:
        where += " AND source_module=:sm"
        params["sm"] = source_module
    rows = db.execute(text(
        f"SELECT id,folder_name,parent_id,description,source_module,created_by,created_at "
        f"FROM dbp_doc_folders {where} ORDER BY folder_name"), params).fetchall()
    data = [{"id": r[0], "folder_name": r[1], "parent_id": r[2], "description": r[3],
             "source_module": r[4], "created_by": r[5],
             "created_at": str(r[6]) if r[6] else None} for r in rows]
    return list_response(data, len(data))

@router.get("/folders/{folder_id}")
def get_folder(folder_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    r = db.execute(text(
        "SELECT id,folder_name,parent_id,description,source_module,created_by,created_at "
        "FROM dbp_doc_folders WHERE id=:id AND tenant_id=:t"), {"id": folder_id, "t": t}).fetchone()
    if not r:
        raise HTTPException(404, detail="Folder not found")
    file_count = db.execute(text("SELECT COUNT(*) FROM dbp_doc_files WHERE folder_id=:fid AND tenant_id=:t AND is_archived=FALSE"),
                            {"fid": folder_id, "t": t}).fetchone()[0] or 0
    sub_count = db.execute(text("SELECT COUNT(*) FROM dbp_doc_folders WHERE parent_id=:fid AND tenant_id=:t"),
                           {"fid": folder_id, "t": t}).fetchone()[0] or 0
    return success_response("Folder details", {
        "id": r[0], "folder_name": r[1], "parent_id": r[2], "description": r[3],
        "source_module": r[4], "created_by": r[5],
        "created_at": str(r[6]) if r[6] else None,
        "file_count": file_count, "subfolder_count": sub_count
    })

@router.delete("/folders/{folder_id}")
def delete_folder(folder_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "delete")
    t = user["tenant_id"]
    f = db.execute(text("SELECT id FROM dbp_doc_folders WHERE id=:id AND tenant_id=:t"),
                   {"id": folder_id, "t": t}).fetchone()
    if not f:
        raise HTTPException(404, detail="Folder not found")
    sub = db.execute(text("SELECT COUNT(*) FROM dbp_doc_folders WHERE parent_id=:fid AND tenant_id=:t"),
                     {"fid": folder_id, "t": t}).fetchone()[0] or 0
    if sub > 0:
        raise HTTPException(400, detail="Cannot delete folder with subfolders")
    files = db.execute(text("SELECT COUNT(*) FROM dbp_doc_files WHERE folder_id=:fid AND tenant_id=:t AND is_archived=FALSE"),
                       {"fid": folder_id, "t": t}).fetchone()[0] or 0
    if files > 0:
        raise HTTPException(400, detail="Cannot delete folder with files")
    db.execute(text("DELETE FROM dbp_doc_folders WHERE id=:id"), {"id": folder_id})
    _log_doc(db, t, None, "folder_deleted", user["id"], f"Deleted folder {folder_id}")
    db.commit()
    return success_response("Folder deleted", {"id": folder_id})


# ═══════════════════════════════════════════════════
# FILES
# ═══════════════════════════════════════════════════

class FileUpload(BaseModel):
    file_name: str
    folder_id: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: int = 0
    storage_path: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    source_module: Optional[str] = None
    source_id: Optional[str] = None

@router.post("/files")
def upload_file(body: FileUpload, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    if body.folder_id:
        folder = db.execute(text("SELECT id FROM dbp_doc_folders WHERE id=:fid AND tenant_id=:t"),
                            {"fid": body.folder_id, "t": t}).fetchone()
        if not folder:
            raise HTTPException(400, detail="Folder not found")
    fid = uid()
    db.execute(text("INSERT INTO dbp_doc_files "
                    "(id,tenant_id,folder_id,file_name,original_name,mime_type,file_size,storage_path,description,tags,source_module,source_id,uploaded_by) "
                    "VALUES (:id,:t,:fi,:fn,:on,:mt,:fs,:sp,:d,:tg,:sm,:si,:ub)"),
               {"id": fid, "t": t, "fi": body.folder_id, "fn": body.file_name,
                "on": body.file_name, "mt": body.mime_type, "fs": body.file_size,
                "sp": body.storage_path, "d": body.description, "tg": body.tags,
                "sm": body.source_module, "si": body.source_id, "ub": user["id"]})
    vid = uid()
    db.execute(text("INSERT INTO dbp_doc_versions "
                    "(id,tenant_id,file_id,version_number,file_name,storage_path,file_size,uploaded_by,change_notes) "
                    "VALUES (:id,:t,:fi,:vn,:fn,:sp,:fs,:ub,:cn)"),
               {"id": vid, "t": t, "fi": fid, "vn": 1, "fn": body.file_name,
                "sp": body.storage_path, "fs": body.file_size, "ub": user["id"], "cn": "Initial upload"})
    _log_doc(db, t, fid, "file_uploaded", user["id"], f"File: {body.file_name}")
    audit_log(db, t, user["id"], "create", "doc_file", fid, new_values={"file_name": body.file_name})
    db.commit()
    return success_response("File uploaded", {"id": fid, "version": 1})

@router.post("/upload")
async def upload_actual_file(
    file: UploadFile = File(...),
    folder_id: Optional[str] = None,
    description: Optional[str] = None,
    source_module: Optional[str] = None,
    source_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    check_permission(user, "create")
    t = user["tenant_id"]

    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads", t)
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = file.filename.replace("/", "_").replace("\\", "_")
    stored_name = f"{uid()}_{safe_name}"
    file_path = os.path.join(upload_dir, stored_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    file_size = len(content)
    mime_type = file.content_type or "application/octet-stream"

    fid = uid()
    db.execute(text(
        "INSERT INTO dbp_doc_files "
        "(id,tenant_id,folder_id,file_name,original_name,mime_type,file_size,storage_path,description,tags,source_module,source_id,uploaded_by) "
        "VALUES (:id,:t,:fi,:fn,:on,:mt,:fs,:sp,:d,:tg,:sm,:si,:ub)"),
        {"id": fid, "t": t, "fi": folder_id, "fn": safe_name,
         "on": file.filename, "mt": mime_type, "fs": file_size,
         "sp": file_path, "d": description, "tg": None,
         "sm": source_module, "si": source_id, "ub": user["id"]})

    vid = uid()
    db.execute(text(
        "INSERT INTO dbp_doc_versions "
        "(id,tenant_id,file_id,version_number,file_name,storage_path,file_size,uploaded_by,change_notes) "
        "VALUES (:id,:t,:fi,:vn,:fn,:sp,:fs,:ub,:cn)"),
        {"id": vid, "t": t, "fi": fid, "vn": 1, "fn": safe_name,
         "sp": file_path, "fs": file_size, "ub": user["id"], "cn": "Initial upload"})

    _log_doc(db, t, fid, "file_uploaded", user["id"], f"File: {file.filename}")
    audit_log(db, t, user["id"], "create", "doc_file", fid, new_values={"file_name": file.filename})

    db.commit()
    return success_response("File uploaded successfully", {
        "id": fid, "file_name": file.filename, "size": file_size,
        "mime_type": mime_type, "version": 1
    })

@router.get("/files")
def list_files(folder_id: Optional[str] = None, source_module: Optional[str] = None,
               source_id: Optional[str] = None, tags: Optional[str] = None,
               search: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t AND is_archived=FALSE"
    params: Dict[str, Any] = {"t": t}
    if folder_id:
        where += " AND folder_id=:fi"
        params["fi"] = folder_id
    if source_module:
        where += " AND source_module=:sm"
        params["sm"] = source_module
    if source_id:
        where += " AND source_id=:si"
        params["si"] = source_id
    if tags:
        where += " AND tags LIKE :tg"
        params["tg"] = f"%{tags}%"
    if search:
        where += " AND (file_name LIKE :s OR description LIKE :s)"
        params["s"] = f"%{search}%"
    rows = db.execute(text(
        f"SELECT id,file_name,mime_type,file_size,folder_id,source_module,source_id,description,tags,uploaded_by,created_at "
        f"FROM dbp_doc_files {where} ORDER BY created_at DESC LIMIT 100"), params).fetchall()
    data = [{"id": r[0], "file_name": r[1], "mime_type": r[2], "file_size": r[3],
             "folder_id": r[4], "source_module": r[5], "source_id": r[6],
             "description": r[7], "tags": r[8], "uploaded_by": r[9],
             "created_at": str(r[10]) if r[10] else None} for r in rows]
    return list_response(data, len(data))

@router.get("/files/{file_id}")
def get_file(file_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    r = db.execute(text(
        "SELECT id,folder_id,file_name,original_name,mime_type,file_size,storage_path,"
        "description,tags,source_module,source_id,uploaded_by,is_archived,created_at "
        "FROM dbp_doc_files WHERE id=:id AND tenant_id=:t"), {"id": file_id, "t": t}).fetchone()
    if not r:
        raise HTTPException(404, detail="File not found")
    versions = db.execute(text(
        "SELECT version_number,file_name,uploaded_by,change_notes,created_at "
        "FROM dbp_doc_versions WHERE file_id=:fid AND tenant_id=:t ORDER BY version_number DESC"),
        {"fid": file_id, "t": t}).fetchall()
    shares = db.execute(text(
        "SELECT shared_with_type,shared_with_value,permission,shared_by,created_at "
        "FROM dbp_doc_shares WHERE file_id=:fid AND tenant_id=:t"),
        {"fid": file_id, "t": t}).fetchall()
    return success_response("File details", {
        "id": r[0], "folder_id": r[1], "file_name": r[2], "original_name": r[3],
        "mime_type": r[4], "file_size": r[5], "storage_path": r[6],
        "description": r[7], "tags": r[8], "source_module": r[9], "source_id": r[10],
        "uploaded_by": r[11], "is_archived": r[12],
        "created_at": str(r[13]) if r[13] else None,
        "versions": [{"version": v[0], "file_name": v[1], "uploaded_by": v[2],
                      "change_notes": v[3], "created_at": str(v[4]) if v[4] else None} for v in versions],
        "shares": [{"type": s[0], "value": s[1], "permission": s[2],
                    "shared_by": s[3], "created_at": str(s[4]) if s[4] else None} for s in shares],
    })

@router.put("/files/{file_id}/archive")
def archive_file(file_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    r = db.execute(text("SELECT is_archived FROM dbp_doc_files WHERE id=:id AND tenant_id=:t"),
                   {"id": file_id, "t": t}).fetchone()
    if not r:
        raise HTTPException(404, detail="File not found")
    new_val = not r[0]
    db.execute(text("UPDATE dbp_doc_files SET is_archived=:v, updated_at=NOW() WHERE id=:id"),
               {"v": new_val, "id": file_id})
    action = "file_archived" if new_val else "file_unarchived"
    _log_doc(db, t, file_id, action, user["id"], f"Archived: {new_val}")
    db.commit()
    return success_response("File archive toggled", {"is_archived": new_val})

@router.delete("/files/{file_id}")
def delete_file(file_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "delete")
    t = user["tenant_id"]
    f = db.execute(text("SELECT id FROM dbp_doc_files WHERE id=:id AND tenant_id=:t"),
                   {"id": file_id, "t": t}).fetchone()
    if not f:
        raise HTTPException(404, detail="File not found")
    db.execute(text("DELETE FROM dbp_doc_versions WHERE file_id=:fid"), {"fid": file_id})
    db.execute(text("DELETE FROM dbp_doc_shares WHERE file_id=:fid"), {"fid": file_id})
    db.execute(text("DELETE FROM dbp_doc_files WHERE id=:id"), {"id": file_id})
    _log_doc(db, t, file_id, "file_deleted", user["id"], f"Deleted file {file_id}")
    audit_log(db, t, user["id"], "delete", "doc_file", file_id)
    db.commit()
    return success_response("File deleted", {"id": file_id})


# ═══════════════════════════════════════════════════
# VERSIONS
# ═══════════════════════════════════════════════════

class VersionUpload(BaseModel):
    file_name: str
    storage_path: Optional[str] = None
    file_size: int = 0
    change_notes: Optional[str] = None

@router.post("/files/{file_id}/versions")
def upload_version(file_id: str, body: VersionUpload, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    f = db.execute(text("SELECT id FROM dbp_doc_files WHERE id=:id AND tenant_id=:t"),
                   {"id": file_id, "t": t}).fetchone()
    if not f:
        raise HTTPException(404, detail="File not found")
    last = db.execute(text("SELECT MAX(version_number) FROM dbp_doc_versions WHERE file_id=:fid"),
                      {"fid": file_id}).fetchone()[0] or 0
    new_ver = last + 1
    vid = uid()
    db.execute(text("INSERT INTO dbp_doc_versions "
                    "(id,tenant_id,file_id,version_number,file_name,storage_path,file_size,uploaded_by,change_notes) "
                    "VALUES (:id,:t,:fi,:vn,:fn,:sp,:fs,:ub,:cn)"),
               {"id": vid, "t": t, "fi": file_id, "vn": new_ver, "fn": body.file_name,
                "sp": body.storage_path, "fs": body.file_size, "ub": user["id"], "cn": body.change_notes})
    db.execute(text("UPDATE dbp_doc_files SET file_name=:fn, storage_path=:sp, file_size=:fs, updated_at=NOW() WHERE id=:fid"),
               {"fn": body.file_name, "sp": body.storage_path, "fs": body.file_size, "fid": file_id})
    _log_doc(db, t, file_id, "version_uploaded", user["id"], f"Version {new_ver}: {body.file_name}")
    db.commit()
    return success_response("Version uploaded", {"version": new_ver})


# ═══════════════════════════════════════════════════
# SHARES
# ═══════════════════════════════════════════════════

class ShareCreate(BaseModel):
    shared_with_type: str = "user"
    shared_with_value: str
    permission: str = "view"

@router.post("/files/{file_id}/shares")
def share_file(file_id: str, body: ShareCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    f = db.execute(text("SELECT id FROM dbp_doc_files WHERE id=:id AND tenant_id=:t"),
                   {"id": file_id, "t": t}).fetchone()
    if not f:
        raise HTTPException(404, detail="File not found")
    if body.shared_with_type not in ("user", "role", "group", "all"):
        raise HTTPException(400, detail="Invalid shared_with_type")
    if body.permission not in ("view", "edit", "admin"):
        raise HTTPException(400, detail="Invalid permission")
    sid = uid()
    db.execute(text("INSERT INTO dbp_doc_shares "
                    "(id,tenant_id,file_id,shared_with_type,shared_with_value,permission,shared_by) "
                    "VALUES (:id,:t,:fi,:swt,:swv,:p,:sb)"),
               {"id": sid, "t": t, "fi": file_id, "swt": body.shared_with_type,
                "swv": body.shared_with_value, "p": body.permission, "sb": user["id"]})
    _log_doc(db, t, file_id, "file_shared", user["id"],
             f"Shared with {body.shared_with_type}:{body.shared_with_value} ({body.permission})")
    db.commit()
    return success_response("File shared", {"id": sid})

@router.delete("/files/{file_id}/shares/{share_id}")
def revoke_share(file_id: str, share_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    db.execute(text("DELETE FROM dbp_doc_shares WHERE id=:id AND file_id=:fi AND tenant_id=:t"),
               {"id": share_id, "fi": file_id, "t": t})
    _log_doc(db, t, file_id, "share_revoked", user["id"], f"Revoked share {share_id}")
    db.commit()
    return success_response("Share revoked", {"id": share_id})


# ═══════════════════════════════════════════════════
# SEARCH
# ═══════════════════════════════════════════════════

@router.get("/search")
def search_files(q: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text(
        "SELECT id,file_name,mime_type,file_size,source_module,source_id,created_at "
        "FROM dbp_doc_files WHERE tenant_id=:t AND is_archived=FALSE "
        "AND (file_name LIKE :q OR description LIKE :q OR tags LIKE :q) "
        "ORDER BY created_at DESC LIMIT 50"),
        {"t": t, "q": f"%{q}%"}).fetchall()
    data = [{"id": r[0], "file_name": r[1], "mime_type": r[2], "file_size": r[3],
             "source_module": r[4], "source_id": r[5],
             "created_at": str(r[6]) if r[6] else None} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════

@router.get("/stats")
def doc_stats(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    folders = db.execute(text("SELECT COUNT(*) FROM dbp_doc_folders WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
    files = db.execute(text("SELECT COUNT(*) FROM dbp_doc_files WHERE tenant_id=:t AND is_archived=FALSE"), {"t": t}).fetchone()[0] or 0
    archived = db.execute(text("SELECT COUNT(*) FROM dbp_doc_files WHERE tenant_id=:t AND is_archived=TRUE"), {"t": t}).fetchone()[0] or 0
    total_size = db.execute(text("SELECT COALESCE(SUM(file_size),0) FROM dbp_doc_files WHERE tenant_id=:t AND is_archived=FALSE"), {"t": t}).fetchone()[0] or 0
    shares = db.execute(text("SELECT COUNT(*) FROM dbp_doc_shares WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
    return success_response("Document stats", {
        "folders": folders, "files": files, "archived": archived,
        "total_size_bytes": total_size, "shares": shares
    })


# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════

def _log_doc(db, tenant_id, file_id, action, actor_id, details):
    lid = uid()
    db.execute(text("INSERT INTO dbp_doc_log (id,tenant_id,file_id,action,actor_id,details) "
                    "VALUES (:id,:t,:fi,:a,:ai,:d)"),
               {"id": lid, "t": tenant_id, "fi": file_id, "a": action, "ai": actor_id, "d": details})
