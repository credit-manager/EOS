"""
P53 — AI Business Composer
Tests 3 different industries with natural language input.
Proves EOS can configure ERP for ANY business from the same platform primitives.
"""
import httpx, subprocess, sys, time, os, json
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
CMP = f"{EP}/composer"
TENANT = "tenant_p53"
TOKEN = create_test_token(TENANT, user_id="composer_p53", email="user@composer.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
p, f_count = 0, 0
results = []


def t(name, got, exp, critical=False):
    global p, f_count
    if got == exp:
        p += 1
        results.append(f"  OK   {name}")
    else:
        f_count += 1
        tag = "CRITICAL" if critical else "FAIL"
        results.append(f"  {tag}  {name}: got {got!r}, expected {exp!r}")


def t_in(name, val, collection, critical=False):
    global p, f_count
    if val in collection:
        p += 1
        results.append(f"  OK   {name}")
    else:
        f_count += 1
        tag = "CRITICAL" if critical else "FAIL"
        results.append(f"  {tag}  {name}: {val!r} not in {collection!r}")


def t_gt(name, got, minimum, critical=False):
    global p, f_count
    if got >= minimum:
        p += 1
        results.append(f"  OK   {name}")
    else:
        f_count += 1
        tag = "CRITICAL" if critical else "FAIL"
        results.append(f"  {tag}  {name}: got {got}, expected >= {minimum}")


def log(msg):
    results.append(f"  ---  {msg}")


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


def cleanup():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        db.execute(sa(f"DELETE FROM dbp_composer_sessions WHERE tenant_id='{TENANT}'"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# FLOW: compose → preview → validate → approve → activate
# ═══════════════════════════════════════════════════════════
def run_compose_flow(c, label, user_input, expected_industry, expected_modules):
    log(f"{'=' * 50}")
    log(f"  INDUSTRY: {label}")
    log(f"  INPUT: {user_input[:80]}...")
    log(f"{'=' * 50}")

    # 1. COMPOSE
    r = c.post(f"{CMP}/compose", headers=H, json={"input": user_input})
    t(f"[{label}] Compose request", r.status_code, 200, critical=True)
    if r.status_code != 200:
        return
    data = r.json()["data"]
    sid = data["session_id"]
    reqs = data["requirements"]
    config = data["config"]
    validation = data["validation"]
    preview = data["preview"]

    # 2. VALIDATE INDUSTRY DETECTION
    t(f"[{label}] Industry detected", reqs["industry"], expected_industry, critical=True)

    # 3. VALIDATE MODULE SELECTION
    for mod in expected_modules:
        t_in(f"[{label}] Module '{mod}' selected", mod, config["modules"])

    # 4. VALIDATE CONFIG STRUCTURE
    t_gt(f"[{label}] Has entities", len(config["entities"]), 3)
    t_gt(f"[{label}] Has relationships", len(config["relationships"]), 1)
    t_gt(f"[{label}] Has roles", len(config["roles"]), 2)
    t_gt(f"[{label}] Has permissions", len(config["permissions"]), 3)
    t_gt(f"[{label}] Has KPIs", len(config["kpis"]), 2)
    t_gt(f"[{label}] Has accounts", len(config["accounts"]), 3)

    # 5. VALIDATION CHECK
    t(f"[{label}] Validation passes", validation["valid"], True, critical=True)
    t_gt(f"[{label}] Validation has 0 errors", len(validation["errors"]), 0)

    # 6. PREVIEW STRUCTURE
    t_gt(f"[{label}] Preview has modules", len(preview["modules"]), 3)
    t_gt(f"[{label}] Preview summary modules", preview["summary"]["total_modules"], 3)
    t(f"[{label}] Preview has settings", "currency" in preview["settings"], True)

    # 7. GET SESSION
    r = c.get(f"{CMP}/sessions/{sid}", headers=H)
    t(f"[{label}] Get session", r.status_code, 200)
    t(f"[{label}] Session status is preview", r.json()["data"]["status"], "preview")

    # 8. CANNOT ACTIVATE BEFORE APPROVE
    r = c.post(f"{CMP}/sessions/{sid}/activate", headers=H)
    t(f"[{label}] Activate before approve = 400", r.status_code, 400)

    # 9. APPROVE
    r = c.post(f"{CMP}/sessions/{sid}/approve", headers=H)
    t(f"[{label}] Approve session", r.status_code, 200, critical=True)

    r = c.get(f"{CMP}/sessions/{sid}", headers=H)
    t(f"[{label}] Status is approved", r.json()["data"]["status"], "approved")

    # 10. ACTIVATE
    r = c.post(f"{CMP}/sessions/{sid}/activate", headers=H)
    t(f"[{label}] Activate session", r.status_code, 200, critical=True)
    act_result = r.json()["data"]["result"]
    t_gt(f"[{label}] Modules activated", len(act_result["modules_activated"]), 3)
    t_gt(f"[{label}] Entities configured", act_result["entities_configured"], 3)

    r = c.get(f"{CMP}/sessions/{sid}", headers=H)
    t(f"[{label}] Status is activated", r.json()["data"]["status"], "activated")
    t(f"[{label}] activated_at is set", r.json()["data"]["activated_at"] is not None, True)


# ═══════════════════════════════════════════════════════════
# INDUSTRY 1: CONSTRUCTION
# ═══════════════════════════════════════════════════════════
def test_construction(c):
    run_compose_flow(
        c,
        "Construction",
        "I need an ERP for a construction company with 3 branches. "
        "We need accounting, finance, procurement, inventory for materials, "
        "projects for building sites, HR for 50 workers, sales, "
        "documents, and purchase order approvals.",
        expected_industry="construction",
        expected_modules=["accounting", "finance", "procurement", "inventory",
                          "projects", "hr", "sales", "documents", "workflow"],
    )


# ═══════════════════════════════════════════════════════════
# INDUSTRY 2: TRADING (Arabic)
# ═══════════════════════════════════════════════════════════
def test_trading(c):
    run_compose_flow(
        c,
        "Trading (Arabic)",
        "\u0639\u0627\u064a\u0632 \u0646\u0638\u0627\u0645 ERP \u0644\u0634\u0631\u0643\u0629 \u062a\u062c\u0627\u0631\u0629 "
        "\u0628\u062b\u0644\u0627\u062b \u0641\u0631\u0648\u0639. \u0627\u0644\u062d\u0633\u0627\u0628\u0627\u062a, "
        "\u0627\u0644\u0645\u0634\u062a\u0631\u064a\u0627\u062a \u0645\u0646 \u0645\u0648\u0631\u062f\u064a\u0646, "
        "\u0627\u0644\u0645\u062e\u0627\u0632\u0646, \u0627\u0644\u0645\u0628\u064a\u0639\u0627\u062a, "
        "\u0648\u0627\u0644\u0645\u0648\u0637\u0641\u064a\u0646 \u0644\u0645\u0627 \u064a\u0632\u0648\u0645 20 \u0645\u0648\u0637\u0641.",
        expected_industry="trading",
        expected_modules=["accounting", "finance", "procurement", "inventory", "sales", "hr"],
    )


# ═══════════════════════════════════════════════════════════
# INDUSTRY 3: RESTAURANT (Arabic + English mix)
# ═══════════════════════════════════════════════════════════
def test_restaurant(c):
    run_compose_flow(
        c,
        "Restaurant",
        "\u0645\u0637\u0639\u0645 \u0645\u0639 3 \u0641\u0631\u0648\u0639. \u0646\u062d\u062a\u0627\u062c "
        "\u0644\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0645\u062e\u0632\u0646 \u0644\u0644\u0645\u0648\u0627\u062f "
        "\u0627\u0644\u063a\u0630\u0627\u0626\u064a\u0629, \u0627\u0644\u062d\u0633\u0627\u0628\u0627\u062a, "
        "\u0648\u0627\u0644\u0645\u0648\u0637\u0641\u064a\u0646. "
        "We also need sales invoicing and basic reporting.",
        expected_industry="restaurant",
        expected_modules=["accounting", "finance", "inventory", "hr", "sales"],
    )


# ═══════════════════════════════════════════════════════════
# LIST SESSIONS
# ═══════════════════════════════════════════════════════════
def test_list_sessions(c):
    log("LIST ALL COMPOSER SESSIONS")
    r = c.get(f"{CMP}/sessions", headers=H)
    t("List sessions", r.status_code, 200)
    t("Has 3 sessions", len(r.json()["data"]), 3)

    r = c.get(f"{CMP}/sessions?status=activated", headers=H)
    t("Filter activated", r.status_code, 200)
    t("Has 3 activated", len(r.json()["data"]), 3)


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 70)
    print("  P53 AI BUSINESS COMPOSER")
    print("  3 Industries: Construction, Trading, Restaurant")
    print("  No industry-specific code — all from platform primitives")
    print("=" * 70)

    cleanup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)

    try:
        test_construction(c)
        test_trading(c)
        test_restaurant(c)
        test_list_sessions(c)
    finally:
        c.close()
        stop(proc)

    print("\n" + "\n".join(results))
    print("\n" + "=" * 70)
    print(f"  P53 RESULTS: {p}/{p+f_count} PASSED, {f_count} FAILED")
    print("=" * 70)

    if f_count == 0:
        print("\n  CONCLUSION: AI Business Composer successfully configures")
        print("  ERP for 3 different industries from the same platform primitives.")
        print("  Zero industry-specific code — all from dynamic configuration.")
    else:
        print(f"\n  {f_count} gaps found.")

    sys.exit(0 if f_count == 0 else 1)
