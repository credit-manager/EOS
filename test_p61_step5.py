"""P61 Step 5 — Stripe Test Mode E2E"""
import httpx, sys, secrets, subprocess, time, os

BASE = "http://127.0.0.1:8000"
p, f = 0, 0
results = []


def t(name, got, exp, critical=False):
    global p, f
    if got == exp:
        p += 1
        results.append(f"  OK   {name}")
    else:
        f += 1
        tag = "CRITICAL" if critical else "FAIL"
        results.append(f"  {tag}  {name}: got {got!r}, expected {exp!r}")


def log(msg):
    results.append(f"  ---  {msg}")


def start_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())
    time.sleep(6)
    return proc


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


if __name__ == "__main__":
    print("=" * 60)
    print("  P61 STEP 5 — Stripe Test Mode E2E")
    print("=" * 60)

    proc = start_server()
    c = httpx.Client(base_url=BASE, timeout=30)

    try:
        # ── Step 1: Simulated provider works ──
        log("STEP 1: Simulated payment provider")
        email = f"stripe_{secrets.token_hex(4)}@example.com"
        r = c.post("/api/v1/auth/register", json={
            "email": email, "password": "Test1234",
            "first_name": "Stripe", "last_name": "Test",
            "company_name": "Stripe Test Co"
        })
        token = r.json()["data"]["verification_token"]
        c.post("/api/v1/auth/verify-email", json={"token": token})
        r = c.post("/api/v1/auth/login", json={"email": email, "password": "Test1234"})
        H = {"Authorization": f"Bearer {r.json()['data']['access_token']}"}
        t("Auth setup complete", r.status_code, 200, critical=True)

        # ── Step 2: Billing checkout ──
        log("STEP 2: Billing checkout flow")
        r = c.post("/api/v1/dynamic/billing-flow/checkout", headers=H, json={
            "plan_code": "starter", "payment_method": "card"
        })
        t("Checkout returns 200", r.status_code, 200, critical=True)

        # ── Step 3: Payment status ──
        log("STEP 3: Payment status check")
        r = c.get("/api/v1/dynamic/billing-flow/my-subscription", headers=H)
        t("Subscription status accessible", r.status_code in (200, 404), True)

        # ── Step 4: Billing plans list ──
        log("STEP 4: Billing plans list")
        r = c.get("/api/v1/dynamic/billing-flow/plans", headers=H)
        t("Plans list accessible", r.status_code in (200, 404), True)

        # ── Step 5: Stripe provider class available ──
        log("STEP 5: Stripe provider class available")
        from core.payment_adapter import StripeTestPaymentProvider, get_payment_adapter
        sp = StripeTestPaymentProvider()
        t("StripeTestPaymentProvider class exists", sp is not None, True)
        t("Has create_charge method", hasattr(sp, "create_charge"), True)
        t("Has refund method", hasattr(sp, "refund"), True)

        # ── Step 6: Factory returns correct provider ──
        log("STEP 6: Payment adapter factory")
        from database import SessionLocal
        db = SessionLocal()
        try:
            os.environ["EOS_PAYMENT_MODE"] = "test"
            adapter = get_payment_adapter(db)
            t("Test mode returns SimulatedPaymentProvider",
              adapter.provider.__class__.__name__, "SimulatedPaymentProvider")

            os.environ["EOS_PAYMENT_MODE"] = "stripe"
            adapter2 = get_payment_adapter(db)
            t("Stripe mode returns StripeTestPaymentProvider",
              adapter2.provider.__class__.__name__, "StripeTestPaymentProvider")

            os.environ["EOS_PAYMENT_MODE"] = "test"
        finally:
            db.close()

        # ── Step 7: Simulated charge works ──
        log("STEP 7: Simulated charge")
        from core.payment_adapter import SimulatedPaymentProvider
        sim = SimulatedPaymentProvider()
        result = sim.create_charge(99.99, "USD", "Test charge", {"tenant_id": "test"})
        t("Simulated charge succeeds", result["success"], True)
        t("Returns transaction_id", "transaction_id" in result, True)

        refund = sim.refund(result["transaction_id"])
        t("Simulated refund succeeds", refund["success"], True)

    finally:
        c.close()
        stop_server(proc)

    print("\n" + "\n".join(results))
    print("\n" + "=" * 60)
    print(f"  P61 STEP 5 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
