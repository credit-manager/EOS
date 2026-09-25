"""
AI Policy Engine - evaluate policies before AI agent execution.

Provides:
- BUILTIN_POLICIES: default policy templates for tenants
- evaluate_policies(): check agent+action against policy rules
- policy_matches_action(): wildcard/regex pattern matching
- PolicyViolationError: raised when a policy denies an action
"""

import re
from typing import Any


class PolicyViolationError(Exception):
    """Raised when an AI agent action violates policy."""
    pass


# ---------------------------------------------------------------------------
# Built-in policy templates
# ---------------------------------------------------------------------------

BUILTIN_POLICIES = [
    {
        "code": "finance_read",
        "name": "Finance Read Allowed",
        "description": "Finance agents may read financial data",
        "agent_types": ["finance"],
        "action_patterns": ["read_*", "get_*", "list_*", "search_*", "export_*"],
        "effect": "permit",
        "priority": 10,
    },
    {
        "code": "finance_modify_escalate",
        "name": "Finance Modify Requires Approval",
        "description": "Finance agents modifying data requires human approval",
        "agent_types": ["finance"],
        "action_patterns": ["create_*", "update_*", "delete_*", "post_*"],
        "effect": "escalate",
        "priority": 20,
    },
    {
        "code": "finance_payment_deny",
        "name": "AI Cannot Execute Payments",
        "description": "AI agents cannot directly execute payment transactions",
        "agent_types": ["finance"],
        "action_patterns": ["execute_payment", "process_payment", "transfer_*"],
        "effect": "deny",
        "priority": 5,
    },
    {
        "code": "procurement_read",
        "name": "Procurement Read Allowed",
        "description": "Procurement agents may read procurement data",
        "agent_types": ["procurement"],
        "action_patterns": ["read_*", "get_*", "list_*", "search_*"],
        "effect": "permit",
        "priority": 10,
    },
    {
        "code": "procurement_create",
        "name": "Procurement Create Allowed",
        "description": "Procurement agents may create requisitions and draft POs",
        "agent_types": ["procurement"],
        "action_patterns": ["create_requisition", "create_draft_po", "update_requisition"],
        "effect": "permit",
        "priority": 20,
    },
    {
        "code": "procurement_approve_deny",
        "name": "Procurement Self-Approval Denied",
        "description": "Procurement agents cannot approve their own POs",
        "agent_types": ["procurement"],
        "action_patterns": ["approve_po", "approve_purchase_order"],
        "effect": "deny",
        "priority": 5,
    },
    {
        "code": "project_read",
        "name": "Project Read Allowed",
        "description": "Project agents may read project data",
        "agent_types": ["project"],
        "action_patterns": ["read_*", "get_*", "list_*", "search_*"],
        "effect": "permit",
        "priority": 10,
    },
    {
        "code": "project_update",
        "name": "Project Update Allowed",
        "description": "Project agents may update project status and progress",
        "agent_types": ["project"],
        "action_patterns": ["update_project", "update_task", "update_status"],
        "effect": "permit",
        "priority": 20,
    },
    {
        "code": "executive_read",
        "name": "Executive Read All",
        "description": "Executive agents may read across all domains",
        "agent_types": ["executive"],
        "action_patterns": ["read_*", "get_*", "list_*", "search_*", "aggregate_*"],
        "effect": "permit",
        "priority": 10,
    },
    {
        "code": "executive_write",
        "name": "Executive Write Reports",
        "description": "Executive agents may write reports and summaries",
        "agent_types": ["executive"],
        "action_patterns": ["create_report", "create_summary", "create_dashboard"],
        "effect": "permit",
        "priority": 20,
    },
    {
        "code": "executive_modify_deny",
        "name": "Executive Cannot Modify Core Data",
        "description": "Executive agents cannot modify core business data",
        "agent_types": ["executive"],
        "action_patterns": ["delete_*", "post_journal", "execute_payment", "approve_*"],
        "effect": "deny",
        "priority": 5,
    },
    {
        "code": "general_read",
        "name": "General Read Only",
        "description": "General agents may read data but not write",
        "agent_types": ["general"],
        "action_patterns": ["read_*", "get_*", "list_*"],
        "effect": "permit",
        "priority": 10,
    },
    {
        "code": "general_write_deny",
        "name": "General Write Denied",
        "description": "General agents cannot write data",
        "agent_types": ["general"],
        "action_patterns": ["create_*", "update_*", "delete_*"],
        "effect": "deny",
        "priority": 5,
    },
    {
        "code": "external_api_escalate",
        "name": "External API Requires Approval",
        "description": "Any call to external APIs requires human approval",
        "agent_types": ["*"],
        "action_patterns": ["call_external_*", "send_webhook", "http_*"],
        "effect": "escalate",
        "priority": 15,
    },
    {
        "code": "data_export_escalate",
        "name": "Bulk Data Export Requires Approval",
        "description": "Bulk data export requires approval",
        "agent_types": ["*"],
        "action_patterns": ["bulk_export_*", "export_all_*", "download_all_*"],
        "effect": "escalate",
        "priority": 15,
    },
    {
        "code": "user_mgmt_deny",
        "name": "User Management Denied",
        "description": "AI agents cannot manage users",
        "agent_types": ["*"],
        "action_patterns": ["create_user", "delete_user", "update_user_role", "disable_user"],
        "effect": "deny",
        "priority": 5,
    },
    {
        "code": "tenant_mgmt_deny",
        "name": "Tenant Management Denied",
        "description": "AI agents cannot manage tenant configuration",
        "agent_types": ["*"],
        "action_patterns": ["update_tenant", "delete_tenant", "configure_*"],
        "effect": "deny",
        "priority": 5,
    },
]


# ---------------------------------------------------------------------------
# Pattern matching
# ---------------------------------------------------------------------------

def policy_matches_action(pattern: str, action: str) -> bool:
    """Check if a policy action pattern matches the given action.

    Supports:
        - Exact match: "create_payment"
        - Wildcard prefix: "read_*"
        - Wildcard suffix: "*_payment"
        - Wildcard both: "*"
    """
    if pattern == "*":
        return True
    if pattern.endswith("*"):
        prefix = pattern[:-1]
        return action.startswith(prefix)
    if pattern.startswith("*"):
        suffix = pattern[1:]
        return action.endswith(suffix)
    return pattern == action


def _agent_matches(agent_types_json: str, agent_type: str) -> bool:
    """Check if agent_type matches the JSON list in agent_types column."""
    import json
    try:
        types = json.loads(agent_types_json)
    except (json.JSONDecodeError, TypeError):
        return False
    if "*" in types:
        return True
    return agent_type in types


# ---------------------------------------------------------------------------
# Policy evaluation engine
# ---------------------------------------------------------------------------

def evaluate_policies(
    agent_type: str,
    action: str,
    policies: list[Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate an agent+action against active policies.

    Returns:
        {
            "effect": "permit" | "deny" | "escalate",
            "allowed": bool,
            "requires_approval": bool,
            "policy_applied": str | None,
            "reason": str,
        }

    Policy evaluation order (first match wins):
        1. deny (lowest priority number = highest priority)
        2. escalate
        3. permit

    If no policy matches, default is DENY.
    """
    matched_deny = None
    matched_escalate = None
    matched_permit = None

    for policy in policies:
        if not getattr(policy, "is_active", True):
            continue
        if not _agent_matches(policy.agent_types, agent_type):
            continue

        # Check if any action pattern matches
        action_matched = False
        patterns = policy.action_patterns
        if isinstance(patterns, str):
            try:
                import json
                patterns = json.loads(patterns)
            except (json.JSONDecodeError, TypeError):
                patterns = [patterns]
        for pat in patterns:
            if policy_matches_action(pat, action):
                action_matched = True
                break
        if not action_matched:
            continue

        effect = policy.effect.value if hasattr(policy.effect, "value") else policy.effect
        priority = getattr(policy, "priority", 100)

        if effect == "deny":
            if matched_deny is None or priority < matched_deny[1]:
                matched_deny = (policy, priority)
        elif effect == "escalate":
            if matched_escalate is None or priority < matched_escalate[1]:
                matched_escalate = (policy, priority)
        elif effect == "permit":
            if matched_permit is None or priority < matched_permit[1]:
                matched_permit = (policy, priority)

    # Deny wins over escalate and permit
    if matched_deny:
        p = matched_deny[0]
        return {
            "effect": "deny",
            "allowed": False,
            "requires_approval": False,
            "policy_applied": p.code,
            "reason": f"Denied by policy: {p.name}",
        }

    # Escalate wins over permit
    if matched_escalate:
        p = matched_escalate[0]
        return {
            "effect": "escalate",
            "allowed": False,
            "requires_approval": True,
            "policy_applied": p.code,
            "reason": f"Requires approval: {p.name}",
        }

    if matched_permit:
        p = matched_permit[0]
        return {
            "effect": "permit",
            "allowed": True,
            "requires_approval": False,
            "policy_applied": p.code,
            "reason": f"Allowed by policy: {p.name}",
        }

    # Default: deny
    return {
        "effect": "deny",
        "allowed": False,
        "requires_approval": False,
        "policy_applied": None,
        "reason": f"No policy allows agent '{agent_type}' to perform '{action}'",
    }
