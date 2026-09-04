"""
P61 Email Adapter — Provider-agnostic email sending.
Console provider (dev/test) + SMTP provider (production).

Providers registered via EOS_EMAIL_PROVIDER env var.
Default: console (safe fallback).
"""
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone

logger = logging.getLogger("eos.email")


class EmailProvider(ABC):
    @abstractmethod
    def send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ) -> dict:
        """Send an email. Returns {success, message_id, error}."""
        ...


class ConsoleEmailProvider(EmailProvider):
    """Logs emails to console/file. For dev, test, staging."""

    def __init__(self):
        self._sent = []

    def send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ) -> dict:
        from_name = from_name or "EOS Platform"
        from_email = from_email or "noreply@eos-platform.com"
        msg_id = f"console_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{hash(to_email) % 10000}"

        entry = {
            "to": to_email,
            "from": f"{from_name} <{from_email}>",
            "subject": subject,
            "html": html_body[:200] + "..." if len(html_body) > 200 else html_body,
            "message_id": msg_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._sent.append(entry)

        logger.info(
            f"[EMAIL-CONSOLE] To: {to_email} | Subject: {subject} | ID: {msg_id}"
        )
        return {"success": True, "message_id": msg_id, "provider": "console"}

    def get_sent(self):
        return list(self._sent)

    def clear(self):
        self._sent.clear()


class SMTPEmailProvider(EmailProvider):
    """Real SMTP email provider for production."""

    def __init__(
        self,
        host: str | None = None,
        port: int = 587,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        from_email: str | None = None,
        from_name: str | None = None,
    ):
        self.host = host or os.getenv("EOS_SMTP_HOST", "smtp.gmail.com")
        self.port = port or int(os.getenv("EOS_SMTP_PORT", "587"))
        self.username = username or os.getenv("EOS_SMTP_USERNAME", "")
        self.password = password or os.getenv("EOS_SMTP_PASSWORD", "")
        self.use_tls = use_tls
        self.from_email = from_email or os.getenv("EOS_FROM_EMAIL", "noreply@eos-platform.com")
        self.from_name = from_name or os.getenv("EOS_FROM_NAME", "EOS Platform")

    def send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ) -> dict:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        from_email = from_email or self.from_email
        from_name = from_name or self.from_name
        msg_id = f"smtp_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{hash(to_email) % 10000}"

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            msg["Message-ID"] = f"<{msg_id}@eos-platform.com>"
            msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

            if text_body:
                msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(from_email, [to_email], msg.as_string())

            logger.info(f"[EMAIL-SMTP] Sent to {to_email} | Subject: {subject} | ID: {msg_id}")
            return {"success": True, "message_id": msg_id, "provider": "smtp"}

        except Exception as e:
            logger.error(f"[EMAIL-SMTP] Failed to {to_email}: {e}")
            return {"success": False, "message_id": None, "error": str(e), "provider": "smtp"}


class EmailTemplateEngine:
    """Pre-built email templates for common flows."""

    @staticmethod
    def verification_email(verification_url: str, first_name: str = "User") -> dict:
        return {
            "subject": "Verify your EOS account",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2563eb;">Welcome to EOS, {first_name}!</h2>
                <p>Thank you for registering. Please verify your email address to activate your account.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}"
                       style="background: #2563eb; color: white; padding: 12px 30px;
                              text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Verify Email
                    </a>
                </div>
                <p style="color: #666; font-size: 12px;">
                    This link expires in 24 hours. If you didn't register, ignore this email.
                </p>
            </div>
            """,
            "text": f"Welcome to EOS! Verify your email: {verification_url}",
        }

    @staticmethod
    def password_reset_email(reset_url: str, first_name: str = "User") -> dict:
        return {
            "subject": "Reset your EOS password",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #dc2626;">Password Reset Request</h2>
                <p>Hello {first_name}, we received a request to reset your password.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}"
                       style="background: #dc2626; color: white; padding: 12px 30px;
                              text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Reset Password
                    </a>
                </div>
                <p style="color: #666; font-size: 12px;">
                    This link expires in 1 hour. If you didn't request this, ignore this email.
                </p>
            </div>
            """,
            "text": f"Reset your password: {reset_url}",
        }

    @staticmethod
    def welcome_email(first_name: str = "User", company_name: str = "Your Company") -> dict:
        return {
            "subject": f"Welcome to EOS, {first_name}!",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #16a34a;">Account Activated!</h2>
                <p>Hello {first_name}, your account for <strong>{company_name}</strong> is now active.</p>
                <p>You can now:</p>
                <ul>
                    <li>Create and manage your ERP entities</li>
                    <li>Use the AI Business Composer</li>
                    <li>Install industry templates from the Marketplace</li>
                </ul>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://localhost:3000/dashboard"
                       style="background: #16a34a; color: white; padding: 12px 30px;
                              text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Go to Dashboard
                    </a>
                </div>
            </div>
            """,
            "text": f"Welcome to EOS! Your account for {company_name} is now active.",
        }


def get_email_provider() -> EmailProvider:
    """Factory: returns configured email provider."""
    provider = os.getenv("EOS_EMAIL_PROVIDER", "console").lower()

    if provider == "smtp":
        return SMTPEmailProvider()
    else:
        return ConsoleEmailProvider()


_provider_instance = None


def get_email_service() -> EmailProvider:
    """Singleton email provider."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = get_email_provider()
    return _provider_instance
