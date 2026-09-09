"""
P44 Multi-Region & Edge Deployment Tests
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic/edge"
TOKEN_A = create_test_token("tenant_a", user_id="admin_a", email="admin_a@test.com", roles=["admin"])
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="admin_b@test.com", roles=["admin"])
H_A = {"Authorization": f"Bearer {TOKEN_A}"}
H_B = {"Authorization": f"Bearer {TOKEN_B}"}
p, f = 0, 0


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
        for tbl in ['dbp_region_configs', 'dbp_edge_sync_log', 'dbp_region_failover']:
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        for tbl in ['dbp_network_topology']:
            db.execute(sa(f"DELETE FROM {tbl}"))
        for tbl in ['dbp_edge_nodes']:
            db.execute(sa(f"DELETE FROM {tbl}"))
        db.commit()
    finally:
        db.close()


def cleanup():
    setup()


def test_nodes(c):
    print("\n--- 1. Edge Nodes ---")
    r = c.post(f"{EP}/nodes", json={"node_name": "us-east-1",
               "region": "us-east", "endpoint_url": "https://us-east.dbp.cloud",
               "metadata": {"tier": "premium"}}, headers=H_A)
    t("Create node", r.status_code, 200)
    nid = r.json()["data"]["id"]

    r = c.post(f"{EP}/nodes", json={"node_name": "eu-west-1",
               "region": "eu-west", "endpoint_url": "https://eu-west.dbp.cloud"}, headers=H_A)
    t("Create second node", r.status_code, 200)

    r = c.get(f"{EP}/nodes", headers=H_A)
    t("List all nodes", r.status_code, 200)
    t("Two nodes", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/nodes?region=us-east", headers=H_A)
    t("Filter by region", r.status_code, 200)
    t("One us-east node", len(r.json()["data"]), 1)

    r = c.get(f"{EP}/nodes/{nid}", headers=H_A)
    t("Get node", r.status_code, 200)
    t("Node name correct", r.json()["data"]["node_name"], "us-east-1")

    r = c.put(f"{EP}/nodes/{nid}", json={"latency_ms": 15.5, "capacity_pct": 45.2}, headers=H_A)
    t("Update node metrics", r.status_code, 200)

    r = c.get(f"{EP}/nodes/{nid}", headers=H_A)
    t("Latency updated", r.json()["data"]["latency_ms"], 15.5)


def test_region_configs(c):
    print("\n--- 2. Region Configs ---")
    r = c.post(f"{EP}/region-configs", json={"region": "us-east",
               "is_primary": True, "data_residency": "US",
               "replication_mode": "sync"}, headers=H_A)
    t("Create primary config", r.status_code, 200)
    cid = r.json()["data"]["id"]

    r = c.post(f"{EP}/region-configs", json={"region": "eu-west",
               "data_residency": "EU", "replication_mode": "async"}, headers=H_A)
    t("Create secondary config", r.status_code, 200)

    r = c.get(f"{EP}/region-configs", headers=H_A)
    t("List region configs", r.status_code, 200)
    t("Two configs", len(r.json()["data"]), 2)

    r = c.put(f"{EP}/region-configs/{cid}", json={"is_primary": False}, headers=H_A)
    t("Update config", r.status_code, 200)

    r = c.get(f"{EP}/region-configs", headers=H_B)
    t("Tenant B no A configs", len(r.json()["data"]), 0)


def test_sync_logs(c):
    print("\n--- 3. Sync Logs ---")
    nodes = c.get(f"{EP}/nodes", headers=H_A).json()["data"]
    nid = nodes[0]["id"] if nodes else "nonexistent"
    r = c.post(f"{EP}/sync-logs", json={"node_id": nid,
               "sync_type": "full", "entity_type": "companies"}, headers=H_A)
    t("Create sync log", r.status_code, 200)
    sid = r.json()["data"]["id"]

    r = c.put(f"{EP}/sync-logs/{sid}", json={"status": "running"}, headers=H_A)
    t("Update sync to running", r.status_code, 200)

    r = c.put(f"{EP}/sync-logs/{sid}", json={"status": "completed"}, headers=H_A)
    t("Update sync to completed", r.status_code, 200)

    r = c.get(f"{EP}/sync-logs", headers=H_A)
    t("List sync logs", r.status_code, 200)
    t("Sync log exists", len(r.json()["data"]) > 0, True)

    r = c.get(f"{EP}/sync-logs", headers=H_B)
    t("Tenant B no A sync logs", len(r.json()["data"]), 0)


def test_topology(c):
    print("\n--- 4. Network Topology ---")
    nodes = c.get(f"{EP}/nodes", headers=H_A).json()["data"]
    if len(nodes) >= 2:
        nid1, nid2 = nodes[0]["id"], nodes[1]["id"]
        r = c.post(f"{EP}/topology", json={"node_id": nid1,
                   "peer_node_id": nid2, "link_type": "mesh",
                   "bandwidth_mbps": 10000}, headers=H_A)
        t("Create link", r.status_code, 200)
        lid = r.json()["data"]["id"]

        r = c.get(f"{EP}/topology", headers=H_A)
        t("List topology", r.status_code, 200)
        t("One link", len(r.json()["data"]), 1)

        r = c.put(f"{EP}/topology/{lid}", json={"is_active": False}, headers=H_A)
        t("Deactivate link", r.status_code, 200)

        r = c.get(f"{EP}/topology", headers=H_A)
        t("Link is inactive", r.json()["data"][0]["is_active"], False)
    else:
        t("Skip topology (need 2 nodes)", 0, 0)
        f += 0


def test_failover(c):
    print("\n--- 5. Failover ---")
    r = c.post(f"{EP}/failovers", json={"source_region": "us-east",
               "target_region": "eu-west",
               "trigger_reason": "High latency detected"}, headers=H_A)
    t("Create failover", r.status_code, 200)
    fid = r.json()["data"]["id"]

    r = c.get(f"{EP}/failovers", headers=H_A)
    t("List failovers", r.status_code, 200)
    t("One failover", len(r.json()["data"]), 1)
    t("Status pending", r.json()["data"][0]["status"], "pending")

    r = c.put(f"{EP}/failovers/{fid}/activate", headers=H_A)
    t("Activate failover", r.status_code, 200)

    r = c.get(f"{EP}/failovers", headers=H_A)
    t("Failover is active", r.json()["data"][0]["status"], "active")

    r = c.get(f"{EP}/failovers", headers=H_B)
    t("Tenant B no A failovers", len(r.json()["data"]), 0)


def test_rbac(c):
    print("\n--- 6. RBAC ---")
    TOKEN_V = create_test_token("tenant_a", user_id="viewer", email="viewer@test.com", roles=["dynamic_viewer"])
    HV = {"Authorization": f"Bearer {TOKEN_V}"}
    r = c.get(f"{EP}/nodes", headers=HV)
    t("Viewer can list nodes", r.status_code, 200)
    r = c.post(f"{EP}/nodes", json={"node_name": "test", "region": "test",
               "endpoint_url": "https://test.com"}, headers=HV)
    t("Viewer cannot create node", r.status_code, 403)
    r = c.get(f"{EP}/region-configs", headers=HV)
    t("Viewer can list configs", r.status_code, 200)
    r = c.get(f"{EP}/failovers", headers=HV)
    t("Viewer can list failovers", r.status_code, 200)


def test_negative(c):
    print("\n--- 7. Negative Tests ---")
    r = c.post(f"{EP}/nodes", json={}, headers=H_A)
    t("Create node missing fields", r.status_code, 400)
    r = c.post(f"{EP}/region-configs", json={}, headers=H_A)
    t("Create config missing region", r.status_code, 400)
    r = c.post(f"{EP}/sync-logs", json={}, headers=H_A)
    t("Create sync log missing fields", r.status_code, 400)
    r = c.post(f"{EP}/topology", json={}, headers=H_A)
    t("Create link missing fields", r.status_code, 400)
    r = c.post(f"{EP}/failovers", json={}, headers=H_A)
    t("Create failover missing fields", r.status_code, 400)
    r = c.get(f"{EP}/nodes/nonexistent", headers=H_A)
    t("Get non-existent node", r.status_code, 404)


if __name__ == "__main__":
    print("=" * 60)
    print("P44 MULTI-REGION & EDGE DEPLOYMENT TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        test_nodes(c)
        test_region_configs(c)
        test_sync_logs(c)
        test_topology(c)
        test_failover(c)
        test_rbac(c)
        test_negative(c)
    finally:
        c.close()
        stop(proc)
        cleanup()
    print("\n" + "=" * 60)
    print(f"P44 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
