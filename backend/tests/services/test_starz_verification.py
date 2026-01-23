import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from sensei.models.base import Base
from sensei.models.external.starz_erp import (
    StarzBase, 
    StarzWarehouse, 
    StarzStockLocation, 
    StarzWmsDevice, 
    StarzWmsWorkstation, 
    StarzLicensePlate, 
    StarzArticle
)
from sensei.services.external.starz_ingestion import StarzErpIngestionService
from sensei.models.inventory import Warehouse, Location, WmsDevice, WmsWorkstation, LicensePlate, InventoryLevel
from sensei.models.product import Product, UnitOfMeasure

@pytest_asyncio.fixture
async def starz_session():
    # Mocking MySQL with SQLite
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(StarzBase.metadata.create_all)
    
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()

@pytest_asyncio.fixture
async def sensei_session():
    # Mocking PostgreSQL with SQLite
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_starz_ingestion_data_mapping(starz_session, sensei_session):
    """
    Verifies that data is correctly mapped from Starz ERP to Sensei OS.
    """
    # 1. Prepare Starz ERP data
    sw = StarzWarehouse(id=1, name="Starz Main", code="STZ01", description="Main Distribution Center")
    starz_session.add(sw)
    
    sa = StarzArticle(id=1, code_reference="PRD-100", stock=500, prix=125.50, description="Industrial Sensor", unit_id=1)
    starz_session.add(sa)
    
    sl = StarzStockLocation(id=1, code="LOC-A1", warehouse_id=1, type="shelf", label="Aisle 1 Shelf 1")
    starz_session.add(sl)
    
    lp = StarzLicensePlate(id=1, code="LPN-001", warehouse_id=1, location_id=1, status="active", item_sku="PRD-100", quantity=10.0)
    starz_session.add(lp)
    
    dev = StarzWmsDevice(
        id=1, 
        device_identifier="DEV-X", 
        name="Handheld Scanner 1", 
        device_type="scanner", 
        status="online", 
        warehouse_id=1,
        capabilities={"scanning": True, "printing": False},
        last_seen_at=datetime.utcnow()
    )
    starz_session.add(dev)
    
    ws = StarzWmsWorkstation(
        id=1, 
        workstation_code="WS-01", 
        warehouse_id=1, 
        station_type="packing", 
        scanner_model="Zebra-X1", 
        connection_type="wifi",
        registered_at=datetime.utcnow(),
        last_activity=datetime.utcnow()
    )
    starz_session.add(ws)
    
    await starz_session.commit()
    
    # 2. Run Ingestion
    service = StarzErpIngestionService()
    stats = await service.run_full_ingestion(starz_session, sensei_session)
    
    # 3. Verify Mapping Results
    assert stats["warehouses"] == 1
    assert stats["articles"] == 1
    assert stats["locations"] == 1
    assert stats["lpns"] == 1
    assert stats["devices"] == 1
    assert stats["workstations"] == 1
    
    # 4. Deep verification of mapped entities in Sensei OS
    
    # Warehouse mapping
    res = await sensei_session.execute(select(Warehouse).where(Warehouse.code == "STZ01"))
    sensei_w = res.scalar_one()
    assert sensei_w.name == "Starz Main"
    assert sensei_w.address == "Main Distribution Center"
    
    # Product mapping
    res = await sensei_session.execute(select(Product).where(Product.part_number == "PRD-100"))
    sensei_p = res.scalar_one()
    assert sensei_p.name == "Industrial Sensor"
    assert sensei_p.standard_cost == 125.50
    
    # Location mapping
    res = await sensei_session.execute(select(Location).where(Location.name == "LOC-A1"))
    sensei_l = res.scalar_one()
    assert sensei_l.warehouse_id == sensei_w.id
    assert sensei_l.location_type == "shelf"
    
    # LPN mapping
    res = await sensei_session.execute(select(LicensePlate).where(LicensePlate.number == "LPN-001"))
    sensei_lp = res.scalar_one()
    assert sensei_lp.status == "active"
    assert sensei_lp.location_id == sensei_l.id
    
    # Inventory mapping
    res = await sensei_session.execute(select(InventoryLevel).where(InventoryLevel.lpn_id == sensei_lp.id))
    sensei_il = res.scalar_one()
    assert sensei_il.product_id == sensei_p.id
    assert sensei_il.quantity_on_hand == 10.0
    
    # Device mapping
    res = await sensei_session.execute(select(WmsDevice).where(WmsDevice.device_identifier == "DEV-X"))
    sensei_d = res.scalar_one()
    assert sensei_d.name == "Handheld Scanner 1"
    assert sensei_d.warehouse_id == sensei_w.id
    assert sensei_d.capabilities["scanning"] is True
    
    # Workstation mapping
    res = await sensei_session.execute(select(WmsWorkstation).where(WmsWorkstation.code == "WS-01"))
    sensei_ws = res.scalar_one()
    assert sensei_ws.warehouse_id == sensei_w.id
    assert sensei_ws.scanner_model == "Zebra-X1"

@pytest.mark.asyncio
async def test_starz_ingestion_edge_cases(starz_session, sensei_session):
    """
    Verifies edge cases in ingestion (e.g., putaway status, missing SKU).
    """
    # 1. Prepare Starz ERP data with edge cases
    sw = StarzWarehouse(id=1, name="Starz Main", code="STZ01")
    starz_session.add(sw)
    
    # LPN with 'putaway' status and missing SKU
    lp1 = StarzLicensePlate(id=1, code="LPN-PUTAWAY", warehouse_id=1, status="putaway")
    starz_session.add(lp1)
    
    # LPN with unknown SKU
    lp2 = StarzLicensePlate(id=2, code="LPN-UNKNOWN", warehouse_id=1, item_sku="UNKNOWN-SKU", quantity=5.0)
    starz_session.add(lp2)
    
    await starz_session.commit()
    
    # 2. Run Ingestion
    service = StarzErpIngestionService()
    await service.run_full_ingestion(starz_session, sensei_session)
    
    # 3. Verify Mapping
    # 'putaway' should be mapped to 'active'
    res = await sensei_session.execute(select(LicensePlate).where(LicensePlate.number == "LPN-PUTAWAY"))
    lp_mapped = res.scalar_one()
    assert lp_mapped.status == "active"
    
    # LPN with unknown SKU should still be created, but no InventoryLevel
    res = await sensei_session.execute(select(LicensePlate).where(LicensePlate.number == "LPN-UNKNOWN"))
    assert res.scalar_one() is not None
    
    res = await sensei_session.execute(select(InventoryLevel))
    levels = res.scalars().all()
    assert len(levels) == 0 # No product found for UNKNOWN-SKU

@pytest.mark.asyncio
async def test_ingestion_idempotency(starz_session, sensei_session):
    """
    Verifies that running ingestion multiple times doesn't create duplicate records.
    """
    sw = StarzWarehouse(id=1, name="Original Name", code="STZ01")
    starz_session.add(sw)
    await starz_session.commit()
    
    service = StarzErpIngestionService()
    
    # First run
    await service.run_full_ingestion(starz_session, sensei_session)
    
    # Update name in Starz
    sw.name = "Updated Name"
    await starz_session.commit()
    
    # Second run
    await service.run_full_ingestion(starz_session, sensei_session)
    
    # Verify only 1 warehouse exists and it's updated
    res = await sensei_session.execute(select(Warehouse))
    warehouses = res.scalars().all()
    assert len(warehouses) == 1
    assert warehouses[0].name == "Updated Name"
