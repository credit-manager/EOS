"""
P36 AI-POWERED FEATURES TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN_A = create_test_token("tenant_a", user_id="admin_a", email="admin_a@test.com", roles=["admin"])
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="admin_b@test.com", roles=["admin"])
H_A = {"Authorization": f"Bearer {TOKEN_A}"}
H_B = {"Authorization": f"Bearer {TOKEN_B}"}
CID_A = "co_p36"
CID_B = "co_p36_b"
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
        for tbl in ("dbp_ai_anomalies", "dbp_ai_recommendations",
                     "dbp_ai_predictions", "dbp_ai_models"):
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_companies WHERE id IN ('co_p36','co_p36_b')"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p36','tenant_a','CP36A','Company P36 A')"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p36_b','tenant_b','CP36B','Company P36 B')"))
        db.commit()
    finally:
        db.close()


def cleanup_final():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        for tbl in ("dbp_ai_anomalies", "dbp_ai_recommendations",
                     "dbp_ai_predictions", "dbp_ai_models"):
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_companies WHERE id IN ('co_p36','co_p36_b')"))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    c = httpx.Client(timeout=30)

    print("=" * 60)
    print("P36 AI-POWERED FEATURES TESTS")
    print("=" * 60)

    setup()
    proc = start()

    try:
        # --- 1. Create Forecast Model ---
        print("\n--- 1. Create Forecast Model ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/ai-models",
                   json={"name": "Revenue Forecast", "model_type": "forecast",
                         "target_entity": "invoice", "config": {"horizon": 30}},
                   headers=H_A)
        t("Create model", r.status_code, 200)
        mid = r.json()["data"]["id"]
        t("Has id", bool(mid), True)

        # --- 2. Create Classification Model ---
        print("\n--- 2. Create Classification Model ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/ai-models",
                   json={"name": "Risk Classifier", "model_type": "classification",
                         "target_entity": "customer", "accuracy_score": 0.87},
                   headers=H_A)
        t("Create classification", r.status_code, 200)
        mid_cls = r.json()["data"]["id"]

        # --- 3. List Models ---
        print("\n--- 3. List Models ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/ai-models", headers=H_A)
        t("List models", r.status_code, 200)
        t("Has 2+ models", len(r.json()["data"]) >= 2, True)

        # --- 4. Get Model ---
        print("\n--- 4. Get Model ---")
        r = c.get(f"{BASE}{EP}/ai-models/{mid}", headers=H_A)
        t("Get model", r.status_code, 200)
        t("Name correct", r.json()["data"]["name"], "Revenue Forecast")
        t("Config not None", r.json()["data"]["config"] is not None, True)

        # --- 5. Update Model ---
        print("\n--- 5. Update Model ---")
        r = c.put(f"{BASE}{EP}/ai-models/{mid}",
                  json={"name": "Revenue Forecast v2", "accuracy_score": 0.91},
                  headers=H_A)
        t("Update model", r.status_code, 200)
        t("Name updated", r.json()["data"]["name"], "Revenue Forecast v2")

        # --- 6. Create Prediction ---
        print("\n--- 6. Create Prediction ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/ai-predictions",
                   json={"model_id": mid, "prediction_type": "revenue_next_month",
                         "predicted_value": {"amount": 50000, "currency": "USD"},
                         "confidence": 0.85, "entity_type": "invoice"},
                   headers=H_A)
        t("Create prediction", r.status_code, 200)
        pid = r.json()["data"]["id"]
        t("Has pred id", bool(pid), True)

        # --- 7. List Predictions ---
        print("\n--- 7. List Predictions ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/ai-predictions", headers=H_A)
        t("List predictions", r.status_code, 200)
        t("Has 1+ prediction", len(r.json()["data"]) >= 1, True)

        # --- 8. Get Prediction ---
        print("\n--- 8. Get Prediction ---")
        r = c.get(f"{BASE}{EP}/ai-predictions/{pid}", headers=H_A)
        t("Get prediction", r.status_code, 200)
        t("Status pending", r.json()["data"]["status"], "pending")
        pred_val = r.json()["data"]["predicted_value"]
        if isinstance(pred_val, str):
            import json
            pred_val = json.loads(pred_val)
        t("Predicted value has amount", pred_val.get("amount"), 50000)

        # --- 9. Acknowledge Prediction ---
        print("\n--- 9. Acknowledge Prediction ---")
        r = c.post(f"{BASE}{EP}/ai-predictions/{pid}/acknowledge",
                   json={"actual_value": {"amount": 48000, "currency": "USD"}},
                   headers=H_A)
        t("Ack prediction", r.status_code, 200)
        t("Status verified", r.json()["data"]["status"], "verified")
        actual = r.json()["data"]["actual_value"]
        if isinstance(actual, str):
            import json
            actual = json.loads(actual)
        t("Actual value set", actual.get("amount"), 48000)

        # --- 10. List Predictions by Status ---
        print("\n--- 10. List Predictions by Status ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/ai-predictions?status=verified", headers=H_A)
        t("Filter verified", r.status_code, 200)
        statuses = [pr["status"] for pr in r.json()["data"]]
        t("All verified", all(s == "verified" for s in statuses), True)

        # --- 11. Create Recommendation ---
        print("\n--- 11. Create Recommendation ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/ai-recommendations",
                   json={"recommendation_type": "upsell", "title": "Cross-sell Product B",
                         "description": "Customer shows high engagement",
                         "priority": "high", "impact_score": 0.75,
                         "entity_type": "customer", "entity_id": "cust-001"},
                   headers=H_A)
        t("Create recommendation", r.status_code, 200)
        rid = r.json()["data"]["id"]

        # --- 12. List Recommendations ---
        print("\n--- 12. List Recommendations ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/ai-recommendations", headers=H_A)
        t("List recs", r.status_code, 200)
        t("Has 1+ rec", len(r.json()["data"]) >= 1, True)

        # --- 13. Acknowledge Recommendation ---
        print("\n--- 13. Acknowledge Recommendation ---")
        r = c.post(f"{BASE}{EP}/ai-recommendations/{rid}/acknowledge", headers=H_A)
        t("Ack recommendation", r.status_code, 200)
        t("Status acknowledged", r.json()["data"]["status"], "acknowledged")
        t("Has acknowledged_by", bool(r.json()["data"]["acknowledged_by"]), True)

        # --- 14. Create Anomaly (auto deviation) ---
        print("\n--- 14. Create Anomaly ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/ai-anomalies",
                   json={"entity_type": "invoice", "metric_name": "total_amount",
                         "expected_value": 10000, "actual_value": 15000,
                         "severity": "high", "entity_id": "inv-001"},
                   headers=H_A)
        t("Create anomaly", r.status_code, 200)
        aid = r.json()["data"]["id"]

        # --- 15. Verify deviation_pct auto-calculated ---
        print("\n--- 15. Verify deviation_pct ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/ai-anomalies", headers=H_A)
        anomalies = r.json()["data"]
        match_a = [a for a in anomalies if a["id"] == aid]
        t("Found anomaly", len(match_a), 1)
        if match_a:
            t("Deviation 50%", match_a[0]["deviation_pct"], 50.0)

        # --- 16. List Anomalies ---
        print("\n--- 16. List Anomalies ---")
        t("Has 1+ anomaly", len(anomalies) >= 1, True)

        # --- 17. Resolve Anomaly ---
        print("\n--- 17. Resolve Anomaly ---")
        r = c.post(f"{BASE}{EP}/ai-anomalies/{aid}/resolve", headers=H_A)
        t("Resolve anomaly", r.status_code, 200)
        t("Status resolved", r.json()["data"]["status"], "resolved")
        t("Has resolved_by", bool(r.json()["data"]["resolved_by"]), True)

        # --- 18. Negative Deviation ---
        print("\n--- 18. Negative Deviation ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/ai-anomalies",
                   json={"entity_type": "invoice", "metric_name": "total_amount",
                         "expected_value": 10000, "actual_value": 8000},
                   headers=H_A)
        t("Create neg anomaly", r.status_code, 200)
        aid2 = r.json()["data"]["id"]
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/ai-anomalies", headers=H_A)
        neg = [a for a in r.json()["data"] if a["id"] == aid2]
        if neg:
            t("Negative deviation", neg[0]["deviation_pct"], -20.0)

        # --- 18b. Create second recommendation (stays pending) ---
        print("\n--- 18b. Create Pending Recommendation ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/ai-recommendations",
                   json={"recommendation_type": "retention", "title": "Loyalty Discount",
                         "description": "Customer at risk",
                         "priority": "medium"},
                   headers=H_A)
        t("Create pending rec", r.status_code, 200)

        # --- 19. Insights ---
        print("\n--- 19. Get Insights ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/ai-insights", headers=H_A)
        t("Get insights", r.status_code, 200)
        ins = r.json()["data"]
        t("Model count >= 2", ins["model_count"] >= 2, True)
        t("Active anomalies >= 1", ins["active_anomalies"] >= 1, True)
        t("Open recs >= 1", ins["open_recommendations"] >= 1, True)

        # --- 20. Tenant Isolation - Models ---
        print("\n--- 20. Tenant Isolation - Models ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_B}/ai-models",
                   json={"name": "B Model", "model_type": "anomaly_detection",
                         "target_entity": "payment"},
                   headers=H_B)
        t("Create B model", r.status_code, 200)

        r = c.get(f"{BASE}{EP}/companies/{CID_A}/ai-models", headers=H_A)
        names = [m["name"] for m in r.json()["data"]]
        t("B not visible to A", "B Model" not in names, True)

        # --- 21. Tenant Isolation - Predictions ---
        print("\n--- 21. Tenant Isolation - Predictions ---")
        mid_b = c.post(f"{BASE}{EP}/companies/{CID_B}/ai-models",
                       json={"name": "B Pred Model", "model_type": "forecast",
                             "target_entity": "customer"},
                       headers=H_B).json()["data"]["id"]
        r = c.post(f"{BASE}{EP}/companies/{CID_B}/ai-predictions",
                   json={"model_id": mid_b, "prediction_type": "churn",
                         "predicted_value": {"score": 0.3}},
                   headers=H_B)
        t("Create B prediction", r.status_code, 200)

        r = c.get(f"{BASE}{EP}/companies/{CID_A}/ai-predictions", headers=H_A)
        for pr in r.json()["data"]:
            t("Pred tenant isolation", pr["tenant_id"], "tenant_a")

        # --- 22. Tenant Isolation - Recommendations ---
        print("\n--- 22. Tenant Isolation - Recommendations ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_B}/ai-recommendations",
                   json={"recommendation_type": "discount", "title": "B Rec",
                         "description": "desc"},
                   headers=H_B)
        t("Create B rec", r.status_code, 200)

        r = c.get(f"{BASE}{EP}/companies/{CID_A}/ai-recommendations", headers=H_A)
        titles = [rec["title"] for rec in r.json()["data"]]
        t("B rec not visible to A", "B Rec" not in titles, True)

        # --- 23. Tenant Isolation - Anomalies ---
        print("\n--- 23. Tenant Isolation - Anomalies ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_B}/ai-anomalies",
                   json={"entity_type": "payment", "metric_name": "amount",
                         "expected_value": 500, "actual_value": 600},
                   headers=H_B)
        t("Create B anomaly", r.status_code, 200)

        r = c.get(f"{BASE}{EP}/companies/{CID_A}/ai-anomalies", headers=H_A)
        for a in r.json()["data"]:
            t("Anomaly tenant isolation", a["tenant_id"], "tenant_a")

        # --- 24. 404 Model ---
        print("\n--- 24. 404 Model ---")
        r = c.get(f"{BASE}{EP}/ai-models/nonexistent", headers=H_A)
        t("404 model", r.status_code, 404)

        # --- 25. 404 Prediction ---
        print("\n--- 25. 404 Prediction ---")
        r = c.get(f"{BASE}{EP}/ai-predictions/nonexistent", headers=H_A)
        t("404 prediction", r.status_code, 404)

        # --- 26. Missing Required Fields ---
        print("\n--- 26. Missing Required Fields ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/ai-models",
                   json={"name": "Incomplete"},
                   headers=H_A)
        t("Missing fields", r.status_code, 400)

        # --- 27. Filter by model_type ---
        print("\n--- 27. Filter by model_type ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/ai-models?model_type=forecast", headers=H_A)
        t("Filter forecast", r.status_code, 200)
        types = [m["model_type"] for m in r.json()["data"]]
        t("All forecast", all(mt == "forecast" for mt in types), True)

        # --- 28. Filter anomalies by severity ---
        print("\n--- 28. Filter anomalies by severity ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/ai-anomalies?severity=high", headers=H_A)
        t("Filter high severity", r.status_code, 200)
        sevs = [a["severity"] for a in r.json()["data"]]
        t("All high", all(s == "high" for s in sevs), True)

        # --- 29. Insights - Tenant B ---
        print("\n--- 29. Insights - Tenant B ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_B}/ai-insights", headers=H_B)
        t("B insights", r.status_code, 200)
        t("B model count >= 1", r.json()["data"]["model_count"] >= 1, True)

        # --- 30. Zero Deviation ---
        print("\n--- 30. Zero Deviation ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/ai-anomalies",
                   json={"entity_type": "invoice", "metric_name": "tax",
                         "expected_value": 500, "actual_value": 500},
                   headers=H_A)
        t("Create zero dev", r.status_code, 200)
        aid3 = r.json()["data"]["id"]
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/ai-anomalies", headers=H_A)
        zero = [a for a in r.json()["data"] if a["id"] == aid3]
        if zero:
            t("Zero deviation", zero[0]["deviation_pct"], 0.0)

    finally:
        stop(proc)
        cleanup_final()
        c.close()

    print(f"\n{'='*60}")
    print(f"P36 RESULTS: {p}/{p + f} PASSED, {f} FAILED")
    print(f"{'='*60}")

    sys.exit(0 if f == 0 else 1)
