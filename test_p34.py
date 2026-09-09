"""
P34 API RATE LIMITING & QUOTAS TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
p, f = 0, 0
CID = "co_p34"


def t(name, got, exp):
    global p, f
    if got == exp:
        p += 1
    else:
        f += 1
        print(f"  FAIL - {name}: got {got!r}, expected {exp!r}")


def start():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())
    time.sleep(5)
    return proc


def stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def setup():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        for tbl in ("dbp_api_usage_logs", "dbp_rate_limit_rules", "dbp_api_keys"):
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_companies WHERE id = 'co_p34'"))
        db.execute(sa(
            "INSERT INTO dbp_companies (id, tenant_id, code, name_en) "
            "VALUES ('co_p34', 'tenant_a', 'COP34', 'P34 Test')"
        ))
        db.commit()
    finally:
        db.close()


# ── API Key Tests ──────────────────────────────────────────────

def test_create_api_key(c):
    print("\n--- 1. Create API Key ---")
    r = c.post(f"{EP}/companies/{CID}/api-keys", headers=H, json={
        "name": "Test Key",
        "permissions": "read,write",
        "rate_limit_read": 300,
        "rate_limit_write": 75,
    })
    t("Create key", r.status_code, 200)
    data = r.json()["data"]
    t("Has id", bool(data.get("id")), True)
    t("Has key", bool(data.get("key")), True)
    t("Name correct", data["name"], "Test Key")
    return data["id"], data["key"]


def test_create_api_key_missing_name(c):
    print("\n--- 2. Create API Key Missing Name ---")
    r = c.post(f"{EP}/companies/{CID}/api-keys", headers=H, json={
        "permissions": "read"
    })
    t("Missing name", r.status_code, 400)


def test_list_api_keys(c, key_id):
    print("\n--- 3. List API Keys ---")
    r = c.get(f"{EP}/companies/{CID}/api-keys", headers=H)
    t("List keys", r.status_code, 200)
    data = r.json()["data"]
    t("Has 1 key", len(data) >= 1, True)
    t("Key active", data[0]["is_active"], True)
    t("Rate limit read", data[0]["rate_limit_read"], 300)
    t("Rate limit write", data[0]["rate_limit_write"], 75)
    return data


def test_validate_api_key(c, plain_key):
    print("\n--- 4. Validate API Key ---")
    from core.api_quota_engine import APIQuotaEngine
    from database import SessionLocal
    db = SessionLocal()
    try:
        engine = APIQuotaEngine(db)
        result = engine.validate_api_key(plain_key)
        t("Validate returns data", result is not None, True)
        if result:
            t("Has id", bool(result.get("id")), True)
            t("Has tenant_id", bool(result.get("tenant_id")), True)
            t("Has name", bool(result.get("name")), True)
            t("Name correct", result["name"], "Test Key")
        db.commit()
    finally:
        db.close()


def test_revoke_api_key(c, key_id):
    print("\n--- 5. Revoke API Key ---")
    r = c.post(f"{EP}/api-keys/{key_id}/revoke", headers=H)
    t("Revoke key", r.status_code, 200)

    r = c.get(f"{EP}/companies/{CID}/api-keys", headers=H)
    keys = r.json()["data"]
    revoked = [k for k in keys if k["id"] == key_id]
    if revoked:
        t("Key inactive after revoke", revoked[0]["is_active"], False)


def test_validate_revoked_key(c, plain_key):
    print("\n--- 6. Validate Revoked Key Fails ---")
    from core.api_quota_engine import APIQuotaEngine
    from database import SessionLocal
    db = SessionLocal()
    try:
        engine = APIQuotaEngine(db)
        result = engine.validate_api_key(plain_key)
        t("Revoked key returns None", result, None)
    finally:
        db.close()


def test_revoke_nonexistent_key(c):
    print("\n--- 7. Revoke Nonexistent Key ---")
    r = c.post(f"{EP}/api-keys/nonexistent/revoke", headers=H)
    t("404 for missing key", r.status_code, 404)


# ── Usage Logging Tests ────────────────────────────────────────

def test_log_api_usage(c, key_id):
    print("\n--- 8. Log API Usage ---")
    from core.api_quota_engine import APIQuotaEngine
    from database import SessionLocal
    db = SessionLocal()
    try:
        engine = APIQuotaEngine(db)
        lid = engine.log_api_usage("tenant_a", key_id,
                                   "/api/v1/dynamic/companies", "GET", 200,
                                   response_time_ms=45)
        t("Log returns id", bool(lid), True)
        db.commit()
    finally:
        db.close()


def test_log_multiple_usages(c, key_id):
    print("\n--- 9. Log Multiple API Usages ---")
    from core.api_quota_engine import APIQuotaEngine
    from database import SessionLocal
    db = SessionLocal()
    try:
        engine = APIQuotaEngine(db)
        engine.log_api_usage("tenant_a", key_id,
                             "/api/v1/dynamic/companies", "POST", 201,
                             response_time_ms=120)
        engine.log_api_usage("tenant_a", key_id,
                             "/api/v1/dynamic/companies", "GET", 200,
                             response_time_ms=30)
        engine.log_api_usage("tenant_a", key_id,
                             "/api/v1/dynamic/companies", "GET", 500,
                             response_time_ms=500)
        db.commit()
    finally:
        db.close()


def test_get_usage_stats(c, key_id):
    print("\n--- 10. Get Usage Stats ---")
    from core.api_quota_engine import APIQuotaEngine
    from database import SessionLocal
    db = SessionLocal()
    try:
        engine = APIQuotaEngine(db)
        stats = engine.get_usage_stats("tenant_a", api_key_id=key_id)
        t("Total requests >= 4", stats["total_requests"] >= 4, True)
        t("Has by_endpoint", bool(stats["by_endpoint"]), True)
        t("Has by_method", bool(stats["by_method"]), True)
        t("Has by_status_code", bool(stats["by_status_code"]), True)
        t("Has avg_response_time", stats["avg_response_time"] is not None, True)
        t("GET in by_method", "GET" in stats["by_method"], True)
        t("POST in by_method", "POST" in stats["by_method"], True)
        t("200 in by_status", "200" in stats["by_status_code"], True)
        t("201 in by_status", "201" in stats["by_status_code"], True)
        t("500 in by_status", "500" in stats["by_status_code"], True)
    finally:
        db.close()


def test_get_usage_stats_via_endpoint(c):
    print("\n--- 11. Get Usage Stats via Endpoint ---")
    r = c.get(f"{EP}/api-usage/stats", headers=H)
    t("Stats endpoint", r.status_code, 200)
    data = r.json()["data"]
    t("Has total_requests", "total_requests" in data, True)


def test_get_usage_via_endpoint(c):
    print("\n--- 12. Get Usage via Endpoint ---")
    r = c.get(f"{EP}/api-usage", headers=H)
    t("Usage endpoint", r.status_code, 200)
    data = r.json()["data"]
    t("Has total_requests", "total_requests" in data, True)


# ── Rate Limit Rules Tests ─────────────────────────────────────

def test_create_rate_limit_rule(c):
    print("\n--- 13. Create Rate Limit Rule ---")
    r = c.post(f"{EP}/companies/{CID}/rate-limit-rules", headers=H, json={
        "endpoint_pattern": "/api/v1/dynamic/companies",
        "method": "GET",
        "rate_limit": 10,
        "window_seconds": 60,
    })
    t("Create rule", r.status_code, 200)
    rid = r.json()["data"]["id"]
    t("Has id", bool(rid), True)
    return rid


def test_create_rate_limit_rule_missing_fields(c):
    print("\n--- 14. Create Rate Limit Rule Missing Fields ---")
    r = c.post(f"{EP}/companies/{CID}/rate-limit-rules", headers=H, json={
        "endpoint_pattern": "/test"
    })
    t("Missing fields", r.status_code, 400)


def test_list_rate_limit_rules(c, rule_id):
    print("\n--- 15. List Rate Limit Rules ---")
    r = c.get(f"{EP}/companies/{CID}/rate-limit-rules", headers=H)
    t("List rules", r.status_code, 200)
    data = r.json()["data"]
    t("Has 1 rule", len(data) >= 1, True)
    t("Pattern correct", data[0]["endpoint_pattern"],
      "/api/v1/dynamic/companies")
    t("Method correct", data[0]["method"], "GET")
    t("Rate limit", data[0]["rate_limit"], 10)


def test_check_rate_limit_allowed(c):
    print("\n--- 16. Check Rate Limit - Allowed ---")
    from core.api_quota_engine import APIQuotaEngine
    from database import SessionLocal
    db = SessionLocal()
    try:
        engine = APIQuotaEngine(db)
        result = engine.check_rate_limit(
            "tenant_a", "/api/v1/dynamic/companies", "GET")
        t("Allowed", result["allowed"], True)
        t("Has remaining", result["remaining"] >= 0, True)
        t("Has reset_at", bool(result["reset_at"]), True)
    finally:
        db.close()


def test_check_rate_limit_exceeding(c):
    print("\n--- 17. Check Rate Limit - Exceeding ---")
    from core.api_quota_engine import APIQuotaEngine
    from database import SessionLocal
    db = SessionLocal()
    try:
        engine = APIQuotaEngine(db)
        for _ in range(12):
            engine.log_api_usage("tenant_a", None,
                                 "/api/v1/dynamic/companies", "GET", 200)
        db.commit()
        result = engine.check_rate_limit(
            "tenant_a", "/api/v1/dynamic/companies", "GET")
        t("Not allowed after exceeding", result["allowed"], False)
        t("Remaining is 0", result["remaining"], 0)
    finally:
        db.close()


def test_check_rate_limit_no_rule(c):
    print("\n--- 18. Check Rate Limit - No Matching Rule ---")
    from core.api_quota_engine import APIQuotaEngine
    from database import SessionLocal
    db = SessionLocal()
    try:
        engine = APIQuotaEngine(db)
        result = engine.check_rate_limit(
            "tenant_a", "/api/v1/dynamic/nonexistent", "GET")
        t("Allowed with no rule", result["allowed"], True)
        t("Remaining -1", result["remaining"], -1)
    finally:
        db.close()


def test_check_rate_limit_via_endpoint(c):
    print("\n--- 19. Check Rate Limit via Endpoint ---")
    r = c.post(f"{EP}/check-rate-limit", headers=H, json={
        "endpoint": "/api/v1/dynamic/companies",
        "method": "POST",
    })
    t("Check rate limit endpoint", r.status_code, 200)
    data = r.json()["data"]
    t("Allowed", data["allowed"], True)


def test_check_rate_limit_missing_fields(c):
    print("\n--- 20. Check Rate Limit Missing Fields ---")
    r = c.post(f"{EP}/check-rate-limit", headers=H, json={
        "endpoint": "/test"
    })
    t("Missing fields", r.status_code, 400)


# ── Second API Key ─────────────────────────────────────────────

def test_create_second_api_key(c):
    print("\n--- 21. Create Second API Key ---")
    r = c.post(f"{EP}/companies/{CID}/api-keys", headers=H, json={
        "name": "Second Key",
    })
    t("Create second key", r.status_code, 200)
    data = r.json()["data"]
    t("Different id", bool(data["id"]), True)
    return data["id"]


def test_list_multiple_api_keys(c):
    print("\n--- 22. List Multiple API Keys ---")
    r = c.get(f"{EP}/companies/{CID}/api-keys", headers=H)
    t("List keys", r.status_code, 200)
    t("Has >= 2 keys", len(r.json()["data"]) >= 2, True)


# ── Tenant Isolation ───────────────────────────────────────────

def test_tenant_isolation_api_keys(c):
    print("\n--- 23. Tenant Isolation - API Keys ---")
    TOKEN_B = create_test_token("tenant_b", user_id="b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}
    r = c.get(f"{EP}/companies/{CID}/api-keys", headers=H_B)
    t("Tenant B no keys", r.status_code, 200)
    t("Tenant B empty list", len(r.json()["data"]), 0)


def test_tenant_isolation_rate_limit_rules(c):
    print("\n--- 24. Tenant Isolation - Rate Limit Rules ---")
    TOKEN_B = create_test_token("tenant_b", user_id="b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}
    r = c.get(f"{EP}/companies/{CID}/rate-limit-rules", headers=H_B)
    t("Tenant B no rules", r.status_code, 200)
    t("Tenant B empty list", len(r.json()["data"]), 0)


def test_tenant_isolation_usage_stats(c):
    print("\n--- 25. Tenant Isolation - Usage Stats ---")
    TOKEN_B = create_test_token("tenant_b", user_id="b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}
    r = c.get(f"{EP}/api-usage/stats", headers=H_B)
    t("Tenant B stats", r.status_code, 200)
    t("Tenant B zero requests", r.json()["data"]["total_requests"], 0)


# ── Additional Tests ───────────────────────────────────────────

def test_create_wildcard_rate_limit_rule(c):
    print("\n--- 26. Create Wildcard Rate Limit Rule ---")
    r = c.post(f"{EP}/companies/{CID}/rate-limit-rules", headers=H, json={
        "endpoint_pattern": "*",
        "method": "*",
        "rate_limit": 100,
        "window_seconds": 30,
    })
    t("Create wildcard rule", r.status_code, 200)


def test_validate_nonexistent_key(c):
    print("\n--- 27. Validate Nonexistent Key ---")
    from core.api_quota_engine import APIQuotaEngine
    from database import SessionLocal
    db = SessionLocal()
    try:
        engine = APIQuotaEngine(db)
        result = engine.validate_api_key("nonexistent-key-value")
        t("Nonexistent returns None", result, None)
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("P34 API RATE LIMITING & QUOTAS TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        kid, plain = test_create_api_key(c)
        test_create_api_key_missing_name(c)
        test_list_api_keys(c, kid)
        test_validate_api_key(c, plain)
        test_revoke_api_key(c, kid)
        test_validate_revoked_key(c, plain)
        test_revoke_nonexistent_key(c)
        test_log_api_usage(c, kid)
        test_log_multiple_usages(c, kid)
        test_get_usage_stats(c, kid)
        test_get_usage_stats_via_endpoint(c)
        test_get_usage_via_endpoint(c)
        rid = test_create_rate_limit_rule(c)
        test_create_rate_limit_rule_missing_fields(c)
        test_list_rate_limit_rules(c, rid)
        test_check_rate_limit_allowed(c)
        test_check_rate_limit_exceeding(c)
        test_check_rate_limit_no_rule(c)
        test_check_rate_limit_via_endpoint(c)
        test_check_rate_limit_missing_fields(c)
        test_create_second_api_key(c)
        test_list_multiple_api_keys(c)
        test_tenant_isolation_api_keys(c)
        test_tenant_isolation_rate_limit_rules(c)
        test_tenant_isolation_usage_stats(c)
        test_create_wildcard_rate_limit_rule(c)
        test_validate_nonexistent_key(c)
    finally:
        c.close()
        stop(proc)
    print("\n" + "=" * 60)
    print(f"P34 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
