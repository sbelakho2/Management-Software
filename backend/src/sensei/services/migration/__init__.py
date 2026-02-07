"""Migration services for legacy system imports.

This module provides import services for migrating data from legacy systems
to the Sensei platform.

Supported Legacy Systems:
- erpStarz: Symfony/PHP ERP system (Tunisia-based manufacturing)

Usage:
    from sensei.services.migration import ERPStarzImportService, migrate_erpstarz_full
    
    async with async_session_factory() as db:
        # Full system migration
        result = await migrate_erpstarz_full(db, actor_id="admin")
        
        # Or module-by-module
        service = ERPStarzImportService(db)
        hr_result = await service.import_hr_module(...)
        inv_result = await service.import_inventory_module(...)
        
        await db.commit()
"""

from sensei.services.migration.erpstarz_import import (
    ERPStarzImportService,
    ERPStarzImportConfig,
    ERPStarzImportResult,
    ImportModule,
    ERPSTARZ_ENTITY_MAP,
    migrate_erpstarz_full,
    check_erpstarz_availability,
)

__all__ = [
    "ERPStarzImportService",
    "ERPStarzImportConfig",
    "ERPStarzImportResult",
    "ImportModule",
    "ERPSTARZ_ENTITY_MAP",
    "migrate_erpstarz_full",
    "check_erpstarz_availability",
]
