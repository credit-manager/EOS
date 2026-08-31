"""
P56 Billing Flow Engine
Plan → Checkout (subscription + pending invoice) → Payment → License → Limits.
Orchestrates existing P41 (plans) and P43 (subscription_engine) primitives.
"""
import time, uuid, json, secrets
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.subscription_engine import SubscriptionEngine


class BillingFlowEngine:
    def __init__(self, db: Session):
        self.db = db
        self.sub = SubscriptionEngine(db)

    # ── CATALOG ──

    def get_plan_catalog(self) -> List[Dict]:
        rows = self.db.execute(text(
            "SELECT id, plan_name, plan_code, price_monthly, price_yearly, "
            "max_users, max_companies, max_storage_gb, features "
            "FROM dbp_saas_plans WHERE is_active = true "
            "AND tenant_id = 'platform' ORDER BY price_monthly"
        )).fetchall()
        return [{"plan_id": r[0], "plan_name": r[1], "plan_code": r[2],
                 "price_monthly": float(r[3]), "price_yearly": float(r[4]),
                 "max_users": r[5], "max_companies": r[6], "max_storage_gb": r[7],
                 "features": self._pj(r[8])} for r in rows]

    def get_plan(self, plan_code: str) -> Optional[Dict]:
        for p in self.get_plan_catalog():
            if p["plan_code"] == plan_code:
                return p
        return None

    # ── CHECKOUT ──

    def checkout(self, tenant_id: str, plan_code: str,
                 billing_cycle: str = "monthly") -> Dict[str, Any]:
        plan = self.get_plan(plan_code)
        if not plan:
            return {"success": False, "error": f"Plan '{plan_code}' not found"}
        if billing_cycle not in ("monthly", "yearly"):
            return {"success": False, "error": "billing_cycle must be monthly|yearly"}

        current = self.sub.get_subscription(tenant_id)
        if current and current.get("status") == "active":
            current_plan = self._plan_name_by_id(current.get("plan_id"))
            return {"success": False,
                    "error": f"Active subscription exists ({current_plan}). Use change-plan."}

        sub_id = self.sub.create_subscription(tenant_id, plan["plan_id"], billing_cycle)
        amount = plan["price_monthly"] if billing_cycle == "monthly" else plan["price_yearly"]
        inv_num = f"SAAS-{tenant_id[:12]}-{int(time.time())}"
        inv = self.sub.create_invoice(tenant_id, sub_id, inv_num, amount,
                                       currency="SAR",
                                       line_items=[{"item": plan["plan_name"],
                                                     "cycle": billing_cycle,
                                                     "amount": amount}])
        invoice_id = inv["id"] if isinstance(inv, dict) and "id" in inv else str(inv)
        self.db.commit()
        return {"success": True, "subscription_id": sub_id,
                "invoice_id": invoice_id, "invoice_number": inv_num,
                "amount_due": amount, "currency": "SAR",
                "status": "awaiting_payment"}

    # ── PAY ──

    def pay_invoice(self, tenant_id: str, invoice_id: str,
                    payment_method: str = "card") -> Dict[str, Any]:
        inv = self.sub.get_invoice(tenant_id, invoice_id)
        if not inv:
            return {"success": False, "error": "Invoice not found"}
        status = inv.get("status")
        if status == "paid":
            return {"success": False, "error": "Invoice already paid"}

        payment = self.sub.create_payment(tenant_id, invoice_id,
                                           float(inv.get("amount") or 0),
                                           currency=inv.get("currency") or "SAR",
                                           payment_method=payment_method,
                                           transaction_id=f"TXN-{secrets.token_hex(6)}")
        self.sub.update_invoice_status(tenant_id, invoice_id, "paid")

        sub = self.sub.get_subscription(tenant_id)
        plan = self._plan_by_id(sub.get("plan_id")) if sub else None
        lic_key = f"LIC-{''.join(secrets.token_hex(4).upper().split())}"
        license_row = None
        try:
            license_row = self.sub.create_license(
                tenant_id, lic_key,
                license_type=plan["plan_code"] if plan else "standard",
                max_seats=plan["max_users"] if plan else 5,
                features=plan["features"] if plan else [])
        except TypeError:
            license_row = self.sub.create_license(
                tenant_id, lic_key, license_type=plan["plan_code"] if plan else "standard")

        self._apply_tenant_limits(tenant_id, plan)
        self.db.commit()
        payment_id = payment["id"] if isinstance(payment, dict) and "id" in payment else str(payment)
        return {"success": True, "invoice_status": "paid", "payment_id": payment_id,
                "license_key": lic_key, "license_active": bool(license_row),
                "plan": plan["plan_code"] if plan else None}

    # ── STATUS ──

    def my_subscription(self, tenant_id: str) -> Optional[Dict]:
        sub = self.sub.get_subscription(tenant_id)
        if not sub:
            return None
        plan = self._plan_by_id(sub.get("plan_id"))
        licenses = self.sub.list_licenses(tenant_id)
        active_lic = next((l for l in licenses if l.get("status") == "active"), None)
        invoices = self.sub.list_invoices(tenant_id, limit=5)
        return {
            "subscription": sub,
            "plan": plan,
            "license": {"key": active_lic.get("license_key"),
                         "seats": active_lic.get("max_seats")} if active_lic else None,
            "recent_invoices": invoices,
        }

    def change_plan(self, tenant_id: str, new_plan_code: str,
                    billing_cycle: str = "monthly") -> Dict[str, Any]:
        current = self.sub.get_subscription(tenant_id)
        if not current or current.get("status") != "active":
            return {"success": False, "error": "No active subscription to change"}
        old_plan = self._plan_by_id(current.get("plan_id"))
        if old_plan and old_plan["plan_code"] == new_plan_code:
            return {"success": False, "error": "Already on this plan"}
        self.sub.cancel_subscription(tenant_id)
        result = self.checkout(tenant_id, new_plan_code, billing_cycle)
        if result.get("success"):
            result["changed_from"] = old_plan["plan_code"] if old_plan else None
        return result

    # ── USAGE ──

    def record_usage(self, tenant_id: str, meter_name: str, meter_value: float) -> Dict:
        row = self.sub.record_usage(tenant_id, meter_name, meter_value)
        self.db.commit()
        return {"success": True}

    def usage_summary(self, tenant_id: str) -> Dict[str, Any]:
        meters = {}
        for u in self.sub.get_usage(tenant_id, limit=500):
            name = u.get("meter_name")
            val = float(u.get("meter_value") or 0)
            meters[name] = max(meters.get(name, 0), val)
        sub = self.sub.get_subscription(tenant_id)
        plan = self._plan_by_id(sub.get("plan_id")) if sub else None
        limits = {"users": plan["max_users"], "storage_gb": plan["max_storage_gb"],
                   "companies": plan["max_companies"]} if plan else {}
        over = []
        if plan:
            if meters.get("active_users", 0) > plan["max_users"]:
                over.append("users")
            if meters.get("storage_gb", 0) > plan["max_storage_gb"]:
                over.append("storage_gb")
        return {"meters": meters, "limits": limits, "over_limit": over}

    # ── INTERNALS ──

    def _apply_tenant_limits(self, tenant_id: str, plan: Optional[Dict]):
        if not plan:
            return
        try:
            from core.saas_cp_engine import SaaSCPEngine
            SaaSCPEngine(self.db).update_tenant(
                tenant_id, plan_id=plan["plan_id"],
                max_users=plan["max_users"], max_companies=plan["max_companies"])
        except Exception:
            pass

    def _plan_by_id(self, plan_id: str) -> Optional[Dict]:
        if not plan_id:
            return None
        row = self.db.execute(text(
            "SELECT id, plan_name, plan_code, price_monthly, max_users, features, "
            "max_companies, max_storage_gb "
            "FROM dbp_saas_plans WHERE id = :pid"
        ), {"pid": plan_id}).fetchone()
        if not row:
            return None
        return {"plan_id": row[0], "plan_name": row[1], "plan_code": row[2],
                "price_monthly": float(row[3]), "max_users": row[4],
                "features": self._pj(row[5]),
                "max_companies": row[6], "max_storage_gb": row[7]}

    def _plan_name_by_id(self, plan_id: str) -> Optional[str]:
        p = self._plan_by_id(plan_id)
        return p["plan_code"] if p else None

    def _pj(self, v):
        if v is None:
            return []
        if isinstance(v, (dict, list)):
            return v
        try:
            return json.loads(v)
        except Exception:
            return []
