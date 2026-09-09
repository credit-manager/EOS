"""
EOS System — In-Memory Rate Limiter

Sliding-window failure counter with temporary blocking. Designed for
brute-force protection on authentication endpoints without external
dependencies (Redis can replace this backend in production deployments).
"""
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, List, Tuple


class RateLimiter:
    """Tracks failures per key; blocks keys that exceed the threshold."""

    def __init__(self, max_failures: int = 5, window_seconds: int = 300, block_seconds: int = 600):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.block_seconds = block_seconds
        self._lock = threading.Lock()
        self._failures: Dict[str, Deque[float]] = defaultdict(deque)
        self._blocked_until: Dict[str, float] = {}
        self._last_cleanup = time.monotonic()

    def is_blocked(self, key: str) -> Tuple[bool, int]:
        """Return (blocked, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            self._cleanup_if_needed(now)
            until = self._blocked_until.get(key)
            if until is not None:
                if until > now:
                    return True, int(until - now) + 1
                del self._blocked_until[key]
            return False, 0

    def record_failure(self, key: str) -> Tuple[bool, int]:
        """Record a failure; returns (now_blocked, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            self._cleanup_if_needed(now)
            hits = self._failures[key]
            hits.append(now)
            while hits and hits[0] <= now - self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_failures:
                self._blocked_until[key] = now + self.block_seconds
                self._failures.pop(key, None)
                return True, self.block_seconds
            return False, 0

    def reset(self, key: str) -> None:
        """Clear failure history (e.g., after a successful login)."""
        with self._lock:
            self._failures.pop(key, None)
            self._blocked_until.pop(key, None)

    def _cleanup_if_needed(self, now: float) -> None:
        """Opportunistic sweep so idle keys don't accumulate forever."""
        if now - self._last_cleanup < 60:
            return
        self._last_cleanup = now
        stale = [k for k, until in self._blocked_until.items() if until <= now]
        for k in stale:
            del self._blocked_until[k]
        cutoff = now - self.window_seconds
        for k in [k for k, dq in self._failures.items() if not dq or dq[-1] <= cutoff]:
            del self._failures[k]


# Login brute-force guard: 5 failures / 5 min -> 10 min block.
login_limiter = RateLimiter(max_failures=5, window_seconds=300, block_seconds=600)
