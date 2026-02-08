"""
Email Service for Sensei OS.

Production-ready email sending with SMTP support, templating,
retry logic, and async operation.
"""

import asyncio
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import aiosmtplib
import structlog

try:
    from jinja2 import Environment, BaseLoader, select_autoescape
    _JINJA2_AVAILABLE = True
except ImportError:  # graceful fallback to str.format()
    _JINJA2_AVAILABLE = False

from sensei.core.config import settings


logger = structlog.get_logger(__name__)


# ─── Jinja2 template environment (#381, #467) ─────────────────────────────────

def _make_jinja_env() -> Any:
    """Create a sandboxed Jinja2 environment for email rendering."""
    if not _JINJA2_AVAILABLE:
        return None
    return Environment(
        loader=BaseLoader(),
        autoescape=select_autoescape(default_for_string=True, default=True),
        trim_blocks=True,
        lstrip_blocks=True,
    )


_jinja_env = _make_jinja_env()


def _render_template(template_str: str, context: Dict[str, Any]) -> str:
    """Render a template string with the given context.

    Uses Jinja2 if available; falls back to Python ``str.format_map()``
    for backward compatibility.
    """
    if _jinja_env is not None:
        tmpl = _jinja_env.from_string(template_str)
        return tmpl.render(**context)
    # Fallback: convert Jinja2 {{var}} to {var} for str.format_map
    return template_str.replace("{{", "{").replace("}}", "}").format_map(context)


class EmailType(str, Enum):
    """Types of system emails."""
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"
    WELCOME = "welcome"
    NOTIFICATION = "notification"
    ALERT = "alert"
    REPORT = "report"


@dataclass
class EmailMessage:
    """Email message data class."""
    to: List[str]
    subject: str
    body_html: str
    body_text: Optional[str] = None
    reply_to: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None


class EmailService:
    """Production email service with SMTP support."""
    
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_from_email: Optional[str] = None,
        smtp_from_name: Optional[str] = None,
        use_tls: Optional[bool] = None,
        use_ssl: Optional[bool] = None,
        enabled: Optional[bool] = None,
    ):
        """
        Initialize email service.
        
        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            smtp_from_email: From email address
            smtp_from_name: From display name
            use_tls: Use STARTTLS
            use_ssl: Use SSL/TLS
            enabled: Whether email sending is enabled
        """
        self.smtp_host = smtp_host or settings.SMTP_HOST
        self.smtp_port = smtp_port or settings.SMTP_PORT
        self.smtp_user = smtp_user or settings.SMTP_USER
        self.smtp_password = smtp_password or settings.SMTP_PASSWORD
        self.smtp_from_email = smtp_from_email or settings.SMTP_FROM_EMAIL
        self.smtp_from_name = smtp_from_name or settings.SMTP_FROM_NAME
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_TLS
        self.use_ssl = use_ssl if use_ssl is not None else settings.SMTP_SSL
        self.enabled = enabled if enabled is not None else settings.EMAIL_ENABLED
        
        self._templates: Dict[EmailType, Dict[str, str]] = self._load_templates()
    
    def _load_templates(self) -> Dict[EmailType, Dict[str, str]]:
        """Load email templates."""
        return {
            EmailType.PASSWORD_RESET: {
                "subject": "Reset Your Sensei OS Password",
                "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password Reset</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">Sensei OS</h1>
    </div>
    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
        <h2 style="color: #333; margin-top: 0;">Reset Your Password</h2>
        <p>You requested to reset your password. Click the button below to create a new password:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ reset_link }}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a>
        </div>
        <p style="color: #666; font-size: 14px;">This link will expire in 1 hour.</p>
        <p style="color: #666; font-size: 14px;">If you didn't request this reset, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
        <p style="color: #999; font-size: 12px;">This is an automated message from Sensei OS. Please do not reply to this email.</p>
    </div>
</body>
</html>
""",
                "text": """
Sensei OS - Password Reset

You requested to reset your password. Visit the link below to create a new password:

{{ reset_link }}

This link will expire in 1 hour.

If you didn't request this reset, you can safely ignore this email.

--
This is an automated message from Sensei OS.
""",
            },
            EmailType.EMAIL_VERIFICATION: {
                "subject": "Verify Your Sensei OS Email",
                "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Verification</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">Sensei OS</h1>
    </div>
    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
        <h2 style="color: #333; margin-top: 0;">Verify Your Email</h2>
        <p>Please verify your email address by clicking the button below:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ verify_link }}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Verify Email</a>
        </div>
        <p style="color: #666; font-size: 14px;">This link will expire in 24 hours.</p>
        <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
        <p style="color: #999; font-size: 12px;">This is an automated message from Sensei OS. Please do not reply to this email.</p>
    </div>
</body>
</html>
""",
                "text": """
Sensei OS - Email Verification

Please verify your email address by visiting the link below:

{{ verify_link }}

This link will expire in 24 hours.

--
This is an automated message from Sensei OS.
""",
            },
            EmailType.WELCOME: {
                "subject": "Welcome to Sensei OS",
                "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">Welcome to Sensei OS!</h1>
    </div>
    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
        <h2 style="color: #333; margin-top: 0;">Hello {{ user_name }}!</h2>
        <p>Your account has been created successfully. You can now log in and start using Sensei OS.</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ login_link }}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Go to Login</a>
        </div>
        <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
        <p style="color: #999; font-size: 12px;">This is an automated message from Sensei OS. Please do not reply to this email.</p>
    </div>
</body>
</html>
""",
                "text": """
Welcome to Sensei OS!

Hello {{ user_name }}!

Your account has been created successfully. You can now log in and start using Sensei OS.

Login: {{ login_link }}

--
This is an automated message from Sensei OS.
""",
            },
        }
    
    async def send_email(
        self,
        message: EmailMessage,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> bool:
        """
        Send an email message (inline, blocks until complete).
        
        For fire-and-forget delivery, use ``send_email_bg()`` instead.
        
        Args:
            message: Email message to send
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            True if email was sent successfully
        """
        if not self.enabled:
            logger.warning(
                "Email sending is disabled",
                to=message.to,
                subject=message.subject,
            )
            return False
        
        if not self.smtp_host:
            logger.error("SMTP host not configured")
            return False
        
        # Build the email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.subject
        msg["From"] = f"{self.smtp_from_name} <{self.smtp_from_email}>"
        msg["To"] = ", ".join(message.to)
        
        if message.reply_to:
            msg["Reply-To"] = message.reply_to
        
        if message.cc:
            msg["Cc"] = ", ".join(message.cc)
        
        # CAN-SPAM / GDPR compliance (#199)
        # Gmail/Yahoo require List-Unsubscribe for bulk senders (Feb 2024 guidelines)
        import uuid as _uuid
        msg["Message-ID"] = f"<{_uuid.uuid4()}@{self.smtp_from_email.split('@')[-1] if self.smtp_from_email else 'sensei.local'}>"
        if hasattr(settings, 'FRONTEND_URL') and settings.FRONTEND_URL:
            unsubscribe_url = f"{settings.FRONTEND_URL}/settings/notifications"
            msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
            msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        
        # Attach text and HTML parts
        if message.body_text:
            msg.attach(MIMEText(message.body_text, "plain", "utf-8"))
        msg.attach(MIMEText(message.body_html, "html", "utf-8"))
        
        # Collect all recipients
        all_recipients = list(message.to)
        if message.cc:
            all_recipients.extend(message.cc)
        if message.bcc:
            all_recipients.extend(message.bcc)
        
        # Send with retry logic
        last_error: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                # Create SSL context if needed
                tls_context = None
                if self.use_tls or self.use_ssl:
                    tls_context = ssl.create_default_context()
                
                # Connect and send
                await aiosmtplib.send(
                    msg,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    username=self.smtp_user if self.smtp_user else None,
                    password=self.smtp_password if self.smtp_password else None,
                    start_tls=self.use_tls,
                    use_tls=self.use_ssl,
                    tls_context=tls_context,
                    recipients=all_recipients,
                )
                
                logger.info(
                    "Email sent successfully",
                    to=message.to,
                    subject=message.subject,
                )
                return True
                
            except Exception as e:
                last_error = e
                logger.warning(
                    "Failed to send email",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                )
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter to avoid retry stampede (#198)
                    import random
                    backoff = retry_delay * (2 ** attempt)
                    jitter = random.uniform(0, backoff * 0.5)
                    await asyncio.sleep(backoff + jitter)
        
        logger.error(
            "Failed to send email after all retries",
            to=message.to,
            subject=message.subject,
            error=str(last_error),
        )
        return False
    
    async def send_password_reset(
        self,
        email: str,
        reset_token: str,
    ) -> bool:
        """
        Send password reset email.
        
        Args:
            email: Recipient email address
            reset_token: Password reset token
            
        Returns:
            True if email was sent
        """
        template = self._templates[EmailType.PASSWORD_RESET]
        reset_link = f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"
        
        ctx = {"reset_link": reset_link}
        message = EmailMessage(
            to=[email],
            subject=template["subject"],
            body_html=_render_template(template["html"], ctx),
            body_text=_render_template(template["text"], ctx),
        )
        
        return await self.send_email(message)
    
    def send_email_bg(self, message: EmailMessage) -> None:
        """
        Enqueue email for background delivery via Celery (#466).

        This is fire-and-forget: the email is serialized onto the
        broker and a Celery worker picks it up asynchronously.
        Use this instead of ``send_email()`` when you don't need to
        block on delivery success.
        """
        from sensei.tasks.email_tasks import send_email_task

        send_email_task.delay(
            to=message.to,
            subject=message.subject,
            body_html=message.body_html,
            body_text=message.body_text,
            reply_to=message.reply_to,
            cc=message.cc,
            bcc=message.bcc,
        )
    
    async def send_email_verification(
        self,
        email: str,
        verification_token: str,
    ) -> bool:
        """
        Send email verification email.
        
        Args:
            email: Recipient email address
            verification_token: Email verification token
            
        Returns:
            True if email was sent
        """
        template = self._templates[EmailType.EMAIL_VERIFICATION]
        verify_link = f"{settings.FRONTEND_URL}/auth/verify-email?token={verification_token}"
        
        ctx = {"verify_link": verify_link}
        message = EmailMessage(
            to=[email],
            subject=template["subject"],
            body_html=_render_template(template["html"], ctx),
            body_text=_render_template(template["text"], ctx),
        )
        
        return await self.send_email(message)
    
    async def send_welcome(
        self,
        email: str,
        name: str,
    ) -> bool:
        """
        Send welcome email to new user.
        
        Args:
            email: Recipient email address
            name: User's display name
            
        Returns:
            True if email was sent
        """
        template = self._templates[EmailType.WELCOME]
        login_link = f"{settings.FRONTEND_URL}/login"
        
        ctx = {"user_name": str(name), "login_link": login_link}
        message = EmailMessage(
            to=[email],
            subject=template["subject"],
            body_html=_render_template(template["html"], ctx),
            body_text=_render_template(template["text"], ctx),
        )
        
        return await self.send_email(message)
    
    async def send_notification(
        self,
        email: str,
        subject: str,
        content_html: str,
        content_text: Optional[str] = None,
    ) -> bool:
        """
        Send a generic notification email.
        
        Args:
            email: Recipient email address
            subject: Email subject
            content_html: HTML content
            content_text: Plain text content (optional)
            
        Returns:
            True if email was sent
        """
        message = EmailMessage(
            to=[email],
            subject=subject,
            body_html=content_html,
            body_text=content_text,
        )
        
        return await self.send_email(message)


# Module-level singleton
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


def reset_email_service() -> None:
    """Reset email service singleton (for testing)."""
    global _email_service
    _email_service = None
