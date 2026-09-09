"""
P49 Blockchain & Immutable Audit Tests
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic/blockchain"
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
        for tbl in ['dbp_blockchain_verification', 'dbp_blockchain_records',
                     'dbp_blockchain_chains', 'dbp_immutable_audit']:
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_blockchain_nodes"))
        db.execute(sa("DELETE FROM dbp_blockchain_verification WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.commit()
    finally:
        db.close()

def cleanup(): setup()


def test_chains(c):
    print("\n--- 1. Blockchain Chains ---")
    r = c.post(f"{EP}/chains", json={"chain_name": "Audit Chain",
               "chain_type": "permissioned", "consensus": "pbft",
               "node_count": 3}, headers=H_A)
    t("Create chain", r.status_code, 200)
    cid = r.json()["data"]["id"]
    r = c.get(f"{EP}/chains", headers=H_A)
    t("List chains", r.status_code, 200)
    t("One chain", len(r.json()["data"]), 1)
    r = c.get(f"{EP}/chains/{cid}", headers=H_A)
    t("Get chain", r.status_code, 200)
    t("Chain name correct", r.json()["data"]["chain_name"], "Audit Chain")
    r = c.get(f"{EP}/chains", headers=H_B)
    t("Tenant B no A chains", len(r.json()["data"]), 0)


def test_nodes(c):
    print("\n--- 2. Blockchain Nodes ---")
    cid = c.post(f"{EP}/chains", json={"chain_name": "Test",
               "chain_type": "test"}, headers=H_A).json()["data"]["id"]
    r = c.post(f"{EP}/nodes", json={"chain_id": cid, "node_name": "Node 1",
               "node_url": "https://node1.chain.io", "role": "leader"}, headers=H_A)
    t("Create node", r.status_code, 200)
    nid = r.json()["data"]["id"]
    r = c.get(f"{EP}/nodes?chain_id={cid}", headers=H_A)
    t("List nodes", r.status_code, 200)
    t("One node", len(r.json()["data"]), 1)
    r = c.put(f"{EP}/nodes/{nid}", json={"status": "syncing"}, headers=H_A)
    t("Update node", r.status_code, 200)


def test_records(c):
    print("\n--- 3. Blockchain Records ---")
    cid = c.post(f"{EP}/chains", json={"chain_name": "Audit",
               "chain_type": "permissioned"}, headers=H_A).json()["data"]["id"]
    r = c.post(f"{EP}/records", json={"entity_type": "invoice",
               "entity_id": "inv_001",
               "content_hash": "a1b2c3d4e5f6", "chain_id": cid}, headers=H_A)
    t("Add record", r.status_code, 200)
    rid = r.json()["data"]["id"]
    r = c.post(f"{EP}/records", json={"entity_type": "company",
               "entity_id": "co_001",
               "content_hash": "f6e5d4c3b2a1", "chain_id": cid}, headers=H_A)
    t("Add second record", r.status_code, 200)
    r = c.get(f"{EP}/records", headers=H_A)
    t("List records", r.status_code, 200)
    t("Two records", len(r.json()["data"]), 2)
    r = c.post(f"{EP}/records/{rid}/verify", json={"verification_result": True}, headers=H_A)
    t("Verify record", r.status_code, 200)
    r = c.get(f"{EP}/verifications?record_id={rid}", headers=H_A)
    t("List verifications", r.status_code, 200)
    t("One verification", len(r.json()["data"]), 1)


def test_immutable_audit(c):
    print("\n--- 4. Immutable Audit ---")
    r = c.post(f"{EP}/immutable-audit", json={"entity_type": "invoice",
               "entity_id": "inv_001", "action": "created",
               "after_data": {"amount": 100}}, headers=H_A)
    t("Add immutable audit", r.status_code, 200)
    r = c.post(f"{EP}/immutable-audit", json={"entity_type": "invoice",
               "entity_id": "inv_001", "action": "updated",
               "before_data": {"amount": 100}, "after_data": {"amount": 150}}, headers=H_A)
    t("Add second audit", r.status_code, 200)
    r = c.get(f"{EP}/immutable-audit", headers=H_A)
    t("List immutable audit", r.status_code, 200)
    t("Two entries", len(r.json()["data"]), 2)
    r = c.get(f"{EP}/immutable-audit?entity_type=invoice", headers=H_A)
    t("Filter by entity", r.status_code, 200)
    t("Two invoice entries", len(r.json()["data"]), 2)
    r = c.get(f"{EP}/immutable-audit", headers=H_B)
    t("Tenant B no A audit", len(r.json()["data"]), 0)


def test_negative(c):
    print("\n--- 5. Negative Tests ---")
    r = c.post(f"{EP}/chains", json={}, headers=H_A)
    t("Create chain missing fields", r.status_code, 400)
    r = c.post(f"{EP}/nodes", json={}, headers=H_A)
    t("Create node missing fields", r.status_code, 400)
    r = c.post(f"{EP}/records", json={}, headers=H_A)
    t("Add record missing fields", r.status_code, 400)
    r = c.get(f"{EP}/chains/nonexistent", headers=H_A)
    t("Get non-existent chain", r.status_code, 404)


if __name__ == "__main__":
    print("=" * 60)
    print("P49 BLOCKCHAIN & IMMUTABLE AUDIT TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        test_chains(c); test_nodes(c); test_records(c)
        test_immutable_audit(c); test_negative(c)
    finally:
        c.close(); stop(proc); cleanup()
    print("\n" + "=" * 60)
    print(f"P49 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
