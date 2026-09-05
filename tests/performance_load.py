"""Deterministic performance/load validation for EOS API.

This suite is intentionally opt-in: CI runs the deterministic benchmark only
when EOS_RUN_PERFORMANCE=1. It uses the same ASGI application as production
without requiring an external server, and reports latency percentiles plus
throughput so regressions become measurable rather than anecdotal.
"""

from __future__ import annotations

import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest


pytestmark = pytest.mark.performance


def _enabled() -> bool:
    return os.getenv("EOS_RUN_PERFORMANCE", "0").lower() in {"1", "true", "yes"}


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(round((percentile / 100) * len(ordered))) - 1))
    return ordered[index]


def _request(client: httpx.Client, path: str) -> tuple[float, int]:
    started = time.perf_counter()
    response = client.get(path)
    elapsed_ms = (time.perf_counter() - started) * 1000
    return elapsed_ms, response.status_code


def test_health_performance_budget() -> None:
    if not _enabled():
        pytest.skip("Set EOS_RUN_PERFORMANCE=1 to run performance validation")

    from main import app

    warmup = 5
    samples = int(os.getenv("EOS_PERF_SAMPLES", "100"))
    concurrency = int(os.getenv("EOS_PERF_CONCURRENCY", "10"))
    p95_budget_ms = float(os.getenv("EOS_PERF_P95_BUDGET_MS", "500"))
    p99_budget_ms = float(os.getenv("EOS_PERF_P99_BUDGET_MS", "1000"))

    transport = httpx.ASGITransport(app=app)
    with httpx.Client(transport=transport, base_url="http://testserver") as client:
        for _ in range(warmup):
            response = client.get("/health")
            assert response.status_code < 500, response.text

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            results = list(pool.map(lambda _: _request(client, "/health"), range(samples)))
        wall_time = time.perf_counter() - started

    latencies = [latency for latency, status in results if status < 500]
    failures = sum(status >= 500 for _, status in results)
    assert failures == 0, f"Health endpoint returned {failures} server errors"
    assert len(latencies) == samples

    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)
    p99 = _percentile(latencies, 99)
    throughput = samples / wall_time if wall_time else float("inf")
    stdev = statistics.pstdev(latencies) if len(latencies) > 1 else 0.0

    print(
        "PERFORMANCE_RESULT "
        f"samples={samples} concurrency={concurrency} "
        f"p50_ms={p50:.2f} p95_ms={p95:.2f} p99_ms={p99:.2f} "
        f"mean_ms={statistics.mean(latencies):.2f} stdev_ms={stdev:.2f} "
        f"throughput_rps={throughput:.2f}"
    )

    assert p95 <= p95_budget_ms, f"p95 {p95:.2f}ms exceeds budget {p95_budget_ms:.2f}ms"
    assert p99 <= p99_budget_ms, f"p99 {p99:.2f}ms exceeds budget {p99_budget_ms:.2f}ms"
