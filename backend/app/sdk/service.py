"""Developer SDK service."""
import hashlib
import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from .models import SDKAPIKey, SDKApp, SDKEndpoint, SDKEvent, SDKPlugin, SDKWebhook


class SDKService:
    def __init__(self, db: Session):
        self.db = db

    # Apps

    def create_app(self, tenant_id: str, data: dict) -> SDKApp:
        app = SDKApp(tenant_id=tenant_id, **data)
        self.db.add(app)
        self.db.commit()
        self.db.refresh(app)
        return app

    def get_app(self, app_id: str, tenant_id: str) -> SDKApp | None:
        return self.db.query(SDKApp).filter(SDKApp.id == app_id, SDKApp.tenant_id == tenant_id).first()

    def list_apps(self, tenant_id: str) -> list[SDKApp]:
        return self.db.query(SDKApp).filter(SDKApp.tenant_id == tenant_id).order_by(SDKApp.name).all()

    def install_app(self, app_id: str, tenant_id: str) -> SDKApp | None:
        app = self.get_app(app_id, tenant_id)
        if not app:
            return None
        app.is_installed = True
        app.installed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(app)
        return app

    # Webhooks

    def create_webhook(self, tenant_id: str, data: dict) -> SDKWebhook:
        webhook = SDKWebhook(tenant_id=tenant_id, **data)
        self.db.add(webhook)
        self.db.commit()
        self.db.refresh(webhook)
        return webhook

    def list_webhooks(self, tenant_id: str, app_id: str | None = None) -> list[SDKWebhook]:
        q = self.db.query(SDKWebhook).filter(SDKWebhook.tenant_id == tenant_id)
        if app_id:
            q = q.filter(SDKWebhook.app_id == app_id)
        return q.order_by(SDKWebhook.name).all()

    # API Keys

    def create_api_key(self, tenant_id: str, data: dict) -> tuple[SDKAPIKey, str]:
        raw_key = f"eos_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:12] + "..."

        api_key = SDKAPIKey(
            tenant_id=tenant_id,
            app_id=data.get("app_id"),
            name=data["name"],
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=data.get("scopes"),
            rate_limit=data.get("rate_limit"),
            expires_at=data.get("expires_at"),
        )
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        return api_key, raw_key

    def list_api_keys(self, tenant_id: str) -> list[SDKAPIKey]:
        return self.db.query(SDKAPIKey).filter(SDKAPIKey.tenant_id == tenant_id).order_by(SDKAPIKey.name).all()

    # Plugins

    def create_plugin(self, tenant_id: str, data: dict) -> SDKPlugin:
        plugin = SDKPlugin(tenant_id=tenant_id, **data)
        self.db.add(plugin)
        self.db.commit()
        self.db.refresh(plugin)
        return plugin

    def list_plugins(self, tenant_id: str, app_id: str | None = None) -> list[SDKPlugin]:
        q = self.db.query(SDKPlugin).filter(SDKPlugin.tenant_id == tenant_id)
        if app_id:
            q = q.filter(SDKPlugin.app_id == app_id)
        return q.order_by(SDKPlugin.name).all()

    # Endpoints

    def create_endpoint(self, tenant_id: str, data: dict) -> SDKEndpoint:
        endpoint = SDKEndpoint(tenant_id=tenant_id, **data)
        self.db.add(endpoint)
        self.db.commit()
        self.db.refresh(endpoint)
        return endpoint

    def list_endpoints(self, tenant_id: str, app_id: str | None = None) -> list[SDKEndpoint]:
        q = self.db.query(SDKEndpoint).filter(SDKEndpoint.tenant_id == tenant_id)
        if app_id:
            q = q.filter(SDKEndpoint.app_id == app_id)
        return q.order_by(SDKEndpoint.path).all()

    # Events

    def publish_event(self, tenant_id: str, event_type: str, payload: dict | None = None, source: str | None = None) -> SDKEvent:
        event = SDKEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            payload=payload,
            source=source,
            status="pending",
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_events(self, tenant_id: str, event_type: str | None = None, status: str | None = None, limit: int = 50) -> list[SDKEvent]:
        q = self.db.query(SDKEvent).filter(SDKEvent.tenant_id == tenant_id)
        if event_type:
            q = q.filter(SDKEvent.event_type == event_type)
        if status:
            q = q.filter(SDKEvent.status == status)
        return q.order_by(SDKEvent.created_at.desc()).limit(limit).all()

    def get_event_stats(self, tenant_id: str) -> dict:
        total = self.db.query(SDKEvent).filter(SDKEvent.tenant_id == tenant_id).count()
        pending = self.db.query(SDKEvent).filter(SDKEvent.tenant_id == tenant_id, SDKEvent.status == "pending").count()
        processed = self.db.query(SDKEvent).filter(SDKEvent.tenant_id == tenant_id, SDKEvent.status == "processed").count()
        failed = self.db.query(SDKEvent).filter(SDKEvent.tenant_id == tenant_id, SDKEvent.status == "failed").count()
        return {"total": total, "pending": pending, "processed": processed, "failed": failed}

    def validate_api_key(self, api_key: str) -> dict | None:
        """Validate an API key and return its metadata if valid."""
        if not api_key or not api_key.startswith("eos_"):
            return None

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_obj = self.db.query(SDKAPIKey).filter(
            SDKAPIKey.key_hash == key_hash,
            SDKAPIKey.is_active,
        ).first()

        if key_obj is None:
            return None

        # Check expiry
        if key_obj.expires_at and key_obj.expires_at < datetime.utcnow():
            return None

        # Update usage stats
        key_obj.last_used_at = datetime.utcnow()
        key_obj.use_count += 1
        self.db.commit()

        return {
            "api_key_id": key_obj.id,
            "tenant_id": key_obj.tenant_id,
            "app_id": key_obj.app_id,
            "name": key_obj.name,
            "scopes": key_obj.scopes or [],
            "rate_limit": key_obj.rate_limit,
        }

    def revoke_api_key(self, tenant_id: str, api_key_id: str) -> bool:
        key_obj = self.db.query(SDKAPIKey).filter(
            SDKAPIKey.id == api_key_id,
            SDKAPIKey.tenant_id == tenant_id,
        ).first()
        if key_obj is None:
            return False
        key_obj.is_active = False
        self.db.commit()
        return True

    def increment_rate_limit(self, api_key_id: str, endpoint: str) -> bool:
        """Check and increment rate limit. Returns True if allowed."""
        from datetime import timedelta
        from .models import SDKRateLimit

        key_obj = self.db.query(SDKAPIKey).filter(SDKAPIKey.id == api_key_id).first()
        if not key_obj or not key_obj.rate_limit:
            return True

        now = datetime.utcnow()
        window_start = now - timedelta(seconds=60)

        limit = self.db.query(SDKRateLimit).filter(
            SDKRateLimit.api_key_id == api_key_id,
            SDKRateLimit.endpoint == endpoint,
            SDKRateLimit.window_start >= window_start,
        ).first()

        if limit is None:
            limit = SDKRateLimit(
                tenant_id=key_obj.tenant_id,
                api_key_id=api_key_id,
                endpoint=endpoint,
                window_seconds=60,
                max_requests=key_obj.rate_limit,
                current_count=1,
                window_start=now,
            )
            self.db.add(limit)
            self.db.commit()
            return True

        if limit.current_count >= limit.max_requests:
            return False

        limit.current_count += 1
        self.db.commit()
        return True
