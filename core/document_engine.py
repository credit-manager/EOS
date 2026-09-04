"""P30 Document Management Engine — tenant-safe document operations."""
import uuid
from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session


def _iso(value):
    return value.isoformat() if value is not None else None


class DocumentEngine:
    def __init__(self, db: Session):
        self.db = db

    def create_folder(self, tenant_id: str, company_id: str, name: str, parent_id: str | None = None, created_by: str | None = None) -> str:
        fid = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO dbp_doc_folders (id,tenant_id,company_id,name,parent_id,created_by) VALUES (:id,:tid,:cid,:name,:pid,:cb)"), {"id":fid,"tid":tenant_id,"cid":company_id,"name":name,"pid":parent_id,"cb":created_by})
        self.db.flush(); return fid

    def list_folders(self, company_id: str, tenant_id: str | None = None, parent_id: str | None = None) -> list[dict]:
        conditions=["company_id=:cid"]; params={"cid":company_id}
        if tenant_id: conditions.append("tenant_id=:tid"); params["tid"]=tenant_id
        if parent_id is not None: conditions.append("parent_id=:pid"); params["pid"]=parent_id
        rows=self.db.execute(text(f"SELECT id,name,parent_id,description,created_by,created_at FROM dbp_doc_folders WHERE {' AND '.join(conditions)} ORDER BY created_at"),params).fetchall()
        return [{"id":r[0],"name":r[1],"parent_id":r[2],"description":r[3],"created_by":r[4],"created_at":_iso(r[5])} for r in rows]

    def delete_folder(self, folder_id: str, tenant_id: str | None = None) -> dict[str, Any]:
        params={"fid":folder_id}; scope=""
        if tenant_id: scope=" AND tenant_id=:tid"; params["tid"]=tenant_id
        if not self.db.execute(text(f"SELECT id FROM dbp_doc_folders WHERE id=:fid{scope}"),params).fetchone(): return {"success":False,"code":"NOT_FOUND","error":"Folder not found"}
        if (self.db.execute(text(f"SELECT COUNT(*) FROM dbp_documents WHERE folder_id=:fid AND tenant_id=:tid"),{"fid":folder_id,"tid":tenant_id}).scalar() or 0)>0: return {"success":False,"code":"FOLDER_NOT_EMPTY","error":"Cannot delete folder containing documents"}
        if (self.db.execute(text(f"SELECT COUNT(*) FROM dbp_doc_folders WHERE parent_id=:fid AND tenant_id=:tid"),{"fid":folder_id,"tid":tenant_id}).scalar() or 0)>0: return {"success":False,"code":"HAS_SUBFOLDERS","error":"Cannot delete folder containing subfolders"}
        self.db.execute(text(f"DELETE FROM dbp_doc_folders WHERE id=:fid{scope}"),params); self.db.flush(); return {"success":True}

    def create_document(self, tenant_id: str, company_id: str, title: str, **kw) -> str:
        did=str(uuid.uuid4()); file_size=kw.get("file_size",0); created_by=kw.get("created_by")
        self.db.execute(text("INSERT INTO dbp_documents (id,tenant_id,company_id,folder_id,title,description,doc_type,file_name,file_size,mime_type,reference_type,reference_id,status,access_level,created_by) VALUES (:id,:tid,:cid,:fid,:title,:desc,:dtype,:fname,:fsize,:mime,:rtype,:rid_,'active',:access,:cb)"), {"id":did,"tid":tenant_id,"cid":company_id,"fid":kw.get("folder_id"),"title":title,"desc":kw.get("description"),"dtype":kw.get("doc_type"),"fname":kw.get("file_name"),"fsize":file_size or 0,"mime":kw.get("mime_type"),"rtype":kw.get("reference_type"),"rid_":kw.get("reference_id"),"access":kw.get("access_level","private"),"cb":created_by})
        self.db.execute(text("INSERT INTO dbp_document_versions (id,tenant_id,document_id,version_number,file_name,file_size,change_notes,uploaded_by) VALUES (:id,:tid,:did,1,:fname,:fsize,'Initial version',:cb)"), {"id":str(uuid.uuid4()),"tid":tenant_id,"did":did,"fname":kw.get("file_name"),"fsize":file_size or 0,"cb":created_by})
        self.db.flush(); return did

    def get_document(self, doc_id: str, tenant_id: str | None = None) -> dict | None:
        params={"did":doc_id}; scope=""
        if tenant_id: scope=" AND tenant_id=:tid"; params["tid"]=tenant_id
        row=self.db.execute(text(f"SELECT id,tenant_id,company_id,folder_id,title,description,doc_type,file_name,file_size,mime_type,reference_type,reference_id,status,access_level,created_by,updated_by,created_at,updated_at FROM dbp_documents WHERE id=:did{scope}"),params).fetchone()
        if not row:return None
        tags=[r[0] for r in self.db.execute(text("SELECT tag FROM dbp_document_tags WHERE document_id=:did AND tenant_id=:tid ORDER BY tag"),{"did":doc_id,"tid":row[1]}).fetchall()]
        v=self.db.execute(text("SELECT id,version_number,file_name,file_size,change_notes,uploaded_by,created_at FROM dbp_document_versions WHERE document_id=:did AND tenant_id=:tid ORDER BY version_number DESC LIMIT 1"),{"did":doc_id,"tid":row[1]}).fetchone()
        latest={"id":v[0],"version_number":int(v[1]),"file_name":v[2],"file_size":int(v[3] or 0),"change_notes":v[4],"uploaded_by":v[5],"created_at":_iso(v[6])} if v else None
        return {"id":row[0],"tenant_id":row[1],"company_id":row[2],"folder_id":row[3],"title":row[4],"description":row[5],"doc_type":row[6],"file_name":row[7],"file_size":int(row[8] or 0),"mime_type":row[9],"reference_type":row[10],"reference_id":row[11],"status":row[12],"access_level":row[13],"created_by":row[14],"updated_by":row[15],"created_at":_iso(row[16]),"updated_at":_iso(row[17]),"tags":tags,"latest_version":latest}

    def list_documents(self, company_id: str, tenant_id: str | None = None, folder_id: str | None = None, doc_type: str | None = None, search: str | None = None, tag: str | None = None) -> list[dict]:
        conditions=["company_id=:cid"]; params={"cid":company_id}
        if tenant_id:conditions.append("tenant_id=:tid");params["tid"]=tenant_id
        if folder_id is not None:conditions.append("folder_id=:fid");params["fid"]=folder_id
        if doc_type:conditions.append("doc_type=:dt");params["dt"]=doc_type
        if search:conditions.append("(title ILIKE :search OR description ILIKE :search)");params["search"]=f"%{search}%"
        if tag:conditions.append("id IN (SELECT document_id FROM dbp_document_tags WHERE tag=:tag AND tenant_id=:tid)");params["tag"]=tag
        rows=self.db.execute(text(f"SELECT id,title,description,doc_type,file_name,file_size,folder_id,status,access_level,mime_type,created_at,updated_at FROM dbp_documents WHERE {' AND '.join(conditions)} ORDER BY created_at DESC"),params).fetchall()
        return [{"id":r[0],"title":r[1],"description":r[2],"doc_type":r[3],"file_name":r[4],"file_size":int(r[5] or 0),"folder_id":r[6],"status":r[7],"access_level":r[8],"mime_type":r[9],"created_at":_iso(r[10]),"updated_at":_iso(r[11])} for r in rows]

    def update_document(self, doc_id: str, tenant_id: str | None = None, **kw) -> dict[str, Any]:
        params={"did":doc_id}; scope=""
        if tenant_id:scope=" AND tenant_id=:tid";params["tid"]=tenant_id
        if not self.db.execute(text(f"SELECT id FROM dbp_documents WHERE id=:did{scope}"),params).fetchone():return {"success":False,"error":"Document not found"}
        allowed={"title","description","folder_id","doc_type","access_level","status"}; updates={k:v for k,v in kw.items() if k in allowed}
        if kw.get("updated_by") is not None:updates["updated_by"]=kw["updated_by"]
        if not updates:return {"success":False,"error":"No valid fields to update"}
        set_clause=", ".join(f"{k}=:{k}" for k in updates); params.update(updates)
        self.db.execute(text(f"UPDATE dbp_documents SET {set_clause},updated_at=NOW() WHERE id=:did{scope}"),params);self.db.flush();return {"success":True,"id":doc_id}

    def delete_document(self, doc_id: str, tenant_id: str | None = None) -> dict[str, Any]:
        params={"did":doc_id};scope=""
        if tenant_id:scope=" AND tenant_id=:tid";params["tid"]=tenant_id
        row=self.db.execute(text(f"SELECT id FROM dbp_documents WHERE id=:did{scope}"),params).fetchone()
        if not row:return {"success":False,"error":"Document not found"}
        for table in ("dbp_document_tags","dbp_document_versions"):
            self.db.execute(text(f"DELETE FROM {table} WHERE document_id=:did" + (" AND tenant_id=:tid" if tenant_id else "")),params)
        self.db.execute(text(f"DELETE FROM dbp_documents WHERE id=:did{scope}"),params);self.db.flush();return {"success":True}

    def add_version(self, doc_id: str, file_name: str, file_size: int | None = None, change_notes: str | None = None, uploaded_by: str | None = None, tenant_id: str | None = None) -> str | None:
        params={"did":doc_id};scope=""
        if tenant_id:scope=" AND tenant_id=:tid";params["tid"]=tenant_id
        doc=self.db.execute(text(f"SELECT tenant_id FROM dbp_documents WHERE id=:did{scope}"),params).fetchone()
        if not doc:return None
        tid=doc[0]; max_v=self.db.execute(text("SELECT COALESCE(MAX(version_number),0) FROM dbp_document_versions WHERE document_id=:did AND tenant_id=:tid"),{"did":doc_id,"tid":tid}).scalar() or 0
        vid=str(uuid.uuid4());self.db.execute(text("INSERT INTO dbp_document_versions (id,tenant_id,document_id,version_number,file_name,file_size,change_notes,uploaded_by) VALUES (:id,:tid,:did,:vn,:fname,:fsize,:notes,:ub)"),{"id":vid,"tid":tid,"did":doc_id,"vn":int(max_v)+1,"fname":file_name,"fsize":file_size or 0,"notes":change_notes,"ub":uploaded_by});self.db.flush();return vid

    def get_versions(self, doc_id: str, tenant_id: str | None = None) -> list[dict]:
        params={"did":doc_id};scope=""
        if tenant_id:scope=" AND tenant_id=:tid";params["tid"]=tenant_id
        rows=self.db.execute(text(f"SELECT id,document_id,version_number,file_name,file_size,change_notes,uploaded_by,created_at FROM dbp_document_versions WHERE document_id=:did{scope} ORDER BY version_number"),params).fetchall()
        return [{"id":r[0],"document_id":r[1],"version_number":int(r[2]),"file_name":r[3],"file_size":int(r[4] or 0),"change_notes":r[5],"uploaded_by":r[6],"created_at":_iso(r[7])} for r in rows]

    def add_tag(self, doc_id: str, tag: str, tenant_id: str | None = None) -> str | None:
        params={"did":doc_id};scope=""
        if tenant_id:scope=" AND tenant_id=:tid";params["tid"]=tenant_id
        doc=self.db.execute(text(f"SELECT tenant_id FROM dbp_documents WHERE id=:did{scope}"),params).fetchone()
        if not doc:return None
        tid=doc[0];existing=self.db.execute(text("SELECT id FROM dbp_document_tags WHERE document_id=:did AND tag=:tag AND tenant_id=:tid"),{"did":doc_id,"tag":tag,"tid":tid}).fetchone()
        if existing:return existing[0]
        tid_id=str(uuid.uuid4());self.db.execute(text("INSERT INTO dbp_document_tags (id,tenant_id,document_id,tag) VALUES (:id,:tid,:did,:tag)"),{"id":tid_id,"tid":tid,"did":doc_id,"tag":tag});self.db.flush();return tid_id

    def remove_tag(self, doc_id: str, tag: str, tenant_id: str | None = None) -> dict[str, Any]:
        params={"did":doc_id,"tag":tag};scope=""
        if tenant_id:scope=" AND tenant_id=:tid";params["tid"]=tenant_id
        result=self.db.execute(text(f"DELETE FROM dbp_document_tags WHERE document_id=:did AND tag=:tag{scope}"),params);self.db.flush();return {"success":result.rowcount>0,"error":None if result.rowcount>0 else "Tag not found on document"}

    def get_tags(self, doc_id: str, tenant_id: str | None = None) -> list[str]:
        params={"did":doc_id};scope=""
        if tenant_id:scope=" AND tenant_id=:tid";params["tid"]=tenant_id
        return [r[0] for r in self.db.execute(text(f"SELECT tag FROM dbp_document_tags WHERE document_id=:did{scope} ORDER BY tag"),params).fetchall()]
