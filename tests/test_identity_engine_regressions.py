from unittest.mock import MagicMock

import pytest

from core.identity_engine import IdentityEngine


def _db_with_identity_ownership(user_ok=True, provider_ok=True):
    db = MagicMock()

    def execute(statement, params=None):
        sql_text = str(statement)
        result = MagicMock()
        if "FROM dbp_users" in sql_text:
            result.fetchone.return_value = (1,) if user_ok else None
        elif "FROM dbp_sso_providers" in sql_text and "SELECT 1" in sql_text:
            result.fetchone.return_value = (1,) if provider_ok else None
        elif "SELECT 1" in sql_text:
            result.fetchone.return_value = (1,)
        else:
            result.rowcount = 1
        return result

    db.execute.side_effect = execute
    return db


def test_sso_session_rejects_cross_tenant_user_or_provider():
    db = _db_with_identity_ownership(user_ok=False, provider_ok=True)
    with pytest.raises(ValueError, match="user does not belong to tenant"):
        IdentityEngine(db).create_session("tenant-a", "user-b", "provider-a", "sso-1")

    db = _db_with_identity_ownership(user_ok=True, provider_ok=False)
    with pytest.raises(ValueError, match="provider does not belong to tenant"):
        IdentityEngine(db).create_session("tenant-a", "user-a", "provider-b", "sso-1")


def test_mfa_setup_requires_user_to_belong_to_tenant():
    db = _db_with_identity_ownership(user_ok=False)
    with pytest.raises(ValueError, match="user does not belong to tenant"):
        IdentityEngine(db).setup_mfa("tenant-a", "user-b", "totp")


def test_role_mapping_requires_provider_to_belong_to_tenant():
    db = _db_with_identity_ownership(provider_ok=False)
    with pytest.raises(ValueError, match="provider does not belong to tenant"):
        IdentityEngine(db).create_role_mapping("tenant-a", "provider-b", "external", "internal")


def test_identity_mutations_fail_closed_when_target_does_not_exist():
    db = _db_with_identity_ownership()
    db.execute.side_effect = None
    missing = MagicMock()
    missing.rowcount = 0
    db.execute.return_value = missing
    with pytest.raises(ValueError, match="provider not found"):
        IdentityEngine(db).update_provider("tenant-a", "missing-provider", provider_name="new")
    with pytest.raises(ValueError, match="MFA configuration not found"):
        IdentityEngine(db).enable_mfa("tenant-a", "missing-mfa")
    with pytest.raises(ValueError, match="role mapping not found"):
        IdentityEngine(db).delete_role_mapping("tenant-a", "missing-rule")
    with pytest.raises(ValueError, match="API key not found"):
        IdentityEngine(db).revoke_api_key("tenant-a", "missing-key")
