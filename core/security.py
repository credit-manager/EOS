"""
P13 Security Engine — Field-Level Security, Row-Level Security,
Sensitive Data Masking, Advanced Input Validation.
"""
import re
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import text


# ──────────────────────────────────────────────────────────────
# FIELD-LEVEL SECURITY
# ──────────────────────────────────────────────────────────────

class FieldSecurity:
    """
    Enforces per-field read/write ACLs based on dbp_fields metadata.

    Columns added to dbp_fields by P13 migration:
      - is_sensitive: bool — field value masked in audit & non-admin reads
      - writable_roles: json — list of role prefixes allowed to write
      - visible_roles: json — list of role prefixes allowed to read (empty = all)
    """

    @staticmethod
    def get_field_security_map(db: Session, entity_id: str) -> Dict[str, Dict]:
        """Returns {field_code: {is_sensitive, writable_roles, visible_roles}}."""
        rows = db.execute(
            text(
                "SELECT code, "
                "COALESCE(is_sensitive, false), "
                "COALESCE(writable_roles, '[]'), "
                "COALESCE(visible_roles, '[]') "
                "FROM dbp_fields WHERE entity_id = :eid"
            ),
            {"eid": entity_id},
        ).fetchall()

        result = {}
        for row in rows:
            code = row[0]
            wr = row[2] if isinstance(row[2], list) else []
            vr = row[3] if isinstance(row[3], list) else []
            result[code] = {
                "is_sensitive": bool(row[1]),
                "writable_roles": wr,
                "visible_roles": vr,
            }
        return result

    @staticmethod
    def filter_writable_columns(
        payload: Dict[str, Any],
        field_security: Dict[str, Dict],
        user_roles: List[str],
    ) -> tuple:
        """
        Filter payload to only allow writable fields.
        Returns (filtered_data, blocked_fields).
        """
        filtered = {}
        blocked = []

        for key, value in payload.items():
            sec = field_security.get(key)
            if not sec or not sec["writable_roles"]:
                filtered[key] = value
                continue

            writable_roles = sec["writable_roles"]
            if _role_matches(user_roles, writable_roles):
                filtered[key] = value
            else:
                blocked.append(key)

        return filtered, blocked

    @staticmethod
    def filter_visible_columns(
        data: Dict[str, Any],
        field_security: Dict[str, Dict],
        user_roles: List[str],
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        """
        Filter output data to hide non-visible fields.
        Admins see everything (except masked sensitive fields).
        """
        if is_admin:
            return dict(data)

        filtered = {}
        for key, value in data.items():
            sec = field_security.get(key)
            if not sec:
                filtered[key] = value
                continue

            visible_roles = sec["visible_roles"]
            if not visible_roles or _role_matches(user_roles, visible_roles):
                filtered[key] = value
            else:
                filtered[key] = "***RESTRICTED***"

        return filtered


# ──────────────────────────────────────────────────────────────
# ROW-LEVEL SECURITY
# ──────────────────────────────────────────────────────────────

class RowSecurity:
    """
    Enforces row-level filtering based on user attributes.
    Rules stored in dbp_row_rules table.
    """

    @staticmethod
    def get_user_row_filter(
        db: Session,
        entity_id: str,
        user_roles: List[str],
        user_attrs: Dict[str, str],
    ) -> Optional[str]:
        """
        Returns a SQL WHERE clause fragment (without WHERE keyword)
        or None if no filter applies.
        """
        rows = db.execute(
            text(
                "SELECT filter_column, filter_type, filter_value, allowed_roles "
                "FROM dbp_row_rules "
                "WHERE entity_id = :eid AND is_active = true "
                "ORDER BY priority ASC"
            ),
            {"eid": entity_id},
        ).fetchall()

        if not rows:
            return None

        conditions = []
        for row in rows:
            col, ftype, fval, allowed_roles = row[0], row[1], row[2], row[3] or []

            if allowed_roles and not _role_matches(user_roles, allowed_roles):
                continue

            attr_value = user_attrs.get(col)
            if attr_value is None:
                continue

            if ftype == "equals":
                conditions.append(f"{col} = :rls_{col}")
            elif ftype == "in":
                values = fval.split(",") if fval else []
                if attr_value in values:
                    conditions.append(f"{col} = :rls_{col}")

        if not conditions:
            return None

        return " AND ".join(conditions)

    @staticmethod
    def get_rls_params(
        db: Session,
        entity_id: str,
        user_roles: List[str],
        user_attrs: Dict[str, str],
    ) -> Dict[str, str]:
        """Returns bind parameters for the RLS WHERE clause."""
        rows = db.execute(
            text(
                "SELECT filter_column, filter_type, filter_value, allowed_roles "
                "FROM dbp_row_rules "
                "WHERE entity_id = :eid AND is_active = true "
                "ORDER BY priority ASC"
            ),
            {"eid": entity_id},
        ).fetchall()

        params = {}
        for row in rows:
            col, ftype, fval, allowed_roles = row[0], row[1], row[2], row[3] or []

            if allowed_roles and not _role_matches(user_roles, allowed_roles):
                continue

            attr_value = user_attrs.get(col)
            if attr_value is None:
                continue

            if ftype == "equals":
                params[f"rls_{col}"] = attr_value
            elif ftype == "in":
                values = fval.split(",") if fval else []
                if attr_value in values:
                    params[f"rls_{col}"] = attr_value

        return params


# ──────────────────────────────────────────────────────────────
# SENSITIVE DATA MASKING
# ──────────────────────────────────────────────────────────────

REDACT_PATTERNS = [
    re.compile(r"(?i)(password|passwd|pwd|secret|token|api_key|apikey|"
               r"authorization|ssn|social_security|national_id|"
               r"credit_card|card_number|cvv|bank_account|routing_number)"),
]

REDACT_VALUE = "***REDACTED***"


def mask_sensitive_data(
    data: Dict[str, Any],
    field_security: Dict[str, Dict],
) -> Dict[str, Any]:
    """Mask values of fields marked as is_sensitive."""
    if not field_security:
        return data

    masked = {}
    for key, value in data.items():
        sec = field_security.get(key)
        if sec and sec.get("is_sensitive") and value is not None:
            masked[key] = REDACT_VALUE
        else:
            masked[key] = value
    return masked


def redact_audit_values(values: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Redact sensitive keys from audit old_values/new_values.
    Matches field names against known sensitive patterns.
    """
    if not values:
        return values

    def _walk(obj):
        if isinstance(obj, dict):
            return {
                k: REDACT_VALUE if _is_sensitive_key(k) else _walk(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [_walk(item) for item in obj]
        return obj

    return _walk(values)


def _is_sensitive_key(key: str) -> bool:
    """Check if a field name matches sensitive data patterns."""
    return any(p.search(key) for p in REDACT_PATTERNS)


# ──────────────────────────────────────────────────────────────
# ADVANCED INPUT VALIDATION
# ──────────────────────────────────────────────────────────────

class InputValidator:
    """
    Validates input data against dbp_fields metadata rules.
    Supports: type, required, min, max, min_length, max_length, pattern (regex).
    """

    TYPE_VALIDATORS = {
        "string": lambda v: isinstance(v, str),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "date": lambda v: isinstance(v, str),  # validated as ISO format
        "datetime": lambda v: isinstance(v, str),
        "email": lambda v: isinstance(v, str) and "@" in v,
    }

    @staticmethod
    def validate_field(
        field_code: str,
        value: Any,
        field_meta: Dict[str, Any],
    ) -> List[str]:
        """
        Validate a single field value against its metadata.
        Returns list of error messages (empty = valid).
        """
        errors = []

        if value is None:
            if field_meta.get("is_required"):
                errors.append(f"{field_code}: required")
            return errors

        ftype = field_meta.get("field_type", "string")
        ui_config = field_meta.get("ui_config", {})
        enum_values = field_meta.get("enum_values", [])

        type_check = InputValidator.TYPE_VALIDATORS.get(ftype)
        if type_check and not type_check(value):
            errors.append(f"{field_code}: invalid type, expected {ftype}")
            return errors

        if enum_values and value not in enum_values:
            errors.append(f"{field_code}: value must be one of {enum_values}")

        if isinstance(value, str):
            min_len = ui_config.get("min_length")
            max_len = ui_config.get("max_length")
            pattern = ui_config.get("pattern")

            if min_len is not None and len(value) < min_len:
                errors.append(f"{field_code}: minimum length {min_len}")
            if max_len is not None and len(value) > max_len:
                errors.append(f"{field_code}: maximum length {max_len}")
            if pattern:
                try:
                    if not re.match(pattern, value):
                        errors.append(f"{field_code}: must match pattern {pattern}")
                except re.error:
                    pass

        if isinstance(value, (int, float)):
            min_val = ui_config.get("min")
            max_val = ui_config.get("max")
            if min_val is not None and value < min_val:
                errors.append(f"{field_code}: minimum value is {min_val}")
            if max_val is not None and value > max_val:
                errors.append(f"{field_code}: maximum value is {max_val}")

        return errors

    @staticmethod
    def validate_record(
        data: Dict[str, Any],
        field_metadata: List[Dict[str, Any]],
        partial: bool = False,
    ) -> List[str]:
        """
        Validate a full record against entity field metadata.
        partial=True skips required checks (for updates).
        """
        all_errors = []
        meta_map = {f["code"]: f for f in field_metadata}

        for fm in field_metadata:
            code = fm["code"]
            value = data.get(code)
            is_req = fm.get("is_required", False)

            if value is None:
                if is_req and not partial:
                    all_errors.append(f"{code}: required")
                continue

            field_errors = InputValidator.validate_field(code, value, fm)
            all_errors.extend(field_errors)

        return all_errors


# ──────────────────────────────────────────────────────────────
# HELPER
# ──────────────────────────────────────────────────────────────

def _role_matches(user_roles: List[str], required_roles: List[str]) -> bool:
    """
    Check if any user role matches any required role.
    Supports prefix matching: 'dynamic_manager' matches 'dynamic_manager'.
    Wildcard '*:*' matches everything.
    """
    if not required_roles:
        return True

    for ur in user_roles:
        if ur == "*:*":
            return True
        if isinstance(ur, dict):
            ur = ur.get("permission", "")
        for rr in required_roles:
            if ur == rr or ur.startswith(rr):
                return True

    return False
