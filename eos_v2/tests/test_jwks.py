from eos_v2.application.identity.jwks import RSAKeyRing


def test_rs256_issue_verify_and_jwks_rotation():
    ring = RSAKeyRing.generate()
    claims = {"sub": "user-1", "tenant_id": "00000000-0000-0000-0000-000000000001", "actor_id": "00000000-0000-0000-0000-000000000002"}
    old = ring.issue(claims)
    old_kid = ring.active.kid
    assert ring.verify(old)["sub"] == "user-1"
    fresh = ring.rotate()
    assert fresh.kid != old_kid
    new = ring.issue(claims)
    assert ring.verify(new)["sub"] == "user-1"
    assert {item["kid"] for item in ring.jwks()["keys"]} == {old_kid, fresh.kid}
    assert ring.verify(old)["actor_id"] == claims["actor_id"]
