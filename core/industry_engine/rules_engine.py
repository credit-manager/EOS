"""
EOS Industry Engine — Business Rules Engine
Defines and evaluates validation, calculation, and condition rules.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RuleType(str, Enum):
    VALIDATION = "validation"      # Validate data before save
    CALCULATION = "calculation"    # Calculate derived fields
    CONDITION = "condition"        # Enable/disable fields based on conditions
    NOTIFICATION = "notification"  # Trigger notifications
    HOOK = "hook"                  # Run custom logic on events


class RuleEvent(str, Enum):
    BEFORE_CREATE = "before_create"
    AFTER_CREATE = "after_create"
    BEFORE_UPDATE = "before_update"
    AFTER_UPDATE = "after_update"
    BEFORE_DELETE = "before_delete"
    AFTER_DELETE = "after_delete"
    ON_SUBMIT = "on_submit"
    ON_APPROVE = "on_approve"
    ON_REJECT = "on_reject"


class ComparisonOp(str, Enum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


@dataclass
class RuleCondition:
    field: str
    operator: ComparisonOp
    value: Any = None


@dataclass
class BusinessRule:
    code: str
    name: str
    name_ar: str
    rule_type: RuleType
    entity: str
    module: str = ""
    description: str = ""
    conditions: list[RuleCondition] = field(default_factory=list)
    event: RuleEvent = RuleEvent.BEFORE_CREATE
    priority: int = 0
    is_active: bool = True
    error_message: str = ""
    error_message_ar: str = ""
    formula: str | None = None        # For CALCULATION rules
    action: dict[str, Any] | None = None  # For HOOK rules
    metadata: dict[str, Any] = field(default_factory=dict)


class RulesEngine:
    """
    Evaluates business rules for entities.
    Rules can validate, calculate, or trigger actions.
    """

    def __init__(self):
        self._rules: dict[str, BusinessRule] = {}
        self._calculators: dict[str, Callable] = {}
        self._validators: dict[str, Callable] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Register built-in platform rules."""
        # Accounting validation rules
        self.register(BusinessRule(
            code="JOURNAL平衡", name="Journal Entry Balanced", name_ar="القيد متوازن",
            rule_type=RuleType.VALIDATION, entity="journal_entry", module="accounting",
            description="Total debit must equal total credit",
            event=RuleEvent.BEFORE_SUBMIT if hasattr(RuleEvent, 'BEFORE_SUBMIT') else RuleEvent.ON_SUBMIT,
            error_message="Journal entry is not balanced",
            error_message_ar="القيد اليومي غير متوازن",
        ))

        # Stock validation rules
        self.register(BusinessRule(
            code="STOCK_MIN", name="Minimum Stock Check", name_ar="التحقق من الحد الأدنى",
            rule_type=RuleType.CONDITION, entity="stock", module="inventory",
            description="Trigger reorder alert when stock falls below minimum",
        ))

        # Financial rules
        self.register(BusinessRule(
            code="DISCOUNT_LIMIT", name="Discount Limit", name_ar="حد الخصم",
            rule_type=RuleType.VALIDATION, entity="quotation", module="sales",
            description="Discount cannot exceed 25% without approval",
            conditions=[RuleCondition("discount_percent", ComparisonOp.GT, 25)],
            error_message="Discount exceeds 25% — requires manager approval",
            error_message_ar="الخصم يتجاوز 25% — يحتاج موافقة المدير",
        ))

    def register(self, rule: BusinessRule):
        """Register a new business rule."""
        self._rules[rule.code] = rule

    def register_calculator(self, rule_code: str, calculator: Callable):
        """Register a custom calculation function."""
        self._calculators[rule_code] = calculator

    def register_validator(self, rule_code: str, validator: Callable):
        """Register a custom validation function."""
        self._validators[rule_code] = validator

    def get(self, code: str) -> BusinessRule | None:
        """Get rule by code."""
        return self._rules.get(code)

    def get_by_entity(self, entity_code: str) -> list[BusinessRule]:
        """Get all rules for an entity."""
        return [r for r in self._rules.values() if r.entity == entity_code and r.is_active]

    def get_by_event(self, entity_code: str, event: RuleEvent) -> list[BusinessRule]:
        """Get rules for an entity that trigger on a specific event."""
        return [r for r in self._rules.values()
                if r.entity == entity_code and r.event == event and r.is_active]

    def evaluate_conditions(self, conditions: list[RuleCondition], data: dict[str, Any]) -> bool:
        """Evaluate if all conditions are met."""
        for cond in conditions:
            value = data.get(cond.field)
            if not self._compare(value, cond.operator, cond.value):
                return False
        return True

    def _compare(self, actual: Any, op: ComparisonOp, expected: Any) -> bool:
        """Compare actual vs expected using the operator."""
        if op == ComparisonOp.EQ:
            return actual == expected
        elif op == ComparisonOp.NEQ:
            return actual != expected
        elif op == ComparisonOp.GT:
            return float(actual or 0) > float(expected)
        elif op == ComparisonOp.GTE:
            return float(actual or 0) >= float(expected)
        elif op == ComparisonOp.LT:
            return float(actual or 0) < float(expected)
        elif op == ComparisonOp.LTE:
            return float(actual or 0) <= float(expected)
        elif op == ComparisonOp.IN:
            return actual in (expected or [])
        elif op == ComparisonOp.NOT_IN:
            return actual not in (expected or [])
        elif op == ComparisonOp.CONTAINS:
            return expected in (actual or "")
        elif op == ComparisonOp.STARTS_WITH:
            return str(actual or "").startswith(str(expected))
        elif op == ComparisonOp.IS_EMPTY:
            return actual is None or actual == ""
        elif op == ComparisonOp.IS_NOT_EMPTY:
            return actual is not None and actual != ""
        return True

    def validate(self, entity_code: str, data: dict[str, Any], event: RuleEvent = RuleEvent.BEFORE_CREATE) -> list[str]:
        """
        Run all validation rules for an entity.
        Returns list of error messages.
        """
        errors = []
        rules = self.get_by_event(entity_code, event)

        for rule in sorted(rules, key=lambda r: r.priority, reverse=True):
            if rule.rule_type != RuleType.VALIDATION:
                continue

            # Check if conditions are met
            if rule.conditions and not self.evaluate_conditions(rule.conditions, data):
                continue

            # Run custom validator if registered
            if rule.code in self._validators:
                custom_errors = self._validators[rule.code](data)
                if custom_errors:
                    errors.extend(custom_errors if isinstance(custom_errors, list) else [custom_errors])
                continue

            # Default validation logic based on rule code
            if rule.code == "JOURNAL平衡":
                debit = sum(float(l.get("debit", 0)) for l in data.get("lines", []))
                credit = sum(float(l.get("credit", 0)) for l in data.get("lines", []))
                if abs(debit - credit) > 0.01:
                    errors.append(rule.error_message_ar or rule.error_message)

            elif rule.code == "DISCOUNT_LIMIT":
                discount = float(data.get("discount_percent", 0))
                if discount > 25:
                    errors.append(rule.error_message_ar or rule.error_message)

        return errors

    def calculate(self, entity_code: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Run all calculation rules for an entity.
        Returns dict of calculated field values.
        """
        results = {}
        rules = self.get_by_entity(entity_code)

        for rule in rules:
            if rule.rule_type != RuleType.CALCULATION:
                continue

            if rule.code in self._calculators:
                results.update(self._calculators[rule.code](data))

        return results

    def get_triggered_actions(self, entity_code: str, data: dict[str, Any], event: RuleEvent) -> list[dict[str, Any]]:
        """Get actions triggered by rules for a given event."""
        actions = []
        rules = self.get_by_event(entity_code, event)

        for rule in rules:
            if rule.rule_type == RuleType.HOOK and rule.action:
                if rule.conditions and not self.evaluate_conditions(rule.conditions, data):
                    continue
                actions.append(rule.action)

        return actions

    def export_rules(self, module_code: str | None = None) -> list[dict[str, Any]]:
        """Export rules for a module (for JSON template definitions)."""
        rules = self._rules.values()
        if module_code:
            rules = [r for r in rules if r.module == module_code]

        return [{
            "code": r.code,
            "name": r.name,
            "name_ar": r.name_ar,
            "rule_type": r.rule_type.value,
            "entity": r.entity,
            "module": r.module,
            "event": r.event.value,
            "conditions": [{"field": c.field, "operator": c.operator.value, "value": c.value} for c in r.conditions],
            "error_message": r.error_message,
            "error_message_ar": r.error_message_ar,
        } for r in rules]
