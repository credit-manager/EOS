"""
P30 DOCUMENT MANAGEMENT TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
p, f = 0, 0
CID = "co_p30"

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
        db.execute(sa("DELETE FROM dbp_document_tags WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_document_versions WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_documents WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_doc_folders WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_companies WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p30', 'tenant_a', 'CO30', 'Test')"))
        db.commit()
    finally:
        db.close()

def test_folders(c):
    print("\n--- 1. Folders ---")
    r = c.post(f"{EP}/companies/{CID}/doc-folders", headers=H, json={"name": "Contracts"})
    t("Create root folder", r.status_code, 200)
    fid = r.json()["data"]["id"]

    r = c.post(f"{EP}/companies/{CID}/doc-folders", headers=H,
               json={"name": "2025 Contracts", "parent_id": fid})
    t("Create child folder", r.status_code, 200)
    child_fid = r.json()["data"]["id"]

    r = c.get(f"{EP}/companies/{CID}/doc-folders", headers=H)
    t("List all folders", r.status_code, 200)
    t("Has 2 folders", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/companies/{CID}/doc-folders", headers=H, params={"parent_id": fid})
    t("List child folders only", r.status_code, 200)
    t("Root has 1 child", len(r.json()["data"]), 1)
    t("Child parent_id set", r.json()["data"][0]["id"], child_fid)
    return fid, child_fid

def test_documents(c, fid):
    print("\n--- 2. Documents ---")
    r = c.post(f"{EP}/companies/{CID}/documents", headers=H, json={
        "title": "Quarterly Report Q3", "description": "Financial report",
        "doc_type": "report", "file_name": "q3_report.pdf",
        "file_size": 204800, "mime_type": "application/pdf",
        "access_level": "internal", "folder_id": fid
    })
    t("Create document", r.status_code, 200)
    did = r.json()["data"]["id"]

    r = c.post(f"{EP}/companies/{CID}/documents", headers=H, json={
        "title": "Employee Handbook", "doc_type": "policy",
        "file_name": "handbook.docx", "file_size": 102400
    })
    t("Create second document", r.status_code, 200)
    did2 = r.json()["data"]["id"]

    r = c.get(f"{EP}/documents/{did}", headers=H)
    t("Get document", r.status_code, 200)
    d = r.json()["data"]
    t("Title matches", d["title"], "Quarterly Report Q3")
    t("Doc type", d["doc_type"], "report")
    t("Folder assigned", d["folder_id"], fid)
    t("Auto version 1", d["latest_version"]["version_number"], 1)
    t("Version file name", d["latest_version"]["file_name"], "q3_report.pdf")

    r = c.get(f"{EP}/companies/{CID}/documents", headers=H)
    t("List documents", r.status_code, 200)
    t("Has 2 documents", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/companies/{CID}/documents", headers=H, params={"folder_id": fid})
    t("Filter by folder", len(r.json()["data"]), 1)

    r = c.put(f"{EP}/documents/{did}", headers=H,
              json={"title": "Quarterly Report Q3 Revised", "status": "archived"})
    t("Update document", r.status_code, 200)

    r = c.get(f"{EP}/documents/{did}", headers=H)
    t("Updated title", r.json()["data"]["title"], "Quarterly Report Q3 Revised")
    t("Updated status", r.json()["data"]["status"], "archived")

    r = c.get(f"{EP}/companies/{CID}/documents", headers=H, params={"search": "handbook"})
    t("Search by title", len(r.json()["data"]), 1)
    t("Search hit correct doc", r.json()["data"][0]["id"], did2)

    r = c.get(f"{EP}/companies/{CID}/documents", headers=H, params={"search": "financial"})
    t("Search by description", len(r.json()["data"]), 1)

    r = c.get(f"{EP}/companies/{CID}/documents", headers=H, params={"search": "nonexistent_xyz"})
    t("Search no match", len(r.json()["data"]), 0)
    return did, did2

def test_versions(c, did):
    print("\n--- 3. Versions ---")
    r = c.post(f"{EP}/documents/{did}/versions", headers=H, json={
        "file_name": "q3_report_v2.pdf", "file_size": 215000,
        "change_notes": "Added revenue breakdown"
    })
    t("Add version 2", r.status_code, 200)

    r = c.post(f"{EP}/documents/{did}/versions", headers=H, json={
        "file_name": "q3_report_final.pdf", "file_size": 220000,
        "change_notes": "Final approved copy"
    })
    t("Add version 3", r.status_code, 200)

    r = c.get(f"{EP}/documents/{did}/versions", headers=H)
    t("List versions", r.status_code, 200)
    versions = r.json()["data"]
    t("Has 3 versions", len(versions), 3)
    t("Version numbers ordered", [v["version_number"] for v in versions], [1, 2, 3])
    t("V2 change notes", versions[1]["change_notes"], "Added revenue breakdown")
    t("V3 file size", versions[2]["file_size"], 220000)

    r = c.get(f"{EP}/documents/{did}", headers=H)
    t("Latest is v3", r.json()["data"]["latest_version"]["version_number"], 3)

def test_tags(c, did, did2):
    print("\n--- 4. Tags ---")
    r = c.post(f"{EP}/documents/{did}/tags", headers=H, json={"tag": "finance"})
    t("Add tag finance", r.status_code, 200)

    r = c.post(f"{EP}/documents/{did}/tags", headers=H, json={"tag": "q3"})
    t("Add tag q3", r.status_code, 200)

    r = c.get(f"{EP}/documents/{did}", headers=H)
    t("Doc has 2 tags", len(r.json()["data"]["tags"]), 2)

    c.post(f"{EP}/documents/{did}/tags", headers=H, json={"tag": "finance"})
    r = c.get(f"{EP}/documents/{did}", headers=H)
    t("No duplicate tags", len(r.json()["data"]["tags"]), 2)

    r = c.delete(f"{EP}/documents/{did}/tags/q3", headers=H)
    t("Remove tag", r.status_code, 200)

    r = c.get(f"{EP}/documents/{did}", headers=H)
    t("Tag removed", r.json()["data"]["tags"], ["finance"])

    r = c.delete(f"{EP}/documents/{did}/tags/q3", headers=H)
    t("Remove missing tag 404", r.status_code, 404)

    r = c.get(f"{EP}/companies/{CID}/documents", headers=H, params={"tag": "finance"})
    t("Filter by tag", len(r.json()["data"]), 1)
    t("Tag filter correct doc", r.json()["data"][0]["id"], did)

def test_delete(c, fid, did, child_fid):
    print("\n--- 5. Deletes ---")
    r = c.delete(f"{EP}/doc-folders/{fid}", headers=H)
    t("Delete folder with docs blocked", r.status_code, 400)

    r = c.delete(f"{EP}/documents/{did}", headers=H)
    t("Delete document", r.status_code, 200)

    r = c.get(f"{EP}/documents/{did}", headers=H)
    t("Deleted doc gone", r.status_code, 404)

    r = c.delete(f"{EP}/doc-folders/{child_fid}", headers=H)
    t("Delete child folder", r.status_code, 200)

    r = c.delete(f"{EP}/doc-folders/{fid}", headers=H)
    t("Delete emptied folder", r.status_code, 200)

    r = c.delete(f"{EP}/doc-folders/{fid}", headers=H)
    t("Delete missing folder 404", r.status_code, 404)

def test_tenant_isolation(c, did2):
    print("\n--- 6. Tenant Isolation ---")
    TOKEN_B = create_test_token("tenant_b", user_id="b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}
    r = c.get(f"{EP}/companies/{CID}/doc-folders", headers=H_B)
    t("Tenant B no folders", len(r.json()["data"]), 0)
    r = c.get(f"{EP}/companies/{CID}/documents", headers=H_B)
    t("Tenant B no documents", len(r.json()["data"]), 0)
    r = c.get(f"{EP}/documents/{did2}", headers=H_B)
    t("Tenant B cannot fetch doc", r.status_code, 404)

if __name__ == "__main__":
    print("=" * 60)
    print("P30 DOCUMENT MANAGEMENT TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        fid, child_fid = test_folders(c)
        did, did2 = test_documents(c, fid)
        test_versions(c, did)
        test_tags(c, did, did2)
        test_delete(c, fid, did, child_fid)
        test_tenant_isolation(c, did2)
    finally:
        c.close(); stop(proc)
    print("\n" + "=" * 60)
    print(f"P30 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
