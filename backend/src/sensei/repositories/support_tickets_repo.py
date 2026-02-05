"""
Database repository for Support Tickets.

Provides async database access for support inbox persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.service_persistence import (
    SupportTicketDB,
    TicketCommentDB,
    UserFeedbackDB,
    RoutingRuleDB,
    A3LiteRecordDB,
    TicketStatusDB,
    TicketPriorityDB,
)


class SupportTicketsRepository:
    """Repository for support ticket database operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a database session."""
        self._session = session
    
    # --------------------------------------------------------------------------
    # Tickets
    # --------------------------------------------------------------------------
    
    async def create_ticket(
        self,
        subject: str,
        description: str,
        category: str,
        priority: str = "medium",
        reporter_id: UUID | None = None,
        reporter_email: str | None = None,
        related_entity_type: str | None = None,
        related_entity_id: UUID | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
        custom_fields: dict[str, Any] | None = None,
        sla_hours: int | None = None,
    ) -> SupportTicketDB:
        """Create a new support ticket."""
        sla_due_at = None
        if sla_hours:
            sla_due_at = datetime.now(timezone.utc) + timedelta(hours=sla_hours)
        
        ticket = SupportTicketDB(
            subject=subject,
            description=description,
            category=category,
            priority=priority,
            status=TicketStatusDB.OPEN.value,
            reporter_id=reporter_id,
            reporter_email=reporter_email,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            source=source,
            tags=tags,
            custom_fields=custom_fields,
            sla_due_at=sla_due_at,
        )
        self._session.add(ticket)
        await self._session.flush()
        await self._session.refresh(ticket)
        return ticket
    
    async def get_ticket(self, ticket_id: UUID) -> SupportTicketDB | None:
        """Get a ticket by ID."""
        result = await self._session.execute(
            select(SupportTicketDB).where(SupportTicketDB.id == ticket_id)
        )
        return result.scalar_one_or_none()
    
    async def update_ticket(self, ticket_id: UUID, **updates: Any) -> SupportTicketDB | None:
        """Update a ticket."""
        ticket = await self.get_ticket(ticket_id)
        if not ticket:
            return None
        
        for key, value in updates.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)
        
        ticket.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(ticket)
        return ticket
    
    async def list_tickets(
        self,
        status: str | list[str] | None = None,
        priority: str | list[str] | None = None,
        category: str | None = None,
        assignee_id: UUID | None = None,
        reporter_id: UUID | None = None,
        sla_breached: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SupportTicketDB]:
        """List tickets with filters."""
        query = select(SupportTicketDB)
        
        if status:
            if isinstance(status, list):
                query = query.where(SupportTicketDB.status.in_(status))
            else:
                query = query.where(SupportTicketDB.status == status)
        
        if priority:
            if isinstance(priority, list):
                query = query.where(SupportTicketDB.priority.in_(priority))
            else:
                query = query.where(SupportTicketDB.priority == priority)
        
        if category:
            query = query.where(SupportTicketDB.category == category)
        
        if assignee_id:
            query = query.where(SupportTicketDB.assignee_id == assignee_id)
        
        if reporter_id:
            query = query.where(SupportTicketDB.reporter_id == reporter_id)
        
        if sla_breached is not None:
            query = query.where(SupportTicketDB.sla_breached == sla_breached)
        
        query = query.order_by(SupportTicketDB.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    async def get_open_count(self) -> int:
        """Get count of open tickets."""
        result = await self._session.execute(
            select(func.count(SupportTicketDB.id)).where(
                SupportTicketDB.status.in_([
                    TicketStatusDB.OPEN.value,
                    TicketStatusDB.IN_PROGRESS.value,
                ])
            )
        )
        return result.scalar() or 0
    
    async def check_sla_breaches(self) -> list[SupportTicketDB]:
        """Find and mark SLA-breached tickets."""
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            select(SupportTicketDB).where(
                and_(
                    SupportTicketDB.sla_breached == False,  # noqa: E712
                    SupportTicketDB.sla_due_at.isnot(None),
                    SupportTicketDB.sla_due_at < now,
                    SupportTicketDB.status.in_([
                        TicketStatusDB.OPEN.value,
                        TicketStatusDB.IN_PROGRESS.value,
                        TicketStatusDB.WAITING_ON_USER.value,
                    ]),
                )
            )
        )
        breached = list(result.scalars().all())
        
        for ticket in breached:
            ticket.sla_breached = True
        
        if breached:
            await self._session.flush()
        
        return breached
    
    # --------------------------------------------------------------------------
    # Ticket Comments
    # --------------------------------------------------------------------------
    
    async def add_comment(
        self,
        ticket_id: UUID,
        content: str,
        author_id: UUID | None = None,
        is_internal: bool = False,
        is_resolution: bool = False,
    ) -> TicketCommentDB:
        """Add a comment to a ticket."""
        comment = TicketCommentDB(
            ticket_id=ticket_id,
            author_id=author_id,
            content=content,
            is_internal=is_internal,
            is_resolution=is_resolution,
        )
        self._session.add(comment)
        
        # Update first_response_at if this is the first non-internal comment
        if not is_internal:
            ticket = await self.get_ticket(ticket_id)
            if ticket and ticket.first_response_at is None:
                ticket.first_response_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        await self._session.refresh(comment)
        return comment
    
    async def list_comments(
        self,
        ticket_id: UUID,
        include_internal: bool = True,
    ) -> list[TicketCommentDB]:
        """List comments for a ticket."""
        query = select(TicketCommentDB).where(
            TicketCommentDB.ticket_id == ticket_id
        )
        
        if not include_internal:
            query = query.where(TicketCommentDB.is_internal == False)  # noqa: E712
        
        query = query.order_by(TicketCommentDB.created_at)
        
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    # --------------------------------------------------------------------------
    # User Feedback
    # --------------------------------------------------------------------------
    
    async def create_feedback(
        self,
        content: str,
        feedback_type: str,
        user_id: UUID | None = None,
        rating: int | None = None,
        title: str | None = None,
        page_url: str | None = None,
        feature_area: str | None = None,
    ) -> UserFeedbackDB:
        """Create user feedback."""
        feedback = UserFeedbackDB(
            user_id=user_id,
            feedback_type=feedback_type,
            rating=rating,
            title=title,
            content=content,
            page_url=page_url,
            feature_area=feature_area,
        )
        self._session.add(feedback)
        await self._session.flush()
        await self._session.refresh(feedback)
        return feedback
    
    async def list_feedback(
        self,
        status: str | None = None,
        feedback_type: str | None = None,
        user_id: UUID | None = None,
        limit: int = 100,
    ) -> list[UserFeedbackDB]:
        """List feedback with filters."""
        query = select(UserFeedbackDB)
        
        if status:
            query = query.where(UserFeedbackDB.status == status)
        if feedback_type:
            query = query.where(UserFeedbackDB.feedback_type == feedback_type)
        if user_id:
            query = query.where(UserFeedbackDB.user_id == user_id)
        
        query = query.order_by(UserFeedbackDB.created_at.desc())
        query = query.limit(limit)
        
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    # --------------------------------------------------------------------------
    # Routing Rules
    # --------------------------------------------------------------------------
    
    async def create_routing_rule(
        self,
        name: str,
        target: str,
        conditions: dict[str, Any],
        priority: int = 0,
        description: str | None = None,
        target_config: dict[str, Any] | None = None,
    ) -> RoutingRuleDB:
        """Create a routing rule."""
        rule = RoutingRuleDB(
            name=name,
            description=description,
            priority=priority,
            conditions=conditions,
            target=target,
            target_config=target_config,
        )
        self._session.add(rule)
        await self._session.flush()
        await self._session.refresh(rule)
        return rule
    
    async def list_routing_rules(self, active_only: bool = True) -> list[RoutingRuleDB]:
        """List routing rules ordered by priority."""
        query = select(RoutingRuleDB)
        
        if active_only:
            query = query.where(RoutingRuleDB.is_active == True)  # noqa: E712
        
        query = query.order_by(RoutingRuleDB.priority.desc())
        
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    # --------------------------------------------------------------------------
    # A3 Lite Records
    # --------------------------------------------------------------------------
    
    async def create_a3_lite(
        self,
        title: str,
        source_ticket_id: UUID | None = None,
        problem_statement: str | None = None,
        owner_id: UUID | None = None,
    ) -> A3LiteRecordDB:
        """Create an A3 Lite record."""
        record = A3LiteRecordDB(
            source_ticket_id=source_ticket_id,
            title=title,
            problem_statement=problem_statement,
            owner_id=owner_id,
        )
        self._session.add(record)
        await self._session.flush()
        await self._session.refresh(record)
        return record
    
    async def get_a3_lite(self, record_id: UUID) -> A3LiteRecordDB | None:
        """Get an A3 Lite record by ID."""
        result = await self._session.execute(
            select(A3LiteRecordDB).where(A3LiteRecordDB.id == record_id)
        )
        return result.scalar_one_or_none()
    
    async def update_a3_lite(self, record_id: UUID, **updates: Any) -> A3LiteRecordDB | None:
        """Update an A3 Lite record."""
        record = await self.get_a3_lite(record_id)
        if not record:
            return None
        
        for key, value in updates.items():
            if hasattr(record, key):
                setattr(record, key, value)
        
        record.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(record)
        return record
    
    async def list_a3_lite(
        self,
        status: str | None = None,
        owner_id: UUID | None = None,
        limit: int = 100,
    ) -> list[A3LiteRecordDB]:
        """List A3 Lite records."""
        query = select(A3LiteRecordDB)
        
        if status:
            query = query.where(A3LiteRecordDB.status == status)
        if owner_id:
            query = query.where(A3LiteRecordDB.owner_id == owner_id)
        
        query = query.order_by(A3LiteRecordDB.created_at.desc())
        query = query.limit(limit)
        
        result = await self._session.execute(query)
        return list(result.scalars().all())


async def get_support_tickets_repo(session: AsyncSession) -> SupportTicketsRepository:
    """Dependency injection helper for SupportTicketsRepository."""
    return SupportTicketsRepository(session)
