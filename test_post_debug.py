import httpx
import subprocess
import time
import sys
import json

BASE = "http://127.0.0.1:8000/api/v1/dynamic"
PROJECT = r"D:\EOS\Eos final"

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

kill_server()
time.sleep(1)

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "main:app", "--port", "8000", "--host", "127.0.0.1"],
    cwd=PROJECT,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.PIPE,
)

time.sleep(3)

try:
    # Test with full payload including name_ar
    payload = {"code": "TEST-001", "name": "Test Account", "name_ar": "حساب تجريبي", "account_type": "asset"}
    r = httpx.post(f"{BASE}/entities/account/records", json=payload, timeout=10)
    data = r.json()
    print(f"Status: {r.status_code}")
    print(f"Keys: {list(data.keys())}")
    print(f"id: {data.get('id')}")
    print(f"tenant_capability: {data.get('tenant_capability')}")
    
    # Also test with tenant_id on NONE table
    payload2 = {
        "code": "TEST-002",
        "name": "Test Account 2",
        "name_ar": "حساب تجريبي 2",
        "account_type": "liability",
        "tenant_id": "SHOULD-NOT-BE-INSERTED"
    }
    r2 = httpx.post(f"{BASE}/entities/account/records", json=payload2, timeout=10)
    data2 = r2.json()
    print(f"\nWith tenant_id:")
    print(f"Status: {r2.status_code}")
    print(f"Keys: {list(data2.keys())}")
    print(f"id: {data2.get('id')}")
    print(f"tenant_capability: {data2.get('tenant_capability')}")

finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    kill_server()
