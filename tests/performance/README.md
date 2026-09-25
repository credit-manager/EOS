# EOS Performance Testing

Performance testing infrastructure for the EOS API.

## Directory Structure

```
tests/performance/
├── locustfile.py      # Locust distributed load tests
├── run_load_test.py   # Lightweight aiohttp-based load test
└── README.md          # This file
```

## Prerequisites

```bash
# For the lightweight load test (aiohttp only)
pip install aiohttp

# For Locust distributed tests
pip install locust
```

## Quick Start

### Lightweight Load Test (aiohttp)

The simplest way to run a performance test with no framework overhead:

```bash
# Default: 100 requests, 10 concurrent
python tests/performance/run_load_test.py http://localhost:8000

# Custom load profile
python tests/performance/run_load_test.py http://localhost:8000 --requests 500 --concurrency 50
```

**Output includes:**
- Overall success/failure rates
- Latency percentiles (P50, P95, P99)
- Per-endpoint breakdown
- Performance assessment against thresholds

### Locust Distributed Tests

For more sophisticated load testing with a web UI:

```bash
# Start Locust web UI
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Then open http://localhost:8089 in your browser
# Configure number of users and spawn rate, then start the test
```

#### Headless Mode

Run Locust without the web UI (useful for CI/CD):

```bash
locust -f tests/performance/locustfile.py \
    --host=http://localhost:8000 \
    --headless \
    -u 100 \          # 100 concurrent users
    -r 10 \           # Spawn 10 users per second
    --run-time 5m     # Run for 5 minutes
```

#### Distributed Mode

For high-load testing across multiple machines:

```bash
# On the master node
locust -f tests/performance/locustfile.py \
    --host=http://localhost:8000 \
    --master

# On each worker node
locust -f tests/performance/locustfile.py \
    --host=http://localhost:8000 \
    --worker \
    --master-host=192.168.1.100
```

## Endpoints Under Test

| Endpoint | Weight | Description |
|----------|--------|-------------|
| `GET /api/v1/health` | 10 | Health check (highest frequency) |
| `GET /api/v1/analytics/home` | 5 | Dashboard analytics |
| `GET /api/v1/metadata/entities` | 3 | Entity listing |
| `POST /api/v1/ai/copilot/chat` | 2 | AI copilot queries |
| `GET /api/v1/graph/map` | 2 | Business relationship graph |
| `GET /api/v1/workflows/instances` | 1 | Workflow management |
| `GET /api/v1/settings` | 1 | Application settings |

## Performance Thresholds

| Metric | Good | Warning | Fail |
|--------|------|---------|------|
| P50 Latency | < 100ms | < 250ms | >= 250ms |
| P95 Latency | < 500ms | < 1000ms | >= 1000ms |
| Success Rate | >= 99% | >= 95% | < 95% |

## CI/CD Integration

Add to your GitHub Actions workflow:

```yaml
- name: Run performance tests
  run: |
    pip install aiohttp
    python tests/performance/run_load_test.py http://localhost:8000 --requests 200 --concurrency 20
```

## Interpreting Results

- **Requests/sec**: Higher is better. Indicates throughput capacity.
- **P50 (Median)**: The "typical" response time experienced by users.
- **P95**: Response time that 95% of requests fall under. Key SLA metric.
- **P99**: Worst-case performance for most users. Investigate if high.
- **Success Rate**: Should be >99% under normal load. Drops indicate server errors or resource exhaustion.
