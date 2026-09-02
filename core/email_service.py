"""
EOS Email Service — SMTP Integration
Supports: SendGrid, Gmail SMTP, custom SMTP
"""
import os
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@eos-saas.com")
        self.from_name = os.getenv("FROM_NAME", "EOS Platform")
        self.enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"

    def send(self, to_email, subject, html_body, attachments=None):
        if not self.enabled:
            return {"success": True, "mode": "dry_run", "message": "Email disabled (dry run)"}
        try:
            msg = MIMEMultipart()
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html"))
            if attachments:
                for filename, content in attachments:
                    att = MIMEApplication(content)
                    att.add_header("Content-Disposition", "attachment", filename=filename)
                    msg.attach(att)
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                if self.smtp_user and self.smtp_pass:
                    server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            return {"success": True, "message": f"Email sent to {to_email}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_invitation(self, to_email, tenant_name, role, invited_by):
        html = f"""
        <div style="font-family: Arial; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1890ff;">You're Invited to EOS Platform</h2>
            <p>You've been invited by <strong>{invited_by}</strong> to join <strong>{tenant_name}</strong> as <strong>{role}</strong>.</p>
            <a href="https://eos-saas.com/accept-invitation" style="background: #1890ff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">Accept Invitation</a>
            <p style="color: #666; margin-top: 20px;">If you didn't expect this invitation, you can ignore this email.</p>
        </div>
        """
        return self.send(to_email, f"Invitation to {tenant_name} — EOS Platform", html)

    def send_password_reset(self, to_email, reset_token, user_name):
        html = f"""
        <div style="font-family: Arial; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #ff4d4f;">Password Reset Request</h2>
            <p>Hi {user_name},</p>
            <p>You requested a password reset. Click below to reset your password:</p>
            <a href="https://eos-saas.com/reset-password?token={reset_token}" style="background: #ff4d4f; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">Reset Password</a>
            <p style="color: #666; margin-top: 20px;">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
        </div>
        """
        return self.send(to_email, "Password Reset — EOS Platform", html)

    def send_notification(self, to_email, title, message, action_url=None):
        action_html = ""
        if action_url:
            action_html = f'<a href="{action_url}" style="background: #1890ff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">View Details</a>'
        html = f"""
        <div style="font-family: Arial; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1890ff;">{title}</h2>
            <p>{message}</p>
            {action_html}
        </div>
        """
        return self.send(to_email, title, html)
