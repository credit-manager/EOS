"""Integration Hub service."""
import time
import logging
import httpx
from datetime import datetime, UTC, timedelta
from typing import Any

from sqlalchemy.orm import Session

from .models import (
    Integration,
    IntegrationEndpoint,
    IntegrationLog,
    IntegrationMapping,
    IntegrationSecret,
    WebhookDelivery,
    WebhookDeliveryAttempt,
    WebhookStatus,
)

logger = logging.getLogger("2to-eos.integrations")


class IntegrationService:
    def __init__(self, db: Session):
        self.db = db

    def create_integration(self, tenant_id: str, data: dict) -> Integration:
        integration = Integration(
            tenant_id=tenant_id,
            code=data["code"],
            name=data["name"],
            description=data.get("description"),
            integration_type=data["integration_type"],
            provider=data.get("provider"),
            config=data.get("config"),
            credentials=data.get("credentials"),
            rate_limit=data.get("rate_limit"),
            timeout_seconds=data.get("timeout_seconds", 30),
            retry_count=data.get("retry_count", 3),
            is_active=data.get("is_active", True),
        )
        self.db.add(integration)
        self.db.commit()
        self.db.refresh(integration)
        return integration

    def get_integration(self, integration_id: str, tenant_id: str) -> Integration | None:
        return (
            self.db.query(Integration)
            .filter(Integration.id == integration_id, Integration.tenant_id == tenant_id)
            .first()
        )

    def list_integrations(self, tenant_id: str, limit: int = 50, offset: int = 0) -> tuple[list[Integration], int]:
        q = self.db.query(Integration).filter(Integration.tenant_id == tenant_id)
        total = q.count()
        items = q.order_by(Integration.name).offset(offset).limit(limit).all()
        return items, total

    def update_integration(self, integration_id: str, tenant_id: str, data: dict) -> Integration | None:
        integration = self.get_integration(integration_id, tenant_id)
        if not integration:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(integration, key, value)
        integration.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(integration)
        return integration

    def delete_integration(self, integration_id: str, tenant_id: str) -> bool:
        integration = self.get_integration(integration_id, tenant_id)
        if not integration:
            return False
        self.db.delete(integration)
        self.db.commit()
        return True

    def create_endpoint(self, integration_id: str, tenant_id: str, data: dict) -> IntegrationEndpoint | None:
        integration = self.get_integration(integration_id, tenant_id)
        if not integration:
            return None
        endpoint = IntegrationEndpoint(
            integration_id=integration_id,
            tenant_id=tenant_id,
            name=data["name"],
            method=data.get("method", "GET"),
            path=data["path"],
            headers=data.get("headers"),
            body_template=data.get("body_template"),
            response_mapping=data.get("response_mapping"),
            error_mapping=data.get("error_mapping"),
            timeout_seconds=data.get("timeout_seconds"),
            is_active=data.get("is_active", True),
        )
        self.db.add(endpoint)
        self.db.commit()
        self.db.refresh(endpoint)
        return endpoint

    def get_endpoint(self, endpoint_id: str, tenant_id: str) -> IntegrationEndpoint | None:
        return (
            self.db.query(IntegrationEndpoint)
            .filter(IntegrationEndpoint.id == endpoint_id, IntegrationEndpoint.tenant_id == tenant_id)
            .first()
        )

    def list_endpoints(self, integration_id: str, tenant_id: str) -> list[IntegrationEndpoint]:
        return (
            self.db.query(IntegrationEndpoint)
            .filter(IntegrationEndpoint.integration_id == integration_id, IntegrationEndpoint.tenant_id == tenant_id)
            .order_by(IntegrationEndpoint.name)
            .all()
        )

    def create_mapping(self, integration_id: str, tenant_id: str, data: dict) -> IntegrationMapping | None:
        integration = self.get_integration(integration_id, tenant_id)
        if not integration:
            return None
        mapping = IntegrationMapping(
            integration_id=integration_id,
            tenant_id=tenant_id,
            name=data["name"],
            source_entity=data["source_entity"],
            target_entity=data["target_entity"],
            field_mappings=data.get("field_mappings"),
            transform_rules=data.get("transform_rules"),
            is_active=data.get("is_active", True),
        )
        self.db.add(mapping)
        self.db.commit()
        self.db.refresh(mapping)
        return mapping

    def list_mappings(self, integration_id: str, tenant_id: str) -> list[IntegrationMapping]:
        return (
            self.db.query(IntegrationMapping)
            .filter(IntegrationMapping.integration_id == integration_id, IntegrationMapping.tenant_id == tenant_id)
            .order_by(IntegrationMapping.name)
            .all()
        )

    def create_log(self, data: dict) -> IntegrationLog:
        log = IntegrationLog(**data)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_logs(
        self,
        tenant_id: str,
        integration_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[IntegrationLog]:
        q = self.db.query(IntegrationLog).filter(IntegrationLog.tenant_id == tenant_id)
        if integration_id:
            q = q.filter(IntegrationLog.integration_id == integration_id)
        if status:
            q = q.filter(IntegrationLog.status == status)
        return q.order_by(IntegrationLog.created_at.desc()).limit(limit).all()

    def create_secret(self, integration_id: str, tenant_id: str, data: dict) -> IntegrationSecret | None:
        integration = self.get_integration(integration_id, tenant_id)
        if not integration:
            return None
        secret = IntegrationSecret(
            integration_id=integration_id,
            tenant_id=tenant_id,
            secret_key=data["secret_key"],
            secret_value_encrypted=data["secret_value"],
            secret_type=data.get("secret_type", "api_key"),
            description=data.get("description"),
            expires_at=data.get("expires_at"),
        )
        self.db.add(secret)
        self.db.commit()
        self.db.refresh(secret)
        return secret

    def list_secrets(self, integration_id: str, tenant_id: str) -> list[IntegrationSecret]:
        return (
            self.db.query(IntegrationSecret)
            .filter(IntegrationSecret.integration_id == integration_id, IntegrationSecret.tenant_id == tenant_id)
            .order_by(IntegrationSecret.secret_key)
            .all()
        )

    def test_endpoint(self, integration_id: str, tenant_id: str, endpoint_name: str, test_data: dict | None = None) -> dict:
        """Test an integration endpoint with real HTTP call."""
        endpoint = (
            self.db.query(IntegrationEndpoint)
            .filter(
                IntegrationEndpoint.integration_id == integration_id,
                IntegrationEndpoint.tenant_id == tenant_id,
                IntegrationEndpoint.name == endpoint_name,
            )
            .first()
        )
        if not endpoint:
            return {"success": False, "error_message": "Endpoint not found"}

        integration = self.get_integration(integration_id, tenant_id)
        if not integration:
            return {"success": False, "error_message": "Integration not found"}

        return self._execute_endpoint(integration, endpoint, test_data or {})

    def _execute_endpoint(self, integration: Integration, endpoint: IntegrationEndpoint, payload: dict) -> dict:
        """Execute an endpoint with real HTTP call."""
        import time
        start_time = time.time()

        # Build request
        url = endpoint.path
        method = endpoint.method.upper()
        headers = endpoint.headers or {}
        timeout = endpoint.timeout_seconds or integration.timeout_seconds or 30

        # Add auth from secrets if configured
        auth_header = self._get_auth_header(integration)
        if auth_header:
            headers.setdefault("Authorization", auth_header)

        try:
            with httpx.Client(timeout=timeout) as client:
                if method == "GET":
                    resp = client.get(url, params=payload, headers=headers)
                elif method == "POST":
                    resp = client.post(url, json=payload, headers=headers)
                elif method == "PUT":
                    resp = client.put(url, json=payload, headers=headers)
                elif method == "PATCH":
                    resp = client.patch(url, json=payload, headers=headers)
                elif method == "DELETE":
                    resp = client.delete(url, headers=headers)
                else:
                    return {"success": False, "error_message": f"Unsupported method: {method}"}

            duration_ms = (time.time() - start_time) * 1000

            # Log the call
            self.create_log({
                "integration_id": str(integration.id),
                "tenant_id": str(integration.tenant_id),
                "endpoint_name": endpoint.name,
                "direction": "outbound",
                "status": "success" if resp.is_success else "error",
                "request_method": method,
                "request_url": url,
                "request_body": payload,
                "response_status": resp.status_code,
                "response_body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
                "duration_ms": duration_ms,
            })

            return {
                "success": resp.is_success,
                "status_code": resp.status_code,
                "response_body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
                "duration_ms": duration_ms,
            }

        except httpx.TimeoutException:
            duration_ms = (time.time() - start_time) * 1000
            self.create_log({
                "integration_id": str(integration.id),
                "tenant_id": str(integration.tenant_id),
                "endpoint_name": endpoint.name,
                "direction": "outbound",
                "status": "timeout",
                "request_method": method,
                "request_url": url,
                "request_body": payload,
                "error_message": "Request timeout",
                "duration_ms": duration_ms,
            })
            return {"success": False, "error_message": "Request timeout", "duration_ms": duration_ms}

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.exception("Endpoint execution failed")
            self.create_log({
                "integration_id": str(integration.id),
                "tenant_id": str(integration.tenant_id),
                "endpoint_name": endpoint.name,
                "direction": "outbound",
                "status": "error",
                "request_method": method,
                "request_url": url,
                "request_body": payload,
                "error_message": str(e),
                "duration_ms": duration_ms,
            })
            return {"success": False, "error_message": str(e), "duration_ms": duration_ms}

    def _get_auth_header(self, integration: Integration) -> str | None:
        """Get authentication header from secrets."""
        if not integration.credentials:
            return None
        # Support bearer token
        if integration.credentials.get("type") == "bearer":
            return f"Bearer {integration.credentials.get('token', '')}"
        # Support API key
        if integration.credentials.get("type") == "api_key":
            key = integration.credentials.get("key", "")
            value = integration.credentials.get("value", "")
            return f"{key} {value}"
        return None

    # ============================================================
    # Webhook Delivery with Retry & Dead-Letter
    # ============================================================

    def queue_webhook(
        self,
        integration_id: str,
        endpoint_id: str,
        tenant_id: str,
        url: str,
        payload: dict,
        headers: dict | None = None,
        method: str = "POST",
        max_attempts: int | None = None,
        scheduled_at: datetime | None = None,
    ) -> WebhookDelivery:
        """Queue a webhook for delivery."""
        integration = self.get_integration(integration_id, tenant_id)
        if not integration:
            raise ValueError("Integration not found")

        endpoint = self.db.query(IntegrationEndpoint).filter(
            IntegrationEndpoint.id == endpoint_id,
            IntegrationEndpoint.tenant_id == tenant_id
        ).first()
        if not endpoint:
            raise ValueError("Endpoint not found")

        delivery = WebhookDelivery(
            tenant_id=tenant_id,
            integration_id=integration_id,
            endpoint_id=endpoint_id,
            url=url,
            method=method.upper(),
            headers=headers or {},
            payload=payload,
            max_attempts=max_attempts or integration.retry_count or 3,
            scheduled_at=scheduled_at,
            status=WebhookStatus.pending.value,
        )
        self.db.add(delivery)
        self.db.commit()
        self.db.refresh(delivery)
        return delivery

    def process_webhook_delivery(self, delivery_id: str) -> WebhookDelivery | None:
        """Process a single webhook delivery with retry logic."""
        delivery = self.db.query(WebhookDelivery).filter(WebhookDelivery.id == delivery_id).first()
        if not delivery:
            return None

        if delivery.status not in (WebhookStatus.pending.value, WebhookStatus.failed.value):
            return delivery

        # Check if scheduled for future
        if delivery.scheduled_at and delivery.scheduled_at > datetime.now(UTC):
            return delivery

        # Check max attempts
        if delivery.attempt_count >= delivery.max_attempts:
            delivery.status = WebhookStatus.dead_letter.value
            delivery.error_message = f"Max attempts ({delivery.max_attempts}) exceeded"
            self.db.commit()
            return delivery

        # Execute delivery
        attempt_number = delivery.attempt_count + 1
        start_time = time.time()

        try:
            with httpx.Client(timeout=30) as client:
                if delivery.method == "GET":
                    resp = client.get(delivery.url, params=delivery.payload, headers=delivery.headers)
                elif delivery.method == "POST":
                    resp = client.post(delivery.url, json=delivery.payload, headers=delivery.headers)
                elif delivery.method == "PUT":
                    resp = client.put(delivery.url, json=delivery.payload, headers=delivery.headers)
                else:
                    resp = client.request(delivery.method, delivery.url, json=delivery.payload, headers=delivery.headers)

            duration_ms = (time.time() - start_time) * 1000

            # Record attempt
            attempt = WebhookDeliveryAttempt(
                delivery_id=delivery.id,
                attempt_number=attempt_number,
                status_code=resp.status_code,
                response_body=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
                duration_ms=duration_ms,
            )
            self.db.add(attempt)

            delivery.attempt_count = attempt_number

            if resp.is_success:
                delivery.status = WebhookStatus.delivered.value
                delivery.response_status = resp.status_code
                delivery.response_body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                delivery.delivered_at = datetime.now(UTC)
            else:
                delivery.status = WebhookStatus.failed.value
                delivery.response_status = resp.status_code
                delivery.response_body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                delivery.error_message = f"HTTP {resp.status_code}: {resp.text}"
                # Schedule retry with exponential backoff
                retry_delay = min(60 * (2 ** (attempt_number - 1)), 3600)  # max 1 hour
                delivery.next_retry_at = datetime.now(UTC).replace(microsecond=0) + timedelta(seconds=retry_delay)

        except httpx.TimeoutException:
            duration_ms = (time.time() - start_time) * 1000
            attempt = WebhookDeliveryAttempt(
                delivery_id=delivery.id,
                attempt_number=attempt_number,
                error_message="Request timeout",
                duration_ms=duration_ms,
            )
            self.db.add(attempt)
            delivery.attempt_count = attempt_number
            delivery.error_message = "Request timeout"
            retry_delay = min(60 * (2 ** (attempt_number - 1)), 3600)
            delivery.next_retry_at = datetime.now(UTC).replace(microsecond=0) + timedelta(seconds=retry_delay)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            attempt = WebhookDeliveryAttempt(
                delivery_id=delivery.id,
                attempt_number=attempt_number,
                error_message=str(e),
                duration_ms=duration_ms,
            )
            self.db.add(attempt)
            delivery.attempt_count = attempt_number
            delivery.error_message = str(e)
            retry_delay = min(60 * (2 ** (attempt_number - 1)), 3600)
            delivery.next_retry_at = datetime.now(UTC).replace(microsecond=0) + timedelta(seconds=retry_delay)

        delivery.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(delivery)
        return delivery

    def process_pending_webhooks(self, tenant_id: str, limit: int = 50) -> dict:
        """Process all pending webhook deliveries for a tenant."""
        now = datetime.now(UTC)
        pending = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.tenant_id == tenant_id,
            WebhookDelivery.status.in_([WebhookStatus.pending.value, WebhookStatus.failed.value]),
            WebhookDelivery.attempt_count < WebhookDelivery.max_attempts,
            WebhookDelivery.next_retry_at.is_(None) | (WebhookDelivery.next_retry_at <= now),
        ).limit(limit).all()

        processed = 0
        delivered = 0
        failed = 0

        for delivery in pending:
            result = self.process_webhook_delivery(delivery.id)
            if result:
                processed += 1
                if result.status == WebhookStatus.delivered.value:
                    delivered += 1
                elif result.status == WebhookStatus.dead_letter.value:
                    failed += 1

        return {"processed": processed, "delivered": delivered, "failed": failed, "dead_letter": failed}

    def get_webhook_delivery(self, delivery_id: str, tenant_id: str) -> WebhookDelivery | None:
        return self.db.query(WebhookDelivery).filter(
            WebhookDelivery.id == delivery_id,
            WebhookDelivery.tenant_id == tenant_id
        ).first()

    def list_webhook_deliveries(
        self,
        tenant_id: str,
        status: str | None = None,
        integration_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[WebhookDelivery], int]:
        q = self.db.query(WebhookDelivery).filter(WebhookDelivery.tenant_id == tenant_id)
        if status:
            q = q.filter(WebhookDelivery.status == status)
        if integration_id:
            q = q.filter(WebhookDelivery.integration_id == integration_id)
        total = q.count()
        items = q.order_by(WebhookDelivery.created_at.desc()).offset(offset).limit(limit).all()
        return items, total

    def get_webhook_attempts(self, delivery_id: str, tenant_id: str) -> list[WebhookDeliveryAttempt]:
        delivery = self.get_webhook_delivery(delivery_id, tenant_id)
        if not delivery:
            return []
        return self.db.query(WebhookDeliveryAttempt).filter(
            WebhookDeliveryAttempt.delivery_id == delivery_id
        ).order_by(WebhookDeliveryAttempt.attempt_number).all()

    def retry_webhook(self, delivery_id: str, tenant_id: str) -> WebhookDelivery | None:
        """Manually retry a failed webhook."""
        delivery = self.get_webhook_delivery(delivery_id, tenant_id)
        if not delivery:
            return None
        if delivery.status not in (WebhookStatus.failed.value, WebhookStatus.dead_letter.value):
            return delivery
        delivery.status = WebhookStatus.pending.value
        delivery.attempt_count = 0
        delivery.next_retry_at = None
        delivery.error_message = None
        delivery.updated_at = datetime.now(UTC)
        self.db.commit()
        return self.process_webhook_delivery(delivery.id)
