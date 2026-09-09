"""
P63 Observability Integration Test
Verifies all P63 components work:
- P63.1: /metrics endpoint (Prometheus format)
- P63.2: Custom metrics (counters, histograms, gauges)
- P63.3: Dashboard JSON files exist and are valid
- P63.4: Alert rules and AlertManager config exist and are valid
- P63.5: Structured logging middleware
- P63.6: Enhanced health checks (/health, /health/full, /health/live, /health/ready)
- P63.7: Log aggregation config exists
"""

import os
import sys
import json
import time
import socket
import subprocess
import pytest
import httpx

BASE = "http://127.0.0.1:8000"
_results = []
_server_proc = None
_server_port = None


def _find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _start_server():
    global _server_proc, _server_port
    port = _find_free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    # Wait for server to be ready
    for _ in range(15):
        time.sleep(1.0)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=2.0) as c:
                r = c.get("/health")
                if r.status_code == 200:
                    break
        except Exception:
            pass
    _server_proc = proc
    _server_port = port
    return proc, port


def _stop_server():
    global _server_proc
    if _server_proc:
        try:
            _server_proc.terminate()
            _server_proc.wait(timeout=5)
        except Exception:
            _server_proc.kill()
        _server_proc = None


def _record(name, passed):
    global _results
    _results.append((name, passed))
    status = "PASS" if passed else "FAIL"
    print(f"  {'✅' if passed else '❌'} {name} [{status}]")


@pytest.fixture(scope="module")
def client():
    """Start server, yield client, stop server."""
    proc, port = _start_server()
    with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=15.0) as c:
        yield c
    _stop_server()


# ═══════════════════════════════════════════════
# P63.1: Prometheus /metrics endpoint
# ═══════════════════════════════════════════════

def test_p63_1_metrics_endpoint(client):
    """P63.1: /metrics returns Prometheus text format."""
    r = client.get("/metrics")
    passed = r.status_code == 200 and "text/plain" in r.headers.get("content-type", "")
    _record("P63.1.1 /metrics returns 200 with text/plain", passed)

    body = r.text
    has_help = "# HELP" in body
    has_type = "# TYPE" in body
    _record("P63.1.2 /metrics contains HELP and TYPE lines", has_help and has_type)

    has_python = "python_" in body or "process_" in body
    _record("P63.1.3 /metrics contains process/platform metrics", has_python)


# ═══════════════════════════════════════════════
# P63.2: Custom metrics defined
# ═══════════════════════════════════════════════

def test_p63_2_custom_metrics():
    """P63.2: core/metrics.py defines custom Prometheus metrics."""
    try:
        from core.metrics import (
            HTTP_REQUESTS_TOTAL,
            HTTP_REQUEST_DURATION,
            AUTH_LOGINS_TOTAL,
            ACTIVE_TENANTS,
            ACTIVE_USERS,
            DB_CONNECTIONS_ACTIVE,
            DB_ERRORS_TOTAL,
            DB_QUERY_DURATION,
            ENTITIES_CREATED_TOTAL,
            MARKETPLACE_INSTALLS_TOTAL,
            BILLING_PAYMENTS_TOTAL,
        )
        _record("P63.2.1 Custom metrics importable from core.metrics", True)
    except ImportError as e:
        _record(f"P63.2.1 Custom metrics import: {e}", False)


# ═══════════════════════════════════════════════
# P63.3: Grafana Dashboard JSON files
# ═══════════════════════════════════════════════

def test_p63_3_dashboard_json():
    """P63.3: Dashboard JSON files exist and are valid."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dashboards_dir = os.path.join(base_dir, "grafana", "dashboards")

    # Overview dashboard
    overview_path = os.path.join(dashboards_dir, "eos-overview.json")
    exists_overview = os.path.exists(overview_path)
    _record("P63.3.1 grafana/dashboards/eos-overview.json exists", exists_overview)

    if exists_overview:
        try:
            with open(overview_path) as f:
                data = json.load(f)
            has_panels = len(data.get("panels", [])) >= 10
            has_uid = "uid" in data and data["uid"] == "eos-overview"
            has_title = "title" in data and data["title"] == "EOS Production Overview"
            _record("P63.3.2 Overview dashboard valid JSON with ≥10 panels", has_panels and has_uid and has_title)
        except Exception as e:
            _record(f"P63.3.2 Overview dashboard parse: {e}", False)

    # Business dashboard
    business_path = os.path.join(dashboards_dir, "eos-business.json")
    exists_business = os.path.exists(business_path)
    _record("P63.3.3 grafana/dashboards/eos-business.json exists", exists_business)

    if exists_business:
        try:
            with open(business_path) as f:
                data = json.load(f)
            has_panels = len(data.get("panels", [])) >= 5
            _record("P63.3.4 Business dashboard valid JSON with ≥5 panels", has_panels)
        except Exception as e:
            _record(f"P63.3.4 Business dashboard parse: {e}", False)

    # Provisioning configs
    ds_path = os.path.join(base_dir, "grafana", "provisioning", "datasources", "prometheus.yaml")
    _record("P63.3.5 Grafana datasource provisioning exists", os.path.exists(ds_path))

    dash_prov_path = os.path.join(base_dir, "grafana", "provisioning", "dashboards", "dashboard.yaml")
    _record("P63.3.6 Grafana dashboard provisioning exists", os.path.exists(dash_prov_path))


# ═══════════════════════════════════════════════
# P63.4: Alert Rules & AlertManager
# ═══════════════════════════════════════════════

def test_p63_4_alerting():
    """P63.4: Alert rules and AlertManager configs exist and are valid."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    monitoring_dir = os.path.join(base_dir, "monitoring")

    # Alert rules
    rules_path = os.path.join(monitoring_dir, "alert_rules.yml")
    exists_rules = os.path.exists(rules_path)
    _record("P63.4.1 monitoring/alert_rules.yml exists", exists_rules)

    if exists_rules:
        try:
            import yaml
            with open(rules_path) as f:
                data = yaml.safe_load(f)
            groups = data.get("groups", [])
            total_rules = sum(len(g.get("rules", [])) for g in groups)
            _record(f"P63.4.2 Alert rules valid YAML ({len(groups)} groups, {total_rules} rules)", total_rules >= 10)
        except ImportError:
            # yaml not installed, check file is non-empty
            with open(rules_path) as f:
                content = f.read()
            _record("P63.4.2 Alert rules file non-empty (yaml module not installed)", len(content) > 100)
        except Exception as e:
            _record(f"P63.4.2 Alert rules parse: {e}", False)

    # Prometheus config
    prom_path = os.path.join(monitoring_dir, "prometheus.yml")
    _record("P63.4.3 monitoring/prometheus.yml exists", os.path.exists(prom_path))

    # AlertManager config
    am_path = os.path.join(monitoring_dir, "alertmanager.yml")
    _record("P63.4.4 monitoring/alertmanager.yml exists", os.path.exists(am_path))


# ═══════════════════════════════════════════════
# P63.5: Structured Logging
# ═══════════════════════════════════════════════

def test_p63_5_structured_logging():
    """P63.5: Structured logging module exists and works."""
    try:
        from core.structured_logging import (
            setup_logging, RequestIdMiddleware, AuditLogger,
            JSONFormatter, HumanFormatter, audit_logger,
            request_id_var, tenant_id_var, user_id_var
        )
        _record("P63.5.1 core.structured_logging imports OK", True)

        # Test JSON formatter
        import logging
        formatter = JSONFormatter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "test message", (), None)
        output = formatter.format(record)
        parsed = json.loads(output)
        has_timestamp = "timestamp" in parsed
        has_level = parsed.get("level") == "INFO"
        has_request_id = "request_id" in parsed
        _record("P63.5.2 JSONFormatter produces valid JSON", has_timestamp and has_level and has_request_id)

        # Test context vars
        request_id_var.set("test-req-123")
        tenant_id_var.set("test-tenant-456")
        user_id_var.set("test-user-789")
        output2 = formatter.format(record)
        parsed2 = json.loads(output2)
        _record("P63.5.3 Context vars propagate to JSON logs",
                parsed2["request_id"] == "test-req-123" and
                parsed2["tenant_id"] == "test-tenant-456" and
                parsed2["user_id"] == "test-user-789")

        # Test audit logger
        audit_logger.log_event("test_event", tenant_id="t1", user_id="u1", details={"key": "value"})
        _record("P63.5.4 AuditLogger.log_event works", True)
    except ImportError as e:
        _record(f"P63.5.1 structured_logging import: {e}", False)
    except Exception as e:
        _record(f"P63.5 structured logging error: {e}", False)


# ═══════════════════════════════════════════════
# P63.6: Enhanced Health Checks
# ═══════════════════════════════════════════════

def test_p63_6_health_checks(client):
    """P63.6: Enhanced health check endpoints."""
    # /health (simple)
    r = client.get("/health")
    passed = r.status_code == 200 and r.json().get("status") == "healthy"
    _record("P63.6.1 /health returns 200 healthy", passed)

    # /health/full
    r = client.get("/health/full")
    data = r.json()
    has_checks = "checks" in data and len(data["checks"]) >= 4
    has_api = "api" in data.get("checks", {})
    has_db = "database" in data.get("checks", {})
    has_disk = "disk" in data.get("checks", {})
    has_memory = "memory" in data.get("checks", {})
    _record("P63.6.2 /health/full has api/database/disk/memory checks",
            r.status_code in (200, 503) and has_checks and has_api and has_db and has_disk and has_memory)

    # /health/live (liveness)
    r = client.get("/health/live")
    _record("P63.6.3 /health/live returns alive", r.status_code == 200 and r.json().get("status") == "alive")

    # /health/ready (readiness)
    r = client.get("/health/ready")
    _record("P63.6.4 /health/ready returns ready", r.status_code == 200 and r.json().get("status") == "ready")


# ═══════════════════════════════════════════════
# P63.7: Log Aggregation Config
# ═══════════════════════════════════════════════

def test_p63_7_log_aggregation():
    """P63.7: Log aggregation configuration exists."""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Loki config
    loki_path = os.path.join(base_dir, "monitoring", "loki.yml")
    has_loki = os.path.exists(loki_path)
    _record("P63.7.1 monitoring/loki.yml exists", has_loki)

    # Promtail config
    promtail_path = os.path.join(base_dir, "monitoring", "promtail.yml")
    has_promtail = os.path.exists(promtail_path)
    _record("P63.7.2 monitoring/promtail.yml exists", has_promtail)

    # Docker compose has grafana
    compose_path = os.path.join(base_dir, "docker-compose.yml")
    if os.path.exists(compose_path):
        with open(compose_path, encoding="utf-8") as f:
            content = f.read()
        has_grafana = "grafana:" in content
        has_prometheus = "prometheus:" in content
        has_alertmanager = "alertmanager:" in content
        has_postgres_exporter = "postgres-exporter:" in content
        has_node_exporter = "node-exporter:" in content
        _record("P63.7.3 docker-compose has monitoring stack",
                has_grafana and has_prometheus and has_alertmanager and has_postgres_exporter and has_node_exporter)
    else:
        _record("P63.7.3 docker-compose.yml exists", False)


# ═══════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    _results = []

    print("=" * 60)
    print("  P63 OBSERVABILITY INTEGRATION TEST")
    print("=" * 60)

    proc, port = _start_server()
    base_url = f"http://127.0.0.1:{port}"

    try:
        with httpx.Client(base_url=base_url, timeout=15.0) as client:
            print("\n--- P63.1: Prometheus /metrics ---")
            test_p63_1_metrics_endpoint(client)

            print("\n--- P63.2: Custom Metrics ---")
            test_p63_2_custom_metrics()

            print("\n--- P63.3: Dashboard JSON ---")
            test_p63_3_dashboard_json()

            print("\n--- P63.4: Alert Rules ---")
            test_p63_4_alerting()

            print("\n--- P63.5: Structured Logging ---")
            test_p63_5_structured_logging()

            print("\n--- P63.6: Health Checks ---")
            test_p63_6_health_checks(client)

            print("\n--- P63.7: Log Aggregation ---")
            test_p63_7_log_aggregation()

    finally:
        _stop_server(proc)

    # Summary
    passed = sum(1 for _, p in _results if p)
    total = len(_results)
    failed = total - passed

    print("\n" + "=" * 60)
    print(f"  P63 RESULTS: {passed}/{total} PASS, {failed} FAIL")
    print("=" * 60)

    if failed > 0:
        print("\nFailed tests:")
        for name, p in _results:
            if not p:
                print(f"  ❌ {name}")

    sys.exit(0 if failed == 0 else 1)