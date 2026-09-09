"""
P58 SaaS Journey Engine — orchestrated end-to-end product flow:
Arabic description → AI config → customize → choose plan → pay → launch ERP.
Composes P53 (AIComposerEngine) + P54 (BuilderEngine) + P56 (BillingFlowEngine)
in-process. No production change before the explicit launch approval gate.
"""
import uuid, json
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.ai_composer import AIComposerEngine
from core.builder_engine import BuilderEngine
from core.billing_flow import BillingFlowEngine

JOURNEY_STEPS = ["drafted", "customized", "plan_selected", "paid", "erp_ready"]


class SaaSJourneyEngine:
    def __init__(self, db: Session):
        self.db = db
        self.composer = AIComposerEngine(db)
        self.builder = BuilderEngine(db)
        self.billing = BillingFlowEngine(db)

    # ── STEP 1: START (AI understanding) ──

    def start_journey(self, tenant_id: str, user_id: str,
                      business_description: str,
                      company_name: Optional[str] = None,
                      admin_email: Optional[str] = None) -> Dict[str, Any]:
        if not business_description or len(business_description.strip()) < 5:
            return {"success": False, "error": "business_description required"}

        session = self.composer.create_session(tenant_id, user_id, business_description)
        proj = self.builder.create_project(
            tenant_id,
            company_name or f"ERP for {session['requirements']['industry']}",
            composer_session_id=session["session_id"],
            initial_config=session["config"])
        if not proj.get("success"):
            return {"success": False, "error": proj["error"]}

        jid = str(uuid.uuid4())
        v = session["validation"]
        compose_summary = {
            "enabled_modules": len(session["config"]["modules"]),
            "entities": v.get("entities_count", 0),
            "relationships": v.get("relationships_count", 0),
            "workflows": v.get("workflows_count", 0),
            "roles": v.get("roles_count", 0),
            "kpis": v.get("kpis_count", 0),
        }
        self.db.execute(text(
            "INSERT INTO dbp_saas_journeys "
            "(id, tenant_id, user_id, company_name, admin_email, business_description, "
            "detected_industry, composer_session_id, project_id, status, steps_data) "
            "VALUES (:id, :t, :u, :cn, :ae, :bd, :ind, :sid, :pid, 'drafted', :sd)"
        ), {"id": jid, "t": tenant_id, "u": user_id,
            "cn": company_name, "ae": admin_email,
            "bd": business_description,
            "ind": session["requirements"]["industry"],
            "sid": session["session_id"], "pid": proj["project_id"],
            "sd": json.dumps({"compose_summary": compose_summary})})
        self.db.flush()

        return {"success": True, "journey_id": jid,
                "status": "drafted",
                "detected_industry": session["requirements"]["industry"],
                "detected_language": session["requirements"]["language"],
                "modules": [m["code"] for m in proj["draft_config"]["modules"]],
                "summary": compose_summary,
                "next_actions": ["customize", "add_entities", "select_plan"]}

    # ── STEP 2: CUSTOMIZE ──

    def customize(self, tenant_id: str, jid: str, body: Dict) -> Dict[str, Any]:
        j = self._get(tenant_id, jid)
        if not j:
            return {"success": False, "error": "Journey not found"}
        if j["status"] in ("paid", "erp_ready"):
            return {"success": False, "error": "Cannot customize after payment"}

        if body.get("settings"):
            self.builder.update_settings(tenant_id, j["project_id"], body["settings"])
        if isinstance(body.get("enable_modules"), list):
            mods = [{"code": c, "enabled": True} for c in body["enable_modules"]]
            r = self.builder.set_modules(tenant_id, j["project_id"], mods)
            if not r.get("success"):
                return {"success": False, "error": r["error"]}
        if isinstance(body.get("disable_modules"), list):
            mods = [{"code": c, "enabled": False} for c in body["disable_modules"]]
            r = self.builder.set_modules(tenant_id, j["project_id"], mods)
            if not r.get("success"):
                return {"success": False, "error": r["error"]}
        for ent in body.get("add_entities", []) or []:
            r = self.builder.add_entity(tenant_id, j["project_id"], ent)
            if not r.get("success"):
                return {"success": False, "error": f"entity {ent.get('entity_code')}: {r['error']}"}
        for wf in body.get("add_workflows", []) or []:
            self.builder.add_workflow(tenant_id, j["project_id"], wf)

        self._advance(tenant_id, jid, "customized",
                      {"customize": {k: v for k, v in body.items()}})
        return {"success": True, "status": "customized"}

    def preview(self, tenant_id: str, jid: str) -> Optional[Dict]:
        j = self._get(tenant_id, jid)
        if not j:
            return None
        p = self.builder.preview(tenant_id, j["project_id"])
        if not p:
            return None
        return {"journey_id": jid, "status": j["status"],
                "industry": j["detected_industry"],
                "validation": p["validation"],
                "config_summary": {
                    "settings": p["config"].get("settings"),
                    "modules_enabled": [m["code"] for m in p["config"].get("modules", [])
                                         if m.get("enabled")],
                    "custom_entities": [e["entity_code"]
                                         for e in p["config"].get("custom_entities", [])]}}

    # ── STEP 3: CHOOSE PLAN ──

    def select_plan(self, tenant_id: str, jid: str, plan_code: str,
                    billing_cycle: str = "monthly") -> Dict[str, Any]:
        j = self._get(tenant_id, jid)
        if not j:
            return {"success": False, "error": "Journey not found"}
        if j["status"] not in ("drafted", "customized", "plan_selected"):
            return {"success": False, "error": f"Cannot select plan at '{j['status']}'"}
        co = self.billing.checkout(tenant_id, plan_code, billing_cycle)
        if not co.get("success"):
            return {"success": False, "error": co["error"]}
        self.db.execute(text(
            "UPDATE dbp_saas_journeys SET plan_code=:pc, billing_cycle=:bc, "
            "invoice_id=:iid, status='plan_selected', updated_at=NOW() WHERE id=:id"
        ), {"pc": plan_code, "bc": billing_cycle, "iid": co["invoice_id"], "id": jid})
        self.db.commit()
        return {"success": True, "status": "plan_selected",
                "amount_due": co["amount_due"], "currency": co["currency"],
                "invoice_id": co["invoice_id"],
                "next_actions": ["pay"]}

    # ── STEP 4: PAY ──

    def pay(self, tenant_id: str, jid: str,
            payment_method: str = "card") -> Dict[str, Any]:
        j = self._get(tenant_id, jid)
        if not j:
            return {"success": False, "error": "Journey not found"}
        if j["status"] != "plan_selected":
            return {"success": False, "error": f"Cannot pay at '{j['status']}' — select a plan first"}
        if not j["invoice_id"]:
            return {"success": False, "error": "No pending invoice"}
        pay = self.billing.pay_invoice(tenant_id, j["invoice_id"], payment_method)
        if not pay.get("success"):
            return {"success": False, "error": pay["error"]}
        self.db.execute(text(
            "UPDATE dbp_saas_journeys SET license_key=:lk, status='paid', "
            "updated_at=NOW() WHERE id=:id"
        ), {"lk": pay["license_key"], "id": jid})
        self.db.commit()
        return {"success": True, "status": "paid",
                "license_key": pay["license_key"], "plan": pay["plan"],
                "next_actions": ["launch (requires confirmed=true)"]}

    # ── STEP 5: LAUNCH (Approval Gate) ──

    def launch(self, tenant_id: str, jid: str, confirmed: bool) -> Dict[str, Any]:
        j = self._get(tenant_id, jid)
        if not j:
            return {"success": False, "error": "Journey not found"}
        if j["status"] != "paid":
            return {"success": False,
                    "error": f"Cannot launch at '{j['status']}' — payment required first"}
        pub = self.builder.publish(
            tenant_id, j["project_id"], published_by=j.get("user_id") or "journey",
            confirmed=confirmed, change_summary=f"SaaS journey launch ({j['detected_industry']})")
        if not pub.get("success"):
            code = "VALIDATION_FAILED" if pub.get("validation") else "LAUNCH_FAILED"
            return {"success": False, "code": code, "error": pub["error"],
                     "validation": pub.get("validation")}
        self.db.execute(text(
            "UPDATE dbp_saas_journeys SET status='erp_ready', updated_at=NOW() WHERE id=:id"
        ), {"id": jid})
        self.db.commit()
        return {"success": True, "status": "erp_ready",
                "version_number": pub["version_number"],
                "entities_published": pub["entities_published"],
                "license_key": j["license_key"]}

    # ── QUERIES ──

    def get_journey(self, tenant_id: str, jid: str) -> Optional[Dict]:
        j = self._get(tenant_id, jid)
        if not j:
            return None
        step_idx = JOURNEY_STEPS.index(j["status"]) if j["status"] in JOURNEY_STEPS else -1
        j["progress_percent"] = round((step_idx + 1) / len(JOURNEY_STEPS) * 100)
        j["steps_remaining"] = JOURNEY_STEPS[step_idx + 1:]
        return j

    def list_journeys(self, tenant_id: str) -> List[Dict]:
        rows = self.db.execute(text(
            "SELECT id, company_name, detected_industry, status, plan_code, created_at "
            "FROM dbp_saas_journeys WHERE tenant_id = :t ORDER BY created_at DESC"),
            {"t": tenant_id}).fetchall()
        return [{"id": r[0], "company_name": r[1], "industry": r[2],
                 "status": r[3], "plan_code": r[4],
                 "created_at": str(r[5]) if r[5] else None} for r in rows]

    # ── INTERNALS ──

    def _get(self, tenant_id: str, jid: str) -> Optional[Dict]:
        row = self.db.execute(text(
            "SELECT id, tenant_id, user_id, company_name, admin_email, business_description, "
            "detected_industry, composer_session_id, project_id, plan_code, billing_cycle, "
            "invoice_id, license_key, status, steps_data, created_at, updated_at "
            "FROM dbp_saas_journeys WHERE id = :id AND tenant_id = :t"),
            {"id": jid, "t": tenant_id}).fetchone()
        if not row:
            return None
        sd = row[14] if isinstance(row[14], dict) else json.loads(row[14] or "{}")
        return {"id": row[0], "tenant_id": row[1], "user_id": row[2],
                "company_name": row[3], "admin_email": row[4],
                "business_description": row[5], "detected_industry": row[6],
                "composer_session_id": row[7], "project_id": row[8],
                "plan_code": row[9], "billing_cycle": row[10],
                "invoice_id": row[11], "license_key": row[12], "status": row[13],
                "steps_data": sd,
                "created_at": str(row[15]) if row[15] else None,
                "updated_at": str(row[16]) if row[16] else None}

    def _advance(self, tenant_id: str, jid: str, status: str, extra: Dict):
        self.db.execute(text(
            "UPDATE dbp_saas_journeys SET status=:st, updated_at=NOW() WHERE id=:id AND tenant_id=:t"),
            {"st": status, "id": jid, "t": tenant_id})
        self.db.commit()
