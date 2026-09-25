"""
Integration Connectors - reference connector implementations for the Integration Hub.

Provides connector skeletons for:
- Banks (sandbox bank connector)
- E-invoicing (Egypt ETA connector - wraps egypt_pack e-invoice generation)
- WhatsApp Business (whatsapp notification connector)
- Email (SMTP notification connector)

Each connector follows the BaseConnector interface from integrations.service.
"""

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from .models import Integration, WebhookStatus
from .service import IntegrationService

logger = logging.getLogger("2to-eos.integrations.connectors")


# ---------------------------------------------------------------------------
# Base Connector Interface
# ---------------------------------------------------------------------------

class BaseConnector:
    """All connectors must implement this interface."""

    connector_type: str = ""  # e.g. "bank", "e_invoice", "notification"
    provider: str = ""        # e.g. "eta", "whatsapp", "smtp"

    def __init__(self, integration: Integration, config: dict | None = None):
        self.integration = integration
        self.config = config or integration.config or {}

    def test_connection(self) -> dict:
        """Test connectivity - return {connected: bool, message: str}"""
        raise NotImplementedError

    def sync(self, options: dict | None = None) -> dict:
        """Execute a sync operation."""
        raise NotImplementedError

    def push(self, data: dict) -> dict:
        """Push data to the external system."""
        raise NotImplementedError

    def pull(self, query: dict | None = None) -> dict:
        """Pull data from the external system."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Bank Connector (sandbox/example)
# ---------------------------------------------------------------------------

class BankConnector(BaseConnector):
    """Sandbox bank connector for demonstration.

    In production, this would integrate with real bank APIs
    (e.g., CIB, NBE, or central bank sandbox).
    """

    connector_type = "bank"
    provider = "sandbox"

    def test_connection(self) -> dict:
        # Sandbox always succeeds
        return {"connected": True, "message": "Sandbox bank connection successful"}

    def sync(self, options: dict | None = None) -> dict:
        """Sync bank transactions (sandbox)."""
        options = options or {}
        account = options.get("account", "1234567890")
        logger.info("Syncing bank account %s (sandbox)", account)

        # In a real implementation, this would:
        # 1. Fetch transactions from bank API
        # 2. Map to EOS bank transaction format
        # 3. Create bank transactions via financial service
        # 4. Return sync summary

        return {
            "connector": self.provider,
            "account": account,
            "transactions_fetched": 0,
            "transactions_created": 0,
            "last_sync": datetime.now().isoformat(),
            "note": "Sandbox - no real transactions",
        }

    def push(self, data: dict) -> dict:
        """Push a payment instruction (sandbox)."""
        logger.info("Push payment instruction (sandbox): %s", data.get("reference"))
        return {"status": "queued", "reference": data.get("reference"), "note": "Sandbox"}


# ---------------------------------------------------------------------------
# Egypt ETA E-invoice Connector
# ---------------------------------------------------------------------------

class EgyptETAConnector(BaseConnector):
    """Egypt Tax Authority (ETA) e-invoice connector.

    Uses EgyptPackService to generate ETA-compliant e-invoices,
    then submits them to the ETA portal (stub for now).
    """

    connector_type = "e_invoice"
    provider = "eta"

    def __init__(self, integration: Integration, db: Session | None = None,
                 config: dict | None = None):
        super().__init__(integration, config)
        self.db = db
        # ETA credentials from integration config
        self.eta_api_key = self.config.get("eta_api_key")
        self.eta_tax_id = self.config.get("eta_tax_id")
        self.eta_company_name = self.config.get("eta_company_name")

    def test_connection(self) -> dict:
        if not self.eta_api_key:
            return {"connected": False, "message": "ETA API key not configured"}
        # In production: call ETA health endpoint
        return {"connected": True, "message": "ETA connection configured (stub)"}

    def push(self, invoice_data: dict) -> dict:
        """Generate and push an e-invoice to ETA."""
        if not self.db:
            raise ValueError("Database session required for ETA connector")

        from ..globalization.egypt_pack import EgyptPackService
        egypt_svc = EgyptPackService(self.db)

        # Generate ETA-compliant e-invoice
        e_invoice = egypt_svc.generate_egypt_e_invoice(invoice_data)

        # In production: submit to ETA portal API
        # For now: return generated invoice for review
        return {
            "status": "generated",
            "eta_format": "ETA_E_INVOICE",
            "invoice_number": invoice_data.get("invoice_number"),
            "eta_compliant": True,
            "eta_submission": "pending_manual_review",  # stub
            "e_invoice": e_invoice,
            "note": "ETA submission stub - manual portal submission required",
        }

    def get_tax_certificate(self) -> dict:
        """Get VAT registration certificate info (stub)."""
        return {
            "tax_id": self.eta_tax_id or "NOT_CONFIGURED",
            "company_name": self.eta_company_name or "NOT_CONFIGURED",
            "vat_registered": bool(self.eta_tax_id),
            "certificate_expiry": None,
            "note": "ETA certificate stub",
        }


# ---------------------------------------------------------------------------
# WhatsApp Business Connector
# ---------------------------------------------------------------------------

class WhatsAppBusinessConnector(BaseConnector):
    """WhatsApp Business API connector for notifications.

    Uses WhatsApp Cloud API (Meta) to send messages.
    """

    connector_type = "notification"
    provider = "whatsapp"

    def __init__(self, integration: Integration, config: dict | None = None):
        super().__init__(integration, config)
        self.whatsapp_token = self.config.get("whatsapp_token")
        self.whatsapp_phone_number_id = self.config.get("whatsapp_phone_number_id")
        self.business_account_id = self.config.get("business_account_id")

    def test_connection(self) -> dict:
        if not self.whatsapp_token:
            return {"connected": False, "message": "WhatsApp token not configured"}
        # In production: call WhatsApp API health check
        return {"connected": True, "message": "WhatsApp configured (stub)"}

    def push(self, message_data: dict) -> dict:
        """Send a WhatsApp message."""
        recipient = message_data.get("to")
        message = message_data.get("message")
        message_type = message_data.get("type", "text")

        if not recipient or not message:
            return {"status": "error", "error": "Missing 'to' or 'message'"}

        # In production: call WhatsApp Cloud API
        # POST https://graph.facebook.com/v17.0/{phone-number-id}/messages
        logger.info("WhatsApp message to %s: %s", recipient, message[:50])

        return {
            "status": "sent_stub",
            "recipient": recipient,
            "message_type": message_type,
            "message_preview": message[:100],
            "note": "WhatsApp stub - requires real WhatsApp Business API credentials",
            "whatsapp_message_id": f"stub-{recipient}-{int(datetime.now().timestamp())}",
        }

    def send_invoice_notification(self, customer_phone: str, invoice_number: str,
                                   amount: float, due_date: str) -> dict:
        """Send an invoice reminder via WhatsApp."""
        message = (
            f"Dear customer,\n\n"
            f"Invoice {invoice_number} Amount: {amount:.2f} EGP\n"
            f"Due Date: {due_date}\n\n"
            f"Please settle at your earliest convenience.\n\n"
            f"Thank you,\nYour Company"
        )
        return self.push({
            "to": customer_phone,
            "message": message,
            "type": "text",
        })


# ---------------------------------------------------------------------------
# Email (SMTP) Connector
# ---------------------------------------------------------------------------

class SMTPConnector(BaseConnector):
    """SMTP email connector for notifications."""

    connector_type = "notification"
    provider = "smtp"

    def __init__(self, integration: Integration, config: dict | None = None):
        super().__init__(integration, config)
        self.smtp_host = self.config.get("smtp_host", "smtp.example.com")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.smtp_user = self.config.get("smtp_user")
        self.smtp_password = self.config.get("smtp_password")
        self.from_address = self.config.get("from_address", "noreply@example.com")

    def test_connection(self) -> dict:
        if not self.smtp_user:
            return {"connected": False, "message": "SMTP credentials not configured"}
        # In production: attempt SMTP connection
        return {"connected": True, "message": "SMTP configured (stub)", "host": self.smtp_host}

    def push(self, email_data: dict) -> dict:
        """Send an email via SMTP."""
        to = email_data.get("to")
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")
        content_type = email_data.get("content_type", "text/plain")

        if not to:
            return {"status": "error", "error": "Missing 'to' address"}

        logger.info("Email to %s: %s", to, subject[:50])

        # In production: use smtplib to send
        return {
            "status": "sent_stub",
            "to": to,
            "subject": subject,
            "body_preview": body[:100],
            "content_type": content_type,
            "from": self.from_address,
            "note": "SMTP stub - requires real SMTP server",
        }


# ---------------------------------------------------------------------------
# Connector Registry
# ---------------------------------------------------------------------------

CONNECTORS: dict[str, type[BaseConnector]] = {
    ("bank", "sandbox"): BankConnector,
    ("e_invoice", "eta"): EgyptETAConnector,
    ("notification", "whatsapp"): WhatsAppBusinessConnector,
    ("notification", "smtp"): SMTPConnector,
}


def get_connector(integration: Integration, db: Session | None = None) -> BaseConnector | None:
    """Instantiate the correct connector for an integration."""
    integration_type = integration.integration_type
    provider = integration.provider

    connector_class = CONNECTORS.get((integration_type, provider))
    if connector_class is None:
        logger.warning("No connector found for %s / %s", integration_type, provider)
        return None

    if issubclass(connector_class, EgyptETAConnector):
        return connector_class(integration, db=db)

    return connector_class(integration)


# ---------------------------------------------------------------------------
# Integration service extensions for connectors
# ---------------------------------------------------------------------------

def execute_connector_sync(
    integration_service: IntegrationService,
    integration_id: str,
    tenant_id: str,
    db: Session,
    options: dict | None = None,
) -> dict:
    """Execute a connector sync operation."""
    integration = integration_service.get_integration(integration_id, tenant_id)
    if not integration:
        return {"success": False, "error": "Integration not found"}

    connector = get_connector(integration, db=db)
    if not connector:
        return {"success": False, "error": f"No connector for {integration.provider}"}

    try:
        result = connector.sync(options)
        # Log success
        integration_service.create_log({
            "integration_id": integration_id,
            "tenant_id": tenant_id,
            "endpoint_name": f"sync_{integration.provider}",
            "direction": "outbound",
            "status": "success",
            "request_method": "SYNC",
            "request_url": integration.provider,
            "response_body": result,
            "duration_ms": 0,
        })
        return {"success": True, "result": result}
    except Exception as e:
        integration_service.create_log({
            "integration_id": integration_id,
            "tenant_id": tenant_id,
            "endpoint_name": f"sync_{integration.provider}",
            "direction": "outbound",
            "status": "error",
            "error_message": str(e),
            "duration_ms": 0,
        })
        return {"success": False, "error": str(e)}


def execute_connector_push(
    integration_service: IntegrationService,
    integration_id: str,
    tenant_id: str,
    db: Session,
    data: dict,
) -> dict:
    """Execute a connector push operation."""
    integration = integration_service.get_integration(integration_id, tenant_id)
    if not integration:
        return {"success": False, "error": "Integration not found"}

    connector = get_connector(integration, db=db)
    if not connector:
        return {"success": False, "error": f"No connector for {integration.provider}"}

    try:
        result = connector.push(data)
        integration_service.create_log({
            "integration_id": integration_id,
            "tenant_id": tenant_id,
            "endpoint_name": f"push_{integration.provider}",
            "direction": "outbound",
            "status": "success",
            "request_method": "PUSH",
            "request_url": integration.provider,
            "request_body": data,
            "response_body": result,
            "duration_ms": 0,
        })
        return {"success": True, "result": result}
    except Exception as e:
        integration_service.create_log({
            "integration_id": integration_id,
            "tenant_id": tenant_id,
            "endpoint_name": f"push_{integration.provider}",
            "direction": "outbound",
            "status": "error",
            "error_message": str(e),
            "duration_ms": 0,
        })
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Connector management endpoints (added to router)
# ---------------------------------------------------------------------------

def register_connector_routes(router, get_db, require_tenant):
    from fastapi import Depends, HTTPException, Query
    from uuid import UUID
