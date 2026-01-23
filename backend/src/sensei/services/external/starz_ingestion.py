"""
Service for ingesting data from starzERP (MySQL) into Sensei OS (PostgreSQL).
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.inventory import Warehouse, Location, WmsDevice, WmsWorkstation, LicensePlate, InventoryLevel
from sensei.models.product import Product, UnitOfMeasure, ProductStatus
from sensei.models.external.starz_erp import (
    StarzWarehouse,
    StarzStockLocation,
    StarzWmsDevice,
    StarzWmsWorkstation,
    StarzLicensePlate,
    StarzArticle,
)

logger = logging.getLogger(__name__)

class StarzErpIngestionService:
    """Ingestion service for starzERP data."""

    async def ingest_warehouses(self, starz_db: AsyncSession, sensei_db: AsyncSession) -> int:
        """Sync warehouses from starzERP."""
        result = await starz_db.execute(select(StarzWarehouse))
        starz_warehouses = result.scalars().all()
        
        count = 0
        for sw in starz_warehouses:
            # Try to find by code
            stmt = select(Warehouse).where(Warehouse.code == sw.code)
            sensei_w = (await sensei_db.execute(stmt)).scalar_one_or_none()
            
            if sensei_w:
                sensei_w.name = sw.name
                sensei_w.address = sw.description
            else:
                sensei_w = Warehouse(
                    name=sw.name,
                    code=sw.code,
                    address=sw.description
                )
                sensei_db.add(sensei_w)
            count += 1
        
        await sensei_db.commit()
        return count

    async def ingest_devices(self, starz_db: AsyncSession, sensei_db: AsyncSession) -> int:
        """Sync devices from starzERP."""
        result = await starz_db.execute(select(StarzWmsDevice))
        starz_devices = result.scalars().all()
        
        count = 0
        for sd in starz_devices:
            # Find warehouse in Sensei OS by starz warehouse code
            # We first need to get the starz warehouse code
            sw_stmt = select(StarzWarehouse).where(StarzWarehouse.id == sd.warehouse_id)
            sw = (await starz_db.execute(sw_stmt)).scalar_one_or_none()
            
            if not sw:
                logger.warning(f"Warehouse ID {sd.warehouse_id} not found for device {sd.device_identifier}")
                continue
                
            sensei_w_stmt = select(Warehouse).where(Warehouse.code == sw.code)
            sensei_w = (await sensei_db.execute(sensei_w_stmt)).scalar_one_or_none()
            
            if not sensei_w:
                logger.warning(f"Warehouse code {sw.code} not found in Sensei OS for device {sd.device_identifier}")
                continue

            stmt = select(WmsDevice).where(WmsDevice.device_identifier == sd.device_identifier)
            sensei_d = (await sensei_db.execute(stmt)).scalar_one_or_none()
            
            if sensei_d:
                sensei_d.name = sd.name
                sensei_d.device_type = sd.device_type
                sensei_d.status = sd.status
                sensei_d.warehouse_id = sensei_w.id
                sensei_d.capabilities = sd.capabilities or {}
                sensei_d.last_seen_at = sd.last_seen_at
            else:
                sensei_d = WmsDevice(
                    device_identifier=sd.device_identifier,
                    name=sd.name,
                    device_type=sd.device_type,
                    status=sd.status,
                    warehouse_id=sensei_w.id,
                    capabilities=sd.capabilities or {},
                    last_seen_at=sd.last_seen_at
                )
                sensei_db.add(sensei_d)
            count += 1
            
        await sensei_db.commit()
        return count

    async def ingest_workstations(self, starz_db: AsyncSession, sensei_db: AsyncSession) -> int:
        """Sync workstations from starzERP."""
        result = await starz_db.execute(select(StarzWmsWorkstation))
        starz_workstations = result.scalars().all()
        
        count = 0
        for sws in starz_workstations:
            # Find warehouse
            sw_stmt = select(StarzWarehouse).where(StarzWarehouse.id == sws.warehouse_id)
            sw = (await starz_db.execute(sw_stmt)).scalar_one_or_none()
            
            if not sw:
                continue
                
            sensei_w_stmt = select(Warehouse).where(Warehouse.code == sw.code)
            sensei_w = (await sensei_db.execute(sensei_w_stmt)).scalar_one_or_none()
            
            if not sensei_w:
                continue

            stmt = select(WmsWorkstation).where(WmsWorkstation.code == sws.workstation_code)
            sensei_ws = (await sensei_db.execute(stmt)).scalar_one_or_none()
            
            if sensei_ws:
                sensei_ws.warehouse_id = sensei_w.id
                sensei_ws.station_type = sws.station_type
                sensei_ws.scanner_model = sws.scanner_model
                sensei_ws.scanner_serial = sws.scanner_serial
                sensei_ws.connection_type = sws.connection_type
                sensei_ws.pc_hostname = sws.pc_hostname
                sensei_ws.is_active = sws.is_active
                sensei_ws.last_activity_at = sws.last_activity
            else:
                sensei_ws = WmsWorkstation(
                    code=sws.workstation_code,
                    warehouse_id=sensei_w.id,
                    station_type=sws.station_type,
                    scanner_model=sws.scanner_model,
                    scanner_serial=sws.scanner_serial,
                    connection_type=sws.connection_type,
                    pc_hostname=sws.pc_hostname,
                    is_active=sws.is_active,
                    last_activity_at=sws.last_activity
                )
                sensei_db.add(sensei_ws)
            count += 1
            
        await sensei_db.commit()
        return count

    async def ingest_locations(self, starz_db: AsyncSession, sensei_db: AsyncSession) -> int:
        """Sync stock locations from starzERP."""
        result = await starz_db.execute(select(StarzStockLocation))
        starz_locations = result.scalars().all()
        
        count = 0
        for sl in starz_locations:
            # Find warehouse
            sw_stmt = select(StarzWarehouse).where(StarzWarehouse.id == sl.warehouse_id)
            sw = (await starz_db.execute(sw_stmt)).scalar_one_or_none()
            
            if not sw:
                continue
                
            sensei_w_stmt = select(Warehouse).where(Warehouse.code == sw.code)
            sensei_w = (await sensei_db.execute(sensei_w_stmt)).scalar_one_or_none()
            
            if not sensei_w:
                continue

            # In Sensei OS, Location name is used for the code if it's from starzERP
            stmt = select(Location).where(
                Location.warehouse_id == sensei_w.id,
                Location.name == sl.code
            )
            sensei_l = (await sensei_db.execute(stmt)).scalar_one_or_none()
            
            if sensei_l:
                sensei_l.location_type = sl.type
            else:
                sensei_l = Location(
                    warehouse_id=sensei_w.id,
                    name=sl.code,
                    location_type=sl.type
                )
                sensei_db.add(sensei_l)
            count += 1
            
        await sensei_db.commit()
        return count

    async def ingest_articles(self, starz_db: AsyncSession, sensei_db: AsyncSession) -> int:
        """Sync Articles from starzERP as Products in Sensei OS."""
        result = await starz_db.execute(select(StarzArticle))
        starz_articles = result.scalars().all()
        
        count = 0
        for sa in starz_articles:
            stmt = select(Product).where(Product.part_number == sa.code_reference)
            sensei_p = (await sensei_db.execute(stmt)).scalar_one_or_none()
            
            if sensei_p:
                sensei_p.name = sa.description or sa.code_reference
                sensei_p.standard_cost = sa.prix
            else:
                sensei_p = Product(
                    name=sa.description or sa.code_reference,
                    part_number=sa.code_reference,
                    standard_cost=sa.prix,
                    unit_of_measure=UnitOfMeasure.PIECE, # Default
                    status=ProductStatus.ACTIVE
                )
                sensei_db.add(sensei_p)
            count += 1
            
        await sensei_db.commit()
        return count

    async def ingest_lpns(self, starz_db: AsyncSession, sensei_db: AsyncSession) -> int:
        """Sync License Plates from starzERP."""
        result = await starz_db.execute(select(StarzLicensePlate))
        starz_lpns = result.scalars().all()
        
        count = 0
        for sl in starz_lpns:
            # Find location mapping
            sensei_location_id = None
            if sl.location_id:
                sloc_stmt = select(StarzStockLocation).where(StarzStockLocation.id == sl.location_id)
                sloc = (await starz_db.execute(sloc_stmt)).scalar_one_or_none()
                if sloc:
                    # Find warehouse for this location to be sure
                    sw_stmt = select(StarzWarehouse).where(StarzWarehouse.id == sloc.warehouse_id)
                    sw = (await starz_db.execute(sw_stmt)).scalar_one_or_none()
                    
                    if sw:
                        sensei_w_stmt = select(Warehouse).where(Warehouse.code == sw.code)
                        sensei_w = (await sensei_db.execute(sensei_w_stmt)).scalar_one_or_none()
                        
                        if sensei_w:
                            l_stmt = select(Location).where(
                                Location.warehouse_id == sensei_w.id,
                                Location.name == sloc.code
                            )
                            sensei_l = (await sensei_db.execute(l_stmt)).scalar_one_or_none()
                            if sensei_l:
                                sensei_location_id = sensei_l.id

            # Find or create LPN
            stmt = select(LicensePlate).where(LicensePlate.number == sl.code)
            sensei_lp = (await sensei_db.execute(stmt)).scalar_one_or_none()
            
            status_mapped = sl.status.lower() if sl.status else "active"
            if status_mapped == "putaway": # erpStarz uses putaway status sometimes
                status_mapped = "active"

            if sensei_lp:
                sensei_lp.status = status_mapped
                sensei_lp.location_id = sensei_location_id
            else:
                sensei_lp = LicensePlate(
                    number=sl.code,
                    status=status_mapped,
                    location_id=sensei_location_id
                )
                sensei_db.add(sensei_lp)
            
            # Flush to get LPN ID if new
            await sensei_db.flush()

            # Handle inventory levels if SKU and quantity are present on LPN
            if sl.item_sku and sl.quantity:
                p_stmt = select(Product).where(Product.part_number == sl.item_sku)
                sensei_p = (await sensei_db.execute(p_stmt)).scalar_one_or_none()
                
                if sensei_p and sensei_location_id:
                    # Check if inventory level exists for this LPN
                    il_stmt = select(InventoryLevel).where(
                        InventoryLevel.lpn_id == sensei_lp.id
                    )
                    sensei_il = (await sensei_db.execute(il_stmt)).scalar_one_or_none()
                    
                    if sensei_il:
                        sensei_il.product_id = sensei_p.id
                        sensei_il.location_id = sensei_location_id
                        sensei_il.quantity_on_hand = sl.quantity
                    else:
                        sensei_il = InventoryLevel(
                            product_id=sensei_p.id,
                            location_id=sensei_location_id,
                            lpn_id=sensei_lp.id,
                            quantity_on_hand=sl.quantity
                        )
                        sensei_db.add(sensei_il)

            count += 1
            
        await sensei_db.commit()
        return count

    async def run_full_ingestion(self, starz_db: AsyncSession, sensei_db: AsyncSession) -> Dict[str, int]:
        """Run all ingestion tasks in correct order."""
        stats = {}
        stats["warehouses"] = await self.ingest_warehouses(starz_db, sensei_db)
        stats["articles"] = await self.ingest_articles(starz_db, sensei_db)
        stats["locations"] = await self.ingest_locations(starz_db, sensei_db)
        stats["lpns"] = await self.ingest_lpns(starz_db, sensei_db)
        stats["devices"] = await self.ingest_devices(starz_db, sensei_db)
        stats["workstations"] = await self.ingest_workstations(starz_db, sensei_db)
        return stats
