from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Mapping

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@dataclass(frozen=True, slots=True)
class SigningKey:
    kid: str
    private_key_pem: str
    public_key_pem: str
    created_at: datetime


class RSAKeyRing:
    """Asymmetric RS256 key ring with overlapping public keys during rotation."""

    def __init__(self, keys: tuple[SigningKey, ...]) -> None:
        if not keys:
            raise ValueError("At least one signing key is required")
        self._keys = {key.kid: key for key in keys}
        self._active_kid = keys[0].kid

    @classmethod
    def generate(cls, bits: int = 3072) -> "RSAKeyRing":
        if bits < 2048:
            raise ValueError("RSA signing keys must be at least 2048 bits")
        private = rsa.generate_private_key(public_exponent=65537, key_size=bits)
        private_pem = private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode("ascii")
        public_pem = private.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")
        kid = hashlib.sha256(public_pem.encode("ascii")).hexdigest()[:24]
        return cls((SigningKey(kid, private_pem, public_pem, datetime.now(timezone.utc)),))

    @property
    def active(self) -> SigningKey:
        return self._keys[self._active_kid]

    def rotate(self) -> SigningKey:
        fresh = RSAKeyRing.generate().active
        self._keys[fresh.kid] = fresh
        self._active_kid = fresh.kid
        return fresh

    def issue(self, claims: Mapping[str, object], ttl_seconds: int = 900) -> str:
        if ttl_seconds <= 0 or ttl_seconds > 3600:
            raise ValueError("Token TTL must be between 1 and 3600 seconds")
        now = datetime.now(timezone.utc)
        payload = dict(claims)
        payload.setdefault("iat", int(now.timestamp()))
        payload.setdefault("exp", int(now.timestamp()) + ttl_seconds)
        return jwt.encode(payload, self.active.private_key_pem, algorithm="RS256", headers={"kid": self.active.kid, "typ": "JWT"})

    def verify(self, token: str) -> dict[str, object]:
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not isinstance(kid, str) or kid not in self._keys:
                raise ValueError("Unknown signing key")
            return jwt.decode(
                token,
                self._keys[kid].public_key_pem,
                algorithms=["RS256"],
                options={"require": ["exp", "sub", "tenant_id", "actor_id"]},
            )
        except (jwt.PyJWTError, ValueError) as exc:
            raise ValueError("Invalid access token") from exc

    def jwks(self) -> dict[str, list[dict[str, object]]]:
        keys: list[dict[str, object]] = []
        for key in self._keys.values():
            public = serialization.load_pem_public_key(key.public_key_pem.encode("ascii"))
            if not isinstance(public, rsa.RSAPublicKey):
                raise ValueError("Signing key is not RSA")
            numbers = public.public_numbers()
            def b64(value: int) -> str:
                raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
                import base64
                return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
            keys.append({"kty": "RSA", "kid": key.kid, "use": "sig", "alg": "RS256", "n": b64(numbers.n), "e": b64(numbers.e)})
        return {"keys": keys}
