"""
P9 Relationship Engine
Manages dynamic entity relationships with strict tenant isolation.
"""

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import DBPEntity, DBPRelationship


class RelationshipEngine:
    """Manage dynamic entity relationships without crossing tenant boundaries."""

    VALID_TYPES = ["one_to_many", "many_to_one", "many_to_many", "lookup"]
    VALID_ON_DELETE = ["restrict", "cascade", "set_null", "no_action"]
    MAX_DEPTH = 3
    _IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    def __init__(self, db: Session):
        self.db = db

    @classmethod
    def _identifier(cls, value: str, label: str) -> str:
        if not value or not cls._IDENTIFIER.fullmatch(value):
            raise ValueError(f"Invalid {label}: {value!r}")
        return value

    def _has_tenant_column(self, table_name: str) -> bool:
        self._identifier(table_name, "table name")
        result = self.db.execute(
            text("SELECT 1 FROM information_schema.columns WHERE table_name = :tname AND column_name = 'tenant_id' AND table_schema = 'public'"),
            {"tname": table_name},
        ).fetchone()
        return result is not None

    def _entity(self, code: str) -> DBPEntity | None:
        return self.db.query(DBPEntity).filter(DBPEntity.code == code).first()

    def create_relationship(self, entity_id: str, code: str, target_entity_code: str,
                            relationship_type: str, source_column: str,
                            target_column: str = "id", lookup_field: str = "name_en",
                            is_required: bool = False, tenant_scope: bool = True,
                            on_delete: str = "restrict", junction_table: str = "",
                            junction_source_col: str = "", junction_target_col: str = "") -> dict[str, Any]:
        if relationship_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid relationship_type: {relationship_type}. Must be one of: {', '.join(self.VALID_TYPES)}")
        if on_delete not in self.VALID_ON_DELETE:
            raise ValueError(f"Invalid on_delete: {on_delete}. Must be one of: {', '.join(self.VALID_ON_DELETE)}")
        if relationship_type == "many_to_many" and not junction_table:
            raise ValueError("many_to_many requires junction_table")

        source_entity = self.db.query(DBPEntity).filter(DBPEntity.id == entity_id).first()
        if not source_entity:
            raise ValueError(f"Source entity not found: {entity_id}")
        target_entity = self._entity(target_entity_code)
        if not target_entity:
            raise ValueError(f"Target entity not found: {target_entity_code}")

        self._identifier(source_column, "source column")
        self._identifier(target_column, "target column")
        self._identifier(lookup_field, "lookup field")
        if source_entity.table_mapping:
            self._identifier(source_entity.table_mapping, "source table")
        if target_entity.table_mapping:
            self._identifier(target_entity.table_mapping, "target table")
        if relationship_type == "many_to_many":
            self._identifier(junction_table, "junction table")
            self._identifier(junction_source_col, "junction source column")
            self._identifier(junction_target_col, "junction target column")

        existing = self.db.query(DBPRelationship).filter(DBPRelationship.entity_id == entity_id, DBPRelationship.code == code).first()
        if existing:
            raise ValueError(f"Relationship '{code}' already exists for this entity")

        if source_entity.table_mapping:
            cols = {row[0] for row in self.db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = :tname AND table_schema = 'public'"), {"tname": source_entity.table_mapping}).fetchall()}
            if source_column not in cols:
                raise ValueError(f"Source column '{source_column}' not found on table '{source_entity.table_mapping}'")
        if target_entity.table_mapping:
            cols = {row[0] for row in self.db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = :tname AND table_schema = 'public'"), {"tname": target_entity.table_mapping}).fetchall()}
            if target_column not in cols:
                raise ValueError(f"Target column '{target_column}' not found on table '{target_entity.table_mapping}'")
        if relationship_type == "many_to_many":
            junction_cols = {row[0] for row in self.db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = :tname AND table_schema = 'public'"), {"tname": junction_table}).fetchall()}
            if junction_source_col not in junction_cols:
                raise ValueError(f"Junction source column '{junction_source_col}' not found")
            if junction_target_col not in junction_cols:
                raise ValueError(f"Junction target column '{junction_target_col}' not found")

        rel = DBPRelationship(entity_id=entity_id, code=code, target_entity_code=target_entity_code,
                              relationship_type=relationship_type, source_column=source_column,
                              target_column=target_column, lookup_field=lookup_field,
                              is_required=is_required, tenant_scope=tenant_scope, on_delete=on_delete,
                              junction_table=junction_table, junction_source_col=junction_source_col,
                              junction_target_col=junction_target_col)
        self.db.add(rel)
        self.db.commit()
        self.db.refresh(rel)
        return {"id": rel.id, "code": rel.code, "target_entity_code": rel.target_entity_code,
                "relationship_type": rel.relationship_type, "source_column": rel.source_column,
                "target_column": rel.target_column, "lookup_field": rel.lookup_field,
                "is_required": rel.is_required, "tenant_scope": rel.tenant_scope,
                "on_delete": rel.on_delete, "junction_table": rel.junction_table or None}

    def get_relationships(self, entity_id: str) -> list[dict[str, Any]]:
        rels = self.db.query(DBPRelationship).filter(DBPRelationship.entity_id == entity_id).all()
        return [{"id": r.id, "code": r.code, "target_entity_code": r.target_entity_code,
                 "relationship_type": r.relationship_type, "source_column": r.source_column,
                 "target_column": r.target_column, "lookup_field": r.lookup_field,
                 "is_required": r.is_required, "tenant_scope": r.tenant_scope} for r in rels]

    def get_relationship(self, entity_id: str, code: str) -> dict | None:
        rel = self.db.query(DBPRelationship).filter(DBPRelationship.entity_id == entity_id, DBPRelationship.code == code).first()
        if not rel:
            return None
        return {"id": rel.id, "code": rel.code, "target_entity_code": rel.target_entity_code,
                "relationship_type": rel.relationship_type, "source_column": rel.source_column,
                "target_column": rel.target_column, "lookup_field": rel.lookup_field,
                "is_required": rel.is_required, "tenant_scope": rel.tenant_scope,
                "on_delete": rel.on_delete, "junction_table": rel.junction_table or "",
                "junction_source_col": rel.junction_source_col or "",
                "junction_target_col": rel.junction_target_col or ""}

    def delete_relationship(self, entity_id: str, code: str) -> bool:
        rel = self.db.query(DBPRelationship).filter(DBPRelationship.entity_id == entity_id, DBPRelationship.code == code).first()
        if not rel:
            return False
        self.db.delete(rel)
        self.db.commit()
        return True

    def _source_value(self, source_entity: DBPEntity, source_record_id: Any, source_column: str,
                      tenant_id: str | None, tenant_scope: bool) -> Any:
        source_table = self._identifier(source_entity.table_mapping or "", "source table")
        source_column = self._identifier(source_column, "source column")
        where = "id = :record_id"
        params: dict[str, Any] = {"record_id": str(source_record_id)}
        if tenant_scope and tenant_id:
            where += " AND tenant_id = :tenant_id"
            params["tenant_id"] = tenant_id
        row = self.db.execute(text(f"SELECT {source_column} FROM {source_table} WHERE {where}"), params).fetchone()
        return row[0] if row else None

    def _m2m_rows(self, source_value: Any, target_table: str, target_column: str,
                  junction_table: str, junction_source_col: str, junction_target_col: str,
                  tenant_scope: bool, tenant_id: str | None) -> list[dict[str, Any]]:
        target_table = self._identifier(target_table, "target table")
        target_column = self._identifier(target_column, "target column")
        junction_table = self._identifier(junction_table, "junction table")
        junction_source_col = self._identifier(junction_source_col, "junction source column")
        junction_target_col = self._identifier(junction_target_col, "junction target column")
        where_parts = [f"j.{junction_source_col} = :source_value"]
        params: dict[str, Any] = {"source_value": source_value}
        if tenant_scope and tenant_id:
            where_parts.append("t.tenant_id = :tenant_id")
            params["tenant_id"] = tenant_id
            if self._has_tenant_column(junction_table):
                where_parts.append("j.tenant_id = :tenant_id")
        query = text(f"SELECT t.* FROM {target_table} t INNER JOIN {junction_table} j ON j.{junction_target_col} = t.{target_column} WHERE {' AND '.join(where_parts)} LIMIT 100")
        rows = self.db.execute(query, params).fetchall()
        return [{k: v for k, v in row._mapping.items() if k != "tenant_id"} for row in rows]

    def fetch_related(self, source_entity_code: str, source_record_id: Any,
                      relationship_code: str, tenant_id: str | None = None) -> Any:
        source_entity = self._entity(source_entity_code)
        if not source_entity:
            return None
        rel = self.db.query(DBPRelationship).filter(DBPRelationship.entity_id == source_entity.id, DBPRelationship.code == relationship_code).first()
        if not rel:
            return None
        target_entity = self._entity(rel.target_entity_code)
        if not target_entity or not target_entity.table_mapping:
            return None
        target_table = self._identifier(target_entity.table_mapping, "target table")

        if rel.relationship_type == "many_to_many":
            source_value = self._source_value(source_entity, source_record_id, rel.source_column, tenant_id, bool(rel.tenant_scope))
            if source_value is None:
                return []
            return self._m2m_rows(source_value, target_table, rel.target_column, rel.junction_table or "",
                                   rel.junction_source_col or "", rel.junction_target_col or "",
                                   bool(rel.tenant_scope), tenant_id)

        if rel.relationship_type in ("one_to_many", "lookup"):
            source_value = self._source_value(source_entity, source_record_id, rel.source_column, tenant_id, bool(rel.tenant_scope))
            if source_value is None:
                return []
            target_column = self._identifier(rel.target_column, "target column")
            where = f"{target_column} = :source_value"
            params = {"source_value": source_value}
            if rel.tenant_scope and tenant_id:
                where += " AND tenant_id = :tenant_id"
                params["tenant_id"] = tenant_id
            if rel.relationship_type == "lookup":
                lookup = self._identifier(rel.lookup_field, "lookup field")
                rows = self.db.execute(text(f"SELECT id, {lookup} FROM {target_table} WHERE {where} ORDER BY {lookup} ASC LIMIT 100"), params).fetchall()
                return [{"id": str(row[0]), "label": str(row[1])} for row in rows]
            rows = self.db.execute(text(f"SELECT * FROM {target_table} WHERE {where} LIMIT 100"), params).fetchall()
            return [{k: v for k, v in row._mapping.items() if k != "tenant_id"} for row in rows]

        if rel.relationship_type == "many_to_one":
            source_table = self._identifier(source_entity.table_mapping or "", "source table")
            source_col = self._identifier(rel.source_column, "source column")
            target_col = self._identifier(rel.target_column, "target column")
            where = "s.id = :record_id"
            params = {"record_id": str(source_record_id)}
            if rel.tenant_scope and tenant_id:
                where += " AND s.tenant_id = :tenant_id AND t.tenant_id = :tenant_id"
                params["tenant_id"] = tenant_id
            row = self.db.execute(text(f"SELECT t.* FROM {target_table} t INNER JOIN {source_table} s ON s.{source_col} = t.{target_col} WHERE {where}"), params).fetchone()
            return dict(row._mapping) if row else None
        return None

    def fetch_nested(self, entity_code: str, record_id: Any, depth: int = 1,
                     tenant_id: str | None = None) -> dict[str, Any]:
        depth = max(0, min(depth, self.MAX_DEPTH))
        entity_row = self.db.execute(text("SELECT id, table_mapping FROM dbp_entities WHERE code = :code"), {"code": entity_code}).fetchone()
        if not entity_row or not entity_row[1]:
            return {}
        entity_id, table_name = entity_row[0], self._identifier(entity_row[1], "table name")
        where = "id = :id"
        params: dict[str, Any] = {"id": str(record_id)}
        if tenant_id:
            where += " AND tenant_id = :tenant_id"
            params["tenant_id"] = tenant_id
        row = self.db.execute(text(f"SELECT * FROM {table_name} WHERE {where}"), params).fetchone()
        if not row:
            return {}
        record = dict(row._mapping)
        record.pop("tenant_id", None)
        if depth <= 0:
            return record
        rels = self.db.execute(text(
            "SELECT code, target_entity_code, relationship_type, source_column, target_column, "
            "lookup_field, tenant_scope, junction_table, junction_source_col, junction_target_col "
            "FROM dbp_relationships WHERE entity_id = :eid"
        ), {"eid": entity_id}).fetchall()
        for rel_row in rels:
            rel_data = dict(rel_row._mapping)
            try:
                record[rel_data["code"]] = self._fetch_related_raw(rel_data, record, tenant_id)
            except (ValueError, KeyError):
                record[rel_data["code"]] = []
        return record

    def _fetch_related_raw(self, rel_data: dict[str, Any], source_record: dict[str, Any],
                           tenant_id: str | None = None) -> Any:
        target_row = self.db.execute(text("SELECT table_mapping FROM dbp_entities WHERE code = :code"), {"code": rel_data["target_entity_code"]}).fetchone()
        if not target_row or not target_row[0]:
            return None
        target_table = self._identifier(target_row[0], "target table")
        source_value = source_record.get(rel_data["source_column"])
        if source_value is None:
            return []
        if rel_data["relationship_type"] == "many_to_many":
            return self._m2m_rows(source_value, target_table, rel_data["target_column"],
                                   rel_data.get("junction_table") or "",
                                   rel_data.get("junction_source_col") or "",
                                   rel_data.get("junction_target_col") or "",
                                   bool(rel_data.get("tenant_scope")), tenant_id)
        target_column = self._identifier(rel_data["target_column"], "target column")
        where = f"{target_column} = :source_value"
        params: dict[str, Any] = {"source_value": source_value}
        if rel_data.get("tenant_scope") and tenant_id:
            where += " AND tenant_id = :tenant_id"
            params["tenant_id"] = tenant_id
        if rel_data["relationship_type"] == "lookup":
            lookup = self._identifier(rel_data["lookup_field"], "lookup field")
            rows = self.db.execute(text(f"SELECT id, {lookup} FROM {target_table} WHERE {where} ORDER BY {lookup} ASC LIMIT 100"), params).fetchall()
            return [{"id": str(r[0]), "label": str(r[1])} for r in rows]
        rows = self.db.execute(text(f"SELECT * FROM {target_table} WHERE {where} LIMIT 100"), params).fetchall()
        return [{k: v for k, v in row._mapping.items() if k != "tenant_id"} for row in rows]

    def validate_referential_integrity(self, entity_code: str, data: dict[str, Any],
                                       tenant_id: str | None = None) -> list[str]:
        errors: list[str] = []
        entity = self._entity(entity_code)
        if not entity:
            return errors
        rels = self.db.query(DBPRelationship).filter(DBPRelationship.entity_id == entity.id, DBPRelationship.is_required.is_(True)).all()
        for rel in rels:
            if rel.source_column not in data or data[rel.source_column] is None:
                continue
            target = self._entity(rel.target_entity_code)
            if not target or not target.table_mapping:
                continue
            table = self._identifier(target.table_mapping, "target table")
            column = self._identifier(rel.target_column, "target column")
            where = f"{column} = :fk_value"
            params: dict[str, Any] = {"fk_value": str(data[rel.source_column])}
            if rel.tenant_scope and tenant_id:
                where += " AND tenant_id = :tenant_id"
                params["tenant_id"] = tenant_id
            if not self.db.execute(text(f"SELECT 1 FROM {table} WHERE {where} LIMIT 1"), params).fetchone():
                errors.append(f"Referential integrity: {rel.code} → {rel.target_entity_code}.{rel.target_column} = '{data[rel.source_column]}' not found")
        return errors

    def check_on_delete(self, entity_code: str, record_id: Any,
                        tenant_id: str | None = None) -> list[str]:
        errors: list[str] = []
        entity = self._entity(entity_code)
        if not entity:
            return errors
        rels = self.db.query(DBPRelationship).filter(DBPRelationship.target_entity_code == entity_code).all()
        for rel in rels:
            if rel.on_delete != "restrict":
                continue
            source = self.db.query(DBPEntity).filter(DBPEntity.id == rel.entity_id).first()
            if not source or not source.table_mapping:
                continue
            table = self._identifier(source.table_mapping, "source table")
            column = self._identifier(rel.source_column, "source column")
            where = f"{column} = :record_id"
            params: dict[str, Any] = {"record_id": str(record_id)}
            if rel.tenant_scope and tenant_id:
                where += " AND tenant_id = :tenant_id"
                params["tenant_id"] = tenant_id
            if self.db.execute(text(f"SELECT 1 FROM {table} WHERE {where} LIMIT 1"), params).fetchone():
                errors.append(f"Cannot delete: {rel.code} relationship has dependent records in {source.code} (on_delete=restrict)")
        return errors
