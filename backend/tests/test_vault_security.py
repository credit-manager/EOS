"""Vault security contract tests — AES-256-GCM, fail-closed production."""
import base64
import importlib
import os

import pytest


@pytest.fixture(autouse=True)
def _reset_key():
    import app.vault as vault
    yield vault
    vault._vault_key = None


def test_roundtrip(_reset_key):
    v = _reset_key
    ct = v.encrypt_value("sk-live-12345")
    assert ct != "sk-live-12345"
    assert v.decrypt_value(ct) == "sk-live-12345"


def test_nonce_uniqueness(_reset_key):
    v = _reset_key
    a = v.encrypt_value("same-secret")
    b = v.encrypt_value("same-secret")
    assert a != b  # random nonce per encryption
    assert v.decrypt_value(a) == v.decrypt_value(b) == "same-secret"


def test_tamper_detection(_reset_key):
    v = _reset_key
    ct = v.encrypt_value("important-token")
    raw = bytearray(base64.b64decode(ct))
    raw[-1] ^= 0xFF  # flip a bit in the auth tag
    tampered = base64.b64encode(bytes(raw)).decode()
    with pytest.raises(ValueError, match="authentication failed"):
        v.decrypt_value(tampered)


def test_wrong_key_fails(_reset_key):
    v = _reset_key
    key1 = base64.b64encode(os.urandom(32)).decode()
    key2 = base64.b64encode(os.urandom(32)).decode()
    os.environ["EOS_VAULT_KEY"] = key1
    v._vault_key = None
    ct = v.encrypt_value("secret")
    os.environ["EOS_VAULT_KEY"] = key2
    v._vault_key = None
    with pytest.raises(ValueError):
        v.decrypt_value(ct)
    del os.environ["EOS_VAULT_KEY"]
    v._vault_key = None


def test_production_fail_closed(_reset_key, monkeypatch):
    """APP_ENV=production without EOS_VAULT_KEY must raise, never fall back."""
    v = _reset_key
    v._vault_key = None
    monkeypatch.delenv("EOS_VAULT_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="EOS_VAULT_KEY is required"):
        v.encrypt_value("anything")


def test_production_rejects_short_key(_reset_key, monkeypatch):
    v = _reset_key
    v._vault_key = None
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("EOS_VAULT_KEY", base64.b64encode(b"tooshort").decode())
    with pytest.raises(RuntimeError, match="32 bytes"):
        v.encrypt_value("anything")


def test_secret_vault_never_exposes_plaintext(_reset_key):
    v = _reset_key
    vault = v.SecretVault("tenant-1")
    vault.set_secret("api_key", "super-secret-value")
    assert "super-secret-value" not in str(vault._store)
    assert vault.get_secret("api_key") == "super-secret-value"
    assert vault.list_secrets() == ["api_key"]
