import io
import json
import sys
import uuid

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import urllib.request

BASE = "http://127.0.0.1:8000"
passed = 0
failed = 0
total = 0

def api(method, path, data=None, token=""):
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = "Bearer " + token
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(BASE + path, body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"_err": e.code, "_body": e.read().decode()[:300]}

def test(name, cond):
    global passed, failed, total
    total += 1
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")

r = api("POST", "/api/v1/auth/login", {"email": "admin@demo.com", "password": "admin123"})
token = r["data"]["access_token"]
_rid = uuid.uuid4().hex[:6].upper()

print("=== P71.3 Universal Document Manager Tests ===\n")

# ═══ 1. FOLDERS ═══
print("--- Folders ---")
root = api("POST", "/docs/folders", {"folder_name": f"Trading Docs-{_rid}", "source_module": "trading"}, token)
test("1.1 Root folder created", "_err" not in root and "id" in root.get("data", {}))
root_id = root["data"]["id"]

sub = api("POST", "/docs/folders", {"folder_name": "Invoices", "parent_id": root_id, "source_module": "trading"}, token)
test("1.2 Subfolder created", "_err" not in sub)
sub_id = sub["data"]["id"]

dup = api("POST", "/docs/folders", {"folder_name": f"Trading Docs-{_rid}", "source_module": "trading"}, token)
test("1.3 Duplicate allowed (not unique constraint)", "_err" not in dup)

folders = api("GET", "/docs/folders", token=token)
test("1.4 Root folders listed", "_err" not in folders)

sub_list = api("GET", f"/docs/folders?parent_id={root_id}", token=token)
test("1.5 Subfolders listed", "_err" not in sub_list and len(sub_list["data"]) >= 1)

detail = api("GET", f"/docs/folders/{root_id}", token=token)
test("1.6 Folder detail has counts", "_err" not in detail and "file_count" in detail["data"])

not_found = api("GET", "/docs/folders/nonexistent", token=token)
test("1.7 Not found for bad ID", "_err" in not_found)

bad_parent = api("POST", "/docs/folders", {"folder_name": "Orphan", "parent_id": "bad-id"}, token)
test("1.8 Bad parent rejected", "_err" in bad_parent)

# ═══ 2. FILES ═══
print("\n--- Files ---")
f1 = api("POST", "/docs/files", {
    "file_name": f"invoice_{_rid}.pdf",
    "folder_id": sub_id,
    "mime_type": "application/pdf",
    "file_size": 102400,
    "storage_path": f"/uploads/invoices/{_rid}.pdf",
    "description": "Q4 2024 invoice",
    "tags": "invoice,q4,2024",
    "source_module": "trading",
    "source_id": uuid.uuid4().hex[:8]
}, token)
test("2.1 File uploaded", "_err" not in f1 and "id" in f1.get("data", {}))
file_id = f1["data"]["id"]

f2 = api("POST", "/docs/files", {
    "file_name": f"contract_{_rid}.docx",
    "folder_id": root_id,
    "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "file_size": 204800,
    "source_module": "services",
    "tags": "contract,legal"
}, token)
test("2.2 Second file uploaded", "_err" not in f2)

files = api("GET", "/docs/files", token=token)
test("2.3 Files listed", "_err" not in files and len(files["data"]) >= 2)

files_in_folder = api("GET", f"/docs/files?folder_id={sub_id}", token=token)
test("2.4 Files filtered by folder", "_err" not in files_in_folder and len(files_in_folder["data"]) == 1)

files_by_tag = api("GET", "/docs/files?tags=contract", token=token)
test("2.5 Files filtered by tag", "_err" not in files_by_tag)

files_by_module = api("GET", "/docs/files?source_module=trading", token=token)
test("2.6 Files filtered by module", "_err" not in files_by_module)

detail = api("GET", f"/docs/files/{file_id}", token=token)
test("2.7 File detail accessible", "_err" not in detail)
test("2.8 Detail has versions", "versions" in detail["data"] and len(detail["data"]["versions"]) >= 1)
test("2.9 Detail has shares list", "shares" in detail["data"])

# ═══ 3. VERSIONS ═══
print("\n--- Versions ---")
v1 = api("POST", f"/docs/files/{file_id}/versions", {
    "file_name": f"invoice_{_rid}_v2.pdf",
    "file_size": 105000,
    "change_notes": "Corrected tax amount"
}, token)
test("3.1 Version 2 uploaded", "_err" not in v1 and v1["data"]["version"] == 2)

v2 = api("POST", f"/docs/files/{file_id}/versions", {
    "file_name": f"invoice_{_rid}_v3.pdf",
    "file_size": 108000,
    "change_notes": "Added late fee"
}, token)
test("3.2 Version 3 uploaded", "_err" not in v2 and v2["data"]["version"] == 3)

detail2 = api("GET", f"/docs/files/{file_id}", token=token)
test("3.3 File updated to latest version", detail2["data"]["file_name"].endswith("v3.pdf"))
test("3.4 All versions tracked", len(detail2["data"]["versions"]) == 3)

# ═══ 4. SHARES ═══
print("\n--- Shares ---")
sh1 = api("POST", f"/docs/files/{file_id}/shares", {
    "shared_with_type": "user",
    "shared_with_value": "user@demo.com",
    "permission": "view"
}, token)
test("4.1 File shared (view)", "_err" not in sh1)
share_id = sh1["data"]["id"]

sh2 = api("POST", f"/docs/files/{file_id}/shares", {
    "shared_with_type": "role",
    "shared_with_value": "manager",
    "permission": "edit"
}, token)
test("4.2 File shared (edit, role)", "_err" not in sh2)

sh3 = api("POST", f"/docs/files/{file_id}/shares", {
    "shared_with_type": "all",
    "shared_with_value": "everyone",
    "permission": "view"
}, token)
test("4.3 File shared (all)", "_err" not in sh3)

detail3 = api("GET", f"/docs/files/{file_id}", token=token)
test("4.4 Shares listed in detail", len(detail3["data"]["shares"]) >= 3)

revoke = api("DELETE", f"/docs/files/{file_id}/shares/{share_id}", token=token)
test("4.5 Share revoked", "_err" not in revoke)

bad_share = api("POST", f"/docs/files/{file_id}/shares", {
    "shared_with_type": "wizard", "shared_with_value": "gandalf"
}, token)
test("4.6 Invalid share type rejected", "_err" in bad_share)

# ═══ 5. SEARCH ═══
print("\n--- Search ---")
search1 = api("GET", "/docs/search?q=invoice", token=token)
test("5.1 Search by name", "_err" not in search1 and len(search1["data"]) >= 1)

search2 = api("GET", "/docs/search?q=contract", token=token)
test("5.2 Search by tag", "_err" not in search2 and len(search2["data"]) >= 1)

search3 = api("GET", "/docs/search?q=nonexistent_xyz", token=token)
test("5.3 Empty search for no match", "_err" not in search3 and len(search3["data"]) == 0)

# ═══ 6. ARCHIVE ═══
print("\n--- Archive ---")
archive = api("PUT", f"/docs/files/{file_id}/archive", token=token)
test("6.1 File archived", "_err" not in archive and archive["data"]["is_archived"] is True)

files_after = api("GET", "/docs/files", token=token)
archived_ids = [f["id"] for f in files_after["data"] if f["id"] == file_id]
test("6.2 Archived file hidden from list", len(archived_ids) == 0)

unarchive = api("PUT", f"/docs/files/{file_id}/archive", token=token)
test("6.3 File unarchived", "_err" not in unarchive and unarchive["data"]["is_archived"] is False)

# ═══ 7. DELETE ═══
print("\n--- Delete ---")
del_share = api("DELETE", f"/docs/files/{file_id}/shares/{sh2['data']['id']}", token=token)
test("7.1 Share deleted", "_err" not in del_share)

del_file = api("DELETE", f"/docs/files/{file_id}", token=token)
test("7.2 File deleted", "_err" not in del_file)

del_gone = api("GET", f"/docs/files/{file_id}", token=token)
test("7.3 Deleted file gone", "_err" in del_gone)

del_bad = api("DELETE", "/docs/files/nonexistent", token=token)
test("7.4 Delete nonexistent rejected", "_err" in del_bad)

del_folder = api("DELETE", f"/docs/folders/{sub_id}", token=token)
test("7.5 Empty subfolder deleted", "_err" not in del_folder)

# ═══ 8. STATS ═══
print("\n--- Stats ---")
stats = api("GET", "/docs/stats", token=token)
test("8.1 Stats accessible", "_err" not in stats)
test("8.2 Has folders count", "folders" in stats["data"])
test("8.3 Has files count", "files" in stats["data"])
test("8.4 Has total size", "total_size_bytes" in stats["data"])
test("8.5 Has shares count", "shares" in stats["data"])

# ═══ 9. CROSS-INDUSTRY ═══
print("\n--- Cross-Industry ---")
rest_folder = api("POST", "/docs/folders", {"folder_name": f"Menus-{_rid}", "source_module": "restaurant"}, token)
test("9.1 Restaurant folder", "_err" not in rest_folder)

mfg_folder = api("POST", "/docs/folders", {"folder_name": f"BOM Specs-{_rid}", "source_module": "manufacturing"}, token)
test("9.2 Manufacturing folder", "_err" not in mfg_folder)

rest_file = api("POST", "/docs/files", {
    "file_name": f"menu_winter_{_rid}.pdf", "folder_id": rest_folder["data"]["id"],
    "mime_type": "application/pdf", "file_size": 50000,
    "source_module": "restaurant", "tags": "menu,winter"
}, token)
test("9.3 Restaurant file uploaded", "_err" not in rest_file)

# ═══ RESULTS ═══
print(f"\n{'='*50}")
print(f"P71.3 Results: {passed} passed, {failed} failed, {total} total")
if failed == 0:
    print("=== ALL TESTS PASSED ===")
else:
    print(f"=== {failed} TESTS FAILED ===")
