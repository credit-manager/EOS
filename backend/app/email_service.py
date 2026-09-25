"""Email service — SendGrid integration."""
import logging
from typing import Any

import httpx

from ..config import get_settings

logger = logging.getLogger("2to-eos.email")

SENDGRID_API = "https://api.sendgrid.com/v3/mail/send"


async def send_email(
    to: str,
    subject: str,
    html_content: str,
    from_email: str | None = None,
    from_name: str = "2TO EOS",
    reply_to: str | None = None,
    categories: list[str] | None = None,
    custom_args: dict[str, str] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.sendgrid_api_key:
        logger.warning("SendGrid API key not configured — email not sent")
        return {"status": "skipped", "reason": "no_api_key"}

    sender = from_email or settings.email_from_address
    payload: dict[str, Any] = {
        "personalizations": [{
            "to": [{"email": to}],
            "subject": subject,
        }],
        "from": {"email": sender, "name": from_name},
        "content": [{"type": "text/html", "value": html_content}],
    }
    if reply_to:
        payload["reply_to"] = {"email": reply_to}
    if categories:
        payload["categories"] = categories
    if custom_args:
        payload["personalizations"][0]["custom_args"] = custom_args

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                SENDGRID_API,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.sendgrid_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            if resp.status_code in (200, 202):
                logger.info("Email sent to %s: %s", to, subject)
                return {"status": "sent", "to": to, "subject": subject}
            else:
                logger.error("SendGrid error %d: %s", resp.status_code, resp.text[:200])
                return {"status": "error", "code": resp.status_code, "detail": resp.text[:200]}
        except Exception as e:
            logger.error("Email send failed: %s", e)
            return {"status": "error", "detail": str(e)}


async def send_welcome_email(to: str, tenant_name: str) -> dict:
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1a56db;">Welcome to 2TO EOS!</h2>
        <p>Your organization <strong>{tenant_name}</strong> has been created.</p>
        <p>You can now log in and start building your business operating system.</p>
        <a href="https://app.2to-eos.com/login" style="display: inline-block; padding: 12px 24px; background: #1a56db; color: white; text-decoration: none; border-radius: 6px; margin-top: 16px;">Log In</a>
        <p style="color: #6b7280; font-size: 12px; margin-top: 24px;">If you didn't create this account, please ignore this email.</p>
    </div>
    """
    return await send_email(to, "Welcome to 2TO EOS", html, categories=["welcome", "onboarding"])


async def send_invoice_email(to: str, invoice_id: str, amount: float, currency: str = "USD") -> dict:
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1a56db;">Invoice Available</h2>
        <p>A new invoice <strong>{invoice_id}</strong> for <strong>${amount:,.2f} {currency}</strong> is ready.</p>
        <a href="https://app.2to-eos.com/billing" style="display: inline-block; padding: 12px 24px; background: #1a56db; color: white; text-decoration: none; border-radius: 6px; margin-top: 16px;">View Invoice</a>
    </div>
    """
    return await send_email(to, f"Invoice {invoice_id} — ${amount:,.2f}", html, categories=["billing", "invoice"])


async def send_password_reset_email(to: str, reset_token: str) -> dict:
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1a56db;">Password Reset</h2>
        <p>You requested a password reset. Click the link below to set a new password.</p>
        <a href="https://app.2to-eos.com/reset-password?token={reset_token}" style="display: inline-block; padding: 12px 24px; background: #1a56db; color: white; text-decoration: none; border-radius: 6px; margin-top: 16px;">Reset Password</a>
        <p style="color: #6b7280; font-size: 12px; margin-top: 24px;">This link expires in 1 hour. If you didn't request this, please ignore this email.</p>
    </div>
    """
    return await send_email(to, "Password Reset Request", html, categories=["auth", "password_reset"])
