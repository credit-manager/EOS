"""EOS Marketplace Engine.

Marketplace content is treated as untrusted metadata. Only published items can
be installed, paid items require an entitlement, and installation payloads are
limited to supported metadata structures before reaching the Builder.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.builder_engine import BuilderEngine


class MarketplaceEngine:
    _MAX_LIST_LIMIT = 200
    _ALLOWED_PAYLOAD_KEYS = {"modules", "entities", "workflows", "dashboards", "reports", "config"}

    def __init__(self, db: Session):
        self.db = db

    @classmethod
    def _limit(cls, value: Any, default: int = 50) -> int:
        try:
            return max(1, min(int(value), cls._MAX_LIST_LIMIT))
        except (TypeError, ValueError):
            return default

    @classmethod
    def _validate_payload(cls, payload: Any) -> Dict[str, Any]:
        if payload is None:
            return {}
        if not isinstance(payload, dict):
            raise ValueError("Marketplace payload must be an object")
        unknown = set(payload) - cls._ALLOWED_PAYLOAD_KEYS
        if unknown:
            raise ValueError(f"Unsupported marketplace payload keys: {sorted(unknown)}")

        result: Dict[str, Any] = {}
        modules = payload.get("modules", [])
        if not isinstance(modules, list) or len(modules) > 500:
            raise ValueError("Invalid marketplace modules")
        result["modules"] = []
        for module in modules:
            if isinstance(module, dict):
                code = str(module.get("code", "")).strip()
                if not code or len(code) > 120:
                    raise ValueError("Invalid marketplace module code")
                result["modules"].append(code)
            else:
                code = str(module).strip()
                if not code or len(code) > 120:
                    raise ValueError("Invalid marketplace module code")
                result["modules"].append(code)

        entities = payload.get("entities", [])
        if not isinstance(entities, list) or len(entities) > 500:
            raise ValueError("Invalid marketplace entities")
        safe_entities = []
        for entity in entities:
            if not isinstance(entity, dict):
                raise ValueError("Marketplace entity definitions must be objects")
            code = str(entity.get("entity_code", "")).strip()
            if not code or len(code) > 120:
                raise ValueError("Invalid marketplace entity code")
            safe_entities.append(entity)
        result["entities"] = safe_entities

        for key in ("workflows", "dashboards", "reports"):
            value = payload.get(key, [])
            if not isinstance(value, list) or len(value) > 500:
                raise ValueError(f"Invalid marketplace {key}")
            result[key] = value

        config = payload.get("config", {})
        if not isinstance(config, dict):
            raise ValueError("Marketplace config must be an object")
        result["config"] = config
        return result

    def list_items(
        self,
        item_type: Optional[str] = None,
        is_featured: Optional[bool] = None,
        is_free: Optional[bool] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        conditions = ["is_published = true"]
        params: Dict[str, Any] = {"lim": self._limit(limit)}
        if item_type:
            conditions.append("item_type=:type")
            params["type"] = str(item_type).strip()
        if is_featured is not None:
            conditions.append("is_featured=:feat")
            params["feat"] = is_featured
        if is_free is not None:
            conditions.append("is_free=:free")
            params["free"] = is_free
        where = " AND ".join(conditions)
        rows = self.db.execute(
            text(
                "SELECT id, item_code, item_type, name_en, name_ar, description, "
                "publisher, version, price_monthly, is_featured, is_free "
                f"FROM dbp_marketplace_items WHERE {where} "
                "ORDER BY sort_order, created_at DESC LIMIT :lim"
            ),
            params,
        ).fetchall()
        return [
            {
                "id": row[0],
                "item_code": row[1],
                "type": row[2],
                "name_en": row[3],
                "name_ar": row[4],
                "description": row[5],
                "publisher": row[6],
                "version": row[7],
                "price_monthly": float(row[8]) if row[8] is not None else 0,
                "price_yearly": None,
                "is_featured": bool(row[9]),
                "is_free": bool(row[10]),
            }
            for row in rows
        ]

    def get_item(self, item_code: str) -> Optional[Dict[str, Any]]:
        row = self.db.execute(
            text(
                "SELECT id, item_code, item_type, name_en, name_ar, description, "
                "publisher, version, price_monthly, is_featured, is_free, payload "
                "FROM dbp_marketplace_items "
                "WHERE item_code=:code AND is_published=true"
            ),
            {"code": str(item_code).strip()},
        ).fetchone()
        if not row:
            return None
        payload = self._validate_payload(row[11] if isinstance(row[11], dict) else json.loads(row[11] or "{}"))
        return {
            "id": row[0],
            "item_code": row[1],
            "type": row[2],
            "name_en": row[3],
            "name_ar": row[4],
            "description": row[5],
            "publisher": row[6],
            "version": row[7],
            "price_monthly": float(row[8]) if row[8] is not None else 0,
            "price_yearly": None,
            "is_featured": bool(row[9]),
            "is_free": bool(row[10]),
            "payload": payload,
        }

    def install_item(self, tenant_id: str, item_code: str, installed_by: str) -> Dict[str, Any]:
        item = self.get_item(item_code)
        if not item:
            return {"success": False, "error": "Marketplace item not found or not published"}
        if not item["is_free"]:
            return {
                "success": False,
                "error": "Paid marketplace items require a verified entitlement before installation",
            }

        existing = self.db.execute(
            text(
                "SELECT id, status FROM dbp_tenant_installations "
                "WHERE tenant_id=:tid AND item_code=:code AND status <> 'removed'"
            ),
            {"tid": tenant_id, "code": item["item_code"]},
        ).fetchone()
        if existing:
            return {"success": False, "error": "Item already installed"}

        payload = item.get("payload", {})
        installation_id = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_tenant_installations "
                "(id, tenant_id, item_code, status, applied_payload, installed_by, installed_at) "
                "VALUES (:id,:tid,:code,'pending',:payload,:by,NOW())"
            ),
            {
                "id": installation_id,
                "tid": tenant_id,
                "code": item["item_code"],
                "payload": json.dumps(payload),
                "by": installed_by,
            },
        )
        self.db.flush()
        return {"success": True, "installation_id": installation_id, "payload": payload}

    def apply_installation(self, tenant_id: str, installation_id: str, draft_pid: str) -> Dict[str, Any]:
        inst_row = self.db.execute(
            text(
                "SELECT id, item_code, applied_payload FROM dbp_tenant_installations "
                "WHERE id=:iid AND tenant_id=:tid AND status='pending'"
            ),
            {"iid": installation_id, "tid": tenant_id},
        ).fetchone()
        if not inst_row:
            return {"success": False, "error": "Installation not found or already applied"}
        if not draft_pid:
            return {"success": False, "error": "Builder project required"}

        payload_raw = inst_row[2]
        payload = self._validate_payload(payload_raw if isinstance(payload_raw, dict) else json.loads(payload_raw or "{}"))
        project = BuilderEngine(self.db).get_project(tenant_id, draft_pid)
        if not project:
            return {"success": False, "error": "Project not found"}

        self._apply_payload(tenant_id, project, payload)
        self.db.execute(
            text(
                "UPDATE dbp_tenant_installations SET status='installed', applied_payload=:p "
                "WHERE id=:iid AND tenant_id=:tid AND status='pending'"
            ),
            {"iid": installation_id, "tid": tenant_id, "p": json.dumps(payload)},
        )
        self.db.flush()
        return {"success": True, "item_code": inst_row[1], "modules_added": len(payload.get("modules", []))}

    def _apply_payload(self, tenant_id: str, draft: Dict[str, Any], payload: Dict[str, Any]) -> None:
        cfg = draft.get("draft_config", {}) if isinstance(draft, dict) else {}
        if isinstance(cfg, str):
            cfg = json.loads(cfg)
        if not isinstance(cfg, dict):
            raise ValueError("Builder draft configuration is invalid")

        modules = set()
        for module in cfg.get("modules", []):
            code = module.get("code") if isinstance(module, dict) else str(module)
            if code:
                modules.add(str(code))
        modules.update(payload.get("modules", []))
        cfg["modules"] = [{"code": code, "enabled": True} for code in sorted(modules)]

        entities = list(cfg.get("custom_entities", []))
        existing_codes = {str(entity.get("entity_code")) for entity in entities if isinstance(entity, dict)}
        for entity in payload.get("entities", []):
            code = entity.get("entity_code")
            if code and code not in existing_codes:
                entities.append(entity)
                existing_codes.add(code)
        cfg["custom_entities"] = entities
        for key in ("workflows", "dashboards", "reports"):
            cfg[key] = list(cfg.get(key, [])) + list(payload.get(key, []))
        if payload.get("config"):
            cfg["marketplace_config"] = payload["config"]
        BuilderEngine(self.db)._save_draft(tenant_id, draft.get("id"), cfg)

    def list_installed(self, tenant_id: str) -> List[Dict[str, Any]]:
        rows = self.db.execute(
            text(
                "SELECT id, item_code, status, installed_at FROM dbp_tenant_installations "
                "WHERE tenant_id=:tid ORDER BY installed_at DESC LIMIT :lim"
            ),
            {"tid": tenant_id, "lim": self._MAX_LIST_LIMIT},
        ).fetchall()
        return [
            {"id": row[0], "item_code": row[1], "status": row[2], "installed_at": str(row[3]) if row[3] else None}
            for row in rows
        ]

    def list_user_installations(self, tenant_id: str) -> List[Dict[str, Any]]:
        return self.list_installed(tenant_id)

    def uninstall_item(self, tenant_id: str, item_code: str, uninstalled_by: str) -> Dict[str, Any]:
        row = self.db.execute(
            text(
                "SELECT id FROM dbp_tenant_installations "
                "WHERE tenant_id=:tid AND item_code=:code AND status <> 'removed' LIMIT 1"
            ),
            {"tid": tenant_id, "code": item_code},
        ).fetchone()
        if not row:
            return {"success": False, "error": "Item not installed"}
        self.db.execute(
            text(
                "UPDATE dbp_tenant_installations SET status='removed', removed_at=NOW() "
                "WHERE id=:iid AND tenant_id=:tid AND status <> 'removed'"
            ),
            {"iid": row[0], "tid": tenant_id},
        )
        self.db.flush()
        return {"success": True, "message": f"Item '{item_code}' uninstalled", "uninstalled_by": uninstalled_by}
