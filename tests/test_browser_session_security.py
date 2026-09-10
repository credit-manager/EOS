"""Regression tests preventing plaintext refresh-token browser storage."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "routers" / "auth.py"
FRONTEND_API = ROOT / "erp-system" / "frontend" / "src" / "services" / "api.ts"


def test_backend_sets_refresh_token_as_httponly_cookie():
    source = AUTH.read_text(encoding="utf-8")
    assert "httponly=True" in source
    assert "samesite=\"lax\"" in source
    assert "_set_refresh_cookie" in source
    assert "_REFRESH_COOKIE" in source


def test_production_refresh_cookie_is_secure():
    source = AUTH.read_text(encoding="utf-8")
    assert "secure=resolve_auth_mode() == \"production\"" in source


def test_backend_refresh_accepts_cookie_without_exposing_new_refresh_token():
    source = AUTH.read_text(encoding="utf-8")
    assert "cookie_token: str | None = Cookie" in source
    assert '"refresh_token": new_raw' not in source
    assert '"refresh_token": refresh' not in source
    assert 'async def logout(response: Response, body: RefreshRequest | None = None' in source


def test_frontend_does_not_persist_refresh_tokens():
    source = FRONTEND_API.read_text(encoding="utf-8")
    assert "withCredentials: true" in source
    assert "localStorage.setItem('refresh_token'" not in source
    assert "localStorage.getItem('refresh_token'" not in source
    assert "apiClient.post('/auth/refresh', {})" in source
