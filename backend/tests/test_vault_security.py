"""Security contract tests for the encrypted vault."""
import base64
import os

import pytest

from backend.app import vault


@pytest.fixture(autouse=True)
def _reset_key():
    vault._vault_key = None
    yield
    vault._vault_key = None
    os.environ.pop("EOS_VAULT_KEY", None)


def test_roundtrip():
    ciphertext = vault.encrypt_value("sk-live-12345")
    assert ciphertext != "sk-live-12345"
    assert vault.decrypt_value(ciphertext) == "sk-live-12345"


def test_nonce_uniqueness():
    first = vault.encrypt_value("same-secret")
    second = vault.encrypt_value("same-secret")
    assert first != second
    assert vault.decrypt_value(first) == vault.decrypt_value(second) == "same-secret"


def test_tamper_detection():
    ciphertext = vault.encrypt_value("important-token")
    raw = bytearray(base64.b64decode(ciphertext))
    raw[-1] ^= 0xFF
    tampered = base64.b64encode(bytes(raw)).decode()
    with pytest.raises(ValueError, match="authentication failed"):
        vault.decrypt_value(tampered)


def test_wrong_key_fails(monkeypatch):
    key1 = base64.b64encode(os.urandom(32)).decode()
    key2 = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("EOS_VAULT_KEY", key1)
    vault._vault_key = None
    ciphertext = vault.encrypt_value("secret")
    monkeypatch.setenv("EOS_VAULT_KEY", key2)
    vault._vault_key = None
    with pytest.raises(ValueError):
        vault.decrypt_value(ciphertext)


def test_production_fail_closed(monkeypatch):
    monkeypatch.delenv("EOS_VAULT_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    vault._vault_key = None
    with pytest.raises(RuntimeError, match="EOS_VAULT_KEY is required"):
        vault.encrypt_value("anything")


def test_production_rejects_short_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("EOS_VAULT_KEY", base64.b64encode(b"tooshort").decode())
    vault._vault_key = None
    with pytest.raises(RuntimeError, match="32 bytes"):
        vault.encrypt_value("anything")


def test_secret_vault_never_exposes_plaintext():
    secret_vault = vault.SecretVault("tenant-1")
    secret_vault.set_secret("api_key", "super-secret-value")
    assert "super-secret-value" not in str(secret_vault._store)
    assert secret_vault.get_secret("api_key") == "super-secret-value"
    assert secret_vault.list_secrets() == ["api_key"]
