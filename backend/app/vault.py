"""Encrypted vault for API keys and secrets."""
import base64
import hashlib
import logging
import os
from typing import Any

logger = logging.getLogger("2to-eos.vault")

_vault_key: bytes | None = None


def _get_vault_key() -> bytes:
    """Get or generate the vault encryption key."""
    global _vault_key
    if _vault_key:
        return _vault_key

    key_env = os.getenv("EOS_VAULT_KEY")
    if key_env:
        _vault_key = base64.b64decode(key_env)
    else:
        seed = os.getenv("EOS_VAULT_SEED", "eos-default-dev-key-change-in-production")
        _vault_key = hashlib.sha256(seed.encode()).digest()
        logger.warning("Using derived vault key — set EOS_VAULT_KEY in production")

    return _vault_key


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value using XOR cipher with the vault key."""
    key = _get_vault_key()
    data = plaintext.encode("utf-8")
    encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a vault-encrypted string value."""
    key = _get_vault_key()
    data = base64.b64decode(ciphertext)
    decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return decrypted.decode("utf-8")


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
        except Exception as e:
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
