"""
Segment Views Service - Database-backed Implementation.

Provides workspace segmentation with database persistence.
Features:
- Saved filter sets per module
- Personal, team, and shared segments
- Smart segments with dynamic criteria
- Segment sharing and collaboration
- Usage analytics
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.models.segment import (
    Segment,
    SegmentShare,
    SegmentUsage,
    SegmentModule,
    SegmentVisibility,
)


def _utcnow() -> datetime:
    """Get current UTC time with timezone info."""
    return datetime.now(timezone.utc)


class FilterOperator:
    """Filter operators for criteria."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"
    DATE_BEFORE = "date_before"
    DATE_AFTER = "date_after"
    DATE_BETWEEN = "date_between"
    RELATIVE_DATE = "relative_date"


class SegmentViewsService:
    """Database-backed service for managing segment views (saved filters)."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create_segment(
        self,
        *,
        name: str,
        module: SegmentModule | str,
        owner_id: UUID,
        description: str = "",
        filter_groups: list[dict] | None = None,
        columns: list[dict] | None = None,
        sort_config: dict | None = None,
        visibility: SegmentVisibility | str = SegmentVisibility.PRIVATE,
        color: str | None = None,
        icon: str | None = None,
        is_smart: bool = False,
        team_id: UUID | None = None,
        department_id: UUID | None = None,
    ) -> Segment:
        """Create a new segment.
        
        Args:
            name: Segment name
            module: Target module for the segment
            owner_id: User ID of the segment owner
            description: Segment description
            filter_groups: Filter criteria groups
            columns: Column configuration
            sort_config: Sort configuration
            visibility: Visibility level
            color: Display color
            icon: Display icon
            is_smart: Whether segment has dynamic criteria
            team_id: Team ID for team-scoped segments
            department_id: Department ID for department-scoped segments
            
        Returns:
            Created Segment instance
        """
        module_str = module.value if isinstance(module, SegmentModule) else module
        visibility_str = visibility.value if isinstance(visibility, SegmentVisibility) else visibility

        segment = Segment(
            name=name.strip(),
            description=description,
            module=module_str,
            owner_id=owner_id,
            visibility=visibility_str,
            filter_groups=filter_groups or [],
            columns=columns or [],
            sort_config=sort_config,
            color=color,
            icon=icon,
            is_smart=is_smart,
            team_id=team_id,
            department_id=department_id,
        )
        self._session.add(segment)
        await self._session.flush()
        await self._session.refresh(segment)
        return segment

    async def get_segment(self, segment_id: UUID) -> Segment | None:
        """Get a segment by ID.
        
        Args:
            segment_id: UUID of the segment
            
        Returns:
            Segment if found, None otherwise
        """
        result = await self._session.execute(
            select(Segment)
            .where(Segment.id == segment_id)
            .options(selectinload(Segment.shares))
        )
        return result.scalar_one_or_none()

    async def get_segment_by_name(
        self,
        name: str,
        module: SegmentModule | str,
        owner_id: UUID,
    ) -> Segment | None:
        """Get a segment by name, module, and owner.
        
        Args:
            name: Segment name
            module: Target module
            owner_id: Owner's user ID
            
        Returns:
            Segment if found, None otherwise
        """
        module_str = module.value if isinstance(module, SegmentModule) else module
        
        result = await self._session.execute(
            select(Segment).where(
                and_(
                    Segment.name == name,
                    Segment.module == module_str,
                    Segment.owner_id == owner_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_segments(
        self,
        user_id: UUID,
        module: SegmentModule | str | None = None,
        visibility: SegmentVisibility | str | None = None,
        include_shared: bool = True,
        only_pinned: bool = False,
        team_id: UUID | None = None,
        department_id: UUID | None = None,
    ) -> Sequence[Segment]:
        """Get segments accessible to a user.
        
        Args:
            user_id: User ID to get segments for
            module: Filter by module
            visibility: Filter by visibility
            include_shared: Include segments shared with user
            only_pinned: Only return pinned segments
            team_id: Filter by team
            department_id: Filter by department
            
        Returns:
            List of accessible Segment instances
        """
        conditions = []
        
        # User's own segments
        user_conditions = [Segment.owner_id == user_id]
        
        if include_shared:
            # Get segment IDs shared with this user
            shared_query = select(SegmentShare.segment_id).where(
                SegmentShare.shared_with_id == user_id
            )
            user_conditions.append(Segment.id.in_(shared_query))
            
            # Include organization-wide segments
            user_conditions.append(
                Segment.visibility == SegmentVisibility.ORGANIZATION.value
            )
        
        conditions.append(or_(*user_conditions))
        
        if module:
            module_str = module.value if isinstance(module, SegmentModule) else module
            conditions.append(Segment.module == module_str)
        
        if visibility:
            vis_str = visibility.value if isinstance(visibility, SegmentVisibility) else visibility
            conditions.append(Segment.visibility == vis_str)
        
        if only_pinned:
            conditions.append(Segment.is_pinned.is_(True))
        
        if team_id:
            conditions.append(Segment.team_id == team_id)
        
        if department_id:
            conditions.append(Segment.department_id == department_id)
        
        query = (
            select(Segment)
            .where(and_(*conditions))
            .order_by(Segment.is_pinned.desc(), Segment.name)
        )
        
        result = await self._session.execute(query)
        return result.scalars().all()

    async def update_segment(
        self,
        segment_id: UUID,
        user_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        filter_groups: list[dict] | None = None,
        columns: list[dict] | None = None,
        sort_config: dict | None = None,
        visibility: SegmentVisibility | str | None = None,
        color: str | None = None,
        icon: str | None = None,
        is_smart: bool | None = None,
    ) -> Segment:
        """Update a segment.
        
        Args:
            segment_id: ID of segment to update
            user_id: ID of user making the update
            name: New name (optional)
            description: New description (optional)
            filter_groups: New filter groups (optional)
            columns: New columns (optional)
            sort_config: New sort config (optional)
            visibility: New visibility (optional)
            color: New color (optional)
            icon: New icon (optional)
            is_smart: New smart flag (optional)
            
        Returns:
            Updated Segment instance
            
        Raises:
            PermissionError: If user lacks edit access
            KeyError: If segment not found
        """
        segment = await self.get_segment(segment_id)
        if not segment:
            raise KeyError("Segment not found")
        
        # Check edit permission
        if segment.owner_id != user_id:
            # Check if user has edit share
            has_edit = await self._session.execute(
                select(SegmentShare).where(
                    and_(
                        SegmentShare.segment_id == segment_id,
                        SegmentShare.shared_with_id == user_id,
                        SegmentShare.can_edit.is_(True),
                    )
                )
            )
            if not has_edit.scalar_one_or_none():
                raise PermissionError("Not permitted to edit this segment")
        
        if name is not None:
            segment.name = name.strip()
        if description is not None:
            segment.description = description
        if filter_groups is not None:
            segment.filter_groups = filter_groups
        if columns is not None:
            segment.columns = columns
        if sort_config is not None:
            segment.sort_config = sort_config
        if visibility is not None:
            segment.visibility = visibility.value if isinstance(visibility, SegmentVisibility) else visibility
        if color is not None:
            segment.color = color
        if icon is not None:
            segment.icon = icon
        if is_smart is not None:
            segment.is_smart = is_smart
        
        await self._session.flush()
        await self._session.refresh(segment)
        return segment

    async def delete_segment(self, segment_id: UUID, user_id: UUID) -> bool:
        """Delete a segment.
        
        Args:
            segment_id: ID of segment to delete
            user_id: ID of user requesting deletion
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            PermissionError: If user is not the owner
        """
        segment = await self.get_segment(segment_id)
        if not segment:
            return False
        
        if segment.owner_id != user_id:
            raise PermissionError("Only the owner can delete a segment")
        
        if segment.is_system:
            raise PermissionError("Cannot delete system segments")
        
        await self._session.delete(segment)
        await self._session.flush()
        return True

    async def duplicate_segment(
        self,
        segment_id: UUID,
        new_owner_id: UUID,
        new_name: str | None = None,
    ) -> Segment:
        """Duplicate a segment.
        
        Args:
            segment_id: ID of segment to duplicate
            new_owner_id: Owner ID for the new segment
            new_name: Name for the new segment (optional)
            
        Returns:
            New Segment instance
            
        Raises:
            KeyError: If original segment not found
        """
        original = await self.get_segment(segment_id)
        if not original:
            raise KeyError("Segment not found")
        
        return await self.create_segment(
            name=new_name or f"{original.name} (Copy)",
            module=original.module,
            owner_id=new_owner_id,
            description=original.description or "",
            filter_groups=original.filter_groups.copy() if original.filter_groups else [],
            columns=original.columns.copy() if original.columns else [],
            sort_config=original.sort_config.copy() if original.sort_config else None,
            visibility=SegmentVisibility.PRIVATE,
            color=original.color,
            icon=original.icon,
            is_smart=original.is_smart,
        )

    # ---- Sharing ----

    async def share_segment(
        self,
        segment_id: UUID,
        shared_by_id: UUID,
        shared_with_id: UUID,
        can_edit: bool = False,
    ) -> SegmentShare:
        """Share a segment with another user.
        
        Args:
            segment_id: ID of segment to share
            shared_by_id: ID of user sharing
            shared_with_id: ID of user to share with
            can_edit: Whether recipient can edit
            
        Returns:
            Created SegmentShare instance
            
        Raises:
            PermissionError: If user cannot share
            KeyError: If segment not found
        """
        segment = await self.get_segment(segment_id)
        if not segment:
            raise KeyError("Segment not found")
        
        if segment.owner_id != shared_by_id:
            raise PermissionError("Only the owner can share a segment")
        
        # Check if already shared
        existing = await self._session.execute(
            select(SegmentShare).where(
                and_(
                    SegmentShare.segment_id == segment_id,
                    SegmentShare.shared_with_id == shared_with_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Segment already shared with this user")
        
        share = SegmentShare(
            segment_id=segment_id,
            shared_by_id=shared_by_id,
            shared_with_id=shared_with_id,
            can_edit=can_edit,
        )
        self._session.add(share)
        await self._session.flush()
        await self._session.refresh(share)
        return share

    async def unshare_segment(
        self,
        segment_id: UUID,
        user_id: UUID,
        owner_id: UUID,
    ) -> bool:
        """Remove a segment share.
        
        Args:
            segment_id: ID of shared segment
            user_id: ID of user to unshare from
            owner_id: ID of segment owner (for permission check)
            
        Returns:
            True if removed, False if not found
            
        Raises:
            PermissionError: If requester is not owner
        """
        segment = await self.get_segment(segment_id)
        if not segment:
            return False
        
        if segment.owner_id != owner_id:
            raise PermissionError("Only the owner can unshare a segment")
        
        result = await self._session.execute(
            delete(SegmentShare).where(
                and_(
                    SegmentShare.segment_id == segment_id,
                    SegmentShare.shared_with_id == user_id,
                )
            )
        )
        await self._session.flush()
        return result.rowcount > 0

    async def get_shares(self, segment_id: UUID) -> Sequence[SegmentShare]:
        """Get all shares for a segment.
        
        Args:
            segment_id: ID of segment
            
        Returns:
            List of SegmentShare instances
        """
        result = await self._session.execute(
            select(SegmentShare)
            .where(SegmentShare.segment_id == segment_id)
            .options(selectinload(SegmentShare.shared_with))
        )
        return result.scalars().all()

    # ---- Default & Pinning ----

    async def set_default_segment(
        self,
        segment_id: UUID,
        user_id: UUID,
        module: SegmentModule | str,
    ) -> Segment:
        """Set a segment as the default for a module.
        
        Args:
            segment_id: ID of segment to set as default
            user_id: User ID setting the default
            module: Module for the default
            
        Returns:
            Updated Segment instance
            
        Raises:
            KeyError: If segment not found
        """
        module_str = module.value if isinstance(module, SegmentModule) else module
        
        # Clear existing defaults for this user/module
        await self._session.execute(
            update(Segment)
            .where(
                and_(
                    Segment.owner_id == user_id,
                    Segment.module == module_str,
                    Segment.is_default.is_(True),
                )
            )
            .values(is_default=False)
        )
        
        segment = await self.get_segment(segment_id)
        if not segment:
            raise KeyError("Segment not found")
        
        segment.is_default = True
        await self._session.flush()
        await self._session.refresh(segment)
        return segment

    async def get_default_segment(
        self,
        user_id: UUID,
        module: SegmentModule | str,
    ) -> Segment | None:
        """Get the default segment for a user/module.
        
        Args:
            user_id: User ID
            module: Module to get default for
            
        Returns:
            Default Segment if set, None otherwise
        """
        module_str = module.value if isinstance(module, SegmentModule) else module
        
        result = await self._session.execute(
            select(Segment).where(
                and_(
                    Segment.owner_id == user_id,
                    Segment.module == module_str,
                    Segment.is_default.is_(True),
                )
            )
        )
        return result.scalar_one_or_none()

    async def pin_segment(self, segment_id: UUID, user_id: UUID) -> Segment:
        """Pin a segment.
        
        Args:
            segment_id: ID of segment to pin
            user_id: ID of user pinning (must be owner)
            
        Returns:
            Updated Segment instance
        """
        segment = await self.get_segment(segment_id)
        if not segment:
            raise KeyError("Segment not found")
        
        segment.is_pinned = True
        await self._session.flush()
        await self._session.refresh(segment)
        return segment

    async def unpin_segment(self, segment_id: UUID, user_id: UUID) -> Segment:
        """Unpin a segment.
        
        Args:
            segment_id: ID of segment to unpin
            user_id: ID of user unpinning
            
        Returns:
            Updated Segment instance
        """
        segment = await self.get_segment(segment_id)
        if not segment:
            raise KeyError("Segment not found")
        
        segment.is_pinned = False
        await self._session.flush()
        await self._session.refresh(segment)
        return segment

    # ---- Usage Analytics ----

    async def record_usage(
        self,
        segment_id: UUID,
        user_id: UUID,
        result_count: int = 0,
        execution_time_ms: int = 0,
    ) -> SegmentUsage:
        """Record segment usage.
        
        Args:
            segment_id: ID of segment used
            user_id: ID of user using the segment
            result_count: Number of results returned
            execution_time_ms: Query execution time in ms
            
        Returns:
            Created SegmentUsage instance
        """
        usage = SegmentUsage(
            segment_id=segment_id,
            user_id=user_id,
            used_at=_utcnow(),
            result_count=result_count,
            execution_time_ms=execution_time_ms,
        )
        self._session.add(usage)
        
        # Update segment usage stats
        await self._session.execute(
            update(Segment)
            .where(Segment.id == segment_id)
            .values(
                use_count=Segment.use_count + 1,
                last_used_at=_utcnow(),
            )
        )
        
        await self._session.flush()
        await self._session.refresh(usage)
        return usage

    async def get_usage_stats(
        self,
        segment_id: UUID,
        days: int = 30,
    ) -> dict:
        """Get usage statistics for a segment.
        
        Args:
            segment_id: ID of segment
            days: Number of days to analyze
            
        Returns:
            Dictionary with usage statistics
        """
        since = _utcnow() - timedelta(days=days)
        
        result = await self._session.execute(
            select(SegmentUsage).where(
                and_(
                    SegmentUsage.segment_id == segment_id,
                    SegmentUsage.used_at >= since,
                )
            )
        )
        usage_records = result.scalars().all()
        
        if not usage_records:
            return {
                "total_uses": 0,
                "unique_users": 0,
                "avg_result_count": 0,
                "avg_execution_time_ms": 0,
            }
        
        unique_users = set(u.user_id for u in usage_records)
        total_results = sum(u.result_count for u in usage_records)
        total_time = sum(u.execution_time_ms for u in usage_records)
        
        return {
            "total_uses": len(usage_records),
            "unique_users": len(unique_users),
            "avg_result_count": total_results / len(usage_records),
            "avg_execution_time_ms": total_time / len(usage_records),
        }

    async def get_popular_segments(
        self,
        module: SegmentModule | str,
        limit: int = 10,
    ) -> Sequence[Segment]:
        """Get most popular segments for a module.
        
        Args:
            module: Module to get popular segments for
            limit: Maximum number to return
            
        Returns:
            List of popular Segment instances
        """
        module_str = module.value if isinstance(module, SegmentModule) else module
        
        result = await self._session.execute(
            select(Segment)
            .where(
                and_(
                    Segment.module == module_str,
                    Segment.visibility == SegmentVisibility.ORGANIZATION.value,
                )
            )
            .order_by(Segment.use_count.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_recent_segments(
        self,
        user_id: UUID,
        limit: int = 5,
    ) -> Sequence[Segment]:
        """Get recently used segments for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number to return
            
        Returns:
            List of recently used Segment instances
        """
        # Get segment IDs from recent usage
        usage_query = (
            select(SegmentUsage.segment_id)
            .where(SegmentUsage.user_id == user_id)
            .order_by(SegmentUsage.used_at.desc())
            .distinct()
            .limit(limit)
        )
        
        result = await self._session.execute(
            select(Segment).where(Segment.id.in_(usage_query))
        )
        return result.scalars().all()

    # ---- System Segments ----

    async def create_system_segment(
        self,
        name: str,
        module: SegmentModule | str,
        filter_groups: list[dict],
        description: str = "",
        color: str | None = None,
        icon: str | None = None,
        is_smart: bool = False,
    ) -> Segment:
        """Create a system segment (visible to all users).
        
        Args:
            name: Segment name
            module: Target module
            filter_groups: Filter criteria
            description: Segment description
            color: Display color
            icon: Display icon
            is_smart: Whether segment is smart (dynamic)
            
        Returns:
            Created Segment instance
        """
        from uuid import UUID as UUIDType
        system_user_id = UUIDType("00000000-0000-0000-0000-000000000001")
        module_str = module.value if isinstance(module, SegmentModule) else module
        
        segment = Segment(
            name=name,
            description=description,
            module=module_str,
            owner_id=system_user_id,
            visibility=SegmentVisibility.ORGANIZATION.value,
            filter_groups=filter_groups,
            columns=[],
            color=color,
            icon=icon,
            is_smart=is_smart,
            is_system=True,
        )
        self._session.add(segment)
        await self._session.flush()
        await self._session.refresh(segment)
        return segment


# Factory function for dependency injection
def get_segment_views_service(session: AsyncSession) -> SegmentViewsService:
    """Get segment views service instance.
    
    Args:
        session: Database session
        
    Returns:
        SegmentViewsService instance
    """
    return SegmentViewsService(session)
