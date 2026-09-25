"""Simple load test script — no external dependencies required.

This module provides a lightweight load testing tool using only Python
standard library + aiohttp. It's designed for quick performance validation
without requiring heavy frameworks like Locust.

Usage:
    python tests/performance/run_load_test.py http://localhost:8000
    python tests/performance/run_load_test.py http://localhost:8000 --requests 500 --concurrency 50

Requirements:
    pip install aiohttp
"""

import asyncio
import aiohttp
import time
import statistics
import sys
from dataclasses import dataclass


@dataclass
class TestResult:
    """Represents the result of a single HTTP request."""
    endpoint: str
    method: str
    status: int
    latency_ms: float
    success: bool


async def test_endpoint(
    session: aiohttp.ClientSession,
    url: str,
    method: str = "GET",
    json_data: dict = None,
    headers: dict = None,
) -> TestResult:
    """Execute a single HTTP request and measure latency.

    Args:
        session: Active aiohttp client session.
        url: Full URL to test.
        method: HTTP method (GET, POST, etc.).
        json_data: Optional JSON body for POST/PUT requests.
        headers: Optional request headers.

    Returns:
        TestResult with timing and status information.
    """
    start = time.monotonic()
    try:
        async with session.request(
            method, url, json=json_data, headers=headers
        ) as resp:
            latency = (time.monotonic() - start) * 1000
            return TestResult(
                endpoint=url,
                method=method,
                status=resp.status,
                latency_ms=latency,
                success=200 <= resp.status < 400,
            )
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return TestResult(
            endpoint=url,
            method=method,
            status=0,
            latency_ms=latency,
            success=False,
        )


def print_header(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_stats(label: str, values: list):
    """Print statistics for a list of numeric values."""
    if not values:
        print(f"  {label}: No data")
        return

    sorted_vals = sorted(values)
    p50 = sorted_vals[int(len(sorted_vals) * 0.50)]
    p95 = sorted_vals[int(len(sorted_vals) * 0.95)]
    p99 = sorted_vals[int(len(sorted_vals) * 0.99)]

    print(f"  {label}:")
    print(f"    Count:   {len(values)}")
    print(f"    Mean:    {statistics.mean(values):.1f}ms")
    print(f"    Median:  {p50:.1f}ms")
    print(f"    P95:     {p95:.1f}ms")
    print(f"    P99:     {p99:.1f}ms")
    print(f"    Min:     {min(values):.1f}ms")
    print(f"    Max:     {max(values):.1f}ms")
    print(f"    Stdev:   {statistics.stdev(values):.1f}ms" if len(values) > 1 else "")


async def authenticate(
    session: aiohttp.ClientSession, base_url: str
) -> str:
    """Register or login to obtain an auth token.

    Args:
        session: Active aiohttp client session.
        base_url: Base URL of the API.

    Returns:
        JWT access token string, or empty string on failure.
    """
    email = "load-test@test.com"
    password = "TestPass12345!"

    # Attempt registration
    await test_endpoint(
        session,
        f"{base_url}/api/v1/auth/register",
        "POST",
        json_data={
            "email": email,
            "password": password,
            "tenant_name": "Load Test",
        },
    )

    # Login to get token
    async with session.post(
        f"{base_url}/api/v1/auth/token",
        json={"email": email, "password": password},
    ) as resp:
        if resp.ok:
            data = await resp.json()
            return data.get("access_token", "")
    return ""


async def run_load_test(
    base_url: str,
    num_requests: int = 100,
    concurrency: int = 10,
):
    """Run a simple load test against the API.

    Distributes requests evenly across a predefined set of endpoints,
    measures latency percentiles, and reports success/failure rates.

    Args:
        base_url: Base URL of the API (e.g., http://localhost:8000).
        num_requests: Total number of requests to send.
        concurrency: Maximum number of concurrent requests.
    """
    print_header("EOS LOAD TEST CONFIGURATION")
    print(f"  Target:        {base_url}")
    print(f"  Requests:      {num_requests}")
    print(f"  Concurrency:   {concurrency}")

    async with aiohttp.ClientSession() as session:
        # Authenticate
        print("\n  Authenticating...")
        token = await authenticate(session, base_url)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        print(f"  Token:         {'obtained' if token else 'none (unauthenticated)'}")

        # Define endpoints to test (weighted by rotation)
        endpoints = [
            ("GET", "/api/v1/health", None),
            ("GET", "/api/v1/analytics/home", None),
            ("GET", "/api/v1/metadata/entities", None),
            ("GET", "/api/v1/graph/map", None),
            ("GET", "/api/v1/settings", None),
        ]

        # Create bounded tasks
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded_test(method, path, data):
            async with semaphore:
                return await test_endpoint(
                    session,
                    f"{base_url}{path}",
                    method,
                    json_data=data,
                    headers=headers,
                )

        # Dispatch all requests
        tasks = []
        for i in range(num_requests):
            method, path, data = endpoints[i % len(endpoints)]
            tasks.append(bounded_test(method, path, data))

        print(f"\n  Running {num_requests} requests with {concurrency} concurrency...")
        start_time = time.monotonic()
        results = await asyncio.gather(*tasks)
        total_time = time.monotonic() - start_time

        # Analyze results
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        latencies = [r.latency_ms for r in successful]

        # Overall summary
        print_header("OVERALL RESULTS")
        print(f"  Total requests:    {len(results)}")
        print(f"  Successful:        {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
        print(f"  Failed:            {len(failed)} ({len(failed)/len(results)*100:.1f}%)")
        print(f"  Total time:        {total_time:.2f}s")
        print(f"  Requests/sec:      {len(results)/total_time:.1f}")

        if latencies:
            print_stats("Latency Distribution", latencies)

        # Per-endpoint breakdown
        print_header("PER-ENDPOINT BREAKDOWN")
        endpoint_groups = {}
        for r in results:
            # Extract path name for grouping
            path_parts = r.endpoint.replace(base_url, "").split("/")
            key = f"{r.method} /{'/'.join(path_parts[-2:]) if len(path_parts) >= 2 else path_parts[-1]}"
            if key not in endpoint_groups:
                endpoint_groups[key] = []
            endpoint_groups[key].append(r)

        print(f"  {'Endpoint':<35} {'Success':<15} {'Avg Latency':<15} {'P95 Latency':<15}")
        print(f"  {'-'*35} {'-'*15} {'-'*15} {'-'*15}")

        for endpoint, group in sorted(endpoint_groups.items()):
            successes = sum(1 for r in group if r.success)
            group_latencies = [r.latency_ms for r in group if r.success]
            avg_lat = statistics.mean(group_latencies) if group_latencies else 0
            p95_lat = (
                sorted(group_latencies)[int(len(group_latencies) * 0.95)]
                if len(group_latencies) > 1
                else avg_lat
            )
            print(
                f"  {endpoint:<35} {successes}/{len(group):<12} {avg_lat:<15.1f} {p95_lat:<15.1f}"
            )

        # Error breakdown
        if failed:
            print_header("ERROR BREAKDOWN")
            error_groups = {}
            for r in failed:
                status = r.status if r.status != 0 else "timeout"
                if status not in error_groups:
                    error_groups[status] = []
                error_groups[status].append(r)

            for status, group in sorted(error_groups.items()):
                print(f"  Status {status}: {len(group)} failures")

        # Performance assessment
        print_header("PERFORMANCE ASSESSMENT")
        if latencies:
            p50 = sorted(latencies)[int(len(latencies) * 0.50)]
            p95 = sorted(latencies)[int(len(latencies) * 0.95)]

            if p50 < 100 and p95 < 500:
                print("  PASS: Response times within acceptable range")
            elif p50 < 250 and p95 < 1000:
                print("  WARN: Response times are borderline")
            else:
                print("  FAIL: Response times exceed acceptable thresholds")

            success_rate = len(successful) / len(results) * 100
            if success_rate >= 99:
                print("  PASS: Success rate >= 99%")
            elif success_rate >= 95:
                print("  WARN: Success rate is borderline")
            else:
                print("  FAIL: Success rate below 95%")
        else:
            print("  FAIL: No successful requests to analyze")


def parse_args():
    """Parse command-line arguments."""
    import argparse

    parser = argparse.ArgumentParser(
        description="EOS API Load Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_load_test.py http://localhost:8000
  python run_load_test.py http://localhost:8000 --requests 500 --concurrency 50
        """,
    )
    parser.add_argument(
        "base_url",
        nargs="?",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=100,
        help="Total number of requests (default: 100)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Maximum concurrent requests (default: 10)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        run_load_test(args.base_url, args.requests, args.concurrency)
    )
