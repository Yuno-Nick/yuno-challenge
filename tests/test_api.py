"""API integration tests for Oasis Rides Fraud Detection."""
import requests
import os
import time
import sys

API_URL = os.getenv("API_URL", "https://oasis-rides-api.onrender.com")

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name} {detail}")
    else:
        FAIL += 1
        print(f"  FAIL  {name} {detail}")


def get(endpoint, timeout=15):
    try:
        r = requests.get(f"{API_URL}{endpoint}", timeout=timeout)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def post(endpoint, timeout=30):
    try:
        r = requests.post(f"{API_URL}{endpoint}", timeout=timeout)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def main():
    print("=" * 55)
    print("  OASIS RIDES FRAUD DETECTION - TEST SUITE")
    print(f"  API: {API_URL}")
    print("=" * 55)
    print()

    # ---- Test 1: Health Check ----
    print("[1/8] Health Check")
    data = get("/api/health")
    test("API is healthy", data.get("status") == "healthy", f"-> {data}")

    # ---- Test 2: Dashboard Metrics ----
    print("\n[2/8] Dashboard Metrics")
    data = get("/api/dashboard/metrics")
    test("Returns metrics", "error" not in data)
    test("Has transactions", data.get("total_transactions", 0) > 0,
         f"-> {data.get('total_transactions', 0)} total")
    test("Has risk assessments", data.get("processed_transactions", 0) > 0,
         f"-> {data.get('processed_transactions', 0)} processed")
    test("Has high risk", data.get("high_risk_count", 0) > 0,
         f"-> {data.get('high_risk_count', 0)} high risk")
    test("Fraud rate > 0", data.get("fraud_rate", 0) > 0,
         f"-> {data.get('fraud_rate', 0)}%")
    test("Amount at risk > 0", data.get("total_amount_at_risk", 0) > 0,
         f"-> ${data.get('total_amount_at_risk', 0):,.2f}")

    # ---- Test 3: High-Risk Alerts ----
    print("\n[3/8] High-Risk Alerts")
    data = get("/api/dashboard/alerts?limit=5")
    alerts = data.get("data", [])
    test("Returns alerts", len(alerts) > 0, f"-> {len(alerts)} alerts")
    if alerts:
        alert = alerts[0]
        test("Alert has risk_score", "risk_score" in alert)
        test("Alert has transaction", "transactions" in alert and alert["transactions"])
        test("Alert has triggered_rules", "triggered_rules" in alert)
        test("Risk score >= 60", alert.get("risk_score", 0) >= 60,
             f"-> score={alert.get('risk_score')}")

    # ---- Test 4: Pattern Data ----
    print("\n[4/8] Pattern Data")
    data = get("/api/dashboard/patterns")
    test("Returns patterns", "error" not in data)
    countries = data.get("fraud_by_country", [])
    test("Has country data", len(countries) > 0, f"-> {len(countries)} countries")
    test("Has all 3 countries", len(countries) >= 3,
         f"-> {[c.get('country') for c in countries]}")
    test("Has score distribution", len(data.get("score_distribution", [])) > 0)
    test("Has time series", len(data.get("time_series", [])) > 0)

    # ---- Test 5: Pipeline Status ----
    print("\n[5/8] Pipeline Status")
    data = get("/api/pipeline/status")
    test("Returns status", "status" in data, f"-> {data.get('status')}")
    test("Has progress", "progress" in data, f"-> {data.get('progress')}%")
    test("Has total count", data.get("total", 0) >= 0)

    # ---- Test 6: Fraud Detection Accuracy ----
    print("\n[6/8] Fraud Detection Accuracy")
    metrics = get("/api/dashboard/metrics")
    total = metrics.get("processed_transactions", 0)
    high = metrics.get("high_risk_count", 0)
    medium = metrics.get("medium_risk_count", 0)
    low = metrics.get("low_risk_count", 0)
    test("Processed > 500 transactions", total > 500, f"-> {total}")
    test("Risk levels sum correctly", high + medium + low == total,
         f"-> {high}+{medium}+{low}={high + medium + low} vs {total}")
    test("Fraud rate between 5-50%", 5 < metrics.get("fraud_rate", 0) < 50,
         f"-> {metrics.get('fraud_rate')}%")
    test("Avg risk score between 5-50", 5 < metrics.get("avg_risk_score", 0) < 50,
         f"-> {metrics.get('avg_risk_score')}")

    # Check specific fraud patterns in alerts
    alerts_data = get("/api/dashboard/alerts?limit=100")
    all_alerts = alerts_data.get("data", [])
    rules_text = " ".join(
        str(a.get("triggered_rules", "")) for a in all_alerts
    )
    test("Detects velocity fraud", "VELOCITY" in rules_text)
    test("Detects geographic anomalies", "GEO_IMPOSSIBLE" in rules_text or "GEO_COUNTRY" in rules_text)
    test("Detects card testing", "CARD_TESTING" in rules_text)
    test("Detects collusion", "COLLUSION" in rules_text)
    test("Detects fraud rings", "FRAUD_RING" in rules_text)

    # ---- Test 7: ML Model ----
    print("\n[7/8] ML Model")
    ml_status = get("/api/ml/status")
    if ml_status.get("trained"):
        test("Model is trained", True)
        ml_metrics = get("/api/ml/metrics")
        model = ml_metrics.get("model", {})
        test("Has precision", model.get("precision_score") is not None,
             f"-> {model.get('precision_score')}")
        test("Has recall", model.get("recall_score") is not None,
             f"-> {model.get('recall_score')}")
        test("Has F1 score", model.get("f1_score") is not None,
             f"-> {model.get('f1_score')}")
        test("F1 > 0.5", (model.get("f1_score") or 0) > 0.5,
             f"-> {model.get('f1_score')}")
    else:
        print("  ML model not trained yet. Training now...")
        result = post("/api/ml/train", timeout=120)
        if "metrics" in result:
            m = result["metrics"]
            test("Training succeeded", True)
            test("Precision > 0.5", m.get("precision", 0) > 0.5, f"-> {m.get('precision')}")
            test("Recall > 0.5", m.get("recall", 0) > 0.5, f"-> {m.get('recall')}")
            test("F1 > 0.5", m.get("f1", 0) > 0.5, f"-> {m.get('f1')}")
        else:
            test("Training succeeded", False, f"-> {result.get('error', 'unknown')}")

    # ---- Test 8: Dashboard Endpoint ----
    print("\n[8/8] Dashboard Accessibility")
    dashboard_url = os.getenv("DASHBOARD_URL", "https://oasis-rides-dashboard.onrender.com")
    try:
        r = requests.get(dashboard_url, timeout=15)
        test("Dashboard responds", r.status_code == 200, f"-> HTTP {r.status_code}")
        test("Is Streamlit app", "streamlit" in r.text.lower() or "stApp" in r.text,
             "-> Streamlit detected")
    except Exception as e:
        test("Dashboard responds", False, f"-> {e}")

    # ---- Summary ----
    print()
    print("=" * 55)
    total_tests = PASS + FAIL
    print(f"  RESULTS: {PASS}/{total_tests} passed, {FAIL} failed")
    print(f"  {'ALL TESTS PASSED!' if FAIL == 0 else f'{FAIL} TESTS FAILED'}")
    print("=" * 55)

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
