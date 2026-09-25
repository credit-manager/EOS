"""Session management for user authentication."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional


# In-memory session storage
# Structure: {session_id: {user_id, tenant_id, token, ip, user_agent, created_at, last_active}}
_session_store: Dict[str, Dict] = {}


def create_session(
    user_id: int,
    tenant_id: int,
    token: str,
    ip: str,
    user_agent: str
) -> Dict:
    """
    Create a new session for a user.

    Args:
        user_id: The user's ID
        tenant_id: The tenant's ID
        token: The JWT token associated with this session
        ip: Client IP address
        user_agent: Client user agent string

    Returns:
        Dictionary containing session details
    """
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    session = {
        "session_id": session_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "token": token,
        "ip": ip,
        "user_agent": user_agent,
        "created_at": now.isoformat(),
        "last_active": now.isoformat(),
        "is_active": True
    }

    _session_store[session_id] = session
    return session


def get_user_sessions(user_id: int) -> List[Dict]:
    """
    Get all active sessions for a user.

    Args:
        user_id: The user's ID

    Returns:
        List of session dictionaries
    """
    return [
        session for session in _session_store.values()
        if session["user_id"] == user_id and session["is_active"]
    ]


def get_session(session_id: str) -> Optional[Dict]:
    """
    Get a specific session by ID.

    Args:
        session_id: The session's unique ID

    Returns:
        Session dictionary if found, None otherwise
    """
    session = _session_store.get(session_id)
    if session and session["is_active"]:
        return session
    return None


def revoke_session(session_id: str) -> bool:
    """
    Revoke a specific session.

    Args:
        session_id: The session's unique ID

    Returns:
        True if session was revoked, False if not found
    """
    if session_id in _session_store:
        _session_store[session_id]["is_active"] = False
        return True
    return False


def revoke_all_sessions(user_id: int) -> int:
    """
    Revoke all sessions for a user.

    Args:
        user_id: The user's ID

    Returns:
        Number of sessions revoked
    """
    count = 0
    for session in _session_store.values():
        if session["user_id"] == user_id and session["is_active"]:
            session["is_active"] = False
            count += 1
    return count


def update_session_activity(session_id: str) -> bool:
    """
    Update the last active timestamp for a session.

    Args:
        session_id: The session's unique ID

    Returns:
        True if session was updated, False if not found
    """
    if session_id in _session_store and _session_store[session_id]["is_active"]:
        _session_store[session_id]["last_active"] = datetime.now(timezone.utc).isoformat()
        return True
    return False


def cleanup_expired_sessions(max_age_hours: int = 24) -> int:
    """
    Remove sessions older than max_age_hours.

    Args:
        max_age_hours: Maximum session age in hours (default: 24)

    Returns:
        Number of sessions removed
    """
    now = datetime.now(timezone.utc)
    sessions_to_remove = []

    for session_id, session in _session_store.items():
        created_at = datetime.fromisoformat(session["created_at"])
        age_hours = (now - created_at).total_seconds() / 3600

        if age_hours > max_age_hours:
            sessions_to_remove.append(session_id)

    for session_id in sessions_to_remove:
        del _session_store[session_id]

    return len(sessions_to_remove)
