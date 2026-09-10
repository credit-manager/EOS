"""Application-level encryption for tenant configuration secrets."""
from __future__ import annotations

import base64
import json
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


_SECRET_KEYS = {
    "secret", "secret_key", "api_key", "password", "token", "private_key",
    "client_secret", "access_token", "refresh_token", "signing_key",
}


def _key() -> bytes:
    raw = os.getenv("EOS_SECRET_ENCRYPTION_KEY", "").strip()
    if not raw:
        raise RuntimeError("EOS_SECRET_ENCRYPTION_KEY is required to encrypt application secrets")
    try:
        decoded = base64.urlsafe_b64decode(raw.encode("ascii"))
    except Exception as exc:
        raise RuntimeError("EOS_SECRET_ENCRYPTION_KEY must be a valid Fernet key") from exc
    if len(decoded) != 32:
        raise RuntimeError("EOS_SECRET_ENCRYPTION_KEY must decode to exactly 32 bytes")
    return raw.encode("ascii")


def contains_secret(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in _SECRET_KEYS:
                return True
            if contains_secret(child):
                return True
    elif isinstance(value, list):
        return any(contains_secret(item) for item in value)
    return False


def encrypt_text(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("secret value must be a non-empty string")
    return Fernet(_key()).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_text(token: str) -> str:
    if not isinstance(token, str) or not token:
        raise ValueError("encrypted secret must be a non-empty string")
    try:
        payload = Fernet(_key()).decrypt(token.encode("ascii"))
    except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError("Encrypted secret cannot be decrypted") from exc
    return payload.decode("utf-8")


def encrypt_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return Fernet(_key()).encrypt(payload).decode("ascii")


def decrypt_json(token: str) -> Any:
    try:
        payload = Fernet(_key()).decrypt(token.encode("ascii"))
    except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError("Encrypted configuration cannot be decrypted") from exc
    return json.loads(payload.decode("utf-8"))
