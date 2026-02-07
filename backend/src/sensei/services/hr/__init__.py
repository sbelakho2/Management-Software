"""HR Services Package.

This package provides HR-related services including:
- Employee lifecycle management
- Compensation and benefits
- Leave management
- Recruiting and talent management
- Legacy data import (jurisdiction-aware)
"""

from sensei.services.hr.legacy_import import (
    HRLegacyImportService,
    LegacyImportConfig,
    LegacyImportResult,
    ImportSourceType,
    migrate_legacy_employees,
    DEFAULT_JURISDICTION,
    VALID_JURISDICTIONS,
)

__all__ = [
    # Legacy import service
    "HRLegacyImportService",
    "LegacyImportConfig",
    "LegacyImportResult",
    "ImportSourceType",
    "migrate_legacy_employees",
    "DEFAULT_JURISDICTION",
    "VALID_JURISDICTIONS",
]
