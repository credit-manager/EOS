"""Business Object V2 — Rich entity configuration for the Business Operating System."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RelationshipConfig:
    target_entity: str
    relation_type: str  # "one_to_many", "many_to_one", "many_to_many"
    foreign_key: str
    label: str
    cascade_delete: bool = False
    required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_entity": self.target_entity,
            "relation_type": self.relation_type,
            "foreign_key": self.foreign_key,
            "label": self.label,
            "cascade_delete": self.cascade_delete,
            "required": self.required,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RelationshipConfig:
        return cls(
            target_entity=data["target_entity"],
            relation_type=data["relation_type"],
            foreign_key=data["foreign_key"],
            label=data["label"],
            cascade_delete=data.get("cascade_delete", False),
            required=data.get("required", False),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        valid_types = {"one_to_many", "many_to_one", "many_to_many", "one_to_one"}
        if self.relation_type not in valid_types:
            errors.append(f"Invalid relation_type '{self.relation_type}', must be one of {sorted(valid_types)}")
        if not self.target_entity:
            errors.append("target_entity is required")
        if not self.foreign_key:
            errors.append("foreign_key is required")
        return errors


@dataclass
class EntityRuleConfig:
    rule_id: str
    event_type: str  # "on_create", "on_update", "on_delete", "on_status_change"
    condition: str
    action: str  # "require_approval", "notify", "block", "auto_create", "webhook"
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "event_type": self.event_type,
            "condition": self.condition,
            "action": self.action,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityRuleConfig:
        return cls(
            rule_id=data["rule_id"],
            event_type=data["event_type"],
            condition=data["condition"],
            action=data["action"],
            params=data.get("params", {}),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        valid_events = {"on_create", "on_update", "on_delete", "on_status_change", "on_submit", "on_approve"}
        if self.event_type not in valid_events:
            errors.append(f"Invalid event_type '{self.event_type}', must be one of {sorted(valid_events)}")
        valid_actions = {"require_approval", "notify", "block", "auto_create", "webhook", "set_field", "log"}
        if self.action not in valid_actions:
            errors.append(f"Invalid action '{self.action}', must be one of {sorted(valid_actions)}")
        if not self.rule_id:
            errors.append("rule_id is required")
        return errors


@dataclass
class EntityWorkflowConfig:
    states: list[str]
    initial_state: str
    transitions: list[dict[str, Any]]
    approval_required: bool = False
    approvers: list[str] = field(default_factory=list)
    timeout_hours: int | None = None
    escalation: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "states": self.states,
            "initial_state": self.initial_state,
            "transitions": self.transitions,
            "approval_required": self.approval_required,
            "approvers": self.approvers,
        }
        if self.timeout_hours is not None:
            result["timeout_hours"] = self.timeout_hours
        if self.escalation is not None:
            result["escalation"] = self.escalation
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityWorkflowConfig:
        return cls(
            states=data["states"],
            initial_state=data["initial_state"],
            transitions=data["transitions"],
            approval_required=data.get("approval_required", False),
            approvers=data.get("approvers", []),
            timeout_hours=data.get("timeout_hours"),
            escalation=data.get("escalation"),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.states:
            errors.append("states list cannot be empty")
        if self.initial_state not in self.states:
            errors.append(f"initial_state '{self.initial_state}' not in states list")
        for i, transition in enumerate(self.transitions):
            if transition.get("from") not in self.states:
                errors.append(f"Transition {i}: 'from' state '{transition.get('from')}' not in states list")
            if transition.get("to") not in self.states:
                errors.append(f"Transition {i}: 'to' state '{transition.get('to')}' not in states list")
        return errors


@dataclass
class EntityDocumentConfig:
    document_types: list[str]
    required: bool = False
    ocr_enabled: bool = False
    classification: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_types": self.document_types,
            "required": self.required,
            "ocr_enabled": self.ocr_enabled,
            "classification": self.classification,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityDocumentConfig:
        return cls(
            document_types=data["document_types"],
            required=data.get("required", False),
            ocr_enabled=data.get("ocr_enabled", False),
            classification=data.get("classification", False),
        )

    def validate(self) -> list[str]:
        if not self.document_types:
            return ["document_types list cannot be empty"]
        return []


@dataclass
class EntityPermissionConfig:
    roles: dict[str, list[str]] = field(default_factory=lambda: {
        "admin": ["create", "read", "update", "delete", "approve"],
        "manager": ["create", "read", "update", "approve"],
        "user": ["create", "read", "update"],
        "viewer": ["read"],
    })
    field_permissions: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    row_level: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "roles": self.roles,
            "field_permissions": self.field_permissions,
            "row_level": self.row_level,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityPermissionConfig:
        return cls(
            roles=data.get("roles", {
                "admin": ["create", "read", "update", "delete", "approve"],
                "manager": ["create", "read", "update", "approve"],
                "user": ["create", "read", "update"],
                "viewer": ["read"],
            }),
            field_permissions=data.get("field_permissions", {}),
            row_level=data.get("row_level", False),
        )

    def validate(self) -> list[str]:
        valid_actions = {"create", "read", "update", "delete", "approve", "export", "import"}
        errors: list[str] = []
        for role, actions in self.roles.items():
            for action in actions:
                if action not in valid_actions:
                    errors.append(f"Role '{role}': invalid action '{action}'")
        return errors


@dataclass
class EntityFinancialConfig:
    has_financial_impact: bool = False
    posting_rules: list[dict[str, Any]] = field(default_factory=list)
    currency_field: str | None = None
    amount_field: str | None = None
    tax_applicable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_financial_impact": self.has_financial_impact,
            "posting_rules": self.posting_rules,
            "currency_field": self.currency_field,
            "amount_field": self.amount_field,
            "tax_applicable": self.tax_applicable,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityFinancialConfig:
        return cls(
            has_financial_impact=data.get("has_financial_impact", False),
            posting_rules=data.get("posting_rules", []),
            currency_field=data.get("currency_field"),
            amount_field=data.get("amount_field"),
            tax_applicable=data.get("tax_applicable", False),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.has_financial_impact and not self.amount_field:
            errors.append("amount_field is required when has_financial_impact is True")
        for i, rule in enumerate(self.posting_rules):
            if "debit" not in rule:
                errors.append(f"Posting rule {i}: missing 'debit' field")
            if "credit" not in rule:
                errors.append(f"Posting rule {i}: missing 'credit' field")
        return errors


@dataclass
class EntityAnalyticsConfig:
    kpis: list[dict[str, Any]] = field(default_factory=list)
    dashboards: list[str] = field(default_factory=list)
    drill_down_enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "kpis": self.kpis,
            "dashboards": self.dashboards,
            "drill_down_enabled": self.drill_down_enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityAnalyticsConfig:
        return cls(
            kpis=data.get("kpis", []),
            dashboards=data.get("dashboards", []),
            drill_down_enabled=data.get("drill_down_enabled", True),
        )


@dataclass
class EntityAIConfig:
    context_enabled: bool = True
    searchable: bool = True
    summarizable: bool = True
    auto_classify: bool = False
    suggested_actions: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_enabled": self.context_enabled,
            "searchable": self.searchable,
            "summarizable": self.summarizable,
            "auto_classify": self.auto_classify,
            "suggested_actions": self.suggested_actions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityAIConfig:
        return cls(
            context_enabled=data.get("context_enabled", True),
            searchable=data.get("searchable", True),
            summarizable=data.get("summarizable", True),
            auto_classify=data.get("auto_classify", False),
            suggested_actions=data.get("suggested_actions", False),
        )


@dataclass
class BusinessObjectConfig:
    """Complete configuration for a Business Object in the EOS."""

    entity_code: str
    entity_name: str
    description: str

    # Core
    fields: list[dict[str, Any]] = field(default_factory=list)

    # Relationships
    relationships: list[RelationshipConfig] = field(default_factory=list)

    # Rules
    rules: list[EntityRuleConfig] = field(default_factory=list)

    # Permissions
    permissions: EntityPermissionConfig = field(default_factory=EntityPermissionConfig)

    # Workflow
    workflow: EntityWorkflowConfig | None = None

    # Documents
    documents: EntityDocumentConfig | None = None

    # Financial
    financial: EntityFinancialConfig | None = None

    # Analytics
    analytics: EntityAnalyticsConfig | None = None

    # AI
    ai: EntityAIConfig = field(default_factory=EntityAIConfig)

    # Audit
    audit_enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        result: dict[str, Any] = {
            "entity_code": self.entity_code,
            "entity_name": self.entity_name,
            "description": self.description,
            "fields": self.fields,
            "relationships": [r.to_dict() for r in self.relationships],
            "rules": [r.to_dict() for r in self.rules],
            "permissions": self.permissions.to_dict(),
            "ai": self.ai.to_dict(),
            "audit_enabled": self.audit_enabled,
        }
        if self.workflow is not None:
            result["workflow"] = self.workflow.to_dict()
        if self.documents is not None:
            result["documents"] = self.documents.to_dict()
        if self.financial is not None:
            result["financial"] = self.financial.to_dict()
        if self.analytics is not None:
            result["analytics"] = self.analytics.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BusinessObjectConfig:
        """Deserialize from dict."""
        workflow = None
        if data.get("workflow"):
            workflow = EntityWorkflowConfig.from_dict(data["workflow"])

        documents = None
        if data.get("documents"):
            documents = EntityDocumentConfig.from_dict(data["documents"])

        financial = None
        if data.get("financial"):
            financial = EntityFinancialConfig.from_dict(data["financial"])

        analytics = None
        if data.get("analytics"):
            analytics = EntityAnalyticsConfig.from_dict(data["analytics"])

        return cls(
            entity_code=data["entity_code"],
            entity_name=data["entity_name"],
            description=data.get("description", ""),
            fields=data.get("fields", []),
            relationships=[RelationshipConfig.from_dict(r) for r in data.get("relationships", [])],
            rules=[EntityRuleConfig.from_dict(r) for r in data.get("rules", [])],
            permissions=EntityPermissionConfig.from_dict(data.get("permissions", {})),
            workflow=workflow,
            documents=documents,
            financial=financial,
            analytics=analytics,
            ai=EntityAIConfig.from_dict(data.get("ai", {})),
            audit_enabled=data.get("audit_enabled", True),
        )

    def validate(self) -> list[str]:
        """Validate the configuration. Returns list of errors."""
        errors: list[str] = []

        if not self.entity_code:
            errors.append("entity_code is required")
        if not self.entity_name:
            errors.append("entity_name is required")

        field_codes = [f.get("code") for f in self.fields if isinstance(f, dict)]
        duplicates = sorted({c for c in field_codes if field_codes.count(c) > 1})
        if duplicates:
            errors.append(f"Duplicate field codes: {', '.join(duplicates)}")

        for rel in self.relationships:
            errors.extend(rel.validate())

        for rule in self.rules:
            errors.extend(rule.validate())

        errors.extend(self.permissions.validate())

        if self.workflow is not None:
            errors.extend(self.workflow.validate())

        if self.documents is not None:
            errors.extend(self.documents.validate())

        if self.financial is not None:
            errors.extend(self.financial.validate())

        return errors
