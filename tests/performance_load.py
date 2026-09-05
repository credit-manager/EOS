"""Deterministic performance/load validation for the EOS API."""

from __future__ import annotations

import asyncio
import os
import statistics
import time

import httpx
import pytest


def _enabled() -> bool:
    return os.getenv("EOS_RUN_PERFORMANCE", "0").lower() in {"1", "true", "yes"}


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    rank = max(1, int((percentile / 100) * len(ordered) + 0.999999))
    return ordered[min(len(ordered), rank) - 1]


@pytest.mark.asyncio
async def test_health_performance_budget() -> None:
    if not _enabled():
        pytest.skip("Set EOS_RUN_PERFORMANCE=1 to run performance validation")

    from main import app

    warmup = 5
    samples = int(os.getenv("EOS_PERF_SAMPLES", "100"))
    concurrency = int(os.getenv("EOS_PERF_CONCURRENCY", "10"))
    p95_budget_ms = float(os.getenv("EOS_PERF_P95_BUDGET_MS", "500"))
    p99_budget_ms = float(os.getenv("EOS_PERF_P99_BUDGET_MS", "1000"))
    if samples < 1 or concurrency < 1:
        raise ValueError("EOS_PERF_SAMPLES and EOS_PERF_CONCURRENCY must be positive")

    transport = httpx.ASGITransport(app=app)
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", limits=limits) as client:
        for _ in range(warmup):
            response = await client.get("/health")
            assert response.status_code < 500, response.text

        async def request() -> tuple[float, int]:
            started = time.perf_counter()
            response = await client.get("/health")
            return (time.perf_counter() - started) * 1000, response.status_code

        started = time.perf_counter()
        results: list[tuple[float, int]] = []
        for offset in range(0, samples, concurrency):
            batch = min(concurrency, samples - offset)
            results.extend(await asyncio.gather(*(request() for _ in range(batch))))
        wall_time = time.perf_counter() - started

    latencies = [latency for latency, status in results if status < 500]
    failures = sum(status >= 500 for _, status in results)
    assert failures == 0, f"Health endpoint returned {failures} server errors"
    assert len(latencies) == samples

    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)
    p99 = _percentile(latencies, 99)
    mean = statistics.mean(latencies)
    stdev = statistics.pstdev(latencies) if len(latencies) > 1 else 0.0
    throughput = samples / wall_time if wall_time else float("inf")

    print(
        "PERFORMANCE_RESULT "
        f"samples={samples} concurrency={concurrency} "
        f"p50_ms={p50:.2f} p95_ms={p95:.2f} p99_ms={p99:.2f} "
        f"mean_ms={mean:.2f} stdev_ms={stdev:.2f} throughput_rps={throughput:.2f}"
    )

    assert p95 <= p95_budget_ms, f"p95 {p95:.2f}ms exceeds budget {p95_budget_ms:.2f}ms"
    assert p99 <= p99_budget_ms, f"p99 {p99:.2f}ms exceeds budget {p99_budget_ms:.2f}ms"
