import re
import time
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from .models import Policy, PolicyExecution
from .schemas import (
    Action,
    Condition,
    ElseClause,
    IfClause,
    ThenClause,
    WhenClause,
)


class PolicyEngine:
    """Policy Engine V2 - WHEN/IF/THEN/ELSE evaluation engine"""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self._action_registry: dict[str, Any] = {}

    def register_action(self, action_type: str, handler: Any) -> None:
        """Register an action handler"""
        self._action_registry[action_type] = handler

    def evaluate(
        self,
        trigger: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Evaluate all matching policies and execute their actions"""
        policies = self._get_policies_for_trigger(trigger, entity_type)
        results = []

        for policy in policies:
            result = self._evaluate_policy(policy, trigger, entity_type, entity_id, context or {})
            results.append(result)

        return results

    def _get_policies_for_trigger(
        self,
        trigger: str,
        entity_type: str | None,
    ) -> list[Policy]:
        """Get all enabled policies matching the trigger"""
        stmt = (
            select(Policy)
            .where(
                Policy.tenant_id == self.tenant_id,
                Policy.enabled.is_(True),
                Policy.when_clause["trigger"].as_string() == trigger,
            )
            .order_by(Policy.priority.desc())
        )

        if entity_type:
            stmt = stmt.where(
                Policy.when_clause["entity_type"].as_string() == entity_type
            )

        return list(self.db.scalars(stmt).all())

    def _evaluate_policy(
        self,
        policy: Policy,
        trigger: str,
        entity_type: str | None,
        entity_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate a single policy"""
        start_time = time.time()

        try:
            # Parse policy definition
            _when = WhenClause(**policy.when_clause)
            if_clause = IfClause(**policy.if_clause)
            then = ThenClause(**policy.then_actions)
            else_clause = ElseClause(**policy.else_actions) if policy.else_actions else None

            # Evaluate IF conditions
            matched = self._evaluate_conditions(if_clause, context)

            # Execute actions based on match
            actions_executed = []
            if matched:
                actions_executed = self._execute_actions(then.actions, context, then.stop_on_failure)
            elif else_clause and else_clause.actions:
                actions_executed = self._execute_actions(else_clause.actions, context, True)

            execution_time_ms = int((time.time() - start_time) * 1000)

            # Log execution
            execution = PolicyExecution(
                tenant_id=self.tenant_id,
                policy_id=policy.id,
                policy_code=policy.code,
                trigger_event=trigger,
                trigger_resource_type=entity_type,
                trigger_resource_id=entity_id,
                matched=matched,
                actions_executed={"actions": actions_executed},
                execution_time_ms=execution_time_ms,
            )
            self.db.add(execution)

            # Audit
            audit_record(
                self.db,
                tenant_id=self.tenant_id,
                actor_id=None,
                action="policy.executed",
                resource_type="policy",
                resource_id=policy.id,
                metadata={
                    "policy_code": policy.code,
                    "trigger": trigger,
                    "matched": matched,
                    "actions_count": len(actions_executed),
                },
            )

            self.db.commit()

            return {
                "policy_id": str(policy.id),
                "policy_code": policy.code,
                "matched": matched,
                "actions_executed": actions_executed,
                "execution_time_ms": execution_time_ms,
            }

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)

            execution = PolicyExecution(
                tenant_id=self.tenant_id,
                policy_id=policy.id,
                policy_code=policy.code,
                trigger_event=trigger,
                trigger_resource_type=entity_type,
                trigger_resource_id=entity_id,
                matched=False,
                actions_executed={},
                execution_time_ms=execution_time_ms,
                error_message=str(e),
            )
            self.db.add(execution)
            self.db.commit()

            return {
                "policy_id": str(policy.id),
                "policy_code": policy.code,
                "matched": False,
                "error": str(e),
                "execution_time_ms": execution_time_ms,
            }

    def _evaluate_conditions(self, if_clause: IfClause, context: dict[str, Any]) -> bool:
        """Evaluate IF conditions"""
        if not if_clause.conditions:
            return True

        results = []
        for condition in if_clause.conditions:
            result = self._evaluate_condition(condition, context)
            if condition.negate:
                result = not result
            results.append(result)

        if if_clause.logic == "and":
            return all(results)
        else:
            return any(results)

    def _evaluate_condition(self, condition: Condition, context: dict[str, Any]) -> bool:
        """Evaluate a single condition"""
        # Get field value from context
        field_value = self._get_field_value(condition.field, context)
        expected_value = condition.value

        operator = condition.operator

        if operator == "eq":
            return field_value == expected_value
        elif operator == "neq":
            return field_value != expected_value
        elif operator == "gt":
            return self._compare_values(field_value, expected_value, lambda a, b: a > b)
        elif operator == "gte":
            return self._compare_values(field_value, expected_value, lambda a, b: a >= b)
        elif operator == "lt":
            return self._compare_values(field_value, expected_value, lambda a, b: a < b)
        elif operator == "lte":
            return self._compare_values(field_value, expected_value, lambda a, b: a <= b)
        elif operator == "in":
            return field_value in expected_value if isinstance(expected_value, list) else False
        elif operator == "not_in":
            return field_value not in expected_value if isinstance(expected_value, list) else True
        elif operator == "contains":
            return expected_value in field_value if isinstance(field_value, str) else False
        elif operator == "not_contains":
            return expected_value not in field_value if isinstance(field_value, str) else True
        elif operator == "starts_with":
            return str(field_value).startswith(str(expected_value)) if field_value else False
        elif operator == "ends_with":
            return str(field_value).endswith(str(expected_value)) if field_value else False
        elif operator == "regex":
            return bool(re.match(str(expected_value), str(field_value))) if field_value else False
        elif operator == "is_null":
            return field_value is None
        elif operator == "is_not_null":
            return field_value is not None
        else:
            return False

    def _get_field_value(self, field_path: str, context: dict[str, Any]) -> Any:
        """Get field value from context using dot notation"""
        parts = field_path.split(".")
        value = context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value

    def _compare_values(
        self,
        actual: Any,
        expected: Any,
        comparator: Any,
    ) -> bool:
        """Compare values safely"""
        try:
            if actual is None or expected is None:
                return False
            return comparator(actual, expected)
        except (TypeError, ValueError):
            return False

    def _execute_actions(
        self,
        actions: list[Action],
        context: dict[str, Any],
        stop_on_failure: bool,
    ) -> list[dict[str, Any]]:
        """Execute a list of actions"""
        results = []

        for action in actions:
            try:
                handler = self._action_registry.get(action.type)
                if handler:
                    result = handler(action.params, context)
                    results.append({
                        "type": action.type,
                        "success": True,
                        "result": result,
                    })
                else:
                    results.append({
                        "type": action.type,
                        "success": False,
                        "error": f"No handler registered for action type: {action.type}",
                    })

            except Exception as e:
                results.append({
                    "type": action.type,
                    "success": False,
                    "error": str(e),
                })

                if stop_on_failure:
                    break

        return results


# Default action handlers
def update_record_handler(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Default handler for update_record action"""
    return {"action": "update_record", "params": params}


def create_record_handler(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Default handler for create_record action"""
    return {"action": "create_record", "params": params}


def send_email_handler(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Default handler for send_email action"""
    return {"action": "send_email", "params": params}


def call_webhook_handler(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Default handler for call_webhook action"""
    return {"action": "call_webhook", "params": params}


def publish_event_handler(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Default handler for publish_event action"""
    return {"action": "publish_event", "params": params}


def notify_handler(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Default handler for notify action"""
    return {"action": "notify", "params": params}


def audit_handler(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Default handler for audit action"""
    return {"action": "audit", "params": params}


def register_default_handlers(engine: PolicyEngine) -> None:
    """Register default action handlers"""
    engine.register_action("update_record", update_record_handler)
    engine.register_action("create_record", create_record_handler)
    engine.register_action("send_email", send_email_handler)
    engine.register_action("call_webhook", call_webhook_handler)
    engine.register_action("publish_event", publish_event_handler)
    engine.register_action("notify", notify_handler)
    engine.register_action("audit", audit_handler)
