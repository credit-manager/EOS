from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from typing import Iterator

from prometheus_client import Counter, Histogram

REQUESTS = Counter("eos_http_requests_total", "HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("eos_http_request_duration_seconds", "HTTP request duration", ["method", "path"])


def request_id() -> str:
    return uuid.uuid4().hex


@contextmanager
def observe_request(method: str, path: str) -> Iterator[None]:
    started = time.perf_counter()
    try:
        yield
    finally:
        REQUEST_LATENCY.labels(method, path).observe(time.perf_counter() - started)


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
