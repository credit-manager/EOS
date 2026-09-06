from uuid import uuid4

import pytest

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.application.identity.authorization import authorize_current_actor, require_tenant_match
from eos_v2.domain.identity.entities import Actor
from eos_v2.domain.permissions.policy import Permission, authorize


def test_authorization_denies_missing_actor() -> None:
    tenant_id = uuid4()
    decision = authorize(None, tenant_id, Permission.READ)
    assert decision.allowed is False
    assert decision.reason == "authentication_required"


def test_authorization_denies_cross_tenant_actor() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    actor = Actor(uuid4(), tenant_a, "user-a")
    decision = authorize(actor, tenant_b, Permission.READ)
    assert decision.allowed is False
    assert decision.reason == "tenant_mismatch"


def test_authorization_is_deny_by_default_even_inside_tenant() -> None:
    tenant_id = uuid4()
    actor = Actor(uuid4(), tenant_id, "user-a")
    decision = authorize(actor, tenant_id, Permission.READ)
    assert decision.allowed is False
    assert decision.reason == "permission_not_granted:read"


def test_current_context_is_authoritative() -> None:
    tenant_id = uuid4()
    other_tenant = uuid4()
    actor = Actor(uuid4(), tenant_id, "user-a")
    token = set_tenant_context(TenantContext(other_tenant, actor.id))
    try:
        decision = authorize_current_actor(actor, Permission.READ)
        assert decision.allowed is False
        assert decision.reason == "tenant_mismatch"
    finally:
        reset_tenant_context(token)


def test_resource_must_match_authenticated_context() -> None:
    tenant_id = uuid4()
    other_tenant = uuid4()
    actor = Actor(uuid4(), tenant_id, "user-a")
    token = set_tenant_context(TenantContext(tenant_id, actor.id))
    try:
        with pytest.raises(PermissionError, match="Cross-tenant access denied"):
            require_tenant_match(actor, other_tenant)
    finally:
        reset_tenant_context(token)


def test_missing_context_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="Tenant context is not set"):
        authorize_current_actor(None, Permission.READ)
