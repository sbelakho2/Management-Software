# Starz Morocco Backend

Intelligent Management System for Manufacturing Excellence.

## Overview

The Starz Morocco backend is built with FastAPI and provides:

- RESTful API endpoints for all system functionality
- SQLAlchemy 2.0 async database models
- Redis caching and Celery task queue integration
- MinIO-based file storage
- Comprehensive middleware for logging, timing, and correlation tracking

## Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Run tests:
   ```bash
   pytest tests/ -v
   ```

## Project Structure

```
src/sensei/
├── api/           # API endpoints
├── core/          # Core configuration and utilities
├── middleware/    # Request/response middleware
├── models/        # SQLAlchemy database models
│   ├── external/  # Legacy database models (StarzERP)
│   └── ...        # Sensei OS domain models
└── services/
    ├── external/  # External system integrations
    │   └── starz_import_service.py  # StarzERP data migration
    └── ...        # Domain services
```

## Data Migration

### StarzERP Import Service

The `starz_import_service.py` provides comprehensive data migration from legacy StarzERP MySQL to Sensei OS PostgreSQL:

- **56 entity types** across all modules (HR, Inventory, Purchasing, Sales, Finance, Quality)
- **Dependency-aware ordering** ensures FK relationships are satisfied
- **Conflict resolution** (skip, update, fail)
- **Progress tracking** with real-time status

```python
from sensei.services.external.starz_import_service import StarzErpImportService

service = StarzErpImportService(
    sensei_session=db,
    starz_connection_string="mysql+aiomysql://user:pass@host/starz",
)
result = await service.import_all()
```

See [StarzERP Data Migration Guide](../docs/guides/starz-erp-data-migration.md) for full documentation.

## License

Proprietary - Starz Morocco. All rights reserved.
