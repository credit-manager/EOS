import subprocess
import time
import httpx
import os
import sys

BASE = "http://127.0.0.1:8000/api/v1/dynamic"
PROJECT = r"D:\EOS\Eos final"

def safe_print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))

def test_get_schema():
    safe_print("1. GET schema...")
    r = httpx.get(f"{BASE}/entities/account/schema", timeout=10)
    data = r.json()
    safe_print(f"   Status: {r.status_code}")
    safe_print(f"   tenant_capability: {data.get('tenant_capability')}")
    safe_print(f"   real_columns: {data.get('real_columns')}")
    return r.status_code == 200

def test_get_records():
    safe_print("2. GET records...")
    r = httpx.get(f"{BASE}/entities/account/records", timeout=10)
    data = r.json()
    safe_print(f"   Status: {r.status_code}")
    safe_print(f"   Count: {data.get('count')}")
    safe_print(f"   tenant_applied: {data.get('tenant_applied')}")
    return r.status_code == 200

def test_post():
    safe_print("3. POST new record...")
    payload = {
        "code": "TEST-001",
        "name": "Test Account",
        "name_ar": "Test Arabic",
        "account_type": "asset"
    }
    safe_print(f"   Payload: {payload}")
    r = httpx.post(f"{BASE}/entities/account/records", json=payload, timeout=10)
    data = r.json()
    safe_print(f"   Status: {r.status_code}")
    safe_print(f"   id: {data.get('id')}")
    safe_print(f"   tenant_capability: {data.get('tenant_capability')}")
    return r.status_code == 200, data.get("id")

def test_post_with_tenant_id():
    safe_print("4. POST with tenant_id on NONE table...")
    payload = {
        "code": "TEST-002",
        "name": "Test Account 2",
        "name_ar": "Test Arabic 2",
        "account_type": "liability",
        "tenant_id": "SHOULD-NOT-BE-INSERTED"
    }
    safe_print(f"   Payload: {payload}")
    r = httpx.post(f"{BASE}/entities/account/records", json=payload, timeout=10)
    data = r.json()
    safe_print(f"   Status: {r.status_code}")
    safe_print(f"   id: {data.get('id')}")
    safe_print(f"   tenant_capability: {data.get('tenant_capability')}")
    return r.status_code == 200, data.get("id")

def test_update(record_id):
    safe_print(f"5. UPDATE record {record_id}...")
    payload = {"name": "Updated Account"}
    safe_print(f"   Payload: {payload}")
    r = httpx.put(f"{BASE}/entities/account/records/{record_id}", json=payload, timeout=10)
    data = r.json()
    safe_print(f"   Status: {r.status_code}")
    safe_print(f"   Response: {str(data)[:200]}")
    return r.status_code == 200

def test_delete(record_id):
    safe_print(f"6. DELETE record {record_id}...")
    r = httpx.delete(f"{BASE}/entities/account/records/{record_id}", timeout=10)
    data = r.json()
    safe_print(f"   Status: {r.status_code}")
    safe_print(f"   Response: {str(data)[:200]}")
    return r.status_code == 200

def kill_server():
    try:
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
        for line in result.stdout.split("\n"):
            if ":8000" in line and "LISTENING" in line:
                parts = line.split()
                pid = parts[-1]
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
    except Exception:
        pass

def main():
    kill_server()
    time.sleep(1)

    safe_print("Starting server...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", "8000", "--host", "127.0.0.1"],
        cwd=PROJECT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    time.sleep(3)

    try:
        results = []

        ok = test_get_schema()
        results.append(("GET schema", ok))

        ok = test_get_records()
        results.append(("GET records", ok))

        ok, post_id_1 = test_post()
        results.append(("POST (no tenant)", ok))

        ok, post_id_2 = test_post_with_tenant_id()
        results.append(("POST (with tenant_id)", ok))

        if post_id_1:
            ok = test_update(post_id_1)
            results.append(("UPDATE", ok))
        else:
            safe_print("   SKIP UPDATE - no record id")
            results.append(("UPDATE", False))

        if post_id_2:
            ok = test_delete(post_id_2)
            results.append(("DELETE", ok))
        else:
            safe_print("   SKIP DELETE - no record id")
            results.append(("DELETE", False))

        safe_print("\n" + "=" * 50)
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
