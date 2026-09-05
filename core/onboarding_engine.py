"""
P52 Onboarding Engine — Productization & SaaS Launch
Handles end-to-end tenant onboarding: industry selection → plan → company → template → modules → admin → activation
"""
import uuid, json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

ONBOARDING_STEPS = [
    "industry_selection",
    "plan_selection",
    "company_creation",
    "template_application",
    "module_configuration",
    "admin_setup",
    "activation",
]


class OnboardingEngine:
    def __init__(self, db: Session):
        self.db = db

    def list_industry_templates(self, is_active: bool = True) -> List[Dict]:
        conditions = []
        params: Dict[str, Any] = {}
        if is_active is not None:
            conditions.append("is_active = :active")
            params["active"] = is_active
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self.db.execute(text(
            f"SELECT id, industry_code, industry_name, industry_name_ar, description, "
            f"default_modules, default_settings, default_accounts, is_active, sort_order "
            f"FROM dbp_industry_templates {where} ORDER BY sort_order, industry_name"
        ), params).fetchall()
        return [{"id": r[0], "industry_code": r[1], "industry_name": r[2],
                 "industry_name_ar": r[3], "description": r[4],
                 "default_modules": self._parse_json(r[5]),
                 "default_settings": self._parse_json(r[6]),
                 "default_accounts": self._parse_json(r[7]),
                 "is_active": r[8], "sort_order": r[9]} for r in rows]

    def get_industry_template(self, template_id: str) -> Optional[Dict]:
        row = self.db.execute(text(
            "SELECT id, industry_code, industry_name, industry_name_ar, description, "
            "default_modules, default_settings, default_accounts "
            "FROM dbp_industry_templates WHERE id = :id"
        ), {"id": template_id}).fetchone()
        if not row:
            return None
        return {"id": row[0], "industry_code": row[1], "industry_name": row[2],
                "industry_name_ar": row[3], "description": row[4],
                "default_modules": self._parse_json(row[5]),
                "default_settings": self._parse_json(row[6]),
                "default_accounts": self._parse_json(row[7])}

    def list_module_definitions(self, category: Optional[str] = None,
                                is_active: bool = True) -> List[Dict]:
        conditions = ["is_active = :active"]
        params: Dict[str, Any] = {"active": is_active}
        if category:
            conditions.append("category = :cat")
            params["cat"] = category
        where = f"WHERE {' AND '.join(conditions)}"
        rows = self.db.execute(text(
            f"SELECT id, module_code, module_name, module_name_ar, description, category, "
            f"required_modules, optional_dependencies, default_enabled, sort_order "
            f"FROM dbp_module_definitions {where} ORDER BY sort_order"
        ), params).fetchall()
        return [{"id": r[0], "module_code": r[1], "module_name": r[2],
                 "module_name_ar": r[3], "description": r[4], "category": r[5],
                 "required_modules": self._parse_json(r[6]),
                 "optional_dependencies": self._parse_json(r[7]),
                 "default_enabled": r[8], "sort_order": r[9]} for r in rows]

    def get_module_definition(self, module_id: str) -> Optional[Dict]:
        row = self.db.execute(text(
            "SELECT id, module_code, module_name, module_name_ar, description, category, "
            "required_modules, optional_dependencies, default_enabled "
            "FROM dbp_module_definitions WHERE id = :id"
        ), {"id": module_id}).fetchone()
        if not row:
            return None
        return {"id": row[0], "module_code": row[1], "module_name": row[2],
                "module_name_ar": row[3], "description": row[4], "category": row[5],
                "required_modules": self._parse_json(row[6]),
                "optional_dependencies": self._parse_json(row[7]),
                "default_enabled": row[8]}

    def create_onboarding(self, tenant_id: str, admin_user_id: str = None,
                          admin_email: str = None) -> str:
        existing = self.get_onboarding(tenant_id)
        if existing:
            if existing["status"] == "completed":
                raise ValueError("Onboarding already completed")
            return existing["id"]
        oid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_tenant_onboarding "
            "(id, tenant_id, current_step, status, admin_user_id, admin_email, "
            "selected_modules, configuration, steps_completed, steps_data) "
            "VALUES (:id, :tid, :step, :st, :auid, :aemail, :mods, :config, :done, :data)"
        ), {
            "id": oid, "tid": tenant_id,
            "step": "industry_selection", "st": "in_progress",
            "auid": admin_user_id, "aemail": admin_email,
            "mods": json.dumps([]), "config": json.dumps({}),
            "done": json.dumps([]), "data": json.dumps({}),
        })
        self.db.flush()
        return oid

    def get_onboarding(self, tenant_id: str) -> Optional[Dict]:
        row = self.db.execute(text(
            "SELECT id, tenant_id, company_id, industry_code, plan_id, current_step, "
            "status, company_name, company_name_ar, admin_user_id, admin_email, "
            "selected_modules, configuration, steps_completed, steps_data, "
            "activated_at, created_at, updated_at "
            "FROM dbp_tenant_onboarding WHERE tenant_id = :tid "
            "ORDER BY created_at DESC LIMIT 1"
        ), {"tid": tenant_id}).fetchone()
        return self._row_to_dict(row) if row else None

    def list_onboardings(self, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        conditions = []
        params: Dict[str, Any] = {"lim": min(max(limit, 1), 100)}
        if status:
            conditions.append("status = :st")
            params["st"] = status
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self.db.execute(text(
            f"SELECT id, tenant_id, company_id, industry_code, plan_id, current_step, "
            f"status, company_name, activated_at, created_at "
            f"FROM dbp_tenant_onboarding {where} ORDER BY created_at DESC LIMIT :lim"
        ), params).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "company_id": r[2],
                 "industry_code": r[3], "plan_id": r[4], "current_step": r[5],
                 "status": r[6], "company_name": r[7],
                 "activated_at": str(r[8]) if r[8] else None,
                 "created_at": str(r[9]) if r[9] else None} for r in rows]

    def update_onboarding_step(self, tenant_id: str, step: str, data: Dict = None) -> bool:
        ob = self.get_onboarding(tenant_id)
        if not ob:
            return False
        if step not in ONBOARDING_STEPS:
            return False
        expected = ob.get("current_step")
        if expected != step:
            return False
        data = data or {}
        if step == "industry_selection":
            code = data.get("industry_code")
            if not code or not self._industry_exists(code):
                return False
        if step == "plan_selection" and data.get("plan_id") not in {"trial", "professional", "enterprise"}:
            return False
        if step == "company_creation" and not str(data.get("company_name") or "").strip():
            return False
        if step == "module_configuration":
            modules = data.get("modules")
            if not isinstance(modules, list) or not modules:
                return False
            valid = {m["module_code"] for m in self.list_module_definitions()}
            if any(m not in valid for m in modules):
                return False
        if step == "activation" and len(ob.get("steps_completed", [])) != len(ONBOARDING_STEPS) - 1:
            return False

        steps_completed = list(ob.get("steps_completed", []))
        if step not in steps_completed:
            steps_completed.append(step)
        steps_data = dict(ob.get("steps_data", {}))
        steps_data[step] = data
        step_idx = ONBOARDING_STEPS.index(step)
        next_idx = step_idx + 1
        next_step = ONBOARDING_STEPS[next_idx] if next_idx < len(ONBOARDING_STEPS) else step
        new_status = "completed" if next_idx >= len(ONBOARDING_STEPS) else "in_progress"

        updates: Dict[str, Any] = {"current_step": next_step, "status": new_status}
        if step == "industry_selection": updates["industry_code"] = data["industry_code"]
        if step == "plan_selection": updates["plan_id"] = data["plan_id"]
        if step == "company_creation":
            updates["company_name"] = str(data["company_name"]).strip()
            updates["company_name_ar"] = str(data.get("company_name_ar") or "").strip() or None
            if data.get("company_id"): updates["company_id"] = data["company_id"]
        if step == "module_configuration": updates["selected_modules"] = json.dumps(data["modules"])
        if step == "activation": updates["activated_at"] = datetime.now(timezone.utc).isoformat()

        set_clauses = []
        params: Dict[str, Any] = {"tid": tenant_id, "expected": step}
        for key, value in updates.items():
            set_clauses.append(f"{key} = :{key}")
            params[key] = value
        set_clauses += ["steps_completed = :done", "steps_data = :sdata", "updated_at = NOW()"]
        params["done"] = json.dumps(steps_completed)
        params["sdata"] = json.dumps(steps_data)
        result = self.db.execute(text(
            f"UPDATE dbp_tenant_onboarding SET {', '.join(set_clauses)} "
            f"WHERE tenant_id = :tid AND current_step = :expected"
        ), params)
        self.db.flush()
        return result.rowcount == 1

    def complete_step(self, tenant_id: str, step: str, data: Dict = None) -> Dict[str, Any]:
        if step not in ONBOARDING_STEPS:
            return {"success": False, "error": f"Invalid step: {step}"}
        ob = self.get_onboarding(tenant_id)
        if not ob:
            return {"success": False, "error": "No onboarding found for this tenant"}
        if ob["status"] == "completed":
            return {"success": False, "error": "Onboarding already completed"}
        if ob.get("current_step") != step:
            return {"success": False, "error": f"Expected step: {ob.get('current_step')}"}
        if not self.update_onboarding_step(tenant_id, step, data):
            return {"success": False, "error": "Step validation failed or onboarding changed concurrently"}
        updated = self.get_onboarding(tenant_id)
        return {"success": True, "current_step": updated["current_step"],
                "status": updated["status"], "steps_completed": updated["steps_completed"]}

    def get_onboarding_status(self, tenant_id: str) -> Dict[str, Any]:
        ob = self.get_onboarding(tenant_id)
        if not ob:
            return {"onboarded": False, "status": "not_started"}
        total = len(ONBOARDING_STEPS)
        done = len(ob.get("steps_completed", []))
        return {"onboarded": ob["status"] == "completed", "status": ob["status"],
                "current_step": ob["current_step"], "progress_percent": round(done / total * 100),
                "steps_completed": ob["steps_completed"],
                "steps_remaining": [s for s in ONBOARDING_STEPS if s not in ob.get("steps_completed", [])],
                "industry_code": ob.get("industry_code"), "plan_id": ob.get("plan_id"),
                "company_name": ob.get("company_name"), "company_id": ob.get("company_id"),
                "selected_modules": ob.get("selected_modules", []), "activated_at": ob.get("activated_at")}

    def get_industry_accounts(self, industry_code: str) -> List[Dict]:
        row = self.db.execute(text("SELECT default_accounts FROM dbp_industry_templates WHERE industry_code = :code"), {"code": industry_code}).fetchone()
        return self._parse_json(row[0]) if row else []

    def get_industry_modules(self, industry_code: str) -> List[str]:
        row = self.db.execute(text("SELECT default_modules FROM dbp_industry_templates WHERE industry_code = :code"), {"code": industry_code}).fetchone()
        return self._parse_json(row[0]) if row else []

    def get_industry_settings(self, industry_code: str) -> Dict:
        row = self.db.execute(text("SELECT default_settings FROM dbp_industry_templates WHERE industry_code = :code"), {"code": industry_code}).fetchone()
        return self._parse_json(row[0]) if row else {}

    def _industry_exists(self, code: str) -> bool:
        return self.db.execute(text("SELECT 1 FROM dbp_industry_templates WHERE industry_code = :code AND is_active = TRUE LIMIT 1"), {"code": code}).first() is not None

    def _parse_json(self, val):
        if val is None: return {}
        if isinstance(val, (dict, list)): return val
        try: return json.loads(val)
        except Exception: return val

    def _row_to_dict(self, row) -> Dict:
        return {"id": row[0], "tenant_id": row[1], "company_id": row[2], "industry_code": row[3],
                "plan_id": row[4], "current_step": row[5], "status": row[6], "company_name": row[7],
                "company_name_ar": row[8], "admin_user_id": row[9], "admin_email": row[10],
                "selected_modules": self._parse_json(row[11]), "configuration": self._parse_json(row[12]),
                "steps_completed": self._parse_json(row[13]), "steps_data": self._parse_json(row[14]),
                "activated_at": str(row[15]) if row[15] else None, "created_at": str(row[16]) if row[16] else None,
                "updated_at": str(row[17]) if row[17] else None}
