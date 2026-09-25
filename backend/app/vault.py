"""Encrypted vault for API keys and secrets.

Security contract (Production Completion Standard):
- Authenticated encryption via AES-256-GCM (cryptography lib). Never XOR/Base64.
- Ciphertext format: base64( nonce[12] || ciphertext+tag ). Unique random nonce per encryption.
- Tampered ciphertext fails authentication (InvalidTag -> ValueError).
- FAIL CLOSED in production: EOS_VAULT_KEY must be set to a valid 32-byte
  base64 key when APP_ENV=production. No hardcoded fallback seed is used in
  production; startup of any encrypt/decrypt raises instead.
- Plaintext never logged, never returned by list APIs.
"""
import base64
import logging
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger("2to-eos.vault")

NONCE_SIZE = 12  # 96-bit nonce recommended for AES-GCM
KEY_SIZE = 32    # AES-256

_vault_key: bytes | None = None


def _is_production() -> bool:
    return os.getenv("APP_ENV", "development").lower() == "production"


def _get_vault_key() -> bytes:
    """Resolve the vault key. Fail-closed in production."""
    global _vault_key
    if _vault_key:
        return _vault_key

    key_env = os.getenv("EOS_VAULT_KEY")
    if key_env:
        try:
            key = base64.b64decode(key_env, validate=True)
        except Exception as exc:  # malformed base64
            raise RuntimeError(
                "EOS_VAULT_KEY is not valid base64; refusing to start crypto operations"
            ) from exc
        if len(key) != KEY_SIZE:
            raise RuntimeError(
                f"EOS_VAULT_KEY must decode to exactly {KEY_SIZE} bytes (AES-256); "
                f"got {len(key)}"
            )
        _vault_key = key
        return _vault_key

    if _is_production():
        # FAIL CLOSED: no fallback key in production, ever.
        raise RuntimeError(
            "SECURITY: EOS_VAULT_KEY is required when APP_ENV=production. "
            "Generate one with: python -c \"import os,base64;"
            "print(base64.b64encode(os.urandom(32)).decode())\""
        )

    # Development/test only: derived ephemeral key, loudly warned.
    seed = os.getenv("EOS_VAULT_SEED", "eos-development-only-vault-seed")
    logger.warning(
        "Using development-derived vault key (non-production only). "
        "Set EOS_VAULT_KEY before deploying."
    )
    import hashlib
    _vault_key = hashlib.sha256(seed.encode()).digest()
    return _vault_key


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string using AES-256-GCM. Returns base64(nonce||ct||tag)."""
    key = _get_vault_key()
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt AES-256-GCM output. Raises ValueError on tamper/auth failure."""
    key = _get_vault_key()
    try:
        raw = base64.b64decode(ciphertext, validate=True)
    except Exception as exc:
        raise ValueError("Ciphertext is not valid base64") from exc
    if len(raw) <= NONCE_SIZE:
        raise ValueError("Ciphertext too short — corrupt or legacy format")
    nonce, ct = raw[:NONCE_SIZE], raw[NONCE_SIZE:]
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ct, None).decode("utf-8")
    except InvalidTag as exc:
        # Authentication failed: tampered ciphertext or wrong key.
        raise ValueError("Vault authentication failed: ciphertext tampered or key mismatch") from exc


class SecretVault:
    """Encrypted storage for API keys and secrets."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._store: dict[str, str] = {}

    def set_secret(self, name: str, value: str) -> None:
        """Store an encrypted secret."""
        self._store[name] = encrypt_value(value)

    def get_secret(self, name: str) -> str | None:
        """Retrieve and decrypt a secret."""
        encrypted = self._store.get(name)
        if not encrypted:
            return None
        try:
            return decrypt_value(encrypted)
        except ValueError as e:
            # Never log the value; only the fact auth failed.
            logger.error("Failed to decrypt secret '%s': %s", name, e)
            return None

    def delete_secret(self, name: str) -> bool:
        """Delete a secret."""
        if name in self._store:
            del self._store[name]
            return True
        return False

    def list_secrets(self) -> list[str]:
        """List secret names (not values)."""
        return list(self._store.keys())
