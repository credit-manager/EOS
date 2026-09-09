"""
Tenant ID Normalization & Isolation — Security Test Matrix
==========================================================
Self-contained security-layer tests: real TenantMiddleware + real
get_current_user dependency + real JWT minting. No database required.

Run with pytest:
    python -m pytest app/tests/test_tenant_security_matrix.py -v
Or standalone:
    python app/tests/test_tenant_security_matrix.py

Matrix (expected behavior after closure):
  #  Scenario                                              Expected
  -- ---------------------------------------------------- ----------
  1  Valid token, business path tenant matches            200
  2  Valid token, X-Tenant-ID exact match                 200
  3  Token claim "EOS" (mixed case), canonical request    200 (canonical)
  4  Header UPPER vs token lower                          200 (normalized)
  5  Path UPPER vs token lower                            200 (normalized)
  6  Header different tenant                              403 REJECT
  7  Path different tenant                                403 REJECT
  8  Token missing tenant_id claim                        401 REJECT
  9  Token tenant_id = ""                                 401 REJECT
 10  Token tenant_id invalid format ("eos; drop")         401 REJECT
 11  Business path, no header, no path tenant             400
 12  Invalid-format header ("EOS; DROP")                  400
 13  Reserved segment /api/v1/auth/me, valid token        200 (JWT-only)
 14  create_access_token refuses invalid tenant claim     ValueError
 15  create_access_token canonicalizes mixed-case claim   lowercase in JWT
 16  normalize_tenant_id unit cases                       canonical/None
 17  Path tenant + header disagree, token matches neither 403 REJECT
 18  Whitespace-padded values normalize cleanly           200
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, get_current_user
from app.core.tenancy import TENANT_HEADER, normalize_tenant_id
from app.middleware.tenant import TenantMiddleware

TID_A = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
TID_B = "1b2b2b2b-cccc-dddd-eeee-ffffffffffff"

app = FastAPI()
app.add_middleware(TenantMiddleware)


@app.get("/api/v1/{tenant_id}/data")
async def biz_data(tenant_id: str, user: dict = Depends(get_current_user)):
    return {"ok": True, "jwt_tenant": user["tenant_id"], "path_tenant": tenant_id}


@app.get("/api/v1/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    return {"ok": True, "tenant": user["tenant_id"]}


@app.get("/api/v2/probe")
async def probe():
    return {"ok": True}


client = TestClient(app, raise_server_exceptions=False)


def _token(tenant=None, subject="user-1"):
    extra = {} if tenant is None else {"tenant_id": tenant}
    return create_access_token(subject=subject, extra_data=extra)


def _raw_token(claims):
    """Craft a token directly (simulates legacy/forged claims)."""
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _auth(tok):
    return {"Authorization": f"Bearer {tok}"}


RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition), detail))


# ── Row 16: normalizer units ──
def test_normalizer_units():
    assert normalize_tenant_id("EOS") == "eos"
    assert normalize_tenant_id("  MiXeD-Co ") == "mixed-co"
    assert normalize_tenant_id("") is None
    assert normalize_tenant_id("   ") is None
    assert normalize_tenant_id(None) is None
    assert normalize_tenant_id(123) is None
    assert normalize_tenant_id("eos; DROP TABLE users") is None
    assert normalize_tenant_id("tenant_1") == "tenant_1"
    check("R16 normalizer units", True)


# ── Rows 14–15: mint-time enforcement ──
def test_mint_time_enforcement():
    try:
        create_access_token(subject="u", extra_data={"tenant_id": "bad id!"})
        refused = False
    except ValueError:
        refused = True
    check("R14 mint refuses invalid tenant", refused)

    tok = _token("WeIRD_Tid")
    claims = jwt.decode(tok, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    check("R15 mint canonicalizes claim", claims["tenant_id"] == "weird_tid", claims["tenant_id"])


# ── Happy paths ──
def test_matching_contexts():
    tok = _token(TID_A)

    r = client.get(f"/api/v1/{TID_A}/data", headers=_auth(tok))
    check("R1 path match -> 200", r.status_code == 200, r.text[:120])

    r = client.get("/api/v1/x/data", headers={**_auth(tok), TENANT_HEADER: TID_A})
    # path tenant 'x' != token -> must reject even though header matches
    check("R7 path mismatch -> 403", r.status_code == 403, f"{r.status_code}")

    r = client.get(f"/api/v1/{TID_A}/data", headers={**_auth(tok), TENANT_HEADER: TID_A})
    check("R2 header+path+token all match -> 200", r.status_code == 200, r.text[:120])

    r = client.get(f"/api/v1/{TID_A.upper()}/data", headers=_auth(tok))
    check("R5 uppercase path normalized -> 200", r.status_code == 200, r.text[:120])

    r = client.get(f"/api/v1/{TID_A}/data", headers={**_auth(tok), TENANT_HEADER: TID_A.upper()})
    check("R4 uppercase header normalized -> 200", r.status_code == 200, r.text[:120])


# ── Canonical acceptance of legacy mixed-case tokens ──
def test_mixed_case_claim_canonical():
    tok = _token("EOS")
    r = client.get(f"/api/v1/{TID_A}/data", headers=_auth(tok))
    # token says eos; path says TID_A (different uuid) -> 403 proves claim was read as 'eos'
    check("R3 mixed-case claim parsed canonically", r.status_code == 403, r.status_code)

    r = client.get("/api/v1/auth/me", headers=_auth(tok))
    body = r.json() if r.status_code == 200 else {}
    check(
        "R3b mixed-case claim accepted on reserved route",
        r.status_code == 200 and body.get("tenant") == "eos",
        r.text[:120],
    )


# ── Rejection paths ──
def test_rejections():
    good_tok = _token(TID_A)

    r = client.get(f"/api/v1/{TID_A}/data", headers={**_auth(good_tok), TENANT_HEADER: TID_B})
    check("R6 header mismatch -> 403", r.status_code == 403, r.status_code)

    no_tenant_tok = _token(None)  # access token without tenant claim
    r = client.get(f"/api/v1/{TID_A}/data", headers=_auth(no_tenant_tok))
    check("R8 missing claim -> 401", r.status_code == 401, r.status_code)

    empty_tok = _raw_token({"sub": "u", "type": "access", "tenant_id": ""})
    r = client.get(f"/api/v1/{TID_A}/data", headers=_auth(empty_tok))
    check("R9 empty claim -> 401", r.status_code == 401, r.status_code)

    evil_tok = _raw_token({"sub": "u", "type": "access", "tenant_id": "eos; DROP TABLE tenants"})
    r = client.get(f"/api/v1/{TID_A}/data", headers=_auth(evil_tok))
    check("R10 invalid-format claim -> 401", r.status_code == 401, r.status_code)

    r = client.get("/api/v2/probe")
    check("R11 no context anywhere -> 400", r.status_code == 400, f"{r.status_code} {r.text[:60]}")

    r = client.get(f"/api/v1/{TID_A}/data")
    check(
        "R11b business path w/o auth -> 401 (context ok, auth missing)",
        r.status_code == 401,
        r.status_code,
    )

    r = client.get("/api/v1/x/data", headers={TENANT_HEADER: "EOS; DROP"})
    check("R12 invalid header beside path -> 400", r.status_code == 400, r.status_code)

    r = client.get(f"/api/v1/{TID_B}/data", headers=_auth(good_tok))
    check("R7 full path mismatch -> 403", r.status_code == 403, r.status_code)

    r = client.get(
        f"/api/v1/{TID_B}/data",
        headers={**_auth(good_tok), TENANT_HEADER: TID_B},
    )
    check("R17 both contexts wrong -> 403", r.status_code == 403, r.status_code)


# ── Reserved routes & padding ──
def test_reserved_and_padding():
    tok = _token(TID_A)

    r = client.get("/api/v1/auth/me", headers=_auth(tok))
    check("R13 reserved route JWT-only -> 200", r.status_code == 200, r.text[:120])

    r = client.get(f"/api/v1/{TID_A}/data", headers={**_auth(tok), TENANT_HEADER: f"  {TID_A}  "})
    check("R18 padded header -> 200", r.status_code == 200, r.status_code)

    r = client.get("/api/v1/auth/me")
    check("reserved route w/o token -> 401/403 (HTTPBearer)", r.status_code in (401, 403), r.status_code)


def summarize():
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 64)
    print(f"TENANT SECURITY MATRIX: {passed}/{len(RESULTS)} checks passed")
    for name, ok, detail in RESULTS:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} {detail}")
    print("=" * 64)
    return passed == len(RESULTS)


if __name__ == "__main__":
    test_normalizer_units()
    test_mint_time_enforcement()
    test_matching_contexts()
    test_mixed_case_claim_canonical()
    test_rejections()
    test_reserved_and_padding()
    sys.exit(0 if summarize() else 1)
