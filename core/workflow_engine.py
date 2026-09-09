"""
P17 Workflow Engine — state machine, transitions, approvals.

Design:
  - Workflow Definition: states + transitions (graph)
  - Workflow Instance: one per record, tracks current state
  - Transitions: from_state → to_state with required roles + conditions
  - Actions: audit trail of every state change
  - Notifications + Events on state changes
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
from datetime import datetime, timezone


class WorkflowEngine:
    """
    Manages workflow lifecycle: definition → instance → transitions → completion.
    """

    VALID_ACTIONS = {"approve", "reject", "cancel", "return", "escalate", "delegate"}
    VALID_INSTANCE_STATUSES = {"active", "completed", "rejected", "cancelled", "expired"}

    def __init__(self, db: Session):
        self.db = db

    # ──────────────────────────────────────────────────────────
    # WORKFLOW DEFINITION
    # ──────────────────────────────────────────────────────────

    def create_workflow(
        self,
        code: str,
        name_en: str,
        entity_code: str,
        tenant_id: Optional[str] = None,
        name_ar: Optional[str] = None,
        description: Optional[str] = None,
        sla_hours: Optional[int] = None,
    ) -> str:
        """Create a workflow definition with initial state."""
        wf_id = str(uuid.uuid4())

        self.db.execute(
            text(
                "INSERT INTO dbp_workflow_definitions "
                "(id, tenant_id, code, name_en, name_ar, description, "
                "entity_code, is_active, is_published, sla_hours) "
                "VALUES (:id, :tid, :code, :name_en, :name_ar, :desc, "
                ":ec, false, false, :sla)"
            ),
            {
                "id": wf_id, "tid": tenant_id, "code": code,
                "name_en": name_en, "name_ar": name_ar,
                "desc": description, "ec": entity_code, "sla": sla_hours,
            },
        )

        # Auto-create initial state
        draft_state_id = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_workflow_states "
                "(id, workflow_id, code, name_en, state_type, is_initial, is_final) "
                "VALUES (:id, :wid, 'draft', 'Draft', 'pending', true, false)"
            ),
            {"id": draft_state_id, "wid": wf_id},
        )

        # Auto-create final states
        approved_id = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_workflow_states "
                "(id, workflow_id, code, name_en, state_type, is_initial, is_final) "
                "VALUES (:id, :wid, 'approved', 'Approved', 'approved', false, true)"
            ),
            {"id": approved_id, "wid": wf_id},
        )

        rejected_id = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_workflow_states "
                "(id, workflow_id, code, name_en, state_type, is_initial, is_final) "
                "VALUES (:id, :wid, 'rejected', 'Rejected', 'rejected', false, true)"
            ),
            {"id": rejected_id, "wid": wf_id},
        )

        self.db.flush()
        return wf_id

    def publish_workflow(self, workflow_id: str) -> bool:
        """Publish a workflow definition (makes it usable)."""
        result = self.db.execute(
            text(
                "UPDATE dbp_workflow_definitions "
                "SET is_published = true, is_active = true "
                "WHERE id = :id"
            ),
            {"id": workflow_id},
        )
        self.db.flush()
        return result.rowcount > 0

    def add_state(
        self,
        workflow_id: str,
        code: str,
        name_en: str,
        state_type: str = "pending",
        is_final: bool = False,
        name_ar: Optional[str] = None,
        allowed_roles: Optional[List[str]] = None,
    ) -> str:
        """Add a state to a workflow."""
        state_id = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_workflow_states "
                "(id, workflow_id, code, name_en, name_ar, state_type, "
                "is_initial, is_final, allowed_roles) "
                "VALUES (:id, :wid, :code, :name_en, :name_ar, :st, "
                "false, :final, :roles)"
            ),
            {
                "id": state_id, "wid": workflow_id, "code": code,
                "name_en": name_en, "name_ar": name_ar,
                "st": state_type, "final": is_final,
                "roles": json_dumps(allowed_roles or []),
            },
        )
        self.db.flush()
        return state_id

    def add_transition(
        self,
        workflow_id: str,
        code: str,
        name_en: str,
        from_state_id: str,
        to_state_id: str,
        action: str = "approve",
        required_roles: Optional[List[str]] = None,
        conditions: Optional[List[Dict]] = None,
    ) -> str:
        """Add a transition between states."""
        trans_id = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_workflow_transitions "
                "(id, workflow_id, code, name_en, from_state_id, to_state_id, "
                "action, required_roles, conditions) "
                "VALUES (:id, :wid, :code, :name_en, :from_s, :to_s, "
                ":action, :roles, :conds)"
            ),
            {
                "id": trans_id, "wid": workflow_id, "code": code,
                "name_en": name_en, "from_s": from_state_id, "to_s": to_state_id,
                "action": action,
                "roles": json_dumps(required_roles or []),
                "conds": json_dumps(conditions or []),
            },
        )
        self.db.flush()
        return trans_id

    def get_workflow_detail(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get full workflow definition with states and transitions."""
        wf = self.db.execute(
            text(
                "SELECT id, code, name_en, name_ar, entity_code, "
                "is_active, is_published, sla_hours, created_at "
                "FROM dbp_workflow_definitions WHERE id = :id"
            ),
            {"id": workflow_id},
        ).fetchone()

        if not wf:
            return None

        states = self.db.execute(
            text(
                "SELECT id, code, name_en, name_ar, state_type, "
                "is_initial, is_final, allowed_roles "
                "FROM dbp_workflow_states WHERE workflow_id = :wid "
                "ORDER BY is_initial DESC, code"
            ),
            {"wid": workflow_id},
        ).fetchall()

        transitions = self.db.execute(
            text(
                "SELECT t.id, t.code, t.name_en, t.action, "
                "s1.code as from_code, s2.code as to_code, "
                "t.required_roles, t.conditions "
                "FROM dbp_workflow_transitions t "
                "JOIN dbp_workflow_states s1 ON t.from_state_id = s1.id "
                "JOIN dbp_workflow_states s2 ON t.to_state_id = s2.id "
                "WHERE t.workflow_id = :wid"
            ),
            {"wid": workflow_id},
        ).fetchall()

        return {
            "id": wf[0],
            "code": wf[1],
            "name_en": wf[2],
            "name_ar": wf[3],
            "entity_code": wf[4],
            "is_active": bool(wf[5]),
            "is_published": bool(wf[6]),
            "sla_hours": wf[7],
            "created_at": wf[8].isoformat() if wf[8] else None,
            "states": [
                {
                    "id": s[0], "code": s[1], "name_en": s[2], "name_ar": s[3],
                    "state_type": s[4], "is_initial": bool(s[5]),
                    "is_final": bool(s[6]), "allowed_roles": s[7],
                }
                for s in states
            ],
            "transitions": [
                {
                    "id": t[0], "code": t[1], "name_en": t[2], "action": t[3],
                    "from_state": t[4], "to_state": t[5],
                    "required_roles": t[6], "conditions": t[7],
                }
                for t in transitions
            ],
        }

    # ──────────────────────────────────────────────────────────
    # WORKFLOW INSTANCE
    # ──────────────────────────────────────────────────────────

    def start_instance(
        self,
        workflow_id: str,
        entity_code: str,
        record_id: str,
        initiated_by: str,
        tenant_id: Optional[str] = None,
        priority: int = 0,
    ) -> Optional[str]:
        """Start a new workflow instance for a record."""
        wf = self.db.execute(
            text(
                "SELECT id, entity_code, is_published, sla_hours "
                "FROM dbp_workflow_definitions WHERE id = :id"
            ),
            {"id": workflow_id},
        ).fetchone()

        if not wf or not wf[2]:
            return None

        # Get initial state
        initial = self.db.execute(
            text(
                "SELECT id FROM dbp_workflow_states "
                "WHERE workflow_id = :wid AND is_initial = true"
            ),
            {"wid": workflow_id},
        ).fetchone()

        if not initial:
            return None

        instance_id = str(uuid.uuid4())
        due_at = None
        if wf[3]:
            from datetime import timedelta
            due_at = datetime.now(timezone.utc) + timedelta(hours=wf[3])

        self.db.execute(
            text(
                "INSERT INTO dbp_workflow_instances "
                "(id, tenant_id, workflow_id, entity_code, record_id, "
                "current_state_id, status, initiated_by, priority, due_at) "
                "VALUES (:id, :tid, :wid, :ec, :rid, "
                ":csid, 'active', :ib, :prio, :due)"
            ),
            {
                "id": instance_id, "tid": tenant_id, "wid": workflow_id,
                "ec": entity_code, "rid": record_id,
                "csid": initial[0], "ib": initiated_by,
                "prio": priority, "due": due_at,
            },
        )

        # Log action
        self._log_action(instance_id, None, "created", None, "draft", initiated_by)
        self.db.flush()
        return instance_id

    def execute_transition(
        self,
        instance_id: str,
        action: str,
        performed_by: str,
        comment: Optional[str] = None,
        user_roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a transition on a workflow instance.
        Returns {success, from_state, to_state, error?}
        """
        action = action.lower()
        if action not in self.VALID_ACTIONS:
            return {"success": False, "error": f"Invalid action: {action}"}

        # Get instance
        inst = self.db.execute(
            text(
                "SELECT id, current_state_id, status, workflow_id "
                "FROM dbp_workflow_instances WHERE id = :id"
            ),
            {"id": instance_id},
        ).fetchone()

        if not inst:
            return {"success": False, "error": "Instance not found"}

        if inst[2] != "active":
            return {"success": False, "error": f"Instance is {inst[2]}, not active"}

        current_state_id = inst[1]

        # Find matching transition
        trans = self.db.execute(
            text(
                "SELECT id, to_state_id, required_roles, action as trans_action "
                "FROM dbp_workflow_transitions "
                "WHERE workflow_id = :wid AND from_state_id = :fsid "
                "AND action = :action AND is_active = true"
            ),
            {"wid": inst[3], "fsid": current_state_id, "action": action},
        ).fetchone()

        if not trans:
            return {"success": False, "error": f"No '{action}' transition from current state"}

        trans_id, to_state_id, required_roles, _ = trans

        # Check role authorization
        if required_roles:
            if isinstance(required_roles, str):
                import json
                required_roles = json.loads(required_roles)
            if required_roles and user_roles:
                if not any(r in required_roles for r in user_roles):
                    if "*" not in user_roles:
                        return {"success": False, "error": "Insufficient role for this transition"}

        # Get state names for audit
        from_state = self.db.execute(
            text("SELECT code FROM dbp_workflow_states WHERE id = :id"),
            {"id": current_state_id},
        ).fetchone()

        to_state = self.db.execute(
            text("SELECT code FROM dbp_workflow_states WHERE id = :id"),
            {"id": to_state_id},
        ).fetchone()

        # Update instance
        now = datetime.now(timezone.utc)
        update_fields = "current_state_id = :csid"
        params: Dict[str, Any] = {"csid": to_state_id, "id": instance_id}

        if to_state and to_state[0] in ("approved", "rejected", "cancelled"):
            update_fields += ", status = :status, completed_at = :now"
            params["status"] = "completed" if to_state[0] == "approved" else to_state[0]
            params["now"] = now

        self.db.execute(
            text(f"UPDATE dbp_workflow_instances SET {update_fields} WHERE id = :id"),
            params,
        )

        # Log action
        self._log_action(
            instance_id, trans_id, action,
            from_state[0] if from_state else None,
            to_state[0] if to_state else None,
            performed_by, comment,
        )

        self.db.flush()
        return {
            "success": True,
            "from_state": from_state[0] if from_state else None,
            "to_state": to_state[0] if to_state else None,
            "status": params.get("status", "active"),
        }

    def cancel_instance(self, instance_id: str, performed_by: str) -> Dict[str, Any]:
        """Cancel a workflow instance."""
        inst = self.db.execute(
            text("SELECT status FROM dbp_workflow_instances WHERE id = :id"),
            {"id": instance_id},
        ).fetchone()

        if not inst:
            return {"success": False, "error": "Instance not found"}
        if inst[0] != "active":
            return {"success": False, "error": f"Instance is {inst[0]}"}

        now = datetime.now(timezone.utc)
        self.db.execute(
            text(
                "UPDATE dbp_workflow_instances "
                "SET status = 'cancelled', completed_at = :now "
                "WHERE id = :id"
            ),
            {"id": instance_id, "now": now},
        )

        self._log_action(instance_id, None, "cancelled", None, "cancelled", performed_by)
        self.db.flush()
        return {"success": True, "status": "cancelled"}

    def get_instance(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow instance with history."""
        inst = self.db.execute(
            text(
                "SELECT i.id, i.workflow_id, i.entity_code, i.record_id, "
                "s.code as current_state, s.name_en as current_state_name, "
                "i.status, i.initiated_by, i.priority, i.due_at, "
                "i.completed_at, i.created_at, w.code as wf_code, "
                "w.name_en as wf_name "
                "FROM dbp_workflow_instances i "
                "LEFT JOIN dbp_workflow_states s ON i.current_state_id = s.id "
                "JOIN dbp_workflow_definitions w ON i.workflow_id = w.id "
                "WHERE i.id = :id"
            ),
            {"id": instance_id},
        ).fetchone()

        if not inst:
            return None

        actions = self.db.execute(
            text(
                "SELECT a.action, a.from_state, a.to_state, "
                "a.performed_by, a.comment, a.created_at "
                "FROM dbp_workflow_actions a "
                "WHERE a.instance_id = :iid "
                "ORDER BY a.created_at ASC"
            ),
            {"iid": instance_id},
        ).fetchall()

        return {
            "id": inst[0],
            "workflow_id": inst[1],
            "workflow_code": inst[12],
            "workflow_name": inst[13],
            "entity_code": inst[2],
            "record_id": inst[3],
            "current_state": inst[4],
            "current_state_name": inst[5],
            "status": inst[6],
            "initiated_by": inst[7],
            "priority": inst[8],
            "due_at": inst[9].isoformat() if inst[9] else None,
            "completed_at": inst[10].isoformat() if inst[10] else None,
            "created_at": inst[11].isoformat() if inst[11] else None,
            "history": [
                {
                    "action": a[0], "from_state": a[1], "to_state": a[2],
                    "performed_by": a[3], "comment": a[4],
                    "created_at": a[5].isoformat() if a[5] else None,
                }
                for a in actions
            ],
        }

    def list_instances(
        self,
        workflow_id: Optional[str] = None,
        entity_code: Optional[str] = None,
        status: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List workflow instances with filters."""
        conditions = []
        params: Dict[str, Any] = {"limit": limit, "offset": offset}

        if workflow_id:
            conditions.append("i.workflow_id = :wid")
            params["wid"] = workflow_id
        if entity_code:
            conditions.append("i.entity_code = :ec")
            params["ec"] = entity_code
        if status:
            conditions.append("i.status = :status")
            params["status"] = status
        if tenant_id:
            conditions.append("i.tenant_id = :tid")
            params["tid"] = tenant_id

        where = " AND ".join(conditions) if conditions else "1=1"

        rows = self.db.execute(
            text(
                f"SELECT i.id, i.entity_code, i.record_id, "
                f"s.code as current_state, i.status, i.initiated_by, "
                f"i.priority, i.due_at, i.created_at, w.code as wf_code "
                f"FROM dbp_workflow_instances i "
                f"LEFT JOIN dbp_workflow_states s ON i.current_state_id = s.id "
                f"JOIN dbp_workflow_definitions w ON i.workflow_id = w.id "
                f"WHERE {where} "
                f"ORDER BY i.created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        ).fetchall()

        return [
            {
                "id": r[0], "entity_code": r[1], "record_id": r[2],
                "current_state": r[3], "status": r[4], "initiated_by": r[5],
                "priority": r[6], "due_at": r[7].isoformat() if r[7] else None,
                "created_at": r[8].isoformat() if r[8] else None,
                "workflow_code": r[9],
            }
            for r in rows
        ]

    def _log_action(
        self,
        instance_id: str,
        transition_id: Optional[str],
        action: str,
        from_state: Optional[str],
        to_state: Optional[str],
        performed_by: str,
        comment: Optional[str] = None,
    ):
        """Log a workflow action (audit trail)."""
        self.db.execute(
            text(
                "INSERT INTO dbp_workflow_actions "
                "(id, instance_id, transition_id, action, from_state, "
                "to_state, performed_by, comment) "
                "VALUES (:id, :iid, :tid, :action, :fs, :ts, :pb, :comment)"
            ),
            {
                "id": str(uuid.uuid4()),
                "iid": instance_id,
                "tid": transition_id,
                "action": action,
                "fs": from_state,
                "ts": to_state,
                "pb": performed_by,
                "comment": comment,
            },
        )


def json_dumps(obj):
    import json
    if obj is None:
        return "[]"
    return json.dumps(obj)
