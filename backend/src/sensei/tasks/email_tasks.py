"""
Celery tasks for background email delivery (#466).

Moves email sending out of the request path into a background task
so API responses are not blocked by SMTP round-trips and retries.
"""

from __future__ import annotations

import logging
from typing import Optional

from sensei.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="sensei.tasks.email_tasks.send_email_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def send_email_task(
    self,
    to: list[str],
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
    reply_to: Optional[str] = None,
    cc: Optional[list[str]] = None,
    bcc: Optional[list[str]] = None,
) -> dict:
    """
    Send an email in the background via Celery.

    All parameters are JSON-serializable primitives so the message
    can travel through the broker without custom serializers.

    Args:
        to: List of recipient email addresses.
        subject: Email subject line.
        body_html: HTML body content.
        body_text: Optional plain-text body.
        reply_to: Optional reply-to address.
        cc: Optional CC recipients.
        bcc: Optional BCC recipients.

    Returns:
        dict with status and metadata on success.

    Raises:
        self.retry: Re-queues on transient SMTP failures.
    """
    import asyncio
    from sensei.services.core.email_service import EmailMessage, EmailService

    message = EmailMessage(
        to=to,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        reply_to=reply_to,
        cc=cc,
        bcc=bcc,
    )
    service = EmailService()

    try:
        # EmailService.send_email is async — run it in a fresh loop
        # since Celery workers are synchronous.
        success = asyncio.run(service.send_email(message, max_retries=1))
        if not success:
            raise RuntimeError("EmailService.send_email returned False")
        logger.info("Email sent successfully to %s: %s", to, subject)
        return {"status": "sent", "to": to, "subject": subject}
    except Exception as exc:
        logger.exception(
            "Email send failed (attempt %d/%d), retrying via Celery",
            self.request.retries + 1,
            self.max_retries + 1,
        )
        raise self.retry(exc=exc)
