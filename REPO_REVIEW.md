# Repository Review & Audit Report

## Summary
- **Frontend**: PASSED. TypeScript check (`tsc`) and Linter (`eslint`) found 0 errors / 0 warnings.
- **Backend**: FAILED. Static analysis (`mypy`) found **1907 errors** across 188 files.

## Frontend Review
All 200+ source files in `frontend/src` passed strict TypeScript type checking and linting.
- Status: **Clean**
- Key dependencies: Next.js, React, Tailwind, Capacitor.

## Backend Review
Significant wiring issues found. Use of undefined variables, missing class attributes, and incorrect function arguments.

### Critical "Wiring" Issues (Functions/Attributes Missing)
The following files have severe issues where code calls functions or accesses attributes that do not exist:

#### 1. `backend/src/sensei/services/ops/today_screen_v2/shop_floor.py`
**Status: CRITICAL (Hundreds of errors)**
- Methods called with wrong arguments (e.g., `CriticalAndon`, `StationEfficiency`).
- Attributes accessed that don't exist on models (e.g., `days_until_due`, `work_center_id`).
- **Example Bug:** `Unexpected keyword argument "work_center_id" for "CriticalAndon"`

#### 2. `backend/src/sensei/services/ai/document_intelligence.py`
**Status: CRITICAL**
- Usage of undefined variables. The code will crash immediately if run.
- **Example Bug:** `Name "cells" is not defined`, `Name "headers" is not defined`.
- **Example Bug:** `"None" has no attribute "get_inputs"` (Logic error assuming non-None).

#### 3. `backend/src/sensei/services/ops/tps_teacher.py`
**Status: FAIL**
- Classes missing expected methods.
- **Example Bug:** `"AsyncImprovementKataAssistant" has no attribute "sessions"`
- **Example Bug:** `"AsyncJidokaMentor" has no attribute "_assess_quality_impact"`

#### 4. `backend/src/sensei/api/v1/endpoints` (Various files)
**Status: FAIL**
- widespread issue with `object` type inference where `.id` is accessed but not known.
- incorrect arguments passed to `NotFoundError`.
- **Files Affected:** `kanban.py`, `obeya.py`, `learning.py`, `andon.py`, `rfqs.py`, `quotes.py`.

#### 5. `backend/src/sensei/main.py`
**Status: FAIL**
- Incorrect service verification.
- **Example Bug:** `Unexpected keyword argument "storage_client" for "DatabaseBackupService"`

## Detailed File Status List

### Frontend (Sample)
- `frontend/src/app/page.tsx`: **OK**
- `frontend/src/components/ui/*.tsx`: **OK**
- (All frontend files are OK)

### Backend (Problematic Files)
| File Path | Status | Issues |
|-----------|--------|--------|
| `backend/src/sensei/services/ops/today_screen_v2/shop_floor.py` | **FAIL** | 100+ Errors (Attr missing, Arg mismatch) |
| `backend/src/sensei/services/ai/document_intelligence.py` | **FAIL** | Undefined variables, Import errors |
| `backend/src/sensei/services/ops/tps_teacher.py` | **FAIL** | Missing methods on Helper classes |
| `backend/src/sensei/api/v1/endpoints/kanban.py` | **FAIL** | Argument mismatch for Exceptions |
| `backend/src/sensei/api/v1/endpoints/learning.py` | **FAIL** | Type inference failure on SQL models |
| `backend/src/sensei/api/v1/endpoints/obeya.py` | **FAIL** | SQL Query construction errors |
| `backend/src/sensei/services/utils/pdf_generation.py` | **FAIL** | List/Dict type mismatches |
| `backend/src/sensei/services/ai/enhanced_ml_pipeline.py` | **FAIL** | Missing methods/imports |

*(Note: 188 files total have errors. See terminal output for full log)*
