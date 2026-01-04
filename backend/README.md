# Sensei OS Backend

Intelligent Management and Teaching System for Starz Morocco.

## Overview

The Sensei OS backend is built with FastAPI and provides:

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
└── models/        # SQLAlchemy database models
```

## License

Proprietary - Starz Morocco
