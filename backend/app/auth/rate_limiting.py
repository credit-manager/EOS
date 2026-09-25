"""Rate limiting for authentication endpoints."""

import time
from collections import defaultdict
from typing import Dict, List


# In-memory storage for rate limiting
# Structure: {key: [timestamp1, timestamp2, ...]}
_rate_limit_store: Dict[str, List[float]] = defaultdict(list)


def check_auth_rate_limit(key: str, max_attempts: int, window_seconds: int) -> bool:
    """
    Check if an action is allowed based on rate limiting.

    Args:
        key: Unique identifier for the rate limit (e.g., IP address, user_id)
        max_attempts: Maximum number of attempts allowed in the window
        window_seconds: Time window in seconds

    Returns:
        True if the action is allowed, False if rate limit exceeded
    """
    now = time.time()
    cutoff = now - window_seconds

    # Clean up old entries
    _rate_limit_store[key] = [
        timestamp for timestamp in _rate_limit_store[key]
        if timestamp > cutoff
    ]

    # Check if under limit
    if len(_rate_limit_store[key]) >= max_attempts:
        return False

    # Record this attempt
    _rate_limit_store[key].append(now)
    return True


def get_remaining_attempts(key: str, max_attempts: int, window_seconds: int) -> int:
    """
    Get the number of remaining attempts for a key.

    Args:
        key: Unique identifier for the rate limit
        max_attempts: Maximum number of attempts allowed in the window
        window_seconds: Time window in seconds

    Returns:
        Number of remaining attempts
    """
    now = time.time()
    cutoff = now - window_seconds

    # Clean up old entries
    _rate_limit_store[key] = [
        timestamp for timestamp in _rate_limit_store[key]
        if timestamp > cutoff
    ]

    return max(0, max_attempts - len(_rate_limit_store[key]))


def reset_rate_limit(key: str) -> None:
    """
    Reset rate limit for a key (e.g., after successful login).

    Args:
        key: Unique identifier to reset
    """
    _rate_limit_store[key] = []


def cleanup_old_entries(max_age_seconds: int = 3600) -> int:
    """
    Clean up entries older than max_age_seconds.

    Args:
        max_age_seconds: Maximum age of entries to keep (default: 1 hour)

    Returns:
        Number of keys cleaned up
    """
    now = time.time()
    cutoff = now - max_age_seconds

    keys_to_remove = []
    for key in _rate_limit_store:
        _rate_limit_store[key] = [
            timestamp for timestamp in _rate_limit_store[key]
            if timestamp > cutoff
        ]
        if not _rate_limit_store[key]:
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del _rate_limit_store[key]

    return len(keys_to_remove)
