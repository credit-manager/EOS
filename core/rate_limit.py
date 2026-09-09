"""
RATE LIMITING MODULE
====================
Simple in-memory rate limiter for FastAPI endpoints.
"""

import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from collections import defaultdict


class RateLimiter:
    """
    In-memory sliding window rate limiter.
    
    Usage:
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        
        @router.get("/endpoint", dependencies=[Depends(limiter.check)])
        async def endpoint():
            ...
    """
    
    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        key_func=None
    ):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Window duration in seconds
            key_func: Function to extract rate limit key from request
                     Default: client IP address
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_func = key_func or self._default_key_func
        
        # In-memory storage: {key: [(timestamp, count), ...]}
        self._requests: Dict[str, list] = defaultdict(list)
    
    def _default_key_func(self, request: Request) -> str:
        """Default key function: client IP address."""
        # Check for X-Forwarded-For (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _cleanup(self, key: str) -> None:
        """Remove expired entries for a key."""
        now = time.time()
        cutoff = now - self.window_seconds
        self._requests[key] = [
            ts for ts in self._requests[key]
            if ts > cutoff
        ]
    
    def check(self, request: Request) -> None:
        """
        Check if request is allowed.
        
        Raises HTTPException if rate limit exceeded.
        """
        key = self.key_func(request)
        
        # Cleanup old entries
        self._cleanup(key)
        
        # Check count
        if len(self._requests[key]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later.",
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                }
            )
        
        # Record request
        self._requests[key].append(time.time())
    
    def get_remaining(self, request: Request) -> int:
        """Get remaining requests for current window."""
        key = self.key_func(request)
        self._cleanup(key)
        return max(0, self.max_requests - len(self._requests[key]))
    
    def get_reset_time(self, request: Request) -> float:
        """Get seconds until rate limit resets."""
        key = self.key_func(request)
        self._cleanup(key)
        
        if not self._requests[key]:
            return 0
        
        oldest = min(self._requests[key])
        reset_time = oldest + self.window_seconds - time.time()
        return max(0, reset_time)


# Pre-configured rate limiters
# Usage: dependencies=[Depends(default_limiter.check)]

# General API: 100 requests per minute
default_limiter = RateLimiter(max_requests=100, window_seconds=60)

# Auth endpoints: 10 requests per minute (stricter)
auth_limiter = RateLimiter(max_requests=10, window_seconds=60)

# Read endpoints: 200 requests per minute (more lenient)
read_limiter = RateLimiter(max_requests=200, window_seconds=60)

# Write endpoints: 200 requests per minute (moderate)
write_limiter = RateLimiter(max_requests=200, window_seconds=60)
