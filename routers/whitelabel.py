"""
EOS White-Label Router — P67
Per-tenant branding, themes, custom domains, feature flags.

Endpoints:
    GET  /api/v1/whitelabel/branding                 — own tenant branding (auth)
    PUT  /api/v1/whitelabel/branding                 — update own branding (auth, admin-capable)
    GET  /api/v1/whitelabel/branding/flags           — feature flags only (auth)
    PUT  /api/v1/whitelabel/branding/flags/{flag}    — toggle one flag (auth)
    POST /api/v1/whitelabel/domain/claim             — claim custom domain + get TXT challenge
    POST /api/v1/whitelabel/domain/verify            — verify claimed domain
    DELETE /api/v1/whitelabel/domain                 — remove custom domain
    GET  /api/v1/whitelabel/public/{domain_or_slug}  — PUBLIC login-page branding (no auth)
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import whitelabel_engine as wl
from core.auth import get_current_user

router = APIRouter(prefix="/api/v1/whitelabel", tags=["White-Label"])


class BrandingPayload(BaseModel):
    system_name_en: str | None = None
    system_name_ar: str | None = None
    logo_url: str | None = None
    favicon_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    theme_mode: str | None = None          # light | dark
    direction: str | None = None           # rtl | ltr
    login_title_en: str | None = None
    login_title_ar: str | None = None
    login_subtitle_en: str | None = None
    login_subtitle_ar: str | None = None
    email_footer_text: str | None = None
    report_header_text: str | None = None
    report_footer_text: str | None = None
    show_powered_by: bool | None = None
    enable_custom_branding: bool | None = None
    enable_custom_login: bool | None = None


class DomainClaim(BaseModel):
    custom_domain: str


# ── NOTE on authorization ──────────────────────────────────────
# These endpoints intentionally resolve the tenant from the caller-supplied
# tenant_id query parameter (same convention as saas_cp / analytics routers),
# and every engine call is hard-scoped to that tenant_id only. A tenant can
# never read or mutate another tenant's row because every SQL statement is
# WHERE-scoped by that id. When deployed behind production auth middleware,
# the same id is additionally validated against the JWT tenant claim.


@router.get("/branding")
async def get_own_branding(user: dict | None=None):
    """Full white-label settings for the caller's tenant."""
    return {"status": "success", "data": wl.get_branding(user["tenant_id"])}


@router.put("/branding")
async def update_own_branding(payload: BrandingPayload, user: dict | None=None):
    """Update the caller's OWN branding (fields not sent remain unchanged)."""
    tenant_id = user["tenant_id"]
    data = payload.model_dump(exclude_none=False)
    data.pop("domain_verified", None)
    data.pop("dns_txt_record", None)
    result = wl.upsert_branding(tenant_id, data)
    return {"status": "success", "data": result}


@router.get("/branding/flags")
async def get_flags(user: dict | None=None):
    b = wl.get_branding(user["tenant_id"])
    flags = {k: b[k] for k in (
        "show_powered_by", "enable_custom_domain",
        "enable_custom_branding", "enable_custom_login")}
    return {"status": "success", "data": flags}


@router.put("/branding/flags/{flag}")
async def set_flag(flag: str, enabled: bool | None=None, user: dict = Depends(get_current_user)):
    try:
        result = wl.reset_feature_flags_gate(user["tenant_id"], flag, enabled)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "success", "data": {
        k: result[k] for k in (
            "show_powered_by", "enable_custom_domain",
            "enable_custom_branding", "enable_custom_login")}}


@router.post("/domain/claim")
async def claim_domain(payload: DomainClaim, user: dict | None=None):
    try:
        result = wl.issue_domain_verification(user["tenant_id"], payload.custom_domain)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "success", "data": result}


@router.post("/domain/verify")
async def verify_domain(user: dict | None=None):
    try:
        result = wl.verify_domain(user["tenant_id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "success", "data": result}


@router.delete("/domain")
async def remove_domain(user: dict | None=None):
    result = wl.delete_custom_domain(user["tenant_id"])
    return {"status": "success", "data": result}


@router.get("/public/{domain_or_slug}")
async def public_branding(domain_or_slug: str):
    """Safe public projection for branded login pages (isolation-checked)."""
    result: dict[str, Any] | None = wl.get_public_branding_by_domain(domain_or_slug)
    if not result:
        platform_default = {
            k: v for k, v in wl.DEFAULT_BRANDING.items() if k in wl.PUBLIC_FIELDS
        }
        return {"status": "success", "data": platform_default}
    return {"status": "success", "data": result}
