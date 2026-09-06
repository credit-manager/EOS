from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import base64
import hashlib
import json
from typing import Mapping

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa


@dataclass(frozen=True, slots=True)
class SigningKey:
    kid: str
    private_key_pem: str
    public_key_pem: str
    created_at: datetime


class RSAKeyRing:
    """In-process asymmetric signing key ring; persist/rotate keys through the deployment secret store."""

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
            encoding=__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM,
            format=__import__("cryptography").hazmat.primitives.serialization.PrivateFormat.PKCS8,
            encryption_algorithm=__import__("cryptography").hazmat.primitives.serialization.NoEncryption(),
        ).decode()
        public_pem = private.public_key().public_bytes(
            encoding=__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM,
            format=__import__("cryptography").hazmat.primitives.serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
        kid = hashlib.sha256(public_pem.encode()).hexdigest()[:24]
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
        now = datetime.now(timezone.utc)
        payload = dict(claims)
        payload.setdefault("iat", now)
        payload.setdefault("exp", int(now.timestamp()) + ttl_seconds)
        return jwt.encode(payload, self.active.private_key_pem, algorithm="RS256", headers={"kid": self.active.kid})

    def verify(self, token: str) -> dict[str, object]:
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not isinstance(kid, str) or kid not in self._keys:
                raise ValueError("Unknown signing key")
            return jwt.decode(token, self._keys[kid].public_key_pem, algorithms=["RS256"], options={"require": ["exp", "sub", "tenant_id", "actor_id"]})
        except jwt.PyJWTError as exc:
            raise ValueError("Invalid access token") from exc

    def jwks(self) -> dict[str, list[dict[str, str]]]:
        keys = []
        for key in self._keys.values():
            public = jwt.algorithms.RSAAlgorithm.from_jwk(jwt.algorithms.RSAAlgorithm.to_jwk(__import__("cryptography").hazmat.primitives.serialization.load_pem_public_key(key.public_key_pem.encode())))
            jwk = json.loads(public.to_jwk())
            jwk["kid"] = key.kid
            jwk["use"] = "sig"
            jwk["alg"] = "RS256"
            keys.append(jwk)
        return {"keys": keys}
