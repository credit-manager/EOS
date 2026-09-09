"""
P55 — Marketplace Engine
Browse and install industry packs, modules, add-ons.
General platform capability, zero company-specific code.
"""
import uuid, json
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from enum import Enum

from core.builder_engine import BuilderEngine


class ItemType(str, Enum):
    INDUSTRY_PACK = "industry_pack"
    MODULE = "module"
    ADDON = "addon"
    DASHBOARD = "dashboard"
    REPORT = "report"
    WORKFLOW = "workflow"


class MarketplaceEngine:
    def __init__(self, db: Session):
        self.db = db

    # ── BROWSE ──

    def list_items(self, item_type: Optional[str] = None,
                   is_featured: Optional[bool] = None,
                   is_free: Optional[bool] = None,
                   limit: int = 50) -> List[Dict]:
        conditions, params = [], {}
        params["lim"] = limit
        if item_type:
            conditions.append("item_type = :type")
            params["type"] = item_type
        if is_featured is not None:
            conditions.append("is_featured = :feat")
            params["feat"] = is_featured
        if is_free is not None:
            conditions.append("is_free = :free")
            params["free"] = is_free
        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        rows = self.db.execute(text(
            f"SELECT id, item_code, item_type, name_en, name_ar, description, "
            f"publisher, version, price_monthly, is_featured, is_free, payload "
            f"FROM dbp_marketplace_items {where} ORDER BY sort_order, created_at DESC "
            f"LIMIT :lim"
        ), params).fetchall()
        return [{"id": r[0], "item_code": r[1], "type": r[2], "name_en": r[3],
                 "name_ar": r[4], "description": r[5], "publisher": r[6],
                 "version": r[7], "price_monthly": float(r[8]) if r[8] else 0,
                 "price_yearly": 0, "is_featured": r[9], "is_free": r[10],
                 "payload": r[11] if r[11] else {}} for r in rows]

    def get_item(self, item_code: str) -> Optional[Dict]:
        row = self.db.execute(text(
            "SELECT id, item_code, item_type, name_en, name_ar, description, publisher, "
            "version, price_monthly, is_featured, is_free, payload FROM dbp_marketplace_items "
            "WHERE item_code = :code AND is_published = true"
        ), {"code": item_code}).fetchone()
        if not row:
            return None
        return {"id": row[0], "item_code": row[1], "type": row[2], "name_en": row[3],
                "name_ar": row[4], "description": row[5], "publisher": row[6],
                "version": row[7], "price_monthly": float(row[8]) if row[8] else 0,
                "is_featured": row[9], "is_free": row[10],
                "payload": row[11] if row[11] else {}}

    # ── INSTALL ──

    def install_item(self, tenant_id: str, item_code: str,
                     installed_by: str) -> Dict[str, Any]:
        all_items = self.list_items()
        item = next((i for i in all_items if i["item_code"] == item_code), None)
        if not item:
            return {"success": False, "error": f"Item '{item_code}' not found"}

        existing = self.db.execute(text(
            "SELECT id FROM dbp_tenant_installations WHERE tenant_id=:tid AND item_code=:code"
        ), {"tid": tenant_id, "code": item_code}).fetchone()
        if existing:
            return {"success": False, "error": "Item already installed"}

        payload = item.get("payload", {})
        isid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_tenant_installations (id, tenant_id, item_code, "
            "status, applied_payload, installed_by, installed_at) "
            "VALUES (:id, :tid, :code, 'pending', :payload, :by, NOW())"
        ), {"id": isid, "tid": tenant_id, "code": item_code,
            "payload": json.dumps(payload), "by": installed_by})
        self.db.flush()

        return {"success": True, "installation_id": isid, "payload": payload}

    def apply_installation(self, tenant_id: str, installation_id: str,
                           draft_pid: str) -> Dict[str, Any]:
        inst_row = self.db.execute(text(
            "SELECT id, item_code, applied_payload FROM dbp_tenant_installations "
            "WHERE id = :iid AND tenant_id = :tid AND status = 'pending'"
        ), {"iid": installation_id, "tid": tenant_id}).fetchone()
        if not inst_row:
            return {"success": False, "error": "Installation not found or already applied"}

        item_code = inst_row[1]
        payload = inst_row[2] if isinstance(inst_row[2], dict) else json.loads(inst_row[2] or "{}")

        if not draft_pid:
            return {"success": False, "error": "Builder project required"}

        be = BuilderEngine(self.db)
        proj = be.get_project(tenant_id, draft_pid)
        if not proj:
            return {"success": False, "error": "Project not found"}

        self._apply_payload(tenant_id, proj, item_code, payload)

        self.db.execute(text(
            "UPDATE dbp_tenant_installations SET status='installed', applied_payload=:p "
            "WHERE id = :iid"
        ), {"iid": installation_id, "p": json.dumps(payload)})
        self.db.flush()

        return {"success": True, "item_code": item_code,
                "modules_added": len(payload.get("modules", []))}

    def _apply_payload(self, tenant_id: str, draft: Dict, item_code: str, payload: Dict):
        cfg = draft.get("draft_config", {}) if isinstance(draft, dict) else {}
        if isinstance(cfg, str):
            cfg = json.loads(cfg)

        mods = set()
        for m in cfg.get("modules", []):
            if isinstance(m, dict):
                mods.add(m.get("code", ""))
            else:
                mods.add(str(m))
        for m in payload.get("modules", []):
            mods.add(str(m))
        cfg["modules"] = [{"code": m, "enabled": True} for m in sorted(mods) if m]

        entities = cfg.get("custom_entities", [])
        entity_codes = {e["entity_code"] for e in entities}
        for ent in payload.get("entities", []):
            if ent.get("entity_code") and ent["entity_code"] not in entity_codes:
                entities.append(ent)
                entity_codes.add(ent["entity_code"])
        cfg["custom_entities"] = entities

        be = BuilderEngine(self.db)
        be._save_draft(tenant_id, draft.get("id"), cfg)

    # ── LIST INSTALLATIONS ──

    def list_installed(self, tenant_id: str) -> List[Dict]:
        rows = self.db.execute(text(
            "SELECT id, item_code, status, installed_at FROM dbp_tenant_installations "
            "WHERE tenant_id = :tid ORDER BY installed_at DESC"
        ), {"tid": tenant_id}).fetchall()
        return [{"id": r[0], "item_code": r[1], "status": r[2],
                 "installed_at": str(r[3]) if r[3] else None} for r in rows]

    def list_user_installations(self, tenant_id: str) -> List[Dict]:
        return self.list_installed(tenant_id)

    def uninstall_item(self, tenant_id: str, item_code: str,
                       uninstalled_by: str) -> Dict[str, Any]:
        row = self.db.execute(text(
            "SELECT id FROM dbp_tenant_installations WHERE tenant_id=:tid AND item_code=:code"
        ), {"tid": tenant_id, "code": item_code}).fetchone()
        if not row:
            return {"success": False, "error": "Item not installed"}

        self.db.execute(text(
            "UPDATE dbp_tenant_installations SET status='removed', removed_at=NOW() "
            "WHERE id = :iid"
        ), {"iid": row[0]})
        self.db.flush()
        return {"success": True, "message": f"Item '{item_code}' uninstalled"}
