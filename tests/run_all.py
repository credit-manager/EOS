"""
EOS Platform — Full Test Suite Runner
Usage: python tests/run_all.py [--quick]
"""
import os
import subprocess
import sys
import time

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TESTS_DIR)

ACTIVE_TESTS = [
    ("Commerce Engine", "test_commerce_engine.py"),
    ("Restaurant ERP", "test_p707b.py"),
    ("Retail ERP", "test_retail_commerce.py"),
    ("Manufacturing ERP", "test_manufacturing.py"),
    ("Services ERP", "test_services.py"),
    ("Notifications", "test_notify.py"),
    ("Approvals", "test_approve.py"),
    ("Documents", "test_docs.py"),
    ("Analytics", "test_analytics.py"),
    ("Customization", "test_custom.py"),
    ("P72 Integration", "test_p72_2.py"),
    ("P72 Certification", "test_p72_full.py"),
    ("P73 Infrastructure", "test_p73_infra.py"),
    ("P73 Security", "test_p73_security.py"),
    ("P73 UX", "test_p73_ux.py"),
    ("P73 Final", "test_p73_final.py"),
    ("P77 Commercial SaaS", "test_p77_commercial.py"),
    ("P78 Architecture Review", "test_p78_review.py"),
    ("P79 Production Deploy", "test_p79_production.py"),
    ("P80 Critical Fixes", "test_p80_critical.py"),
    ("P81 Payments", "test_p81_payments.py"),
    ("P82-P85 Currency/Portal/Reports", "test_p82_85.py"),
]

def run_test(name, script):
    script_path = os.path.join(TESTS_DIR, script)
    if not os.path.exists(script_path):
        script_path = os.path.join(ROOT_DIR, script)

    start = time.time()
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=ROOT_DIR
    )
    elapsed = time.time() - start

    output = result.stdout
    passed = failed = total = 0
    for line in output.split("\n"):
        if "Results:" in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "passed,":
                    passed = int(parts[i-1])
                elif p == "failed,":
                    failed = int(parts[i-1])
                elif p == "total":
                    total = int(parts[i-1])

    status = "PASS" if failed == 0 else "FAIL"
    return status, passed, failed, total, elapsed

def main():
    quick = "--quick" in sys.argv
    if quick:
        tests = ACTIVE_TESTS[:6]
    else:
        tests = ACTIVE_TESTS

    print(f"{'='*60}")
    print("EOS PLATFORM — FULL TEST SUITE")
    print(f"{'='*60}\n")

    total_passed = 0
    total_failed = 0
    total_tests = 0
    results = []

    for name, script in tests:
        status, passed, failed, total, elapsed = run_test(name, script)
        total_passed += passed
        total_failed += failed
        total_tests += total
        results.append((name, status, passed, failed, total, elapsed))
        print(f"  [{status}] {name}: {passed}/{total} ({elapsed:.1f}s)")

    print(f"\n{'='*60}")
    print(f"RESULTS: {total_passed} passed, {total_failed} failed, {total_tests} total")
    print(f"{'='*60}")

    if total_failed == 0:
        print("ALL TESTS PASSED")
    else:
        print(f"FAILED: {total_failed} tests")

    return 0 if total_failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
