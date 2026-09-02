from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.audit import log_dynamic_audit
from core.auth import optional_get_current_user, require_permission
from core.dynamic_verification import DynamicVerificationEngine
from core.errors import ErrorCodes, create_error_response, secure_db_error
from core.event_bus import EventBus
from core.metadata_engine import MetadataEngine
from core.query_parser import QueryParseError, QueryParser
from core.rate_limit import read_limiter, write_limiter

router = APIRouter(prefix="/api/v1/dynamic", tags=["Dynamic CRUD"])
BULK_MAX_RECORDS = 500


def get_verification_engine(
    entity_code: str,
    db: Session=None,
    current_user: dict | None = Depends(optional_get_current_user),
):
    """Resolve entity metadata only within the authenticated tenant context."""
    tenant_id = current_user.get("tenant_id") if current_user else None
    return DynamicVerificationEngine(db, entity_code, tenant_id=tenant_id)


def _require_tenant(current_user: dict | None) -> str:
    if not current_user or not current_user.get("tenant_id"):
        raise HTTPException(status_code=401, detail="Authentication required for SCOPED entity")
    return current_user["tenant_id"]


def _validate_identifier(identifier: str) -> str:
    import re
    if not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9_]+", identifier):
        raise HTTPException(status_code=400, detail="Invalid SQL identifier")
    return identifier


@router.get("/entities/{entity_code}/schema", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_schema(entity_code: str, db: Session=None, verification: DynamicVerificationEngine = Depends(get_verification_engine)):
    if not verification.entity_exists():
        raise HTTPException(status_code=404, detail=f"الكيان '{entity_code}' غير موجود")
    table_error = verification.validate_table_mapping()
    if table_error:
        raise HTTPException(status_code=400, detail=table_error)
    engine = MetadataEngine(db)
    return {"status": "success", "data": engine.get_full_schema(entity_code), "table": verification.entity_meta.get("table_mapping"), "tenant_capability": verification.tenant_capability, "real_columns": verification.get_table_columns()}


@router.get("/entities/{entity_code}/records", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_records(entity_code: str, filters: str | None = None, sort: str | None = None, limit: int = 100, offset: int = 0, include: str | None = None, include_deleted: bool = False, db: Session=None, current_user: dict | None = Depends(optional_get_current_user)):
    tenant_id = current_user.get("tenant_id") if current_user else None
    ent_sql = "SELECT id, table_mapping, tenant_id FROM dbp_entities WHERE code = :code"
    ent_params = {"code": entity_code}
    if tenant_id:
        ent_sql += " AND (tenant_id = :tenant_id OR tenant_id IS NULL)"
        ent_params["tenant_id"] = tenant_id
    else:
        ent_sql += " AND tenant_id IS NULL"
    ent_row = db.execute(text(ent_sql), ent_params).fetchone()
    if not ent_row:
        raise HTTPException(status_code=404, detail=f"الكيان '{entity_code}' غير موجود")
    entity_id, table_mapping = ent_row[0], ent_row[1]
    table_name = _validate_identifier(table_mapping)

    col_rows = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = :tname ORDER BY ordinal_position"), {"tname": table_name}).fetchall()
    real_columns = {row[0].lower(): row[0] for row in col_rows}
    has_tenant = "tenant_id" in real_columns
    try:
        parser = QueryParser(real_columns)
        query_filter = parser.parse_query(filters_str=filters, sort_str=sort, limit=limit, offset=offset)
    except QueryParseError as e:
        return create_error_response(status_code=400, code=ErrorCodes.VALIDATION_ERROR, details=[{"message": str(e), "message_en": str(e)}])

    where_clauses, params = [], {}
    if has_tenant:
        auth_tenant_id = _require_tenant(current_user)
        where_clauses.append("tenant_id = :tenant_id")
        params["tenant_id"] = auth_tenant_id
    if "deleted_at" in real_columns:
        if include_deleted:
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")
            roles = current_user.get("roles", [])
            perms = current_user.get("permissions", [])
            is_admin = "*:*" in perms or "admin" in roles or any(isinstance(r, dict) and r.get("permission") == "*:*" for r in roles)
            if not is_admin:
                raise HTTPException(status_code=403, detail="include_deleted requires admin role")
        else:
            where_clauses.append("deleted_at IS NULL")
    user_where, user_params = parser.build_where_clause(query_filter.filters)
    if user_where:
        where_clauses.append(user_where)
        params.update(user_params)
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    order_sql = parser.build_order_clause(query_filter.sorts) or "ORDER BY created_at DESC"
    total = db.execute(text(f"SELECT COUNT(*) FROM {table_name} WHERE {where_sql}"), params).scalar()
    params.update({"limit": query_filter.limit, "offset": query_filter.offset})
    result = db.execute(text(f"SELECT * FROM {table_name} WHERE {where_sql} {order_sql} LIMIT :limit OFFSET :offset"), params)
    records = [dict(row._mapping) for row in result]

    if include:
        include_list = [x.strip() for x in include.split(",") if x.strip()]
        for inc in include_list:
            rel = db.execute(text("SELECT target_entity_code, relationship_type, source_column, target_column, lookup_field, tenant_scope, junction_table, junction_source_col, junction_target_col FROM dbp_relationships WHERE entity_id = :eid AND code = :code"), {"eid": entity_id, "code": inc}).fetchone()
            if not rel:
                continue
            target_code, rel_type, source_col, target_col, lookup_field, tenant_scope, junction, j_src, j_tgt = rel
            tgt_sql = "SELECT table_mapping, tenant_id FROM dbp_entities WHERE code = :code"
            tgt_params = {"code": target_code}
            if tenant_id:
                tgt_sql += " AND (tenant_id = :tenant_id OR tenant_id IS NULL)"
                tgt_params["tenant_id"] = tenant_id
            else:
                tgt_sql += " AND tenant_id IS NULL"
            tgt = db.execute(text(tgt_sql), tgt_params).fetchone()
            if not tgt or not tgt[0]:
                continue
            target_table = _validate_identifier(tgt[0])
            for record in records:
                source_value = record.get(source_col)
                if source_value is None:
                    record[inc] = []
                    continue
                where_parts = [f"{target_col} = :sv"]
                rel_params = {"sv": source_value}
                if tenant_scope and tenant_id:
                    where_parts.append("tenant_id = :tid")
                    rel_params["tid"] = tenant_id
                rel_where = " AND ".join(where_parts)
                if rel_type == "lookup":
                    lookup_field = _validate_identifier(lookup_field)
                    rows = db.execute(text(f"SELECT id, {lookup_field} FROM {target_table} WHERE {rel_where} ORDER BY {lookup_field} ASC LIMIT 100"), rel_params).fetchall()
                    record[inc] = [{"id": str(r[0]), "label": str(r[1])} for r in rows]
                elif rel_type == "many_to_many":
                    if not junction or not j_src or not j_tgt:
                        record[inc] = []
                        continue
                    junction, j_src, j_tgt = map(_validate_identifier, (junction, j_src, j_tgt))
                    rows = db.execute(text(f"SELECT t.* FROM {target_table} t INNER JOIN {junction} j ON j.{j_tgt} = t.{target_col} WHERE j.{j_src} = :sv LIMIT 100"), {"sv": source_value}).fetchall()
                    record[inc] = [{k: v for k, v in row._mapping.items() if k != "tenant_id"} for row in rows]
                else:
                    rows = db.execute(text(f"SELECT * FROM {target_table} WHERE {rel_where} LIMIT 100"), rel_params).fetchall()
                    record[inc] = [{k: v for k, v in row._mapping.items() if k != "tenant_id"} for row in rows]
    return {"status": "success", "data": records, "count": len(records), "tenant_applied": has_tenant, "effective_tenant": tenant_id, "pagination": {"total": total, "limit": query_filter.limit, "offset": query_filter.offset, "has_next": (query_filter.offset + query_filter.limit) < total}}


@router.post("/entities/{entity_code}/records", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_record(entity_code: str, payload: dict[str, Any], request: Request, db: Session=None, verification: DynamicVerificationEngine = Depends(get_verification_engine), current_user: dict | None = Depends(optional_get_current_user)):
    if not verification.entity_exists(): raise HTTPException(status_code=404, detail=f"الكيان '{entity_code}' غير موجود")
    table_error = verification.validate_table_mapping()
    if table_error: raise HTTPException(status_code=400, detail=table_error)
    try:
        verification.validate_required_fields(payload); verification.validate_enum_fields(payload)
    except ValueError as e:
        return create_error_response(status_code=400, code=ErrorCodes.VALIDATION_ERROR, details=[{"message": str(e), "message_en": str(e)}])
    not_null_errors = verification.validate_not_null_columns(payload, exclude_cols=["tenant_id"])
    if not_null_errors: return create_error_response(status_code=400, code=ErrorCodes.NOT_NULL_VIOLATION, details=[{"message": e, "message_en": e} for e in not_null_errors])
    effective_tenant = _require_tenant(current_user) if verification.has_tenant_id_column() else None
    duplicate_errors = verification.check_duplicate_by_unique_fields(payload, tenant_id=effective_tenant)
    if duplicate_errors: return create_error_response(status_code=409, code=ErrorCodes.DUPLICATE_RECORD, details=[{"message": e, "message_en": e} for e in duplicate_errors])
    table_name = _validate_identifier(verification.entity_meta["table_mapping"])
    pk_col = _validate_identifier(verification.get_pk_column())
    clean_data = {pk_col: verification.generate_pk_value()}
    if verification.has_tenant_id_column(): clean_data["tenant_id"] = effective_tenant
    for key, value in payload.items():
        if key not in (pk_col, "tenant_id") and verification.check_column_exists(key): clean_data[key] = value
    try:
        result = db.execute(text(f"INSERT INTO {table_name} ({', '.join(map(_validate_identifier, clean_data.keys()))}) VALUES ({', '.join(':'+k for k in clean_data)}) RETURNING {pk_col}"), clean_data)
        new_id = result.scalar()
        log_dynamic_audit(db=db, tenant_id=effective_tenant or "unknown", user_id=current_user.get("id") if current_user else None, user_email=current_user.get("email") if current_user else None, action="create", entity_code=entity_code, record_id=new_id, new_values=clean_data, ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent") if request else None, status="success")
        EventBus(db).emit("record.created", entity_code, tenant_id=effective_tenant, user_id=current_user.get("id") if current_user else None, record_id=new_id, payload=clean_data)
        db.commit()
        return {"status": "success", "id": new_id, "message": "تم إنشاؤه بنجاح", "tenant_capability": verification.tenant_capability, "effective_tenant": effective_tenant}
    except Exception as e:
        db.rollback(); return secure_db_error(e)


@router.put("/entities/{entity_code}/records/{record_id}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_record(entity_code: str, record_id: str, payload: dict[str, Any], request: Request, db: Session=None, verification: DynamicVerificationEngine = Depends(get_verification_engine), current_user: dict | None = Depends(optional_get_current_user)):
    if not verification.entity_exists(): raise HTTPException(status_code=404, detail=f"الكيان '{entity_code}' غير موجود")
    table_error = verification.validate_table_mapping()
    if table_error: raise HTTPException(status_code=400, detail=table_error)
    valid_cols = [k for k in payload if k not in ("id", "tenant_id") and verification.check_column_exists(k)]
    if not valid_cols: raise HTTPException(status_code=400, detail="لا توجد أعمدة صالحة للتحديث")
    table_name = _validate_identifier(verification.entity_meta["table_mapping"]); pk_col = _validate_identifier(verification.get_pk_column())
    update_params = {"id": record_id}; set_parts = []
    for key in valid_cols: set_parts.append(f"{_validate_identifier(key)} = :{key}"); update_params[key] = payload[key]
    where_clause = f"WHERE {pk_col} = :id"
    if verification.real_columns.get("deleted_at") is not None: where_clause += " AND deleted_at IS NULL"
    auth_tenant_id = None
    if verification.has_tenant_id_column(): auth_tenant_id = _require_tenant(current_user); where_clause += " AND tenant_id = :tenant_filter"; update_params["tenant_filter"] = auth_tenant_id
    try:
        result = db.execute(text(f"UPDATE {table_name} SET {', '.join(set_parts)} {where_clause}"), update_params)
        if result.rowcount == 0: raise HTTPException(status_code=404, detail="السجل غير موجود")
        log_dynamic_audit(db=db, tenant_id=auth_tenant_id or "unknown", user_id=current_user.get("id") if current_user else None, user_email=current_user.get("email") if current_user else None, action="update", entity_code=entity_code, record_id=record_id, new_values={k: payload[k] for k in valid_cols}, ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent") if request else None, status="success")
        EventBus(db).emit("record.updated", entity_code, tenant_id=auth_tenant_id, user_id=current_user.get("id") if current_user else None, record_id=record_id, payload={"new": {k: payload[k] for k in valid_cols}})
        db.commit(); return {"status": "success", "message": "تم تحديث السجل بنجاح"}
    except HTTPException: raise
    except Exception as e: db.rollback(); return secure_db_error(e)


@router.delete("/entities/{entity_code}/records/{record_id}", dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def delete_record(entity_code: str, record_id: str, request: Request, db: Session=None, current_user: dict | None = Depends(optional_get_current_user)):
    tenant_id = current_user.get("tenant_id") if current_user else None
    ent_sql = "SELECT table_mapping, tenant_id FROM dbp_entities WHERE code = :code"
    ent_params = {"code": entity_code}
    if tenant_id: ent_sql += " AND (tenant_id = :tenant_id OR tenant_id IS NULL)"; ent_params["tenant_id"] = tenant_id
    else: ent_sql += " AND tenant_id IS NULL"
    ent = db.execute(text(ent_sql), ent_params).fetchone()
    if not ent: raise HTTPException(status_code=404, detail=f"الكيان '{entity_code}' غير موجود")
    table_name = _validate_identifier(ent[0])
    cols = {r[0].lower(): r[0] for r in db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = :tname"), {"tname": table_name}).fetchall()}
    has_tenant, has_deleted = "tenant_id" in cols, "deleted_at" in cols
    effective_tenant = _require_tenant(current_user) if has_tenant else None
    user_id = current_user.get("id") if current_user else None
    if has_deleted:
        q = f"UPDATE {table_name} SET deleted_at = :deleted_at, deleted_by = :deleted_by WHERE id = :id AND deleted_at IS NULL" + (" AND tenant_id = :tenant_id" if has_tenant else "")
        p = {"deleted_at": datetime.now(timezone.utc), "deleted_by": user_id, "id": record_id}
        if has_tenant: p["tenant_id"] = effective_tenant
    else:
        q = f"DELETE FROM {table_name} WHERE id = :id" + (" AND tenant_id = :tenant_id" if has_tenant else "")
        p = {"id": record_id}
        if has_tenant: p["tenant_id"] = effective_tenant
    try:
        result = db.execute(text(q), p)
        if result.rowcount == 0: raise HTTPException(status_code=404, detail="السجل غير موجود")
        log_dynamic_audit(db=db, tenant_id=effective_tenant or "unknown", user_id=user_id, user_email=current_user.get("email") if current_user else None, action="delete", entity_code=entity_code, record_id=record_id, ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent") if request else None, status="success")
        EventBus(db).emit("record.deleted", entity_code, tenant_id=effective_tenant, user_id=user_id, record_id=record_id)
        db.commit(); return {"status": "success", "message": "تم حذف السجل بنجاح"}
    except HTTPException: raise
    except Exception as e: db.rollback(); return secure_db_error(e)


@router.post("/entities/{entity_code}/records/{record_id}/restore", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def restore_record(entity_code: str, record_id: str, request: Request, db: Session=None, verification: DynamicVerificationEngine = Depends(get_verification_engine), current_user: dict | None = Depends(optional_get_current_user)):
    if not verification.entity_exists(): raise HTTPException(status_code=404, detail=f"الكيان '{entity_code}' غير موجود")
    table_error = verification.validate_table_mapping()
    if table_error: raise HTTPException(status_code=400, detail=table_error)
    if verification.real_columns.get("deleted_at") is None: raise HTTPException(status_code=400, detail="Entity does not support soft delete")
    auth_tenant_id = _require_tenant(current_user) if verification.has_tenant_id_column() else current_user.get("tenant_id")
    table_name = _validate_identifier(verification.entity_meta["table_mapping"])
    where = "WHERE id = :id" + (" AND tenant_id = :tenant_id" if verification.has_tenant_id_column() else "")
    params = {"id": record_id};
    if verification.has_tenant_id_column(): params["tenant_id"] = auth_tenant_id
    row = db.execute(text(f"SELECT deleted_at FROM {table_name} {where}"), params).fetchone()
    if not row: raise HTTPException(status_code=404, detail="السجل غير موجود")
    if row[0] is None: raise HTTPException(status_code=400, detail="السجل غير محذوف")
    result = db.execute(text(f"UPDATE {table_name} SET deleted_at = NULL, deleted_by = NULL {where}"), params)
    if result.rowcount == 0: raise HTTPException(status_code=404, detail="السجل غير موجود")
    log_dynamic_audit(db=db, tenant_id=auth_tenant_id or "unknown", user_id=current_user.get("id"), user_email=current_user.get("email"), action="restore", entity_code=entity_code, record_id=record_id, status="success")
    EventBus(db).emit("record.restored", entity_code, tenant_id=auth_tenant_id, user_id=current_user.get("id"), record_id=record_id)
    db.commit(); return {"status": "success", "message": "تم استرجاع السجل بنجاح"}


# Bulk/import/export endpoints intentionally remain delegated to the existing
# implementations in subsequent modules; this router now contains the secured
# core single-record API surface.
