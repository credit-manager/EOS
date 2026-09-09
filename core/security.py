"""
P13 Security Engine — Field-Level Security, Row-Level Security,
Sensitive Data Masking, Advanced Input Validation.
"""
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text


_SAFE_SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(value: Any) -> Optional[str]:
    """Return a SQL identifier only when it matches the metadata identifier contract."""
    candidate = str(value or "")
    return candidate if _SAFE_SQL_IDENTIFIER.fullmatch(candidate) else None


def _role_matches(user_roles: List[str], required_roles: List[str]) -> bool:
    """Match roles exactly, or as a namespaced descendant (for example module:manage)."""
    if not required_roles:
        return True

    for user_role in user_roles:
        if isinstance(user_role, dict):
            user_role = user_role.get("permission", "")
        user_role = str(user_role)
        if user_role in {"*", "*:*"}:
            return True
        for required_role in required_roles:
            required_role = str(required_role)
            if user_role == required_role or user_role.startswith(required_role + ":"):
                return True
    return False


# ──────────────────────────────────────────────────────────────
# FIELD-LEVEL SECURITY
# ──────────────────────────────────────────────────────────────

class FieldSecurity:
    """Enforces per-field read/write ACLs based on dbp_fields metadata."""

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
        """Filter payload to only allow writable fields. Returns (filtered_data, blocked_fields)."""
        filtered = {}
        blocked = []

        for key, value in payload.items():
            sec = field_security.get(key)
            if not sec or not sec["writable_roles"]:
                filtered[key] = value
                continue

            if _role_matches(user_roles, sec["writable_roles"]):
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
        """Filter output data to hide non-visible fields."""
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
    """Enforces row-level filtering based on user attributes."""

    @staticmethod
    def get_user_row_filter(
        db: Session,
        entity_id: str,
        user_roles: List[str],
        user_attrs: Dict[str, str],
    ) -> Optional[str]:
        """Return a SQL WHERE fragment without allowing metadata to inject SQL identifiers."""
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
            col = _safe_identifier(col)
            if col is None:
                continue
            if allowed_roles and not _role_matches(user_roles, allowed_roles):
                continue

            attr_value = user_attrs.get(col)
            if attr_value is None:
                continue

            if ftype == "equals":
                conditions.append(f'{col} = :rls_{col}')
            elif ftype == "in":
                values = fval.split(",") if fval else []
                if attr_value in values:
                    conditions.append(f'{col} = :rls_{col}')

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
        """Return bind parameters for the validated RLS WHERE fragment."""
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
            col = _safe_identifier(col)
            if col is None:
                continue
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
    """Redact sensitive keys from audit old_values/new_values."""
    if not values:
        return values

    def _walk(obj):
        if isinstance(obj, dict):
            return {k: REDACT_VALUE if _is_sensitive_key(k) else _walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
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
    """Validates input data against dbp_fields metadata rules."""

    TYPE_VALIDATORS = {
        "string": lambda v: isinstance(v, str),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "date": lambda v: isinstance(v, str),
        "datetime": lambda v: isinstance(v, str),
        "email": lambda v: isinstance(v, str) and "@" in v,
    }

    @staticmethod
    def validate_field(field_code: str, value: Any, field_meta: Dict[str, Any]) -> List[str]:
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
                    if not re.fullmatch(pattern, value):
                        errors.append(f"{field_code}: must match pattern")
                except re.error:
                    errors.append(f"{field_code}: invalid validation pattern configuration")

        if isinstance(value, (int, float)) and not isinstance(value, bool):
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
        all_errors = []
        for fm in field_metadata:
            code = fm["code"]
            value = data.get(code)
            if value is None:
                if fm.get("is_required", False) and not partial:
                    all_errors.append(f"{code}: required")
                continue
            all_errors.extend(InputValidator.validate_field(code, value, fm))
        return all_errors
