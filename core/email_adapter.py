"""
P61 Email Adapter — Provider-agnostic email sending.
Console provider (dev/test) + SMTP provider (production).

EOS_EMAIL_PROVIDER may explicitly select console or smtp. When unset,
production authentication mode defaults to SMTP so password recovery and
account invitations are delivered instead of merely being logged.
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger("eos.email")


class EmailProvider(ABC):
    @abstractmethod
    def send(self, to_email: str, subject: str, html_body: str, text_body: Optional[str] = None,
             from_email: Optional[str] = None, from_name: Optional[str] = None) -> dict:
        ...


class ConsoleEmailProvider(EmailProvider):
    """Development/test provider. Never used implicitly in production."""
    def __init__(self):
        self._sent = []

    def send(self, to_email, subject, html_body, text_body=None, from_email=None, from_name=None):
        from_name = from_name or "EOS Platform"
        from_email = from_email or "noreply@eos-platform.com"
        msg_id = f"console_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{hash(to_email) % 10000}"
        self._sent.append({"to": to_email, "from": f"{from_name} <{from_email}>", "subject": subject,
                           "html": html_body[:200] + "..." if len(html_body) > 200 else html_body,
                           "message_id": msg_id, "timestamp": datetime.now(timezone.utc).isoformat()})
        logger.info("[EMAIL-CONSOLE] To: %s | Subject: %s | ID: %s", to_email, subject, msg_id)
        return {"success": True, "message_id": msg_id, "provider": "console"}

    def get_sent(self):
        return list(self._sent)

    def clear(self):
        self._sent.clear()


class SMTPEmailProvider(EmailProvider):
    """Real SMTP provider for production delivery."""
    def __init__(self, host=None, port=None, username=None, password=None, use_tls=None, from_email=None, from_name=None):
        self.host = host or os.getenv("EOS_SMTP_HOST", "smtp.gmail.com")
        self.port = int(port or os.getenv("EOS_SMTP_PORT", "587"))
        self.username = username if username is not None else os.getenv("EOS_SMTP_USERNAME", "")
        self.password = password if password is not None else os.getenv("EOS_SMTP_PASSWORD", "")
        self.use_tls = use_tls if use_tls is not None else os.getenv("EOS_SMTP_TLS", "true").lower() == "true"
        self.from_email = from_email or os.getenv("EOS_FROM_EMAIL") or self.username
        self.from_name = from_name or os.getenv("EOS_FROM_NAME", "EOS Platform")

    def send(self, to_email, subject, html_body, text_body=None, from_email=None, from_name=None):
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.utils import formataddr, make_msgid

        if not self.host or not self.from_email:
            return {"success": False, "message_id": None, "error": "SMTP sender configuration is incomplete", "provider": "smtp"}
        from_email = from_email or self.from_email
        from_name = from_name or self.from_name
        domain = from_email.split("@", 1)[1] if "@" in from_email else None
        msg_id = make_msgid(domain=domain)
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = formataddr((from_name, from_email))
            msg["To"] = to_email
            msg["Subject"] = subject
            msg["Message-ID"] = msg_id
            msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
            if text_body:
                msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))
            with smtplib.SMTP(self.host, self.port, timeout=int(os.getenv("EOS_SMTP_TIMEOUT", "20"))) as server:
                server.ehlo()
                if self.use_tls:
                    server.starttls()
                    server.ehlo()
                if self.username:
                    if not self.password:
                        raise RuntimeError("EOS_SMTP_PASSWORD is required when EOS_SMTP_USERNAME is set")
                    server.login(self.username, self.password)
                server.sendmail(from_email, [to_email], msg.as_string())
            logger.info("[EMAIL-SMTP] Sent to %s | Subject: %s | ID: %s", to_email, subject, msg_id)
            return {"success": True, "message_id": msg_id, "provider": "smtp"}
        except Exception as exc:
            logger.error("[EMAIL-SMTP] Delivery failed to %s: %s", to_email, type(exc).__name__)
            return {"success": False, "message_id": None, "error": str(exc), "provider": "smtp"}


class EmailTemplateEngine:
    @staticmethod
    def verification_email(verification_url: str, first_name: str = "User") -> dict:
        return {"subject": "Verify your EOS account",
                "html": f"<div style='font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px'><h2>Welcome to EOS, {first_name}!</h2><p>Please verify your email address to activate your account.</p><p><a href='{verification_url}'>Verify Email</a></p><p style='color:#666;font-size:12px'>This link expires in 24 hours.</p></div>",
                "text": f"Welcome to EOS! Verify your email: {verification_url}"}

    @staticmethod
    def password_reset_email(reset_url: str, first_name: str = "User") -> dict:
        return {"subject": "Reset your EOS password",
                "html": f"<div style='font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px'><h2>Password Reset Request</h2><p>Hello {first_name}, we received a request to reset your password.</p><p><a href='{reset_url}'>Reset Password</a></p><p style='color:#666;font-size:12px'>This link expires in 2 hours. If you didn't request this, ignore this email.</p></div>",
                "text": f"Reset your EOS password: {reset_url}"}

    @staticmethod
    def invitation_email(invitation_url: str, first_name: str, company_name: str = "your organization") -> dict:
        return {"subject": f"You're invited to {company_name} on EOS",
                "html": f"<div style='font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px'><h2>You're invited, {first_name}!</h2><p>You have been invited to join <strong>{company_name}</strong> on EOS.</p><p><a href='{invitation_url}' style='background:#2563eb;color:white;padding:12px 24px;text-decoration:none;border-radius:6px'>Accept Invitation</a></p><p style='color:#666;font-size:12px'>This invitation expires in 72 hours. If you did not expect this invitation, you can ignore it.</p></div>",
                "text": f"You're invited to {company_name} on EOS. Accept your invitation: {invitation_url}"}

    @staticmethod
    def welcome_email(first_name="User", company_name="Your Company") -> dict:
        frontend_url = os.getenv("EOS_FRONTEND_URL", "http://localhost:3000").rstrip("/")
        return {"subject": f"Welcome to EOS, {first_name}!",
                "html": f"<div style='font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px'><h2>Account Activated!</h2><p>Hello {first_name}, your account for <strong>{company_name}</strong> is now active.</p><p><a href='{frontend_url}/dashboard'>Go to Dashboard</a></p></div>",
                "text": f"Welcome to EOS! Your account for {company_name} is now active: {frontend_url}/dashboard"}


def get_email_provider() -> EmailProvider:
    configured = os.getenv("EOS_EMAIL_PROVIDER")
    provider = configured.lower() if configured else ("smtp" if os.getenv("EOS_AUTH_MODE", "test").lower() == "production" else "console")
    if provider == "smtp":
        return SMTPEmailProvider()
    if provider == "console":
        return ConsoleEmailProvider()
    raise RuntimeError(f"Unsupported EOS_EMAIL_PROVIDER: {provider}")


_provider_instance = None


def get_email_service() -> EmailProvider:
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = get_email_provider()
    return _provider_instance
