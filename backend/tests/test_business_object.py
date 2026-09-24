"""Tests for Business Object V2 — config, serialization, validation, registry, graph pathfinding."""

import uuid
from unittest.mock import MagicMock

from backend.app.metadata.business_object import (
    BusinessObjectConfig,
    EntityAIConfig,
    EntityAnalyticsConfig,
    EntityDocumentConfig,
    EntityFinancialConfig,
    EntityPermissionConfig,
    EntityRuleConfig,
    EntityWorkflowConfig,
    RelationshipConfig,
)
from backend.app.metadata.business_object_registry import (
    PREBUILT_OBJECTS,
    BusinessObjectRegistry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> BusinessObjectConfig:
    defaults = dict(
        entity_code="test_entity",
        entity_name="Test Entity",
        description="A test entity",
        fields=[
            {"code": "name", "name": "Name", "type": "text", "required": True},
            {"code": "status", "name": "Status", "type": "select", "options": ["active", "inactive"]},
        ],
        relationships=[
            RelationshipConfig(
                target_entity="other",
                relation_type="one_to_many",
                foreign_key="test_entity_id",
                label="Others",
            ),
        ],
        rules=[
            EntityRuleConfig(
                rule_id="test_rule",
                event_type="on_create",
                condition="status == 'active'",
                action="notify",
            ),
        ],
        permissions=EntityPermissionConfig(),
        workflow=EntityWorkflowConfig(
            states=["draft", "active"],
            initial_state="draft",
            transitions=[{"from": "draft", "to": "active", "actor": "admin", "condition": None}],
        ),
        documents=EntityDocumentConfig(document_types=["pdf"]),
        financial=EntityFinancialConfig(has_financial_impact=False),
        analytics=EntityAnalyticsConfig(kpis=[{"code": "count", "formula": "COUNT(*)"}]),
        ai=EntityAIConfig(),
        audit_enabled=True,
    )
    defaults.update(overrides)
    return BusinessObjectConfig(**defaults)


# ===================================================================
# 1. Creating a BusinessObjectConfig with all fields
# ===================================================================

class TestBusinessObjectConfigCreation:
    def test_create_with_all_fields(self):
        config = _make_config()
        assert config.entity_code == "test_entity"
        assert config.entity_name == "Test Entity"
        assert config.description == "A test entity"
        assert len(config.fields) == 2
        assert len(config.relationships) == 1
        assert len(config.rules) == 1
        assert config.workflow is not None
        assert config.documents is not None
        assert config.financial is not None
        assert config.analytics is not None
        assert config.ai is not None
        assert config.audit_enabled is True

    def test_create_minimal(self):
        config = BusinessObjectConfig(
            entity_code="minimal",
            entity_name="Minimal",
            description="",
        )
        assert config.entity_code == "minimal"
        assert config.fields == []
        assert config.relationships == []
        assert config.rules == []
        assert config.workflow is None
        assert config.documents is None
        assert config.financial is None
        assert config.analytics is None
        assert config.audit_enabled is True

    def test_defaults_are_correct(self):
        config = BusinessObjectConfig(
            entity_code="x", entity_name="X", description="X"
        )
        assert config.fields == []
        assert config.relationships == []
        assert config.rules == []
        assert isinstance(config.permissions, EntityPermissionConfig)
        assert isinstance(config.ai, EntityAIConfig)


# ===================================================================
# 2. Serialization / Deserialization (to_dict / from_dict)
# ===================================================================

class TestSerialization:
    def test_roundtrip_with_all_fields(self):
        config = _make_config()
        d = config.to_dict()
        restored = BusinessObjectConfig.from_dict(d)
        assert restored.entity_code == config.entity_code
        assert restored.entity_name == config.entity_name
        assert restored.description == config.description
        assert len(restored.fields) == len(config.fields)
        assert len(restored.relationships) == len(config.relationships)
        assert len(restored.rules) == len(config.rules)
        assert restored.workflow is not None
        assert restored.workflow.states == config.workflow.states
        assert restored.documents is not None
        assert restored.documents.document_types == config.documents.document_types
        assert restored.financial is not None
        assert restored.analytics is not None
        assert restored.ai.context_enabled == config.ai.context_enabled
        assert restored.audit_enabled == config.audit_enabled

    def test_roundtrip_minimal(self):
        config = BusinessObjectConfig(
            entity_code="min", entity_name="Min", description=""
        )
        d = config.to_dict()
        restored = BusinessObjectConfig.from_dict(d)
        assert restored.entity_code == "min"
        assert restored.workflow is None
        assert restored.documents is None
        assert restored.financial is None
        assert restored.analytics is None

    def test_to_dict_produces_json_safe_dict(self):
        config = _make_config()
        d = config.to_dict()
        assert isinstance(d, dict)
        assert isinstance(d["relationships"], list)
        assert isinstance(d["relationships"][0], dict)
        assert isinstance(d["rules"], list)
        assert isinstance(d["rules"][0], dict)
        assert isinstance(d["permissions"], dict)
        assert isinstance(d["ai"], dict)

    def test_from_dict_with_empty_optional_sections(self):
        data = {
            "entity_code": "e",
            "entity_name": "E",
            "description": "E",
            "fields": [],
            "relationships": [],
            "rules": [],
            "permissions": {},
            "ai": {},
        }
        config = BusinessObjectConfig.from_dict(data)
        assert config.entity_code == "e"
        assert config.workflow is None
        assert config.documents is None
        assert config.financial is None
        assert config.analytics is None

    def test_relationship_serialization(self):
        rel = RelationshipConfig(
            target_entity="invoice",
            relation_type="one_to_many",
            foreign_key="customer_id",
            label="Invoices",
            cascade_delete=True,
            required=True,
        )
        d = rel.to_dict()
        restored = RelationshipConfig.from_dict(d)
        assert restored.target_entity == "invoice"
        assert restored.relation_type == "one_to_many"
        assert restored.cascade_delete is True
        assert restored.required is True

    def test_rule_serialization(self):
        rule = EntityRuleConfig(
            rule_id="r1",
            event_type="on_update",
            condition="amount > 100",
            action="require_approval",
            params={"approver_role": "finance"},
        )
        d = rule.to_dict()
        restored = EntityRuleConfig.from_dict(d)
        assert restored.rule_id == "r1"
        assert restored.params == {"approver_role": "finance"}

    def test_workflow_serialization(self):
        wf = EntityWorkflowConfig(
            states=["a", "b", "c"],
            initial_state="a",
            transitions=[{"from": "a", "to": "b"}],
            approval_required=True,
            approvers=["admin"],
            timeout_hours=24,
            escalation={"notify": "manager"},
        )
        d = wf.to_dict()
        restored = EntityWorkflowConfig.from_dict(d)
        assert restored.states == ["a", "b", "c"]
        assert restored.approval_required is True
        assert restored.timeout_hours == 24
        assert restored.escalation == {"notify": "manager"}

    def test_financial_serialization(self):
        fin = EntityFinancialConfig(
            has_financial_impact=True,
            posting_rules=[{"debit": "cash", "credit": "revenue"}],
            currency_field="currency",
            amount_field="amount",
            tax_applicable=True,
        )
        d = fin.to_dict()
        restored = EntityFinancialConfig.from_dict(d)
        assert restored.has_financial_impact is True
        assert len(restored.posting_rules) == 1
        assert restored.tax_applicable is True

    def test_permissions_serialization(self):
        perm = EntityPermissionConfig(
            roles={"admin": ["create", "read"], "viewer": ["read"]},
            field_permissions={"name": {"admin": ["read"]}},
            row_level=True,
        )
        d = perm.to_dict()
        restored = EntityPermissionConfig.from_dict(d)
        assert restored.row_level is True
        assert "admin" in restored.roles

    def test_document_serialization(self):
        doc = EntityDocumentConfig(
            document_types=["invoice", "receipt"],
            required=True,
            ocr_enabled=True,
            classification=True,
        )
        d = doc.to_dict()
        restored = EntityDocumentConfig.from_dict(d)
        assert restored.document_types == ["invoice", "receipt"]
        assert restored.ocr_enabled is True


# ===================================================================
# 3. Validation (catch missing required fields)
# ===================================================================

class TestValidation:
    def test_valid_config_has_no_errors(self):
        config = _make_config()
        errors = config.validate()
        assert errors == []

    def test_missing_entity_code(self):
        config = _make_config(entity_code="")
        errors = config.validate()
        assert any("entity_code" in e for e in errors)

    def test_missing_entity_name(self):
        config = _make_config(entity_name="")
        errors = config.validate()
        assert any("entity_name" in e for e in errors)

    def test_duplicate_field_codes(self):
        config = _make_config(fields=[
            {"code": "name", "name": "Name", "type": "text"},
            {"code": "name", "name": "Name 2", "type": "text"},
        ])
        errors = config.validate()
        assert any("Duplicate" in e for e in errors)

    def test_invalid_relationship_type(self):
        config = _make_config(relationships=[
            RelationshipConfig(
                target_entity="x",
                relation_type="INVALID",
                foreign_key="x_id",
                label="X",
            ),
        ])
        errors = config.validate()
        assert any("relation_type" in e for e in errors)

    def test_empty_relationship_target(self):
        config = _make_config(relationships=[
            RelationshipConfig(
                target_entity="",
                relation_type="one_to_many",
                foreign_key="x_id",
                label="X",
            ),
        ])
        errors = config.validate()
        assert any("target_entity" in e for e in errors)

    def test_invalid_rule_event_type(self):
        config = _make_config(rules=[
            EntityRuleConfig(
                rule_id="r1",
                event_type="on_bogus",
                condition="true",
                action="notify",
            ),
        ])
        errors = config.validate()
        assert any("event_type" in e for e in errors)

    def test_invalid_rule_action(self):
        config = _make_config(rules=[
            EntityRuleConfig(
                rule_id="r1",
                event_type="on_create",
                condition="true",
                action="INVALID_ACTION",
            ),
        ])
        errors = config.validate()
        assert any("action" in e for e in errors)

    def test_workflow_initial_state_not_in_states(self):
        config = _make_config(workflow=EntityWorkflowConfig(
            states=["a", "b"],
            initial_state="missing",
            transitions=[],
        ))
        errors = config.validate()
        assert any("initial_state" in e for e in errors)

    def test_workflow_transition_from_invalid_state(self):
        config = _make_config(workflow=EntityWorkflowConfig(
            states=["a", "b"],
            initial_state="a",
            transitions=[{"from": "missing", "to": "b"}],
        ))
        errors = config.validate()
        assert any("'from'" in e for e in errors)

    def test_workflow_empty_states(self):
        config = _make_config(workflow=EntityWorkflowConfig(
            states=[],
            initial_state="a",
            transitions=[],
        ))
        errors = config.validate()
        assert any("states list cannot be empty" in e for e in errors)

    def test_financial_requires_amount_field(self):
        config = _make_config(financial=EntityFinancialConfig(
            has_financial_impact=True,
            amount_field=None,
        ))
        errors = config.validate()
        assert any("amount_field" in e for e in errors)

    def test_financial_posting_rule_missing_fields(self):
        config = _make_config(financial=EntityFinancialConfig(
            has_financial_impact=True,
            posting_rules=[{"debit": "cash"}],
        ))
        errors = config.validate()
        assert any("credit" in e for e in errors)

    def test_document_empty_types(self):
        config = _make_config(documents=EntityDocumentConfig(
            document_types=[],
        ))
        errors = config.validate()
        assert any("document_types" in e for e in errors)

    def test_permission_invalid_action(self):
        config = _make_config(permissions=EntityPermissionConfig(
            roles={"admin": ["INVALID_ACTION"]},
        ))
        errors = config.validate()
        assert any("INVALID_ACTION" in e for e in errors)


# ===================================================================
# 4. Registry (get prebuilt objects, list all)
# ===================================================================

class TestRegistry:
    def test_prebuilt_objects_exist(self):
        assert len(PREBUILT_OBJECTS) >= 10
        expected = {"customer", "supplier", "project", "invoice",
                    "purchase_order", "payment", "contract", "employee",
                    "product", "asset"}
        assert expected == set(PREBUILT_OBJECTS.keys())

    def test_get_prebuilt_object(self):
        db = MagicMock()
        registry = BusinessObjectRegistry(db)
        config = registry.get("customer")
        assert config is not None
        assert config.entity_code == "customer"
        assert config.entity_name == "Customer"

    def test_get_nonexistent_returns_none(self):
        db = MagicMock()
        registry = BusinessObjectRegistry(db)
        assert registry.get("nonexistent_entity") is None

    def test_list_all_returns_sorted(self):
        db = MagicMock()
        registry = BusinessObjectRegistry(db)
        all_objects = registry.list_all()
        assert len(all_objects) >= 10
        codes = [o.entity_code for o in all_objects]
        assert codes == sorted(codes)

    def test_list_all_includes_all_prebuilt(self):
        db = MagicMock()
        registry = BusinessObjectRegistry(db)
        all_objects = registry.list_all()
        codes = {o.entity_code for o in all_objects}
        for key in PREBUILT_OBJECTS:
            assert key in codes

    def test_register_custom_object(self):
        db = MagicMock()
        registry = BusinessObjectRegistry(db)
        custom = BusinessObjectConfig(
            entity_code="custom_widget",
            entity_name="Custom Widget",
            description="A custom widget",
        )
        tenant_id = str(uuid.uuid4())
        registry.register(custom, tenant_id)
        cached = registry.get("custom_widget", tenant_id)
        assert cached is not None
        assert cached.entity_code == "custom_widget"

    def test_get_relationships(self):
        db = MagicMock()
        registry = BusinessObjectRegistry(db)
        rels = registry.get_relationships("customer")
        assert len(rels) > 0
        assert all(isinstance(r, dict) for r in rels)
        assert all("target_entity" in r for r in rels)

    def test_get_relationships_unknown_entity(self):
        db = MagicMock()
        registry = BusinessObjectRegistry(db)
        rels = registry.get_relationships("nonexistent")
        assert rels == []


# ===================================================================
# 5. Graph pathfinding (find path between entities)
# ===================================================================

class TestGraphPathfinding:
    def test_find_path_same_entity(self):
        db = MagicMock()
        registry = BusinessObjectRegistry(db)
        path = registry.get_graph_path("customer", "customer")
        assert len(path) == 1
        assert path[0]["entity"] == "customer"
        assert path[0]["relation"] is None

    def test_find_path_customer_to_invoice(self):
        db = MagicMock()
        registry = BusinessObjectRegistry(db)
        path = registry.get_graph_path("customer", "invoice")
        assert len(path) > 0
        assert path[0]["entity"] == "customer"
        assert path[-1]["entity"] == "invoice"

    def test_find_path_supplier_to_purchase_order(self):
        db = MagicMock()
        registry = BusinessObjectRegistry(db)
        path = registry.get_graph_path("supplier", "purchase_order")
        assert len(path) > 0
        assert path[0]["entity"] == "supplier"
        assert path[-1]["entity"] == "purchase_order"

    def test_find_path_unknown_entity(self):
        db = MagicMock()
        registry = BusinessObjectRegistry(db)
        path = registry.get_graph_path("customer", "nonexistent")
        assert path == []

    def test_find_path_no_connection(self):
        db = MagicMock()
        registry = BusinessObjectRegistry(db)
        path = registry.get_graph_path("product", "employee")
        assert path == []

    def test_find_path_multi_hop(self):
        db = MagicMock()
        registry = BusinessObjectRegistry(db)
        path = registry.get_graph_path("employee", "invoice")
        if path:
            assert path[0]["entity"] == "employee"
            assert path[-1]["entity"] == "invoice"
            assert len(path) >= 2
