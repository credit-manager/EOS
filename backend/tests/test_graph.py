from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)
_PASSWORD = "Correct-Horse-Battery-42"


def _register(email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": _PASSWORD, "tenant_name": f"Tenant {email}"},
    )
    assert response.status_code == 201
    return response.json()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _publish_entity(headers: dict, payload: dict) -> None:
    created = client.post("/api/v1/metadata/entities", json=payload, headers=headers)
    assert created.status_code == 201
    published = client.post(f"/api/v1/metadata/entities/{payload['code']}/publish", headers=headers)
    assert published.status_code == 200


def _record(headers: dict, entity: str, data: dict) -> dict:
    resp = client.post(f"/api/v1/entities/{entity}/records", json={"data": data}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _setup_entities(headers: dict) -> None:
    _publish_entity(
        headers,
        {
            "code": "customer",
            "name": "Customer",
            "fields": [
                {"code": "name", "type": "text", "required": True},
                {"code": "code", "type": "text"},
            ],
        },
    )
    _publish_entity(
        headers,
        {
            "code": "project",
            "name": "Project",
            "fields": [
                {"code": "name", "type": "text", "required": True},
                {
                    "code": "customer",
                    "type": "relation",
                    "target_entity": "customer",
                    "nullable": True,
                },
            ],
        },
    )
    _publish_entity(
        headers,
        {
            "code": "contract",
            "name": "Contract",
            "fields": [
                {"code": "name", "type": "text", "required": True},
                {
                    "code": "project",
                    "type": "relation",
                    "target_entity": "project",
                    "nullable": True,
                },
            ],
        },
    )


def test_graph_story_traverses_relations() -> None:
    user = _register(f"graph-user-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_entities(headers)
    customer = _record(headers, "customer", {"name": "ACME", "code": "C-100"})
    project = _record(headers, "project", {"name": "Tower A", "customer": customer["id"]})

    story = client.get(f"/api/v1/graph/project/{project['id']}", headers=headers).json()
    assert story["root"]["entity_code"] == "project"
    assert story["root"]["title"] == "Tower A"
    assert len(story["nodes"]) == 2
    assert len(story["edges"]) == 1
    edge = story["edges"][0]
    assert edge["field"] == "customer"
    assert edge["target_entity"] == "customer"
    assert edge["source"] == f"project:{project['id']}"
    assert edge["target"] == f"customer:{customer['id']}"
    customer_node = next(node for node in story["nodes"] if node["entity_code"] == "customer")
    assert customer_node["title"] == "ACME"
    assert customer_node["data"]["code"] == "C-100"


def test_graph_depth_controls_expansion() -> None:
    user = _register(f"graph-depth-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_entities(headers)
    customer = _record(headers, "customer", {"name": "MEGA"})
    project = _record(headers, "project", {"name": "P1", "customer": customer["id"]})
    contract = _record(headers, "contract", {"name": "K1", "project": project["id"]})

    depth1 = client.get(f"/api/v1/graph/contract/{contract['id']}?depth=1", headers=headers).json()
    assert len(depth1["nodes"]) == 2
    assert {node["entity_code"] for node in depth1["nodes"]} == {"contract", "project"}

    depth2 = client.get(f"/api/v1/graph/contract/{contract['id']}?depth=2", headers=headers).json()
    assert len(depth2["nodes"]) == 3
    assert {node["entity_code"] for node in depth2["nodes"]} == {"contract", "project", "customer"}


def test_graph_cycle_is_safe() -> None:
    user = _register(f"graph-cycle-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _publish_entity(
        headers,
        {
            "code": "partner",
            "name": "Partner",
            "fields": [
                {"code": "name", "type": "text", "required": True},
                {"code": "peer", "type": "relation", "target_entity": "partner", "nullable": True},
            ],
        },
    )
    a = _record(headers, "partner", {"name": "A"})
    b = _record(headers, "partner", {"name": "B", "peer": a["id"]})
    client.patch(
        f"/api/v1/entities/partner/records/{a['id']}",
        json={"data": {"name": "A", "peer": b["id"]}, "version": 1},
        headers=headers,
    ).json()

    story = client.get(f"/api/v1/graph/partner/{a['id']}?depth=3", headers=headers).json()
    assert {node["ref"] for node in story["nodes"]} == {
        f"partner:{a['id']}",
        f"partner:{b['id']}",
    }
    assert len(story["edges"]) == 2


def test_graph_is_tenant_isolated() -> None:
    user = _register(f"graph-iso-{uuid4()}@example.com")
    other = _register(f"graph-other-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    other_headers = _headers(other["access_token"])
    _setup_entities(headers)
    _setup_entities(other_headers)
    customer = _record(headers, "customer", {"name": "ACME"})
    project = _record(headers, "project", {"name": "Tower A", "customer": customer["id"]})

    for entity, record in (("customer", customer), ("project", project)):
        resp = client.get(f"/api/v1/graph/{entity}/{record['id']}", headers=other_headers)
        assert resp.status_code == 404

    own = client.get(f"/api/v1/graph/project/{project['id']}", headers=headers)
    assert own.status_code == 200
    assert len(own.json()["nodes"]) == 2


def test_graph_hides_edges_to_read_restricted_entities() -> None:
    member_email = f"graph-perm-member-{uuid4()}@example.com"
    user = _register(f"graph-perm-{uuid4()}@example.com")
    _register(member_email)
    headers = _headers(user["access_token"])
    assert (
        client.post(
            "/api/v1/auth/members", json={"email": member_email, "role": "member"}, headers=headers
        ).status_code
        == 201
    )
    member_login = client.post(
        "/api/v1/auth/token",
        json={"email": member_email, "password": _PASSWORD, "tenant_id": user["tenant_id"]},
    )
    assert member_login.status_code == 200
    member_headers = _headers(member_login.json()["access_token"])

    _publish_entity(
        headers,
        {
            "code": "secret_doc",
            "name": "Secret Doc",
            "fields": [{"code": "title", "type": "text", "required": True}],
            "permissions": {"admin": ["create", "read", "update", "delete"], "member": ["create"]},
        },
    )
    _publish_entity(
        headers,
        {
            "code": "dossier",
            "name": "Dossier",
            "fields": [
                {"code": "name", "type": "text", "required": True},
                {
                    "code": "doc",
                    "type": "relation",
                    "target_entity": "secret_doc",
                    "nullable": True,
                },
            ],
        },
    )
    secret = _record(headers, "secret_doc", {"title": "Confidential"})
    dossier = _record(headers, "dossier", {"name": "D-1", "doc": secret["id"]})

    admin_story = client.get(f"/api/v1/graph/dossier/{dossier['id']}", headers=headers).json()
    assert len(admin_story["nodes"]) == 2
    assert len(admin_story["edges"]) == 1

    member_story = client.get(
        f"/api/v1/graph/dossier/{dossier['id']}", headers=member_headers
    ).json()
    assert len(member_story["nodes"]) == 1
    assert len(member_story["edges"]) == 0


def test_relationship_created_event_and_rule_reaction() -> None:
    user = _register(f"graph-evt-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_entities(headers)

    rule = client.post(
        "/api/v1/rules",
        headers=headers,
        json={
            "name": "notify on customer relation",
            "event_type": "graph.relationship.created",
            "conditions": [{"field": "payload.field", "op": "eq", "value": "customer"}],
            "priority": 5,
            "enabled": True,
            "actions": [
                {
                    "type": "publish_event",
                    "event_type": "wf.graph.relation_seen",
                    "payload": {"target": "{{payload.target_entity}}"},
                }
            ],
        },
    )
    assert rule.status_code == 201

    customer = _record(headers, "customer", {"name": "ACME"})
    _record(headers, "project", {"name": "Tower A", "customer": customer["id"]})

    created = client.get(
        "/api/v1/events?event_type=graph.relationship.created", headers=headers
    ).json()
    assert created["total"] == 1
    assert created["items"][0]["payload"]["field"] == "customer"
    assert created["items"][0]["payload"]["target_id"] == customer["id"]

    derived = client.get("/api/v1/events?event_type=wf.graph.relation_seen", headers=headers).json()
    assert derived["total"] == 1
    assert derived["items"][0]["payload"]["target"] == "customer"


def test_relationship_removed_event_on_update() -> None:
    user = _register(f"graph-rm-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_entities(headers)
    customer = _record(headers, "customer", {"name": "ACME"})
    project = _record(headers, "project", {"name": "Tower A", "customer": customer["id"]})

    updated = client.patch(
        f"/api/v1/entities/project/records/{project['id']}",
        json={"data": {"name": "Tower A"}, "version": 1},
        headers=headers,
    )
    assert updated.status_code == 200

    removed = client.get(
        "/api/v1/events?event_type=graph.relationship.removed", headers=headers
    ).json()
    assert removed["total"] == 1
    assert removed["items"][0]["payload"]["field"] == "customer"
    assert removed["items"][0]["payload"]["target_id"] == customer["id"]
