"""
P48 IoT & Device Tests
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic/iot"
TOKEN_A = create_test_token("tenant_a", user_id="admin_a", email="admin_a@test.com", roles=["admin"])
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="admin_b@test.com", roles=["admin"])
H_A = {"Authorization": f"Bearer {TOKEN_A}"}
H_B = {"Authorization": f"Bearer {TOKEN_B}"}
p, f = 0, 0


def t(name, got, exp):
    global p, f
    if got == exp: p += 1
    else: f += 1; print(f"  FAIL - {name}: got {got!r}, expected {exp!r}")


def start():
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())
    time.sleep(5)
    return proc

def stop(proc):
    proc.terminate()
    try: proc.wait(timeout=5)
    except: proc.kill()

def setup():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        for tbl in ['dbp_iot_telemetry', 'dbp_iot_alerts', 'dbp_iot_rules',
                     'dbp_iot_firmware', 'dbp_iot_devices']:
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.commit()
    finally:
        db.close()

def cleanup(): setup()


def test_devices(c):
    print("\n--- 1. IoT Devices ---")
    r = c.post(f"{EP}/devices", json={"device_name": "Temp Sensor A",
               "device_type": "sensor", "device_model": "TS-100",
               "serial_number": "SN001", "location": "Factory Floor 1"}, headers=H_A)
    t("Create device", r.status_code, 200)
    did = r.json()["data"]["id"]
    r = c.post(f"{EP}/devices", json={"device_name": "Gateway B",
               "device_type": "gateway", "location": "Server Room"}, headers=H_A)
    t("Create second device", r.status_code, 200)
    r = c.get(f"{EP}/devices", headers=H_A)
    t("List devices", r.status_code, 200)
    t("Two devices", len(r.json()["data"]), 2)
    r = c.get(f"{EP}/devices/{did}", headers=H_A)
    t("Get device", r.status_code, 200)
    r = c.put(f"{EP}/devices/{did}", json={"firmware_version": "2.1.0"}, headers=H_A)
    t("Update device", r.status_code, 200)
    r = c.put(f"{EP}/devices/{did}/heartbeat", headers=H_A)
    t("Heartbeat", r.status_code, 200)
    r = c.get(f"{EP}/devices", headers=H_B)
    t("Tenant B no A devices", len(r.json()["data"]), 0)


def test_telemetry(c):
    print("\n--- 2. Telemetry ---")
    did = c.post(f"{EP}/devices", json={"device_name": "Sensor",
               "device_type": "sensor"}, headers=H_A).json()["data"]["id"]
    r = c.post(f"{EP}/telemetry", json={"device_id": did,
               "metric_name": "temperature", "metric_value": 23.5,
               "unit": "celsius"}, headers=H_A)
    t("Record telemetry", r.status_code, 200)
    r = c.post(f"{EP}/telemetry", json={"device_id": did,
               "metric_name": "humidity", "metric_value": 65.0}, headers=H_A)
    t("Record second telemetry", r.status_code, 200)
    r = c.get(f"{EP}/telemetry?device_id={did}", headers=H_A)
    t("List telemetry", r.status_code, 200)
    t("Two records", len(r.json()["data"]), 2)
    r = c.get(f"{EP}/telemetry", headers=H_B)
    t("Tenant B no A telemetry", len(r.json()["data"]), 0)


def test_alerts(c):
    print("\n--- 3. IoT Alerts ---")
    did = c.post(f"{EP}/devices", json={"device_name": "Sensor",
               "device_type": "sensor"}, headers=H_A).json()["data"]["id"]
    r = c.post(f"{EP}/alerts", json={"device_id": did,
               "alert_type": "threshold_exceeded", "severity": "high",
               "message": "Temperature above 30C"}, headers=H_A)
    t("Create alert", r.status_code, 200)
    aid = r.json()["data"]["id"]
    r = c.get(f"{EP}/alerts", headers=H_A)
    t("List alerts", r.status_code, 200)
    t("One alert", len(r.json()["data"]), 1)
    r = c.put(f"{EP}/alerts/{aid}/acknowledge", headers=H_A)
    t("Acknowledge alert", r.status_code, 200)


def test_rules(c):
    print("\n--- 4. IoT Rules ---")
    r = c.post(f"{EP}/rules", json={"rule_name": "Temp Alert",
               "device_type": "sensor",
               "condition_config": {"metric": "temperature", "op": ">", "value": 30},
               "action_config": {"type": "alert", "severity": "high"}}, headers=H_A)
    t("Create rule", r.status_code, 200)
    rid = r.json()["data"]["id"]
    r = c.get(f"{EP}/rules", headers=H_A)
    t("List rules", r.status_code, 200)
    t("One rule", len(r.json()["data"]), 1)
    r = c.put(f"{EP}/rules/{rid}", json={"is_active": False}, headers=H_A)
    t("Update rule", r.status_code, 200)


def test_firmware(c):
    print("\n--- 5. Firmware ---")
    r = c.post(f"{EP}/firmware", json={"device_type": "sensor",
               "version": "2.1.0", "changelog": "Bug fixes",
               "download_url": "https://releases.example.com/v2.1.0.bin",
               "file_size_bytes": 1048576}, headers=H_A)
    t("Create firmware", r.status_code, 200)
    r = c.get(f"{EP}/firmware", headers=H_A)
    t("List firmware", r.status_code, 200)
    t("One firmware", len(r.json()["data"]), 1)


def test_negative(c):
    print("\n--- 6. Negative Tests ---")
    r = c.post(f"{EP}/devices", json={}, headers=H_A)
    t("Create device missing fields", r.status_code, 400)
    r = c.post(f"{EP}/telemetry", json={}, headers=H_A)
    t("Record telemetry missing fields", r.status_code, 400)
    r = c.post(f"{EP}/alerts", json={}, headers=H_A)
    t("Create alert missing fields", r.status_code, 400)
    r = c.get(f"{EP}/devices/nonexistent", headers=H_A)
    t("Get non-existent device", r.status_code, 404)


if __name__ == "__main__":
    print("=" * 60)
    print("P48 IOT & DEVICE TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        test_devices(c); test_telemetry(c); test_alerts(c)
        test_rules(c); test_firmware(c); test_negative(c)
    finally:
        c.close(); stop(proc); cleanup()
    print("\n" + "=" * 60)
    print(f"P48 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
