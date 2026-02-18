import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sensei.models.analytics import ExportedRecord
from sensei.models.base import Base
from sensei.models.reasoning_trace import ReasoningTrace
from sensei.services.core.single_data_thread import SingleDataThreadService
from sensei.services.domain_events import NCCreatedEvent
from sensei.services.ops.analytics_warehouse import FactType


@pytest_asyncio.fixture
async def thread_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, expire_on_commit=False, autoflush=True
    )
    yield session_factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_single_data_thread_exports_event(thread_session_factory):
    service = SingleDataThreadService(session_factory=thread_session_factory)

    event = NCCreatedEvent(nc_id="nc-1", severity="critical", product_id="prod-1")
    await service.handle_event(event)

    async with thread_session_factory() as session:
        exported = (await session.execute(select(ExportedRecord))).scalars().all()
        assert exported
        assert exported[0].fact_type == FactType.NON_CONFORMANCE.value
        assert exported[0].data["event_type"] == "NCCreatedEvent"

        traces = (await session.execute(select(ReasoningTrace))).scalars().all()
        assert traces
