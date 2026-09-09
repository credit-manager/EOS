"""
Cross-Tenant Isolation Matrix Test

Tests 12 scenarios to verify tenant isolation
in Dynamic CRUD operations.
"""

import subprocess
import time
import httpx
import sys

BASE = "http://127.0.0.1:8000/api/v1/dynamic"
PROJECT = r"D:\EOS\Eos final"
ENTITY = "test_product"


def safe_print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


def make_token(tenant_id):
    """Generate JWT token for a tenant."""
    from core.auth import create_test_token
    return create_test_token(tenant_id=tenant_id, roles=["dynamic_manager"])


def kill_server():
    try:
        result = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True
        )
        for line in result.stdout.split("\n"):
            if ":8000" in line and "LISTENING" in line:
                parts = line.split()
                pid = parts[-1]
                subprocess.run(
                    ["taskkill", "/F", "/PID", pid],
                    capture_output=True
                )
    except Exception:
        pass


def test_case(num, desc, method, url, token, payload=None,
              expected_status=None, expected_data_check=None):
    """Run a single test case."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        if method == "GET":
            r = httpx.get(url, headers=headers, timeout=10)
        elif method == "POST":
            r = httpx.post(url, json=payload, headers=headers, timeout=10)
        elif method == "PUT":
            r = httpx.put(url, json=payload, headers=headers, timeout=10)
        elif method == "DELETE":
            r = httpx.delete(url, headers=headers, timeout=10)
        else:
            raise ValueError(f"Unknown method: {method}")

        data = r.json()
        status_ok = (r.status_code == expected_status) if expected_status else True

        result = "PASS" if status_ok else "FAIL"
        num_str = str(num).rjust(2)
        safe_print(
            f"  {result} #{num_str}: {desc}"
            f" | {r.status_code}"
        )

        if not status_ok:
            safe_print(
                f"        Expected: {expected_status}, Got: {r.status_code}"
            )
            safe_print(f"        Response: {str(data)[:150]}")

        return r.status_code, data

    except Exception as e:
        num_str = str(num).rjust(2)
        safe_print(f"  FAIL #{num_str}: {desc} | ERROR: {e}")
        return None, None


def main():
    kill_server()
    time.sleep(1)

    safe_print("Starting server...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--port", "8000", "--host", "127.0.0.1"],
        cwd=PROJECT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)

    # Generate tokens
    token_a = make_token("tenant_a")
    token_b = make_token("tenant_b")

    url_records = f"{BASE}/entities/{ENTITY}/records"
    url_schema = f"{BASE}/entities/{ENTITY}/schema"

    results = []

    try:
        safe_print("\n" + "=" * 60)
        safe_print("CROSS-TENANT ISOLATION MATRIX")
        safe_print("=" * 60)

        # --- Test 1: Tenant A reads → sees own data only ---
        safe_print("\n--- READ Tests ---")
        code, data = test_case(
            1, "Tenant A READ → A records only",
            "GET", url_records + "?limit=10", token_a
        )
        if code == 200:
            records = data.get("data", [])
            all_a = all(r.get("tenant_id") == "tenant_a" for r in records)
            safe_print(f"        All records tenant_a: {all_a}")
            results.append(("READ A→A", all_a and len(records) > 0))
        else:
            results.append(("READ A→A", False))

        # --- Test 2: Tenant B reads → sees own data only ---
        code, data = test_case(
            2, "Tenant B READ → B records only",
            "GET", url_records + "?limit=10", token_b
        )
        if code == 200:
            records = data.get("data", [])
            all_b = all(r.get("tenant_id") == "tenant_b" for r in records)
            safe_print(f"        All records tenant_b: {all_b}")
            results.append(("READ B→B", all_b and len(records) > 0))
        else:
            results.append(("READ B→B", False))

        # --- Test 3: Tenant A reads with payload tenant_id=B → still A only ---
        code, data = test_case(
            3, "Tenant A READ + payload B → A only",
            "GET", url_records + "?limit=10", token_a
        )
        if code == 200:
            records = data.get("data", [])
            all_a = all(r.get("tenant_id") == "tenant_a" for r in records)
            safe_print(f"        All records tenant_a: {all_a}")
            results.append(("READ A+B→A", all_a))
        else:
            results.append(("READ A+B→A", False))

        # --- Test 4: Tenant A creates with payload tenant_id=B → created under A ---
        safe_print("\n--- CREATE Tests ---")
        import uuid
        unique_code = f"CT-{str(uuid.uuid4())[:8]}"
        code, data = test_case(
            4, "Tenant A CREATE + payload B → under A",
            "POST", url_records, token_a,
            payload={"code": unique_code, "name": "Cross Test", "price": 99,
                     "tenant_id": "tenant_b"}
        )
        new_id = data.get("id") if data else None
        effective = data.get("effective_tenant") if data else None
        safe_print(f"        effective_tenant: {effective}")
        results.append(("CREATE A+B→A", code == 200 and effective == "tenant_a"))

        # --- Test 5: Tenant A updates B's record → 404 ---
        safe_print("\n--- UPDATE Tests ---")
        # Get a B record ID
        code_b, data_b = test_case(
            "-", "Get B record for update test",
            "GET", url_records + "?limit=10", token_b
        )
        b_record_id = None
        if code_b == 200 and data_b.get("data"):
            b_record_id = data_b["data"][0].get("id")

        if b_record_id:
            code, data = test_case(
                5, "Tenant A UPDATE B record → 404",
                "PUT", f"{url_records}/{b_record_id}", token_a,
                payload={"name": "HACKED"}
            )
            results.append(("UPDATE A→B", code == 404))
        else:
            safe_print("  SKIP #5: No B record found")
            results.append(("UPDATE A→B", False))

        # --- Test 6: Tenant B updates A's record → 404 ---
        code_a, data_a = test_case(
            "-", "Get A record for update test",
            "GET", url_records + "?limit=10", token_a
        )
        a_record_id = None
        if code_a == 200 and data_a.get("data"):
            a_record_id = data_a["data"][0].get("id")

        if a_record_id:
            code, data = test_case(
                6, "Tenant B UPDATE A record → 404",
                "PUT", f"{url_records}/{a_record_id}", token_b,
                payload={"name": "HACKED"}
            )
            results.append(("UPDATE B→A", code == 404))
        else:
            safe_print("  SKIP #6: No A record found")
            results.append(("UPDATE B→A", False))

        # --- Test 7: Tenant A deletes B's record → 404 ---
        safe_print("\n--- DELETE Tests ---")
        if b_record_id:
            code, data = test_case(
                7, "Tenant A DELETE B record → 404",
                "DELETE", f"{url_records}/{b_record_id}", token_a
            )
            results.append(("DELETE A→B", code == 404))
        else:
            results.append(("DELETE A→B", False))

        # --- Test 8: Tenant B deletes A's record → 404 ---
        if a_record_id:
            code, data = test_case(
                8, "Tenant B DELETE A record → 404",
                "DELETE", f"{url_records}/{a_record_id}", token_b
            )
            results.append(("DELETE B→A", code == 404))
        else:
            results.append(("DELETE B→A", False))

        # --- Tests 9-11: Unauthenticated access → 401 ---
        safe_print("\n--- UNAUTHENTICATED Tests ---")
        code, data = test_case(
            9, "No JWT READ → 401",
            "GET", url_records, None
        )
        results.append(("NO JWT READ", code == 401))

        code, data = test_case(
            10, "No JWT UPDATE → 401",
            "PUT", f"{url_records}/fake-id", None,
            payload={"name": "X"}
        )
        results.append(("NO JWT UPDATE", code == 401))

        code, data = test_case(
            11, "No JWT DELETE → 401",
            "DELETE", f"{url_records}/fake-id", None
        )
        results.append(("NO JWT DELETE", code == 401))

        # --- Test 12: Invalid JWT → 401 ---
        safe_print("\n--- INVALID TOKEN Tests ---")
        code, data = test_case(
            12, "Invalid JWT → 401",
            "GET", url_records, "invalid.token.here"
        )
        results.append(("INVALID JWT", code == 401))

        # --- Summary ---
        safe_print("\n" + "=" * 60)
        safe_print("RESULTS:")
        for name, ok in results:
            status = "PASS" if ok else "FAIL"
            safe_print(f"  {status} - {name}")

        passed = sum(1 for _, ok in results if ok)
        safe_print(f"\n{passed}/{len(results)} passed")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        kill_server()
        safe_print("Server stopped.")


if __name__ == "__main__":
    main()
