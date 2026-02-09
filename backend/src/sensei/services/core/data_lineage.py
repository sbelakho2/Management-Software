"""Data lineage service.

Implements a centralized, deterministic service for tracking cross-module
relationships between key entities.

This is intentionally generic:
- entity_type: string token (e.g., "product", "work_order", "non_conformance")
- entity_id: canonical string id (supports int/UUID/etc)

The service is safe to call from endpoints as a best-effort enrichment.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.data_lineage import DataLineageLink


@dataclass(frozen=True)
class LineageNode:
    entity_type: str
    entity_id: str


@dataclass(frozen=True)
class LineageEdge:
    source: LineageNode
    target: LineageNode
    relationship_type: str


@dataclass
class LineageGraph:
    nodes: list[LineageNode]
    edges: list[LineageEdge]


class DataLineageService:
    """Centralized service for recording and querying lineage relationships."""

    def canonical_entity_id(self, entity_id: Any) -> str:
        if entity_id is None:
            raise ValueError("entity_id is required")
        return str(entity_id)

    async def link(
        self,
        db: AsyncSession,
        *,
        source_entity_type: str,
        source_entity_id: Any,
        relationship_type: str,
        target_entity_type: str,
        target_entity_id: Any,
        created_by_id: Any | None = None,
        reasoning_id: str | None = None,
        metadata: dict | None = None,
    ) -> DataLineageLink:
        """Create an idempotent directed link between two entities."""

        source_id = self.canonical_entity_id(source_entity_id)
        target_id = self.canonical_entity_id(target_entity_id)

        existing = await db.execute(
            select(DataLineageLink).where(
                DataLineageLink.source_entity_type == source_entity_type,
                DataLineageLink.source_entity_id == source_id,
                DataLineageLink.relationship_type == relationship_type,
                DataLineageLink.target_entity_type == target_entity_type,
                DataLineageLink.target_entity_id == target_id,
            )
        )
        link = existing.scalar_one_or_none()
        if link is not None:
            return link

        link = DataLineageLink(
            source_entity_type=source_entity_type,
            source_entity_id=source_id,
            relationship_type=relationship_type,
            target_entity_type=target_entity_type,
            target_entity_id=target_id,
            reasoning_id=reasoning_id,
            link_metadata=metadata,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.add(link)
        try:
            # Use a savepoint so rollback doesn't kill the outer transaction
            async with db.begin_nested():
                await db.flush()
        except IntegrityError:
            # Another concurrent request inserted the same link.
            existing2 = await db.execute(
                select(DataLineageLink).where(
                    DataLineageLink.source_entity_type == source_entity_type,
                    DataLineageLink.source_entity_id == source_id,
                    DataLineageLink.relationship_type == relationship_type,
                    DataLineageLink.target_entity_type == target_entity_type,
                    DataLineageLink.target_entity_id == target_id,
                )
            )
            link2 = existing2.scalar_one()
            return link2

        return link

    async def get_graph(
        self,
        db: AsyncSession,
        *,
        root_entity_type: str,
        root_entity_id: Any,
        max_depth: int = 3,
    ) -> LineageGraph:
        """Return a small lineage graph around a root entity."""

        if max_depth < 0:
            raise ValueError("max_depth must be >= 0")

        root = LineageNode(root_entity_type, self.canonical_entity_id(root_entity_id))

        nodes: dict[tuple[str, str], LineageNode] = {(root.entity_type, root.entity_id): root}
        edges: list[LineageEdge] = []

        visited: set[tuple[str, str]] = set()
        q: deque[tuple[LineageNode, int]] = deque([(root, 0)])

        while q:
            node, depth = q.popleft()
            key = (node.entity_type, node.entity_id)
            if key in visited:
                continue
            visited.add(key)

            if depth >= max_depth:
                continue

            result = await db.execute(
                select(DataLineageLink).where(
                    or_(
                        (DataLineageLink.source_entity_type == node.entity_type)
                        & (DataLineageLink.source_entity_id == node.entity_id),
                        (DataLineageLink.target_entity_type == node.entity_type)
                        & (DataLineageLink.target_entity_id == node.entity_id),
                    )
                )
            )
            links = result.scalars().all()

            for link in links:
                src = LineageNode(link.source_entity_type, link.source_entity_id)
                dst = LineageNode(link.target_entity_type, link.target_entity_id)

                nodes.setdefault((src.entity_type, src.entity_id), src)
                nodes.setdefault((dst.entity_type, dst.entity_id), dst)
                edges.append(LineageEdge(source=src, target=dst, relationship_type=link.relationship_type))

                # Undirected traversal for neighborhood discovery.
                other = dst if (src.entity_type, src.entity_id) == key else src
                other_key = (other.entity_type, other.entity_id)
                if other_key not in visited:
                    q.append((other, depth + 1))

        return LineageGraph(nodes=list(nodes.values()), edges=edges)

    async def capture_work_order_created(
        self,
        db: AsyncSession,
        *,
        work_order_id: int,
        product_id: int,
        created_by_id: Any | None = None,
        reasoning_id: str | None = None,
    ) -> None:
        await self.link(
            db,
            source_entity_type="product",
            source_entity_id=product_id,
            relationship_type="has_work_order",
            target_entity_type="work_order",
            target_entity_id=work_order_id,
            created_by_id=created_by_id,
            reasoning_id=reasoning_id,
        )

    async def capture_non_conformance_created(
        self,
        db: AsyncSession,
        *,
        non_conformance_id: int,
        product_id: int | None,
        work_order_id: int | None,
        created_by_id: Any | None = None,
        reasoning_id: str | None = None,
    ) -> None:
        if product_id is not None:
            await self.link(
                db,
                source_entity_type="product",
                source_entity_id=product_id,
                relationship_type="has_non_conformance",
                target_entity_type="non_conformance",
                target_entity_id=non_conformance_id,
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
            )

        if work_order_id is not None:
            await self.link(
                db,
                source_entity_type="work_order",
                source_entity_id=work_order_id,
                relationship_type="has_non_conformance",
                target_entity_type="non_conformance",
                target_entity_id=non_conformance_id,
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
            )

    async def capture_capa_created(
        self,
        db: AsyncSession,
        *,
        capa_id: int,
        source_nc_id: int | None,
        created_by_id: Any | None = None,
        reasoning_id: str | None = None,
    ) -> None:
        if source_nc_id is not None:
            await self.link(
                db,
                source_entity_type="non_conformance",
                source_entity_id=source_nc_id,
                relationship_type="has_capa",
                target_entity_type="capa",
                target_entity_id=capa_id,
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
            )

    async def capture_capa_action_created(
        self,
        db: AsyncSession,
        *,
        capa_id: int,
        action_id: int,
        created_by_id: Any | None = None,
        reasoning_id: str | None = None,
    ) -> None:
        await self.link(
            db,
            source_entity_type="capa",
            source_entity_id=capa_id,
            relationship_type="has_capa_action",
            target_entity_type="capa_action",
            target_entity_id=action_id,
            created_by_id=created_by_id,
            reasoning_id=reasoning_id,
        )

    async def capture_inspection_plan_created(
        self,
        db: AsyncSession,
        *,
        plan_id: int,
        product_id: int | None,
        station_id: int | None,
        created_by_id: Any | None = None,
        reasoning_id: str | None = None,
    ) -> None:
        if product_id is not None:
            await self.link(
                db,
                source_entity_type="product",
                source_entity_id=product_id,
                relationship_type="has_inspection_plan",
                target_entity_type="inspection_plan",
                target_entity_id=plan_id,
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
            )
        if station_id is not None:
            await self.link(
                db,
                source_entity_type="station",
                source_entity_id=station_id,
                relationship_type="has_inspection_plan",
                target_entity_type="inspection_plan",
                target_entity_id=plan_id,
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
            )

    async def capture_inspection_record_created(
        self,
        db: AsyncSession,
        *,
        record_id: int,
        inspection_plan_id: int,
        work_order_id: int | None,
        nc_id: int | None,
        created_by_id: Any | None = None,
        reasoning_id: str | None = None,
    ) -> None:
        await self.link(
            db,
            source_entity_type="inspection_plan",
            source_entity_id=inspection_plan_id,
            relationship_type="has_inspection_record",
            target_entity_type="inspection_record",
            target_entity_id=record_id,
            created_by_id=created_by_id,
            reasoning_id=reasoning_id,
        )
        if work_order_id is not None:
            await self.link(
                db,
                source_entity_type="work_order",
                source_entity_id=work_order_id,
                relationship_type="has_inspection_record",
                target_entity_type="inspection_record",
                target_entity_id=record_id,
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
            )
        if nc_id is not None:
            await self.link(
                db,
                source_entity_type="non_conformance",
                source_entity_id=nc_id,
                relationship_type="has_inspection_record",
                target_entity_type="inspection_record",
                target_entity_id=record_id,
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
            )

    async def capture_skill_requirement_created(
        self,
        db: AsyncSession,
        *,
        requirement_id: int,
        skill_id: int,
        station_id: int | None,
        product_id: int | None,
        created_by_id: Any | None = None,
        reasoning_id: str | None = None,
    ) -> None:
        await self.link(
            db,
            source_entity_type="skill",
            source_entity_id=skill_id,
            relationship_type="is_required_by",
            target_entity_type="skill_requirement",
            target_entity_id=requirement_id,
            created_by_id=created_by_id,
            reasoning_id=reasoning_id,
        )
        if station_id is not None:
            await self.link(
                db,
                source_entity_type="station",
                source_entity_id=station_id,
                relationship_type="has_skill_requirement",
                target_entity_type="skill_requirement",
                target_entity_id=requirement_id,
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
            )
        if product_id is not None:
            await self.link(
                db,
                source_entity_type="product",
                source_entity_id=product_id,
                relationship_type="has_skill_requirement",
                target_entity_type="skill_requirement",
                target_entity_id=requirement_id,
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
            )

    async def capture_training_created(
        self,
        db: AsyncSession,
        *,
        training_id: int,
        skill_id: int,
        created_by_id: Any | None = None,
        reasoning_id: str | None = None,
    ) -> None:
        await self.link(
            db,
            source_entity_type="skill",
            source_entity_id=skill_id,
            relationship_type="has_training",
            target_entity_type="training",
            target_entity_id=training_id,
            created_by_id=created_by_id,
            reasoning_id=reasoning_id,
        )

    async def capture_training_participant_enrolled(
        self,
        db: AsyncSession,
        *,
        training_id: int,
        participant_id: int,
        user_id: Any,
        created_by_id: Any | None = None,
        reasoning_id: str | None = None,
    ) -> None:
        await self.link(
            db,
            source_entity_type="training",
            source_entity_id=training_id,
            relationship_type="has_participant",
            target_entity_type="training_participant",
            target_entity_id=participant_id,
            created_by_id=created_by_id,
            reasoning_id=reasoning_id,
        )
        await self.link(
            db,
            source_entity_type="user",
            source_entity_id=user_id,
            relationship_type="enrolled_in",
            target_entity_type="training",
            target_entity_id=training_id,
            created_by_id=created_by_id,
            reasoning_id=reasoning_id,
        )

    async def capture_user_skill_created(
        self,
        db: AsyncSession,
        *,
        user_skill_id: int,
        user_id: Any,
        skill_id: int,
        created_by_id: Any | None = None,
        reasoning_id: str | None = None,
    ) -> None:
        await self.link(
            db,
            source_entity_type="user",
            source_entity_id=user_id,
            relationship_type="has_skill",
            target_entity_type="user_skill",
            target_entity_id=user_skill_id,
            created_by_id=created_by_id,
            reasoning_id=reasoning_id,
        )
        await self.link(
            db,
            source_entity_type="skill",
            source_entity_id=skill_id,
            relationship_type="has_user_skill",
            target_entity_type="user_skill",
            target_entity_id=user_skill_id,
            created_by_id=created_by_id,
            reasoning_id=reasoning_id,
        )


_service_instance: Optional[DataLineageService] = None


def get_data_lineage_service() -> DataLineageService:
    global _service_instance
    if _service_instance is None:
        _service_instance = DataLineageService()
    return _service_instance
