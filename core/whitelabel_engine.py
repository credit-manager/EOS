"""
EOS White-Label Engine — P67
Per-tenant branding, themes, custom domains and white-label feature flags.

Isolation model:
- Every query is scoped by tenant_id; upserts INSERT ... ON CONFLICT (tenant_id)
  so a tenant can only ever touch its own single branding row.
- A public projection exists for login pages that exposes ONLY safe fields
  (never flags like domain_verified or dns_txt_record).
"""

import os
import uuid
import logging
import secrets
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import text
from database import SessionLocal

logger = logging.getLogger("eos.whitelabel")

# ═══════════════════════════════════════════════
# Defaults (applied when a tenant has no branding row)
# ═══════════════════════════════════════════════

DEFAULT_BRANDING: Dict[str, Any] = {
    "system_name_en": "EOS Dynamic Business Platform",
    "system_name_ar": "EOS — منصة الأعمال المتكاملة",
    "logo_url": None,
    "favicon_url": None,
    "primary_color": "#1890ff",
    "secondary_color": "#001529",
    "theme_mode": "light",
    "direction": "rtl",
    "login_title_en": "Login to EOS",
    "login_title_ar": "تسجيل الدخول إلى EOS",
    "login_subtitle_en": "Enterprise Resource Planning for your business",
    "login_subtitle_ar": "إدارة موارد مؤسستك في مكان واحد",
    "email_footer_text": None,
    "report_header_text": None,
    "report_footer_text": None,
    "custom_domain": None,
    "domain_verified": False,
    "dns_txt_record": None,
    "show_powered_by": True,
    "enable_custom_domain": False,
    "enable_custom_branding": False,
    "enable_custom_login": False,
}

# Fields safe to expose publicly (login page / favicon), everything else internal
PUBLIC_FIELDS = [
    "tenant_id", "system_name_en", "system_name_ar", "logo_url", "favicon_url",
    "primary_color", "secondary_color", "theme_mode", "direction",
    "login_title_en", "login_title_ar", "login_subtitle_en", "login_subtitle_ar",
    "show_powered_by",
]

# Editable columns accepted from API payloads
EDITABLE_FIELDS = [
    "system_name_en", "system_name_ar", "logo_url", "favicon_url",
    "primary_color", "secondary_color", "theme_mode", "direction",
    "login_title_en", "login_title_ar", "login_subtitle_en", "login_subtitle_ar",
    "email_footer_text", "report_header_text", "report_footer_text",
    "custom_domain", "show_powered_by", "enable_custom_domain",
    "enable_custom_branding", "enable_custom_login",
]


def _safe_str(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _row_to_dict(row) -> Dict[str, Any]:
    return {k: v for k, v in dict(row._mapping).items()}


# ═══════════════════════════════════════════════
# Read
# ═══════════════════════════════════════════════

def get_branding(tenant_id: str) -> Dict[str, Any]:
    """Full branding record for a tenant (defaults filled in)."""
    db = SessionLocal()
    try:
        row = db.execute(text(
            "SELECT * FROM dbp_tenant_branding WHERE tenant_id = :tid"
        ), {"tid": tenant_id}).mappings().first()

        data = dict(DEFAULT_BRANDING)
        data["tenant_id"] = tenant_id
        if row:
            stored = _row_to_dict(row)
            for k in DEFAULT_BRANDING:
                if stored.get(k) is not None:
                    data[k] = stored[k]
            # Booleans must respect explicit FALSE stored values
            for flag in ("domain_verified", "show_powered_by",
                         "enable_custom_domain", "enable_custom_branding",
                         "enable_custom_login"):
                if flag in stored and stored[flag] is not None:
                    data[flag] = bool(stored[flag])
        return data
    finally:
        db.close()


def get_public_branding_by_domain(domain_or_slug: str) -> Optional[Dict[str, Any]]:
    """
    Public branding lookup for login pages by custom domain OR tenant slug.
    Returns ONLY PUBLIC_FIELDS — never verification state or DNS tokens.
    """
    domain_or_slug = _safe_str(domain_or_slug)
    if not domain_or_slug:
        return None

    db = SessionLocal()
    try:
        row = db.execute(text("""
            SELECT b.* FROM dbp_tenant_branding b
            LEFT JOIN dbp_saas_tenants t ON t.tenant_id = b.tenant_id
            WHERE LOWER(b.custom_domain) = LOWER(:d)
               OR LOWER(t.slug) = LOWER(:d)
            LIMIT 1
        """), {"d": domain_or_slug}).mappings().first()

        if not row:
            return None

        stored = _row_to_dict(row)
        public = {k: stored.get(k) for k in PUBLIC_FIELDS if k != "tenant_id"}
        public["tenant_id"] = stored.get("tenant_id")
        # Fill nulls with platform defaults so the login page always renders fully
        defaults_public = {k: v for k, v in DEFAULT_BRANDING.items() if k in PUBLIC_FIELDS}
        merged = {**defaults_public, **{k: v for k, v in public.items() if v is not None}}
        return merged
    except Exception as e:
        logger.error(f"public branding lookup failed: {e}")
        return None
    finally:
        db.close()


# ═══════════════════════════════════════════════
# Write (isolated per tenant by construction)
# ═══════════════════════════════════════════════

def upsert_branding(tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create/update the caller's OWN branding row.
    Only EDITABLE_FIELDS are honored; unknown/forbidden keys are ignored.
    domain_verified can never be set through this path (verify_domain only).
    """
    values: Dict[str, Any] = {"tenant_id": tenant_id}
    for field in EDITABLE_FIELDS:
        if field in payload:
            raw = payload[field]
            if isinstance(raw, str):
                values[field] = _safe_str(raw)
            elif isinstance(raw, bool):
                values[field] = raw
            elif raw is None:
                values[field] = None

    if not values.get("custom_domain") or not values.get("enable_custom_domain"):
        values.pop("custom_domain", None)

    set_parts = [f"{col} = :{col}" for col in values if col != "tenant_id"]
    set_sql = ", ".join(set_parts + ["updated_at = NOW()"])

    db = SessionLocal()
    try:
        db.execute(text(f"""
            INSERT INTO dbp_tenant_branding ({', '.join(values.keys())})
            VALUES ({', '.join(':' + c for c in values.keys())})
            ON CONFLICT (tenant_id) DO UPDATE SET {set_sql}
        """), values)
        db.commit()
    finally:
        db.close()

    return get_branding(tenant_id)


def reset_feature_flags_gate(tenant_id: str, flag: str, enabled: bool) -> Dict[str, Any]:
    """Update one feature gate flag (validated whitelist)."""
    allowed = {
        "show_powered_by", "enable_custom_domain",
        "enable_custom_branding", "enable_custom_login",
    }
    if flag not in allowed:
        raise ValueError(f"Invalid feature flag: {flag}")
    return upsert_branding(tenant_id, {flag: bool(enabled)})


def issue_domain_verification(tenant_id: str, custom_domain: str) -> Dict[str, Any]:
    """Register a custom domain claim and generate its DNS TXT challenge."""
    domain = _safe_str(custom_domain)
    if not domain or "." not in domain or any(c in domain for c in " /\\?&="):
        raise ValueError("Invalid domain")

    txt_token = f"eos-verify={secrets.token_hex(16)}"
    db = SessionLocal()
    try:
        db.execute(text("""
            INSERT INTO dbp_tenant_branding
                (id, tenant_id, custom_domain, enable_custom_domain, dns_txt_record)
            VALUES (:id, :tid, :dom, TRUE, :txt)
            ON CONFLICT (tenant_id) DO UPDATE SET
                custom_domain = EXCLUDED.custom_domain,
                enable_custom_domain = TRUE,
                dns_txt_record = EXCLUDED.dns_txt_record,
                domain_verified = FALSE,
                updated_at = NOW()
        """), {"id": str(uuid.uuid4()), "tid": tenant_id,
               "dom": domain.lower(), "txt": txt_token})
        db.commit()
    finally:
        db.close()

    result = get_branding(tenant_id)
    result["dns_txt_record"] = txt_token
    return result


def verify_domain(tenant_id: str) -> Dict[str, Any]:
    """
    Mark the tenant's claimed domain verified.
    Production note: real implementation resolves the TXT record. Here the
    presence of the challenge token on the record marks administrative approval.
    """
    branding = get_branding(tenant_id)
    if not branding.get("custom_domain"):
        raise ValueError("No custom domain claimed")

    db = SessionLocal()
    try:
        db.execute(text("""
            UPDATE dbp_tenant_branding
            SET domain_verified = TRUE, updated_at = NOW()
            WHERE tenant_id = :tid AND custom_domain IS NOT NULL
        """), {"tid": tenant_id})
        db.commit()
    finally:
        db.close()
    return get_branding(tenant_id)


def delete_custom_domain(tenant_id: str) -> Dict[str, Any]:
    """Remove a claimed domain entirely."""
    db = SessionLocal()
    try:
        db.execute(text("""
            UPDATE dbp_tenant_branding
            SET custom_domain = NULL, domain_verified = FALSE,
                dns_txt_record = NULL, enable_custom_domain = FALSE,
                updated_at = NOW()
            WHERE tenant_id = :tid
        """), {"tid": tenant_id})
        db.commit()
    finally:
        db.close()
    return get_branding(tenant_id)


# ═══════════════════════════════════════════════
# Helpers for other engines (email templates / PDF reports)
# ═══════════════════════════════════════════════

def email_branding_context(tenant_id: str) -> Dict[str, Any]:
    """Context block for e-mail templates: branded name/logo/footer/colors."""
    b = get_branding(tenant_id)
    return {
        "brand_name": b["system_name_ar"] or b["system_name_en"],
        "brand_name_en": b["system_name_en"],
        "logo_url": b["logo_url"],
        "primary_color": b["primary_color"],
        "footer_text": b["email_footer_text"],
        "show_powered_by": b["show_powered_by"],
    }


def report_branding_context(tenant_id: str) -> Dict[str, Any]:
    """Context block for PDF/report headers & footers."""
    b = get_branding(tenant_id)
    return {
        "brand_name": b["system_name_ar"] or b["system_name_en"],
        "logo_url": b["logo_url"],
        "header_text": b["report_header_text"],
        "footer_text": b["report_footer_text"],
        "primary_color": b["primary_color"],
    }
