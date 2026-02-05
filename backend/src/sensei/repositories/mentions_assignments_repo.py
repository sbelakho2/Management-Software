"""
Database repository for Mentions and Assignments.

Provides async database access for mentions, assignments, and tasks from comments.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, delete, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.service_persistence import (
    MentionDB,
    AssignmentDB,
    TaskFromCommentDB,
)


class MentionsAssignmentsRepository:
    """Repository for mentions and assignments database operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a database session."""
        self._session = session
    
    # --------------------------------------------------------------------------
    # Mentions
    # --------------------------------------------------------------------------
    
    async def create_mention(
        self,
        mentioned_user_id: UUID,
        mentioned_by_user_id: UUID,
        entity_type: str,
        entity_id: UUID,
        context_text: str | None = None,
        context_start_position: int | None = None,
        context_end_position: int | None = None,
        notification_sent: bool = False,
    ) -> MentionDB:
        """Create a new mention."""
        mention = MentionDB(
            mentioned_user_id=mentioned_user_id,
            mentioned_by_user_id=mentioned_by_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            context_text=context_text,
            context_start_position=context_start_position,
            context_end_position=context_end_position,
            notification_sent=notification_sent,
        )
        self._session.add(mention)
        await self._session.flush()
        await self._session.refresh(mention)
        return mention
    
    async def get_mention(self, mention_id: UUID) -> MentionDB | None:
        """Get a mention by ID."""
        result = await self._session.execute(
            select(MentionDB).where(MentionDB.id == mention_id)
        )
        return result.scalar_one_or_none()
    
    async def list_mentions_for_user(
        self,
        user_id: UUID,
        unread_only: bool = False,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> list[MentionDB]:
        """List mentions for a user."""
        query = select(MentionDB).where(MentionDB.mentioned_user_id == user_id)
        
        if unread_only:
            query = query.where(MentionDB.read_at.is_(None))
        
        if entity_type:
            query = query.where(MentionDB.entity_type == entity_type)
        
        query = query.order_by(MentionDB.created_at.desc())
        query = query.limit(limit)
        
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    async def list_mentions_on_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> list[MentionDB]:
        """List all mentions on a specific entity."""
        result = await self._session.execute(
            select(MentionDB).where(
                and_(
                    MentionDB.entity_type == entity_type,
                    MentionDB.entity_id == entity_id,
                )
            ).order_by(MentionDB.created_at)
        )
        return list(result.scalars().all())
    
    async def mark_mention_read(self, mention_id: UUID) -> MentionDB | None:
        """Mark a mention as read."""
        mention = await self.get_mention(mention_id)
        if not mention:
            return None
        
        mention.read_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        await self._session.refresh(mention)
        return mention
    
    async def mark_all_mentions_read(self, user_id: UUID) -> int:
        """Mark all mentions for a user as read."""
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            update(MentionDB)
            .where(
                and_(
                    MentionDB.mentioned_user_id == user_id,
                    MentionDB.read_at.is_(None),
                )
            )
            .values(read_at=now)
        )
        return result.rowcount  # type: ignore[return-value]
    
    async def delete_mention(self, mention_id: UUID) -> bool:
        """Delete a mention."""
        result = await self._session.execute(
            delete(MentionDB).where(MentionDB.id == mention_id)
        )
        return result.rowcount > 0  # type: ignore[return-value]
    
    async def delete_mentions_for_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> int:
        """Delete all mentions on an entity."""
        result = await self._session.execute(
            delete(MentionDB).where(
                and_(
                    MentionDB.entity_type == entity_type,
                    MentionDB.entity_id == entity_id,
                )
            )
        )
        return result.rowcount  # type: ignore[return-value]
    
    async def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread mentions for a user."""
        from sqlalchemy import func
        
        result = await self._session.execute(
            select(func.count())
            .select_from(MentionDB)
            .where(
                and_(
                    MentionDB.mentioned_user_id == user_id,
                    MentionDB.read_at.is_(None),
                )
            )
        )
        return result.scalar_one()  # type: ignore[return-value]
    
    # --------------------------------------------------------------------------
    # Assignments
    # --------------------------------------------------------------------------
    
    async def create_assignment(
        self,
        assignee_user_id: UUID,
        assigned_by_user_id: UUID,
        entity_type: str,
        entity_id: UUID,
        assignment_type: str = "primary",
        due_date: datetime | None = None,
        priority: str | None = None,
        notes: str | None = None,
    ) -> AssignmentDB:
        """Create a new assignment."""
        assignment = AssignmentDB(
            assignee_user_id=assignee_user_id,
            assigned_by_user_id=assigned_by_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            assignment_type=assignment_type,
            due_date=due_date,
            priority=priority,
            notes=notes,
        )
        self._session.add(assignment)
        await self._session.flush()
        await self._session.refresh(assignment)
        return assignment
    
    async def get_assignment(self, assignment_id: UUID) -> AssignmentDB | None:
        """Get an assignment by ID."""
        result = await self._session.execute(
            select(AssignmentDB).where(AssignmentDB.id == assignment_id)
        )
        return result.scalar_one_or_none()
    
    async def get_assignment_for_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        assignment_type: str = "primary",
    ) -> AssignmentDB | None:
        """Get the assignment for an entity."""
        result = await self._session.execute(
            select(AssignmentDB).where(
                and_(
                    AssignmentDB.entity_type == entity_type,
                    AssignmentDB.entity_id == entity_id,
                    AssignmentDB.assignment_type == assignment_type,
                    AssignmentDB.unassigned_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def list_assignments_for_user(
        self,
        user_id: UUID,
        include_completed: bool = False,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> list[AssignmentDB]:
        """List assignments for a user."""
        query = select(AssignmentDB).where(
            AssignmentDB.assignee_user_id == user_id
        )
        
        if not include_completed:
            query = query.where(
                and_(
                    AssignmentDB.completed_at.is_(None),
                    AssignmentDB.unassigned_at.is_(None),
                )
            )
        
        if entity_type:
            query = query.where(AssignmentDB.entity_type == entity_type)
        
        query = query.order_by(AssignmentDB.created_at.desc())
        query = query.limit(limit)
        
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    async def accept_assignment(self, assignment_id: UUID) -> AssignmentDB | None:
        """Mark an assignment as accepted."""
        assignment = await self.get_assignment(assignment_id)
        if not assignment:
            return None
        
        assignment.accepted_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        await self._session.refresh(assignment)
        return assignment
    
    async def complete_assignment(self, assignment_id: UUID) -> AssignmentDB | None:
        """Mark an assignment as completed."""
        assignment = await self.get_assignment(assignment_id)
        if not assignment:
            return None
        
        assignment.completed_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        await self._session.refresh(assignment)
        return assignment
    
    async def unassign(self, assignment_id: UUID) -> AssignmentDB | None:
        """Remove an assignment."""
        assignment = await self.get_assignment(assignment_id)
        if not assignment:
            return None
        
        assignment.unassigned_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        await self._session.refresh(assignment)
        return assignment
    
    async def reassign(
        self,
        assignment_id: UUID,
        new_assignee_id: UUID,
        reassigned_by_user_id: UUID,
    ) -> AssignmentDB | None:
        """Reassign to a different user."""
        old_assignment = await self.get_assignment(assignment_id)
        if not old_assignment:
            return None
        
        # Mark old assignment as unassigned
        old_assignment.unassigned_at = datetime.now(timezone.utc)
        
        # Create new assignment
        new_assignment = await self.create_assignment(
            assignee_user_id=new_assignee_id,
            assigned_by_user_id=reassigned_by_user_id,
            entity_type=old_assignment.entity_type,
            entity_id=old_assignment.entity_id,
            assignment_type=old_assignment.assignment_type,
            due_date=old_assignment.due_date,
            priority=old_assignment.priority,
            notes=old_assignment.notes,
        )
        
        await self._session.flush()
        return new_assignment
    
    async def delete_assignment(self, assignment_id: UUID) -> bool:
        """Delete an assignment."""
        result = await self._session.execute(
            delete(AssignmentDB).where(AssignmentDB.id == assignment_id)
        )
        return result.rowcount > 0  # type: ignore[return-value]
    
    # --------------------------------------------------------------------------
    # Tasks from Comments
    # --------------------------------------------------------------------------
    
    async def create_task_from_comment(
        self,
        comment_id: UUID,
        comment_entity_type: str,
        comment_entity_id: UUID,
        task_text: str,
        assignee_user_id: UUID | None = None,
        created_by_user_id: UUID | None = None,
        due_date: datetime | None = None,
        priority: str = "medium",
    ) -> TaskFromCommentDB:
        """Create a task extracted from a comment."""
        task = TaskFromCommentDB(
            comment_id=comment_id,
            comment_entity_type=comment_entity_type,
            comment_entity_id=comment_entity_id,
            task_text=task_text,
            assignee_user_id=assignee_user_id,
            created_by_user_id=created_by_user_id,
            due_date=due_date,
            priority=priority,
            status="pending",
        )
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return task
    
    async def get_task(self, task_id: UUID) -> TaskFromCommentDB | None:
        """Get a task by ID."""
        result = await self._session.execute(
            select(TaskFromCommentDB).where(TaskFromCommentDB.id == task_id)
        )
        return result.scalar_one_or_none()
    
    async def list_tasks_for_user(
        self,
        user_id: UUID,
        include_completed: bool = False,
        limit: int = 100,
    ) -> list[TaskFromCommentDB]:
        """List tasks assigned to a user."""
        query = select(TaskFromCommentDB).where(
            TaskFromCommentDB.assignee_user_id == user_id
        )
        
        if not include_completed:
            query = query.where(TaskFromCommentDB.status != "completed")
        
        query = query.order_by(TaskFromCommentDB.created_at.desc())
        query = query.limit(limit)
        
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    async def list_tasks_for_comment(
        self,
        comment_id: UUID,
    ) -> list[TaskFromCommentDB]:
        """List tasks from a specific comment."""
        result = await self._session.execute(
            select(TaskFromCommentDB)
            .where(TaskFromCommentDB.comment_id == comment_id)
            .order_by(TaskFromCommentDB.created_at)
        )
        return list(result.scalars().all())
    
    async def list_tasks_on_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> list[TaskFromCommentDB]:
        """List all tasks on comments for an entity."""
        result = await self._session.execute(
            select(TaskFromCommentDB).where(
                and_(
                    TaskFromCommentDB.comment_entity_type == entity_type,
                    TaskFromCommentDB.comment_entity_id == entity_id,
                )
            ).order_by(TaskFromCommentDB.created_at)
        )
        return list(result.scalars().all())
    
    async def update_task_status(
        self,
        task_id: UUID,
        status: str,
    ) -> TaskFromCommentDB | None:
        """Update task status."""
        task = await self.get_task(task_id)
        if not task:
            return None
        
        task.status = status
        task.updated_at = datetime.now(timezone.utc)
        
        if status == "completed":
            task.completed_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        await self._session.refresh(task)
        return task
    
    async def assign_task(
        self,
        task_id: UUID,
        assignee_user_id: UUID,
    ) -> TaskFromCommentDB | None:
        """Assign a task to a user."""
        task = await self.get_task(task_id)
        if not task:
            return None
        
        task.assignee_user_id = assignee_user_id
        task.updated_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        await self._session.refresh(task)
        return task
    
    async def delete_task(self, task_id: UUID) -> bool:
        """Delete a task."""
        result = await self._session.execute(
            delete(TaskFromCommentDB).where(TaskFromCommentDB.id == task_id)
        )
        return result.rowcount > 0  # type: ignore[return-value]


async def get_mentions_assignments_repo(
    session: AsyncSession,
) -> MentionsAssignmentsRepository:
    """Dependency injection helper for MentionsAssignmentsRepository."""
    return MentionsAssignmentsRepository(session)
