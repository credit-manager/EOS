"""
P52 — Productization & SaaS Launch
End-to-end onboarding simulation: New customer signs up, picks industry, configures ERP.
"""
import httpx, subprocess, sys, time, os, json
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
ONB = f"{EP}/onboarding"
TENANT = "tenant_p52"
TOKEN = create_test_token(TENANT, user_id="newuser_p52", email="user@al-omran.com", roles=["admin"])
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
        db.execute(sa(f"DELETE FROM dbp_tenant_onboarding WHERE tenant_id='{TENANT}'"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# STAGE 1: Browse Industry Templates
# ═══════════════════════════════════════════════════════════
def stage_1_industries(c):
    log("STAGE 1: Industry Template Discovery")

    r = c.get(f"{ONB}/industries", headers=H)
    t("List industries", r.status_code, 200)
    industries = r.json()["data"]
    t("Has 6+ industries", len(industries) >= 6, True)

    construction = None
    for ind in industries:
        if ind["industry_code"] == "construction":
            construction = ind
            break
    t("Construction template exists", construction is not None, True, critical=True)

    if construction:
        t("Has default modules", len(construction["default_modules"]) > 0, True)
        t("Has default accounts", len(construction["default_accounts"]) > 0, True)
        t("Has default settings", len(construction["default_settings"]) > 0, True)

    r = c.get(f"{ONB}/industries/ind-construction", headers=H)
    t("Get construction template", r.status_code, 200)
    t("Template has SAR currency", r.json()["data"]["default_settings"].get("base_currency"), "SAR")

    return construction


# ═══════════════════════════════════════════════════════════
# STAGE 2: Browse Module Definitions
# ═══════════════════════════════════════════════════════════
def stage_2_modules(c):
    log("STAGE 2: Module Definition Discovery")

    r = c.get(f"{ONB}/modules", headers=H)
    t("List all modules", r.status_code, 200)
    modules = r.json()["data"]
    t("Has 10+ modules", len(modules) >= 10, True)

    r = c.get(f"{ONB}/modules?category=financial", headers=H)
    t("Filter by category=financial", r.status_code, 200)
    t("Financial modules exist", len(r.json()["data"]) > 0, True)

    r = c.get(f"{ONB}/modules?category=operations", headers=H)
    t("Filter by category=operations", r.status_code, 200)
    t("Operations modules exist", len(r.json()["data"]) > 0, True)

    r = c.get(f"{ONB}/modules/mod-accounting", headers=H)
    t("Get accounting module", r.status_code, 200)

    return modules


# ═══════════════════════════════════════════════════════════
# STAGE 3: Start Onboarding
# ═══════════════════════════════════════════════════════════
def stage_3_start(c):
    log("STAGE 3: Start Onboarding")

    r = c.post(f"{ONB}/start", headers=H, json={
        "admin_user_id": "newuser_p52",
        "admin_email": "admin@al-omran.com",
    })
    t("Start onboarding", r.status_code, 200, critical=True)

    r = c.get(f"{ONB}/status", headers=H)
    t("Get onboarding status", r.status_code, 200)
    status = r.json()["data"]
    t("Status is in_progress", status["status"], "in_progress")
    t("Current step is industry_selection", status["current_step"], "industry_selection")
    t("Progress 0%", status["progress_percent"], 0)
    t("Steps completed is empty", len(status["steps_completed"]), 0)
    t("Steps remaining has all 7", len(status["steps_remaining"]), 7)


# ═══════════════════════════════════════════════════════════
# STAGE 4: Complete Step 1 — Industry Selection
# ═══════════════════════════════════════════════════════════
def stage_4_industry(c):
    log("STAGE 4: Step 1 — Industry Selection")

    r = c.post(f"{ONB}/complete-step", headers=H, json={
        "step": "industry_selection",
        "data": {"industry_code": "construction"},
    })
    t("Complete industry_selection", r.status_code, 200, critical=True)
    result = r.json()["data"]
    t("Advances to plan_selection", result["current_step"], "plan_selection")

    r = c.get(f"{ONB}/status", headers=H)
    status = r.json()["data"]
    t("1 step completed", len(status["steps_completed"]), 1)
    t("Industry code saved", status["industry_code"], "construction")


# ═══════════════════════════════════════════════════════════
# STAGE 5: Complete Step 2 — Plan Selection
# ═══════════════════════════════════════════════════════════
def stage_5_plan(c):
    log("STAGE 5: Step 2 — Plan Selection")

    r = c.post(f"{ONB}/complete-step", headers=H, json={
        "step": "plan_selection",
        "data": {"plan_id": "plan-enterprise", "plan_name": "Enterprise"},
    })
    t("Complete plan_selection", r.status_code, 200)
    result = r.json()["data"]
    t("Advances to company_creation", result["current_step"], "company_creation")

    r = c.get(f"{ONB}/status", headers=H)
    t("2 steps completed", len(r.json()["data"]["steps_completed"]), 2)


# ═══════════════════════════════════════════════════════════
# STAGE 6: Complete Step 3 — Company Creation
# ═══════════════════════════════════════════════════════════
def stage_6_company(c):
    log("STAGE 6: Step 3 — Company Creation")

    r = c.post(f"{ONB}/complete-step", headers=H, json={
        "step": "company_creation",
        "data": {
            "company_name": "Al-Omran Construction Co.",
            "company_name_ar": "\u0634\u0631\u0643\u0629 \u0627\u0644\u0639\u064f\u0645\u0631\u0627\u0646 \u0644\u0644\u0645\u0642\u0627\u0648\u0644\u0627\u062a",
            "company_id": "comp_p52_001",
            "city": "Riyadh",
            "country": "SA",
        },
    })
    t("Complete company_creation", r.status_code, 200, critical=True)
    result = r.json()["data"]
    t("Advances to template_application", result["current_step"], "template_application")

    r = c.get(f"{ONB}/status", headers=H)
    status = r.json()["data"]
    t("3 steps completed", len(status["steps_completed"]), 3)
    t("Company name saved", status["company_name"], "Al-Omran Construction Co.")


# ═══════════════════════════════════════════════════════════
# STAGE 7: Complete Step 4 — Template Application
# ═══════════════════════════════════════════════════════════
def stage_7_template(c):
    log("STAGE 7: Step 4 — Template Application")

    r = c.post(f"{ONB}/complete-step", headers=H, json={
        "step": "template_application",
        "data": {
            "template_applied": True,
            "accounts_created": 11,
            "settings_applied": True,
        },
    })
    t("Complete template_application", r.status_code, 200)
    result = r.json()["data"]
    t("Advances to module_configuration", result["current_step"], "module_configuration")

    r = c.get(f"{ONB}/status", headers=H)
    t("4 steps completed", len(r.json()["data"]["steps_completed"]), 4)


# ═══════════════════════════════════════════════════════════
# STAGE 8: Complete Step 5 — Module Configuration
# ═══════════════════════════════════════════════════════════
def stage_8_modules(c):
    log("STAGE 8: Step 5 — Module Configuration")

    r = c.post(f"{ONB}/complete-step", headers=H, json={
        "step": "module_configuration",
        "data": {
            "modules": ["accounting", "finance", "procurement", "inventory",
                         "projects", "hr", "sales", "documents", "workflow", "audit"],
        },
    })
    t("Complete module_configuration", r.status_code, 200)
    result = r.json()["data"]
    t("Advances to admin_setup", result["current_step"], "admin_setup")

    r = c.get(f"{ONB}/status", headers=H)
    status = r.json()["data"]
    t("5 steps completed", len(status["steps_completed"]), 5)
    t("10 modules selected", len(status["selected_modules"]), 10)


# ═══════════════════════════════════════════════════════════
# STAGE 9: Complete Step 6 — Admin Setup
# ═══════════════════════════════════════════════════════════
def stage_9_admin(c):
    log("STAGE 9: Step 6 — Admin Setup")

    r = c.post(f"{ONB}/complete-step", headers=H, json={
        "step": "admin_setup",
        "data": {
            "admin_name": "Ahmad Al-Mutairi",
            "admin_email": "admin@al-omran.com",
            "admin_role": "admin",
        },
    })
    t("Complete admin_setup", r.status_code, 200)
    result = r.json()["data"]
    t("Advances to activation", result["current_step"], "activation")

    r = c.get(f"{ONB}/status", headers=H)
    t("6 steps completed", len(r.json()["data"]["steps_completed"]), 6)


# ═══════════════════════════════════════════════════════════
# STAGE 10: Complete Step 7 — Activation
# ═══════════════════════════════════════════════════════════
def stage_10_activation(c):
    log("STAGE 10: Step 7 — Activation (Final)")

    r = c.post(f"{ONB}/complete-step", headers=H, json={
        "step": "activation",
        "data": {
            "activated_by": "newuser_p52",
            "activation_notes": "Construction company onboarding complete",
        },
    })
    t("Complete activation", r.status_code, 200, critical=True)
    result = r.json()["data"]
    t("Status is completed", result["status"], "completed")

    r = c.get(f"{ONB}/status", headers=H)
    status = r.json()["data"]
    t("Onboarded is True", status["onboarded"], True)
    t("All 7 steps completed", len(status["steps_completed"]), 7)
    t("0 steps remaining", len(status["steps_remaining"]), 0)
    t("Progress 100%", status["progress_percent"], 100)
    t("Activated_at is set", status["activated_at"] is not None, True)

    r = c.get(f"{ONB}/current", headers=H)
    t("Get current onboarding", r.status_code, 200)
    t("Onboarding shows completed", r.json()["data"]["status"], "completed")


# ═══════════════════════════════════════════════════════════
# STAGE 11: Verify Cannot Re-start
# ═══════════════════════════════════════════════════════════
def stage_11_cannot_restart(c):
    log("STAGE 11: Cannot Re-start Completed Onboarding")

    r = c.post(f"{ONB}/start", headers=H, json={})
    t("Re-start returns 400", r.status_code, 400)


# ═══════════════════════════════════════════════════════════
# STAGE 12: Admin Lists All Onboardings
# ═══════════════════════════════════════════════════════════
def stage_12_list(c):
    log("STAGE 12: Admin — List Onboardings")

    r = c.get(f"{ONB}/list", headers=H)
    t("List all onboardings", r.status_code, 200)
    t("Has at least 1 onboarding", len(r.json()["data"]) >= 1, True)

    r = c.get(f"{ONB}/list?status=completed", headers=H)
    t("Filter by status=completed", r.status_code, 200)
    t("Has completed onboarding", len(r.json()["data"]) >= 1, True)


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 70)
    print("  P52 PRODUCTIZATION & SAAS LAUNCH")
    print("  End-to-End Customer Onboarding Simulation")
    print("=" * 70)

    cleanup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)

    try:
        stage_1_industries(c)
        stage_2_modules(c)
        stage_3_start(c)
        stage_4_industry(c)
        stage_5_plan(c)
        stage_6_company(c)
        stage_7_template(c)
        stage_8_modules(c)
        stage_9_admin(c)
        stage_10_activation(c)
        stage_11_cannot_restart(c)
        stage_12_list(c)
    finally:
        c.close()
        stop(proc)

    print("\n" + "\n".join(results))
    print("\n" + "=" * 70)
    print(f"  P52 RESULTS: {p}/{p+f_count} PASSED, {f_count} FAILED")
    print("=" * 70)

    if f_count == 0:
        print("\n  CONCLUSION: EOS successfully supports end-to-end SaaS")
        print("  customer onboarding — from industry selection to ERP activation!")
    else:
        print(f"\n  {f_count} gaps found.")

    sys.exit(0 if f_count == 0 else 1)
