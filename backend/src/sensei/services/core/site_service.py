from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.site import Site


class SiteService:
    """Service for managing sites."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_sites(self) -> list[Site]:
        result = await self.db.execute(select(Site))
        return list(result.scalars().all())

    async def get_site(self, site_id: UUID) -> Optional[Site]:
        result = await self.db.execute(select(Site).where(Site.id == site_id))
        return result.scalar_one_or_none()

    async def create_site(self, **kwargs) -> Site:
        site = Site(**kwargs)
        self.db.add(site)
        await self.db.flush()
        return site

    async def update_site(self, site: Site, **kwargs) -> Site:
        for key, value in kwargs.items():
            setattr(site, key, value)
        await self.db.flush()
        return site
