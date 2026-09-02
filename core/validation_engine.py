"""
P20 Advanced Validation Engine

Provides:
  - Field-level validators (type, range, regex, enum, custom)
  - Cross-field validators (match, compare, dependent)
  - Conditional validators (if field X has value Y, then field Z must...)
  - Business rule validators (unique, reference integrity, computed)
  - Validation rule CRUD (store rules in DB per entity/field)
  - Batch validation for bulk operations
"""
import json
import re
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class ValidationEngine:
    """
    Advanced validation engine for dynamic entities.
    
    Validation layers (executed in order):
      1. Type validation (field type matches declared type)
      2. Required validation (non-null check)
      3. Constraint validation (min/max, regex, enum)
      4. Cross-field validation (match, compare, dependent)
      5. Conditional validation (if-then rules)
      6. Business rules (unique, reference, computed)
    """

    FIELD_TYPES = {
        "string", "text", "integer", "decimal", "boolean",
        "date", "datetime", "email", "phone", "url",
        "json", "enum", "multi_enum", "file", "relation",
    }

    BUILTIN_VALIDATORS = {
        "required", "min_length", "max_length", "min", "max",
        "regex", "email", "phone", "url", "enum",
        "match_field", "gt_field", "lt_field", "gte_field", "lte_field",
        "unique", "reference", "custom",
    }

    def __init__(self, db: Session):
        self.db = db

    # ──────────────────────────────────────────────────────
    # RULE MANAGEMENT
    # ──────────────────────────────────────────────────────

    def create_rule(
        self,
        entity_id: str,
        field_code: str | None,
        rule_type: str,
        rule_config: dict[str, Any],
        name_en: str | None = None,
        name_ar: str | None = None,
        severity: str = "error",
        tenant_id: str | None = None,
        condition: dict[str, Any] | None = None,
    ) -> str | None:
        """Create a validation rule."""
        if rule_type not in self.BUILTIN_VALIDATORS and rule_type != "conditional":
            return None

        rule_id = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_validation_rules "
                "(id, tenant_id, entity_id, field_code, rule_type, rule_config, "
                " name_en, name_ar, severity, is_active, condition_config) "
                "VALUES (:id, :tenant, :eid, :fc, :rt, :rc, :ne, :na, :sev, true, :cond)"
            ),
            {
                "id": rule_id, "tenant": tenant_id, "eid": entity_id,
                "fc": field_code, "rt": rule_type,
                "rc": json.dumps(rule_config),
                "ne": name_en, "na": name_ar, "sev": severity,
                "cond": json.dumps(condition) if condition else None,
            },
        )
        self.db.flush()
        return rule_id

    def get_rules(
        self,
        entity_id: str,
        field_code: str | None = None,
        tenant_id: str | None = None,
    ) -> list[dict]:
        """Get validation rules for an entity."""
        conditions = ["entity_id = :eid", "is_active = true"]
        params: dict[str, Any] = {"eid": entity_id}

        if field_code:
            conditions.append("field_code = :fc")
            params["fc"] = field_code
        if tenant_id:
            conditions.append("(tenant_id = :tid OR tenant_id IS NULL)")
            params["tid"] = tenant_id

        where = " AND ".join(conditions)

        rows = self.db.execute(
            text(
                f"SELECT id, field_code, rule_type, rule_config, name_en, name_ar, "
                f"severity, condition_config, created_at "
                f"FROM dbp_validation_rules WHERE {where} ORDER BY rule_type"
            ),
            params,
        ).fetchall()

        return [
            {
                "id": r[0], "field_code": r[1], "rule_type": r[2],
                "rule_config": r[3] if isinstance(r[3], dict) else json.loads(r[3]) if r[3] else {},
                "name_en": r[4], "name_ar": r[5], "severity": r[6],
                "condition_config": r[7] if isinstance(r[7], dict) else json.loads(r[7]) if r[7] else None,
                "created_at": r[8].isoformat() if r[8] else None,
            }
            for r in rows
        ]

    def delete_rule(self, rule_id: str) -> bool:
        """Soft-delete a validation rule."""
        result = self.db.execute(
            text("UPDATE dbp_validation_rules SET is_active = false WHERE id = :rid"),
            {"rid": rule_id},
        )
        self.db.flush()
        return result.rowcount > 0

    # ──────────────────────────────────────────────────────
    # VALIDATION EXECUTION
    # ──────────────────────────────────────────────────────

    def validate_record(
        self,
        entity_id: str,
        data: dict[str, Any],
        existing_data: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Validate a single record against all rules.
        Returns: {valid: bool, errors: [...], warnings: [...]}
        """
        rules = self.get_rules(entity_id, tenant_id=tenant_id)
        errors = []
        warnings = []

        # Get entity fields for type checking
        fields = self._get_entity_fields(entity_id)
        field_map = {f["code"]: f for f in fields}

        for rule in rules:
            field_code = rule["field_code"]

            # Check condition
            if rule["condition_config"]:
                if not self._evaluate_condition(rule["condition_config"], data, existing_data):
                    continue

            result = self._apply_rule(rule, data, existing_data, field_map)

            if result:
                entry = {
                    "field": field_code,
                    "rule": rule["rule_type"],
                    "message": result,
                    "severity": rule["severity"],
                }
                if rule["severity"] == "error":
                    errors.append(entry)
                else:
                    warnings.append(entry)

        # Type validation (always runs)
        type_errors = self._validate_types(data, field_map)
        errors.extend(type_errors)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def validate_batch(
        self,
        entity_id: str,
        records: list[dict[str, Any]],
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Validate a batch of records.
        Returns: {valid: bool, results: [{index, valid, errors, warnings}, ...]}
        """
        results = []
        all_valid = True

        for i, record in enumerate(records):
            result = self.validate_record(entity_id, record, tenant_id=tenant_id)
            results.append({"index": i, **result})
            if not result["valid"]:
                all_valid = False

        return {
            "valid": all_valid,
            "total": len(records),
            "valid_count": sum(1 for r in results if r["valid"]),
            "invalid_count": sum(1 for r in results if not r["valid"]),
            "results": results,
        }

    # ──────────────────────────────────────────────────────
    # RULE APPLICATION
    # ──────────────────────────────────────────────────────

    def _apply_rule(
        self,
        rule: dict[str, Any],
        data: dict[str, Any],
        existing_data: dict[str, Any] | None,
        field_map: dict[str, dict],
    ) -> str | None:
        """Apply a single validation rule. Returns error message or None."""
        field_code = rule["field_code"]
        config = rule["rule_config"]
        value = data.get(field_code)

        rt = rule["rule_type"]

        if rt == "required":
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return config.get("message", f"{field_code} is required")

        elif rt == "min_length":
            if isinstance(value, str) and len(value) < config.get("value", 0):
                return config.get("message", f"{field_code} must be at least {config['value']} characters")

        elif rt == "max_length":
            if isinstance(value, str) and len(value) > config.get("value", 999):
                return config.get("message", f"{field_code} must be at most {config['value']} characters")

        elif rt == "min":
            if value is not None:
                try:
                    if float(value) < config.get("value", 0):
                        return config.get("message", f"{field_code} must be >= {config['value']}")
                except (ValueError, TypeError):
                    pass

        elif rt == "max":
            if value is not None:
                try:
                    if float(value) > config.get("value", 999999):
                        return config.get("message", f"{field_code} must be <= {config['value']}")
                except (ValueError, TypeError):
                    pass

        elif rt == "regex":
            if isinstance(value, str) and value:
                pattern = config.get("pattern", "")
                if pattern and not re.match(pattern, value):
                    return config.get("message", f"{field_code} does not match required format")

        elif rt == "email":
            if isinstance(value, str) and value:
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
                    return config.get("message", f"{field_code} must be a valid email")

        elif rt == "phone":
            if isinstance(value, str) and value:
                if not re.match(r'^[\+]?[\d\s\-\(\)]{7,20}$', value):
                    return config.get("message", f"{field_code} must be a valid phone number")

        elif rt == "url":
            if isinstance(value, str) and value:
                if not re.match(r'^https?://.+', value):
                    return config.get("message", f"{field_code} must be a valid URL")

        elif rt == "enum":
            allowed = config.get("values", [])
            if value is not None and allowed and value not in allowed:
                return config.get("message", f"{field_code} must be one of: {', '.join(str(v) for v in allowed)}")

        elif rt == "match_field":
            other_field = config.get("other_field", "")
            other_val = data.get(other_field)
            if value is not None and other_val is not None and value != other_val:
                return config.get("message", f"{field_code} must match {other_field}")

        elif rt == "gt_field":
            other_field = config.get("other_field", "")
            other_val = data.get(other_field)
            if value is not None and other_val is not None:
                try:
                    if float(value) <= float(other_val):
                        return config.get("message", f"{field_code} must be greater than {other_field}")
                except (ValueError, TypeError):
                    pass

        elif rt == "lt_field":
            other_field = config.get("other_field", "")
            other_val = data.get(other_field)
            if value is not None and other_val is not None:
                try:
                    if float(value) >= float(other_val):
                        return config.get("message", f"{field_code} must be less than {other_field}")
                except (ValueError, TypeError):
                    pass

        elif rt == "gte_field":
            other_field = config.get("other_field", "")
            other_val = data.get(other_field)
            if value is not None and other_val is not None:
                try:
                    if float(value) < float(other_val):
                        return config.get("message", f"{field_code} must be >= {other_field}")
                except (ValueError, TypeError):
                    pass

        elif rt == "lte_field":
            other_field = config.get("other_field", "")
            other_val = data.get(other_field)
            if value is not None and other_val is not None:
                try:
                    if float(value) > float(other_val):
                        return config.get("message", f"{field_code} must be <= {other_field}")
                except (ValueError, TypeError):
                    pass

        elif rt == "unique":
            if value is not None:
                is_unique = self._check_unique(
                    entity_id=rule.get("entity_id", ""),
                    field_code=field_code,
                    value=value,
                    exclude_id=existing_data.get("id") if existing_data else None,
                    tenant_id=rule.get("tenant_id"),
                )
                if not is_unique:
                    return config.get("message", f"{field_code} value '{value}' already exists")

        elif rt == "reference":
            ref_entity = config.get("ref_entity", "")
            ref_field = config.get("ref_field", "id")
            if value is not None:
                exists = self._check_reference(ref_entity, ref_field, value)
                if not exists:
                    return config.get("message", f"{field_code} references non-existent {ref_entity}.{ref_field}")

        return None

    # ──────────────────────────────────────────────────────
    # TYPE VALIDATION
    # ──────────────────────────────────────────────────────

    def _validate_types(self, data: dict[str, Any], field_map: dict[str, dict]) -> list[dict]:
        """Validate field types."""
        errors = []

        for field_code, field_info in field_map.items():
            value = data.get(field_code)
            if value is None:
                continue

            ftype = field_info.get("field_type", "string")
            err = self._check_type(field_code, value, ftype)
            if err:
                errors.append({
                    "field": field_code,
                    "rule": "type",
                    "message": err,
                    "severity": "error",
                })

        return errors

    def _check_type(self, field_code: str, value: Any, expected_type: str) -> str | None:
        """Check a single value matches expected type."""
        if expected_type in ("string", "text", "email", "phone", "url"):
            if not isinstance(value, str):
                return f"{field_code} must be a string"
        elif expected_type == "integer":
            try:
                int(value)
            except (ValueError, TypeError):
                return f"{field_code} must be an integer"
        elif expected_type == "decimal":
            try:
                float(value)
            except (ValueError, TypeError):
                return f"{field_code} must be a number"
        elif expected_type == "boolean":
            if not isinstance(value, bool):
                return f"{field_code} must be a boolean"
        elif expected_type == "json":
            if not isinstance(value, (dict, list)):
                return f"{field_code} must be JSON"
        elif expected_type == "enum" and not isinstance(value, str):
            return f"{field_code} must be a string"
        return None

    # ──────────────────────────────────────────────────────
    # CONDITION EVALUATION
    # ──────────────────────────────────────────────────────

    def _evaluate_condition(
        self,
        condition: dict[str, Any],
        data: dict[str, Any],
        existing_data: dict[str, Any] | None,
    ) -> bool:
        """Evaluate a condition dict. Returns True if rule should run."""
        cond_type = condition.get("type", "field_equals")

        if cond_type == "field_equals":
            field = condition.get("field", "")
            value = condition.get("value")
            return data.get(field) == value

        elif cond_type == "field_not_empty":
            field = condition.get("field", "")
            val = data.get(field)
            return val is not None and val != ""

        elif cond_type == "field_empty":
            field = condition.get("field", "")
            val = data.get(field)
            return val is None or val == ""

        elif cond_type == "field_gt":
            field = condition.get("field", "")
            value = condition.get("value", 0)
            try:
                return float(data.get(field, 0)) > float(value)
            except (ValueError, TypeError):
                return False

        elif cond_type == "field_in":
            field = condition.get("field", "")
            values = condition.get("values", [])
            return data.get(field) in values

        return True

    # ──────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────

    def _get_entity_fields(self, entity_id: str) -> list[dict]:
        """Get field definitions for an entity."""
        rows = self.db.execute(
            text("SELECT code, field_type, is_required, ui_config, enum_values "
                 "FROM dbp_fields WHERE entity_id = :eid"),
            {"eid": entity_id},
        ).fetchall()

        return [
            {
                "code": r[0], "field_type": r[1], "is_required": bool(r[2]),
                "ui_config": json.loads(r[3]) if r[3] else {},
                "enum_values": json.loads(r[4]) if r[4] else [],
            }
            for r in rows
        ]

    def _check_unique(
        self,
        entity_id: str,
        field_code: str,
        value: Any,
        exclude_id: str | None = None,
        tenant_id: str | None = None,
    ) -> bool:
        """Check if a value is unique for a field in the entity's table."""
        entity = self.db.execute(
            text("SELECT table_mapping FROM dbp_entities WHERE id = :eid"),
            {"eid": entity_id},
        ).fetchone()

        if not entity or not entity[0]:
            return True

        table = entity[0]
        conditions = [f"{field_code} = :val"]
        params: dict[str, Any] = {"val": value}

        if exclude_id:
            conditions.append("id != :eid")
            params["eid"] = exclude_id
        if tenant_id:
            conditions.append("tenant_id = :tid")
            params["tid"] = tenant_id

        where = " AND ".join(conditions)

        count = self.db.execute(
            text(f"SELECT COUNT(*) FROM {table} WHERE {where}"),
            params,
        ).scalar()

        return (count or 0) == 0

    def _check_reference(self, ref_entity: str, ref_field: str, value: Any) -> bool:
        """Check if a reference exists."""
        entity = self.db.execute(
            text("SELECT table_mapping FROM dbp_entities WHERE code = :ec"),
            {"ec": ref_entity},
        ).fetchone()

        if not entity or not entity[0]:
            return True

        table = entity[0]
        count = self.db.execute(
            text(f"SELECT COUNT(*) FROM {table} WHERE {ref_field} = :val"),
            {"val": value},
        ).scalar()

        return (count or 0) > 0
