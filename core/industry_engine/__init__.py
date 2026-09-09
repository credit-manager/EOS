"""
EOS Industry Engine — Core Architecture
Exports all engines for the Industry Framework.
"""

from .module_engine import ModuleEngine, ModuleDefinition, ModuleCategory, ModuleCapability, ModuleStatus
from .entity_engine import EntityEngine, EntityDefinition, FieldDefinition, FieldType, FieldCategory, FieldValidation, EntityRelationship
from .rules_engine import RulesEngine, BusinessRule, RuleType, RuleEvent, RuleCondition, ComparisonOp
from .workflow_engine import WorkflowEngine, WorkflowDefinition, WorkflowStep, WorkflowInstance, WorkflowStatus, StepType, EscalationType
from .permission_engine import PermissionEngine, Permission, Role, PermissionGrant, PermissionAction, AccessLevel
from .terminology_engine import TerminologyEngine, IndustryTerminology, TermSet
from .accounting_mapping import AccountingMappingEngine, AccountMapping, IndustryAccountingMapping, JournalType, PostingTrigger
from .settings_engine import SettingsEngine, IndustrySettings, CurrencyConfig, TaxConfig, FiscalYearConfig, TaxSystem

__all__ = [
    # Module Engine
    "ModuleEngine", "ModuleDefinition", "ModuleCategory", "ModuleCapability", "ModuleStatus",
    # Entity Engine
    "EntityEngine", "EntityDefinition", "FieldDefinition", "FieldType", "FieldCategory", "FieldValidation", "EntityRelationship",
    # Rules Engine
    "RulesEngine", "BusinessRule", "RuleType", "RuleEvent", "RuleCondition", "ComparisonOp",
    # Workflow Engine
    "WorkflowEngine", "WorkflowDefinition", "WorkflowStep", "WorkflowInstance", "WorkflowStatus", "StepType", "EscalationType",
    # Permission Engine
    "PermissionEngine", "Permission", "Role", "PermissionGrant", "PermissionAction", "AccessLevel",
    # Terminology Engine
    "TerminologyEngine", "IndustryTerminology", "TermSet",
    # Accounting Mapping
    "AccountingMappingEngine", "AccountMapping", "IndustryAccountingMapping", "JournalType", "PostingTrigger",
    # Settings Engine
    "SettingsEngine", "IndustrySettings", "CurrencyConfig", "TaxConfig", "FiscalYearConfig", "TaxSystem",
]


class IndustryEngine:
    """
    Composite engine that combines all sub-engines.
    Single entry point for the Industry Framework.
    """

    def __init__(self):
        self.modules = ModuleEngine()
        self.entities = EntityEngine()
        self.rules = RulesEngine()
        self.workflows = WorkflowEngine()
        self.permissions = PermissionEngine()
        self.terminology = TerminologyEngine()
        self.accounting = AccountingMappingEngine()
        self.settings = SettingsEngine()

    def register_industry(self, industry_code: str, template: dict):
        """
        Register a complete industry template.
        template should contain: modules, entities, workflows, rules,
        permissions, terminology, accounting, settings.
        """
        # Register entities
        for entity_data in template.get("entities", []):
            if isinstance(entity_data, EntityDefinition):
                self.entities.register(entity_data)

        # Register workflows
        for wf_data in template.get("workflows", []):
            if isinstance(wf_data, WorkflowDefinition):
                self.workflows.register(wf_data)

        # Register rules
        for rule_data in template.get("rules", []):
            if isinstance(rule_data, BusinessRule):
                self.rules.register(rule_data)

        # Register terminology
        if "terminology" in template:
            term = template["terminology"]
            if isinstance(term, IndustryTerminology):
                self.terminology.register(term)

        # Register accounting mappings
        if "accounting" in template:
            acct = template["accounting"]
            if isinstance(acct, IndustryAccountingMapping):
                self.accounting.register(acct)

        # Register settings
        if "settings" in template:
            settings = template["settings"]
            if isinstance(settings, IndustrySettings):
                self.settings.register(settings)

    def get_industry_menu(self, industry_code: str, module_codes: list) -> list:
        """Get menu for an industry based on active modules."""
        # Get terminology for labels
        term = self.terminology.get(industry_code)

        # Get menu from modules
        menu = self.modules.get_menu_for_modules(module_codes)

        # Apply industry terminology
        if term:
            for item in menu:
                key = item.get("key", item.get("path", "")).split("/")[-1]
                label_term = term.menu_labels.get(key)
                if label_term:
                    item["label"] = label_term.en
                    item["labelAr"] = label_term.ar

        return menu

    def get_industry_dashboard(self, industry_code: str, module_codes: list) -> list:
        """Get dashboard widget list for an industry."""
        return self.modules.get_dashboard_widgets(module_codes)

    def get_industry_permissions(self, industry_code: str, module_codes: list) -> list:
        """Get all permissions for an industry."""
        return self.modules.get_permissions(module_codes)

    def validate_operation(self, industry_code: str, entity_code: str, data: dict, event: str = "before_create") -> list:
        """Validate an operation against business rules."""
        rule_event = RuleEvent(event) if hasattr(RuleEvent, event.upper()) else RuleEvent.BEFORE_CREATE
        return self.rules.validate(entity_code, data, rule_event)

    def post_journal(self, industry_code: str, event: str, data: dict) -> dict:
        """Generate journal entry for a business event."""
        return self.accounting.generate_journal_entry(industry_code, event, data)


# Global instance
industry_engine = IndustryEngine()
