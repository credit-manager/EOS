"""
P9 Relationship Engine
Manages entity relationships: creation, validation, nested reads.
Separate from MetadataEngine (protected).
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import DBPEntity, DBPRelationship


class RelationshipEngine:
    """Manages dynamic entity relationships."""

    VALID_TYPES = [
        "one_to_many", "many_to_one", "many_to_many", "lookup"
    ]
    VALID_ON_DELETE = ["restrict", "cascade", "set_null", "no_action"]
    MAX_DEPTH = 3  # Maximum nesting depth for nested reads

    def __init__(self, db: Session):
        self.db = db

    def create_relationship(
        self,
        entity_id: str,
        code: str,
        target_entity_code: str,
        relationship_type: str,
        source_column: str,
        target_column: str = "id",
        lookup_field: str = "name_en",
        is_required: bool = False,
        tenant_scope: bool = True,
        on_delete: str = "restrict",
        junction_table: str = "",
        junction_source_col: str = "",
        junction_target_col: str = "",
    ) -> dict[str, Any]:
        """Create a new relationship definition."""
        if relationship_type not in self.VALID_TYPES:
            raise ValueError(
                f"Invalid relationship_type: {relationship_type}. "
                f"Must be one of: {', '.join(self.VALID_TYPES)}"
            )
        if on_delete not in self.VALID_ON_DELETE:
            raise ValueError(
                f"Invalid on_delete: {on_delete}. "
                f"Must be one of: {', '.join(self.VALID_ON_DELETE)}"
            )
        if relationship_type == "many_to_many" and not junction_table:
            raise ValueError(
                "many_to_many requires junction_table"
            )

        # Validate source entity exists
        source_entity = self.db.query(DBPEntity).filter(
            DBPEntity.id == entity_id
        ).first()
        if not source_entity:
            raise ValueError(f"Source entity not found: {entity_id}")

        # Validate target entity exists
        target_entity = self.db.query(DBPEntity).filter(
            DBPEntity.code == target_entity_code
        ).first()
        if not target_entity:
            raise ValueError(
                f"Target entity not found: {target_entity_code}"
            )

        # Check duplicate code
        existing = self.db.query(DBPRelationship).filter(
            DBPRelationship.entity_id == entity_id,
            DBPRelationship.code == code
        ).first()
        if existing:
            raise ValueError(
                f"Relationship '{code}' already exists for this entity"
            )

        # Validate source column exists on source table
        if source_entity.table_mapping:
            cols = [
                row[0] for row in self.db.execute(
                    text("SELECT column_name FROM information_schema.columns "
                         "WHERE table_name = :tname AND table_schema = 'public'"),
                    {"tname": source_entity.table_mapping}
                ).fetchall()
            ]
            if source_column not in cols:
                raise ValueError(
                    f"Source column '{source_column}' not found on "
                    f"table '{source_entity.table_mapping}'"
                )

        # Validate target column exists on target table
        if target_entity.table_mapping:
            cols = [
                row[0] for row in self.db.execute(
                    text("SELECT column_name FROM information_schema.columns "
                         "WHERE table_name = :tname AND table_schema = 'public'"),
                    {"tname": target_entity.table_mapping}
                ).fetchall()
            ]
            if target_column not in cols:
                raise ValueError(
                    f"Target column '{target_column}' not found on "
                    f"table '{target_entity.table_mapping}'"
                )

        rel = DBPRelationship(
            entity_id=entity_id,
            code=code,
            target_entity_code=target_entity_code,
            relationship_type=relationship_type,
            source_column=source_column,
            target_column=target_column,
            lookup_field=lookup_field,
            is_required=is_required,
            tenant_scope=tenant_scope,
            on_delete=on_delete,
            junction_table=junction_table,
            junction_source_col=junction_source_col,
            junction_target_col=junction_target_col,
        )
        self.db.add(rel)
        self.db.commit()
        self.db.refresh(rel)

        return {
            "id": rel.id,
            "code": rel.code,
            "target_entity_code": rel.target_entity_code,
            "relationship_type": rel.relationship_type,
            "source_column": rel.source_column,
            "target_column": rel.target_column,
            "lookup_field": rel.lookup_field,
            "is_required": rel.is_required,
            "tenant_scope": rel.tenant_scope,
            "on_delete": rel.on_delete,
            "junction_table": rel.junction_table or None,
        }

    def get_relationships(self, entity_id: str) -> list[dict[str, Any]]:
        """Get all relationships for an entity."""
        rels = self.db.query(DBPRelationship).filter(
            DBPRelationship.entity_id == entity_id
        ).all()
        return [
            {
                "id": r.id,
                "code": r.code,
                "target_entity_code": r.target_entity_code,
                "relationship_type": r.relationship_type,
                "source_column": r.source_column,
                "target_column": r.target_column,
                "lookup_field": r.lookup_field,
                "is_required": r.is_required,
                "tenant_scope": r.tenant_scope,
            }
            for r in rels
        ]

    def get_relationship(self, entity_id: str, code: str) -> dict | None:
        """Get a single relationship by code."""
        rel = self.db.query(DBPRelationship).filter(
            DBPRelationship.entity_id == entity_id,
            DBPRelationship.code == code
        ).first()
        if not rel:
            return None
        return {
            "id": rel.id,
            "code": rel.code,
            "target_entity_code": rel.target_entity_code,
            "relationship_type": rel.relationship_type,
            "source_column": rel.source_column,
            "target_column": rel.target_column,
            "lookup_field": rel.lookup_field,
            "is_required": rel.is_required,
            "tenant_scope": rel.tenant_scope,
            "on_delete": rel.on_delete,
            "junction_table": rel.junction_table or "",
            "junction_source_col": rel.junction_source_col or "",
            "junction_target_col": rel.junction_target_col or "",
        }

    def delete_relationship(self, entity_id: str, code: str) -> bool:
        """Delete a relationship definition."""
        rel = self.db.query(DBPRelationship).filter(
            DBPRelationship.entity_id == entity_id,
            DBPRelationship.code == code
        ).first()
        if not rel:
            return False
        self.db.delete(rel)
        self.db.commit()
        return True

    def fetch_related(
        self,
        source_entity_code: str,
        source_record_id: Any,
        relationship_code: str,
        tenant_id: str | None = None,
    ) -> Any:
        """Fetch related records for a single relationship."""
        # Get source entity
        source_entity = self.db.query(DBPEntity).filter(
            DBPEntity.code == source_entity_code
        ).first()
        if not source_entity:
            return None

        # Get relationship definition
        rel = self.db.query(DBPRelationship).filter(
            DBPRelationship.entity_id == source_entity.id,
            DBPRelationship.code == relationship_code
        ).first()
        if not rel:
            return None

        # Get target entity
        target_entity = self.db.query(DBPEntity).filter(
            DBPEntity.code == rel.target_entity_code
        ).first()
        if not target_entity or not target_entity.table_mapping:
            return None

        target_table = target_entity.table_mapping

        # Build query based on relationship type
        if rel.relationship_type in ("one_to_many", "lookup"):
            # Fetch records where target[target_column] = source[source_column]
            # First get the source column value from source record
            source_table = source_entity.table_mapping
            source_val_query = text(
                f"SELECT {rel.source_column} FROM {source_table} "
                f"WHERE id = :record_id"
            )
            result = self.db.execute(
                source_val_query, {"record_id": str(source_record_id)}
            ).fetchone()
            if not result:
                return []

            source_value = result[0]

            # Query target table
            where_parts = [f"{rel.target_column} = :source_value"]
            params = {"source_value": source_value}

            if rel.tenant_scope and tenant_id:
                where_parts.append("tenant_id = :tenant_id")
                params["tenant_id"] = tenant_id

            where_sql = " AND ".join(where_parts)

            if rel.relationship_type == "lookup":
                # Return only id + lookup_field
                lookup_col = rel.lookup_field
                query = text(
                    f"SELECT id, {lookup_col} FROM {target_table} "
                    f"WHERE {where_sql} "
                    f"ORDER BY {lookup_col} ASC "
                    f"LIMIT 100"
                )
                rows = self.db.execute(query, params).fetchall()
                return [
                    {"id": str(row[0]), "label": str(row[1])}
                    for row in rows
                ]
            else:
                # Return full records
                query = text(
                    f"SELECT * FROM {target_table} "
                    f"WHERE {where_sql} "
                    f"LIMIT 100"
                )
                rows = self.db.execute(query, params).fetchall()
                columns = [col for col in rows[0] if col != "tenant_id"] if rows else []
                return [
                    {col: getattr(row, col) for col in columns}
                    for row in rows
                ]

        elif rel.relationship_type == "many_to_one":
            # Fetch single record where source[source_column] = target[target_column]
            source_table = source_entity.table_mapping
            query = text(
                f"SELECT t.* FROM {target_table} t "
                f"INNER JOIN {source_table} s "
                f"ON s.{rel.source_column} = t.{rel.target_column} "
                f"WHERE s.id = :record_id"
            )
            params = {"record_id": str(source_record_id)}

            if rel.tenant_scope and tenant_id:
                query = text(
                    f"SELECT t.* FROM {target_table} t "
                    f"INNER JOIN {source_table} s "
                    f"ON s.{rel.source_column} = t.{rel.target_column} "
                    f"WHERE s.id = :record_id "
                    f"AND t.tenant_id = :tenant_id"
                )
                params["tenant_id"] = tenant_id

            row = self.db.execute(query, params).fetchone()
            if not row:
                return None
            return dict(row._mapping)

        return None

    def fetch_nested(
        self,
        entity_code: str,
        record_id: Any,
        depth: int = 1,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch a record with nested related records.
        Uses raw SQL for everything to avoid ORM session conflicts.
        """
        depth = min(depth, self.MAX_DEPTH)

        # Get entity info via raw SQL
        entity_row = self.db.execute(
            text(
                "SELECT id, table_mapping FROM dbp_entities "
                "WHERE code = :code"
            ),
            {"code": entity_code}
        ).fetchone()
        if not entity_row or not entity_row[1]:
            return {}

        entity_id = entity_row[0]
        table_name = entity_row[1]

        # Fetch base record
        if tenant_id:
            query = text(
                f"SELECT * FROM {table_name} "
                f"WHERE id = :id AND tenant_id = :tenant_id"
            )
            row = self.db.execute(
                query, {"id": str(record_id), "tenant_id": tenant_id}
            ).fetchone()
        else:
            query = text(f"SELECT * FROM {table_name} WHERE id = :id")
            row = self.db.execute(
                query, {"id": str(record_id)}
            ).fetchone()

        if not row:
            return {}

        record = dict(row._mapping)
        record.pop("tenant_id", None)

        # Fetch relationships (only if depth > 0)
        if depth > 0:
            rels = self.db.execute(
                text(
                    "SELECT code, target_entity_code, "
                    "relationship_type, source_column, target_column, "
                    "lookup_field, tenant_scope "
                    "FROM dbp_relationships WHERE entity_id = :eid"
                ),
                {"eid": entity_id}
            ).fetchall()

            for rel_row in rels:
                rel_data = dict(rel_row._mapping)
                try:
                    related = self._fetch_related_raw(
                        rel_data, record, tenant_id
                    )
                except Exception:
                    related = []
                record[rel_data["code"]] = related

        return record

    def _fetch_related_raw(
        self,
        rel_data: dict[str, Any],
        source_record: dict[str, Any],
        tenant_id: str | None = None,
    ) -> Any:
        """Fetch related records using raw SQL only."""
        target_code = rel_data["target_entity_code"]
        target_row = self.db.execute(
            text("SELECT table_mapping FROM dbp_entities WHERE code = :code"),
            {"code": target_code}
        ).fetchone()
        if not target_row or not target_row[0]:
            return None

        target_table = target_row[0]
        source_value = source_record.get(rel_data["source_column"])
        if source_value is None:
            return []

        where_parts = [f"{rel_data['target_column']} = :source_value"]
        params: dict[str, Any] = {"source_value": source_value}

        if rel_data["tenant_scope"] and tenant_id:
            where_parts.append("tenant_id = :tenant_id")
            params["tenant_id"] = tenant_id

        where_sql = " AND ".join(where_parts)

        if rel_data["relationship_type"] == "many_to_many":
            junction = rel_data.get("junction_table", "")
            j_src = rel_data.get("junction_source_col", "")
            j_tgt = rel_data.get("junction_target_col", "")
            if not junction or not j_src or not j_tgt:
                return []
            query = text(
                f"SELECT t.* FROM {target_table} t "
                f"INNER JOIN {junction} j "
                f"ON j.{j_tgt} = t.{rel_data['target_column']} "
                f"WHERE j.{j_src} = :source_value "
                f"LIMIT 100"
            )
            rows = self.db.execute(query, params).fetchall()
            if not rows:
                return []
            columns = [
                c for c in rows[0] if c != "tenant_id"
            ]
            return [
                {col: row[col] for col in columns}
                for row in rows
            ]

        if rel_data["relationship_type"] == "lookup":
            lookup_col = rel_data["lookup_field"]
            query = text(
                f"SELECT id, {lookup_col} FROM {target_table} "
                f"WHERE {where_sql} "
                f"ORDER BY {lookup_col} ASC "
                f"LIMIT 100"
            )
            rows = self.db.execute(query, params).fetchall()
            return [
                {"id": str(r[0]), "label": str(r[1])}
                for r in rows
            ]
        else:
            query = text(
                f"SELECT * FROM {target_table} "
                f"WHERE {where_sql} "
                f"LIMIT 100"
            )
            rows = self.db.execute(query, params).fetchall()
            if not rows:
                return []
            columns = [
                c for c in rows[0] if c != "tenant_id"
            ]
            return [
                {col: row[col] for col in columns}
                for row in rows
            ]

    def validate_referential_integrity(
        self,
        entity_code: str,
        data: dict[str, Any],
        tenant_id: str | None = None,
    ) -> list[str]:
        """
        Validate that all required relationship foreign keys
        point to existing records.
        """
        errors = []
        entity = self.db.query(DBPEntity).filter(
            DBPEntity.code == entity_code
        ).first()
        if not entity:
            return errors

        rels = self.db.query(DBPRelationship).filter(
            DBPRelationship.entity_id == entity.id,
            DBPRelationship.is_required == True
        ).all()

        for rel in rels:
            if rel.source_column not in data:
                continue  # Not provided — let NOT NULL handle it

            fk_value = data[rel.source_column]
            if fk_value is None:
                continue  # Let NOT NULL handle it

            # Check target exists
            target_entity = self.db.query(DBPEntity).filter(
                DBPEntity.code == rel.target_entity_code
            ).first()
            if not target_entity or not target_entity.table_mapping:
                continue

            target_table = target_entity.table_mapping
            where_parts = [f"{rel.target_column} = :fk_value"]
            params = {"fk_value": str(fk_value)}

            if rel.tenant_scope and tenant_id:
                where_parts.append("tenant_id = :tenant_id")
                params["tenant_id"] = tenant_id

            where_sql = " AND ".join(where_parts)
            check = text(
                f"SELECT 1 FROM {target_table} WHERE {where_sql} LIMIT 1"
            )
            exists = self.db.execute(check, params).fetchone()

            if not exists:
                errors.append(
                    f"Referential integrity: {rel.code} → "
                    f"{rel.target_entity_code}.{rel.target_column} "
                    f"= '{fk_value}' not found"
                )

        return errors

    def check_on_delete(
        self,
        entity_code: str,
        record_id: Any,
        tenant_id: str | None = None,
    ) -> list[str]:
        """
        Check if a record can be deleted based on on_delete rules.
        Returns error messages if deletion is blocked.
        """
        errors = []
        entity = self.db.query(DBPEntity).filter(
            DBPEntity.code == entity_code
        ).first()
        if not entity:
            return errors

        # Find all relationships where THIS entity is the target
        rels = self.db.query(DBPRelationship).filter(
            DBPRelationship.target_entity_code == entity_code
        ).all()

        for rel in rels:
            if rel.on_delete == "restrict":
                # Check if any source records reference this target
                source_entity = self.db.query(DBPEntity).filter(
                    DBPEntity.id == rel.entity_id
                ).first()
                if not source_entity or not source_entity.table_mapping:
                    continue

                source_table = source_entity.table_mapping
                check = text(
                    f"SELECT 1 FROM {source_table} "
                    f"WHERE {rel.source_column} = :record_id "
                    f"LIMIT 1"
                )
                params = {"record_id": str(record_id)}

                if rel.tenant_scope and tenant_id:
                    check = text(
                        f"SELECT 1 FROM {source_table} "
                        f"WHERE {rel.source_column} = :record_id "
                        f"AND tenant_id = :tenant_id "
                        f"LIMIT 1"
                    )
                    params["tenant_id"] = tenant_id

                has_dependents = self.db.execute(
                    check, params
                ).fetchone()

                if has_dependents:
                    errors.append(
                        f"Cannot delete: {rel.code} relationship "
                        f"has dependent records in "
                        f"{source_entity.code} (on_delete=restrict)"
                    )

        return errors

    def _has_tenant_column(self, table_name: str) -> bool:
        """Check if a table has tenant_id column."""
        result = self.db.execute(
            text("SELECT 1 FROM information_schema.columns "
                 "WHERE table_name = :tname AND column_name = 'tenant_id' "
                 "AND table_schema = 'public'"),
            {"tname": table_name}
        ).fetchone()
        return result is not None
