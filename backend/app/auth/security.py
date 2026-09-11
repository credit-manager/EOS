import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from .models import AuthSession, TenantMembership, User

_ALGORITHM = "HS256"
_ISSUER = "2to-eos"
_HASH_ITERATIONS = 600_000
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    tenant_id: UUID
    role: str
    session_id: UUID


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _HASH_ITERATIONS)
    return f"pbkdf2_sha256${_HASH_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), _b64decode(salt), int(iterations))
        return hmac.compare_digest(digest, _b64decode(expected))
    except (TypeError, ValueError):
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(*, user_id: UUID, tenant_id: UUID, role: str) -> tuple[str, AuthSession]:
    settings = get_settings()
    now = int(time.time())
    session_id = uuid4()
    payload = {
        "iss": _ISSUER,
        "sub": str(user_id),
        "tid": str(tenant_id),
        "role": role,
        "sid": str(session_id),
        "iat": now,
        "exp": now + settings.access_token_ttl_seconds,
        "typ": "access",
    }
    header = {"alg": _ALGORITHM, "typ": "JWT"}
    encoded_header = _b64(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    signature = hmac.new(settings.jwt_secret.encode(), signing_input, hashlib.sha256).digest()
    token = f"{encoded_header}.{encoded_payload}.{_b64(signature)}"
    session = AuthSession(
        id=session_id,
        user_id=user_id,
        tenant_id=tenant_id,
        token_hash=_hash_token(token),
        expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
    )
    return token, session


def decode_access_token(token: str) -> Principal:
    settings = get_settings()
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".", 2)
        header = json.loads(_b64decode(encoded_header))
        payload = json.loads(_b64decode(encoded_payload))
        if header.get("alg") != _ALGORITHM or header.get("typ") != "JWT":
            raise ValueError("invalid token header")
        expected = hmac.new(
            settings.jwt_secret.encode(),
            f"{encoded_header}.{encoded_payload}".encode(),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(expected, _b64decode(encoded_signature)):
            raise ValueError("invalid token signature")
        if payload.get("iss") != _ISSUER or payload.get("typ") != "access":
            raise ValueError("invalid token claims")
        if int(payload["exp"]) <= int(time.time()):
            raise ValueError("token expired")
        return Principal(
            user_id=UUID(payload["sub"]),
            tenant_id=UUID(payload["tid"]),
            role=str(payload["role"]),
            session_id=UUID(payload["sid"]),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeError) as exc:
        raise HTTPException(status_code=401, detail="invalid or expired access token") from exc


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def require_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer access token required")
    token = credentials.credentials
    principal = decode_access_token(token)
    session = db.scalar(select(AuthSession).where(AuthSession.id == principal.session_id))
    now = datetime.now(UTC)
    if session is None or session.user_id != principal.user_id or session.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=401, detail="access session is not valid")
    if session.revoked_at is not None or _utc(session.expires_at) <= now:
        raise HTTPException(status_code=401, detail="access session is revoked or expired")
    if not hmac.compare_digest(session.token_hash, _hash_token(token)):
        raise HTTPException(status_code=401, detail="access session is not valid")
    user = db.scalar(select(User).where(User.id == principal.user_id, User.is_active.is_(True)))
    membership = db.scalar(
        select(TenantMembership).where(
            TenantMembership.user_id == principal.user_id,
            TenantMembership.tenant_id == principal.tenant_id,
        )
    )
    if user is None or membership is None or membership.role != principal.role:
        raise HTTPException(status_code=403, detail="tenant membership is not valid")
    return principal


def revoke_session(db: Session, session_id: UUID) -> None:
    session = db.scalar(select(AuthSession).where(AuthSession.id == session_id))
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        db.flush()
