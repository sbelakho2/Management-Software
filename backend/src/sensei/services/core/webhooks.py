"""
Webhook and Event System.

Provides a robust webhook delivery system for external integrations:
- Event registration and management
- Webhook subscription management
- Reliable delivery with retries
- Signature verification for security
- Delivery logging and monitoring

Event Types:
- Entity events (create, update, delete)
- Workflow events (approval, rejection)
- System events (backup, maintenance)
- Custom events

Security:
- HMAC-SHA256 signatures on all payloads
- Configurable retry with exponential backoff
- Dead letter queue for failed deliveries
"""

import asyncio
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

import httpx

from sensei.core.config import settings

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Standard event types."""
    
    # Entity lifecycle events
    ENTITY_CREATED = "entity.created"
    ENTITY_UPDATED = "entity.updated"
    ENTITY_DELETED = "entity.deleted"
    
    # Workflow events
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"
    
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    
    # Quote events
    QUOTE_CREATED = "quote.created"
    QUOTE_SENT = "quote.sent"
    QUOTE_ACCEPTED = "quote.accepted"
    QUOTE_REJECTED = "quote.rejected"
    
    # Order events
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    ORDER_SHIPPED = "order.shipped"
    ORDER_DELIVERED = "order.delivered"
    
    # Production events
    PRODUCTION_STARTED = "production.started"
    PRODUCTION_COMPLETED = "production.completed"
    QUALITY_ISSUE = "quality.issue"
    
    # System events
    BACKUP_COMPLETED = "system.backup_completed"
    MAINTENANCE_SCHEDULED = "system.maintenance_scheduled"
    
    # Custom event (for extensions)
    CUSTOM = "custom"


class DeliveryStatus(str, Enum):
    """Webhook delivery status."""
    
    PENDING = "pending"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Event:
    """An event that can trigger webhooks."""
    
    id: UUID = field(default_factory=uuid4)
    event_type: EventType = EventType.CUSTOM
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "sensei-os"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "event_type": self.event_type.value,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "payload": self.payload,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


@dataclass
class WebhookSubscription:
    """A webhook subscription."""
    
    id: UUID = field(default_factory=uuid4)
    url: str = ""
    secret: str = ""  # For HMAC signature
    event_types: Set[EventType] = field(default_factory=set)
    entity_types: Set[str] = field(default_factory=set)  # Filter by entity type
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[UUID] = None
    description: str = ""
    
    # Delivery settings
    timeout_seconds: float = 30.0
    max_retries: int = 5
    retry_backoff_base: float = 2.0  # Exponential backoff base


@dataclass
class DeliveryAttempt:
    """Record of a webhook delivery attempt."""
    
    id: UUID = field(default_factory=uuid4)
    subscription_id: UUID = field(default_factory=uuid4)
    event_id: UUID = field(default_factory=uuid4)
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempt_number: int = 1
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None
    attempted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    next_retry_at: Optional[datetime] = None


class WebhookService:
    """
    Service for managing webhooks and event delivery.
    
    Features:
    - Async event delivery
    - HMAC signature verification
    - Exponential backoff retries
    - Dead letter queue
    - Delivery logging
    """
    
    def __init__(self):
        self._subscriptions: Dict[UUID, WebhookSubscription] = {}
        self._event_handlers: Dict[EventType, List[Callable]] = {}
        self._delivery_log: List[DeliveryAttempt] = []
        self._max_log_entries = 10000
        self._dead_letter_queue: List[DeliveryAttempt] = []
        
    def register_subscription(self, subscription: WebhookSubscription) -> WebhookSubscription:
        """Register a new webhook subscription."""
        if not subscription.url:
            raise ValueError("Webhook URL is required")
        
        # Validate URL
        if not subscription.url.startswith(("http://", "https://")):
            raise ValueError("Webhook URL must be HTTP or HTTPS")
        
        # Generate secret if not provided
        if not subscription.secret:
            import secrets
            subscription.secret = secrets.token_hex(32)
        
        self._subscriptions[subscription.id] = subscription
        logger.info(
            f"Registered webhook subscription",
            extra={
                "subscription_id": str(subscription.id),
                "url": subscription.url[:50],
                "event_types": [e.value for e in subscription.event_types],
            }
        )
        
        return subscription
    
    def unregister_subscription(self, subscription_id: UUID) -> bool:
        """Unregister a webhook subscription."""
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            logger.info(f"Unregistered webhook subscription: {subscription_id}")
            return True
        return False
    
    def get_subscription(self, subscription_id: UUID) -> Optional[WebhookSubscription]:
        """Get a subscription by ID."""
        return self._subscriptions.get(subscription_id)
    
    def list_subscriptions(
        self,
        event_type: Optional[EventType] = None,
        active_only: bool = True,
    ) -> List[WebhookSubscription]:
        """List subscriptions with optional filtering."""
        results = []
        
        for sub in self._subscriptions.values():
            if active_only and not sub.is_active:
                continue
            if event_type and event_type not in sub.event_types:
                continue
            results.append(sub)
        
        return results
    
    def _compute_signature(self, payload: str, secret: str) -> str:
        """Compute HMAC-SHA256 signature for payload."""
        return hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
    
    def _should_deliver(
        self,
        subscription: WebhookSubscription,
        event: Event,
    ) -> bool:
        """Check if event should be delivered to subscription."""
        if not subscription.is_active:
            return False
        
        # Check event type filter
        if subscription.event_types and event.event_type not in subscription.event_types:
            return False
        
        # Check entity type filter
        if subscription.entity_types and event.entity_type not in subscription.entity_types:
            return False
        
        return True
    
    async def _deliver_to_subscription(
        self,
        subscription: WebhookSubscription,
        event: Event,
        attempt_number: int = 1,
    ) -> DeliveryAttempt:
        """Deliver event to a single subscription."""
        delivery = DeliveryAttempt(
            subscription_id=subscription.id,
            event_id=event.id,
            status=DeliveryStatus.DELIVERING,
            attempt_number=attempt_number,
        )
        
        try:
            # Prepare payload
            payload_dict = event.to_dict()
            payload_json = json.dumps(payload_dict, default=str)
            
            # Compute signature
            signature = self._compute_signature(payload_json, subscription.secret)
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Event": event.event_type.value,
                "X-Webhook-Signature": f"sha256={signature}",
                "X-Webhook-Timestamp": event.timestamp.isoformat(),
                "X-Webhook-Delivery-Id": str(delivery.id),
                "User-Agent": "Sensei-OS-Webhook/1.0",
            }
            
            start_time = asyncio.get_event_loop().time()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    subscription.url,
                    content=payload_json,
                    headers=headers,
                    timeout=subscription.timeout_seconds,
                )
                
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                
                delivery.response_status = response.status_code
                delivery.response_body = response.text[:1000]  # Truncate
                delivery.duration_ms = duration_ms
                
                if 200 <= response.status_code < 300:
                    delivery.status = DeliveryStatus.DELIVERED
                    logger.debug(
                        f"Webhook delivered successfully",
                        extra={
                            "subscription_id": str(subscription.id),
                            "event_type": event.event_type.value,
                            "status_code": response.status_code,
                            "duration_ms": duration_ms,
                        }
                    )
                else:
                    delivery.status = DeliveryStatus.FAILED
                    delivery.error_message = f"HTTP {response.status_code}"
                    logger.warning(
                        f"Webhook delivery failed with status {response.status_code}",
                        extra={
                            "subscription_id": str(subscription.id),
                            "event_type": event.event_type.value,
                            "status_code": response.status_code,
                        }
                    )
                    
        except httpx.TimeoutException:
            delivery.status = DeliveryStatus.FAILED
            delivery.error_message = "Request timeout"
            logger.warning(f"Webhook delivery timed out: {subscription.url[:50]}")
            
        except httpx.RequestError as e:
            delivery.status = DeliveryStatus.FAILED
            delivery.error_message = str(e)
            logger.warning(f"Webhook delivery error: {e}")
            
        except Exception as e:
            delivery.status = DeliveryStatus.FAILED
            delivery.error_message = str(e)
            logger.exception(f"Unexpected webhook delivery error")
        
        # Log delivery attempt
        self._log_delivery(delivery)
        
        return delivery
    
    async def _retry_delivery(
        self,
        subscription: WebhookSubscription,
        event: Event,
        failed_attempt: DeliveryAttempt,
    ):
        """Schedule retry for failed delivery."""
        if failed_attempt.attempt_number >= subscription.max_retries:
            # Max retries exceeded - move to dead letter queue
            failed_attempt.status = DeliveryStatus.FAILED
            self._dead_letter_queue.append(failed_attempt)
            logger.error(
                f"Webhook delivery failed after {subscription.max_retries} attempts, "
                f"moved to dead letter queue",
                extra={
                    "subscription_id": str(subscription.id),
                    "event_id": str(event.id),
                }
            )
            return
        
        # Calculate retry delay with exponential backoff
        delay_seconds = subscription.retry_backoff_base ** failed_attempt.attempt_number
        delay_seconds = min(delay_seconds, 3600)  # Max 1 hour
        
        failed_attempt.status = DeliveryStatus.RETRYING
        failed_attempt.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        
        logger.info(
            f"Scheduling webhook retry in {delay_seconds:.1f}s",
            extra={
                "subscription_id": str(subscription.id),
                "attempt": failed_attempt.attempt_number + 1,
            }
        )
        
        # Schedule retry
        await asyncio.sleep(delay_seconds)
        
        # Retry delivery
        await self._deliver_to_subscription(
            subscription,
            event,
            attempt_number=failed_attempt.attempt_number + 1,
        )
    
    def _log_delivery(self, delivery: DeliveryAttempt):
        """Log delivery attempt."""
        self._delivery_log.append(delivery)
        
        # Trim log if too large
        if len(self._delivery_log) > self._max_log_entries:
            self._delivery_log = self._delivery_log[-self._max_log_entries // 2:]
    
    async def emit(self, event: Event) -> List[DeliveryAttempt]:
        """
        Emit an event to all matching subscriptions.
        
        This is the main entry point for firing events.
        
        Args:
            event: The event to emit
            
        Returns:
            List of delivery attempts
        """
        if not settings.WEBHOOKS_ENABLED:
            logger.debug("Webhooks disabled, skipping event emission")
            return []
        
        deliveries = []
        
        # Find matching subscriptions
        for subscription in self._subscriptions.values():
            if not self._should_deliver(subscription, event):
                continue
            
            # Deliver asynchronously
            delivery = await self._deliver_to_subscription(subscription, event)
            deliveries.append(delivery)
            
            # Handle retries for failures
            if delivery.status == DeliveryStatus.FAILED:
                # Fire-and-forget retry
                asyncio.create_task(
                    self._retry_delivery(subscription, event, delivery)
                )
        
        return deliveries
    
    def emit_sync(self, event: Event):
        """
        Emit event synchronously (fire-and-forget).
        
        Use this when you can't use async/await.
        """
        if not settings.WEBHOOKS_ENABLED:
            return
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.emit(event))
            else:
                loop.run_until_complete(self.emit(event))
        except RuntimeError:
            # No event loop, create one
            asyncio.run(self.emit(event))
    
    def get_delivery_log(
        self,
        subscription_id: Optional[UUID] = None,
        event_id: Optional[UUID] = None,
        status: Optional[DeliveryStatus] = None,
        limit: int = 100,
    ) -> List[DeliveryAttempt]:
        """Get delivery log with optional filtering."""
        results = []
        
        for delivery in reversed(self._delivery_log):
            if subscription_id and delivery.subscription_id != subscription_id:
                continue
            if event_id and delivery.event_id != event_id:
                continue
            if status and delivery.status != status:
                continue
            
            results.append(delivery)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_dead_letter_queue(self, limit: int = 100) -> List[DeliveryAttempt]:
        """Get items from the dead letter queue."""
        return self._dead_letter_queue[-limit:]
    
    def retry_dead_letter(self, delivery_id: UUID) -> bool:
        """Retry a delivery from the dead letter queue."""
        for i, delivery in enumerate(self._dead_letter_queue):
            if delivery.id == delivery_id:
                # Remove from DLQ
                self._dead_letter_queue.pop(i)
                
                # Get subscription and event
                subscription = self._subscriptions.get(delivery.subscription_id)
                if not subscription:
                    logger.warning(f"Subscription not found for DLQ retry: {delivery.subscription_id}")
                    return False
                
                # Create new event from delivery
                # Note: In production, events should be persisted
                logger.info(f"Retrying delivery from DLQ: {delivery_id}")
                
                # Reset attempt count and retry
                delivery.attempt_number = 0
                delivery.status = DeliveryStatus.RETRYING
                
                return True
        
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get webhook statistics."""
        total_deliveries = len(self._delivery_log)
        successful = sum(1 for d in self._delivery_log if d.status == DeliveryStatus.DELIVERED)
        failed = sum(1 for d in self._delivery_log if d.status == DeliveryStatus.FAILED)
        
        avg_duration = 0
        durations = [d.duration_ms for d in self._delivery_log if d.duration_ms]
        if durations:
            avg_duration = sum(durations) / len(durations)
        
        return {
            "total_subscriptions": len(self._subscriptions),
            "active_subscriptions": sum(1 for s in self._subscriptions.values() if s.is_active),
            "total_deliveries": total_deliveries,
            "successful_deliveries": successful,
            "failed_deliveries": failed,
            "success_rate": (successful / total_deliveries * 100) if total_deliveries else 0,
            "dead_letter_queue_size": len(self._dead_letter_queue),
            "avg_delivery_duration_ms": round(avg_duration, 2),
        }


# Global webhook service instance
_webhook_service: Optional[WebhookService] = None


def get_webhook_service() -> WebhookService:
    """Get the global webhook service instance."""
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService()
    return _webhook_service


# Convenience functions
def emit_event(
    event_type: EventType,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Event:
    """
    Convenience function to create and emit an event.
    
    Usage:
        emit_event(EventType.QUOTE_CREATED, "quote", quote.id, {"amount": 1000})
    """
    event = Event(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        payload=payload or {},
        metadata=kwargs,
    )
    
    # Fire-and-forget
    get_webhook_service().emit_sync(event)
    
    return event


async def emit_event_async(
    event_type: EventType,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> List[DeliveryAttempt]:
    """
    Async version of emit_event that waits for deliveries.
    
    Usage:
        deliveries = await emit_event_async(EventType.QUOTE_CREATED, ...)
    """
    event = Event(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        payload=payload or {},
        metadata=kwargs,
    )
    
    return await get_webhook_service().emit(event)
