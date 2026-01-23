# Backend Error Fix Strategy - 1907 Errors

## COMPLETED ✅
- Phase 1: Fixed 7 critical undefined variable/import errors
  - auth.py: Added settings import  
  - document_intelligence.py: Removed duplicate return
  - qms_quality.py: Added Any import
  - ai_reasoning.py: Added Any import
  - visual_quality_inspection.py: Added UUID import

## REMAINING MAJOR CATEGORIES

### 1. API Endpoints - "object" has no attribute "id" (307 errors)
**Root Cause**: FastAPI `Depends()` returns `object` type, needs explicit annotation
**Pattern**: `current_user = Depends(get_current_user)` 
**Fix**: Add type annotation: `current_user: User = Depends(get_current_user)`

**Files to Fix** (Top 10):
- backend/src/sensei/api/v1/endpoints/training.py (28 occurrences)
- backend/src/sensei/api/v1/endpoints/tasks.py (22)
- backend/src/sensei/api/v1/endpoints/kanban.py (21)
- backend/src/sensei/api/v1/endpoints/opportunities.py (20)
- backend/src/sensei/api/v1/endpoints/quotes.py (20)
- backend/src/sensei/api/v1/endpoints/a3.py (18)
- backend/src/sensei/api/v1/endpoints/andon.py (18)
- backend/src/sensei/api/v1/endpoints/purchase.py (18)
- backend/src/sensei/api/v1/endpoints/obeya.py (17)
- backend/src/sensei/api/v1/endpoints/contacts.py (10)

###

 2. Today Screen Services - Model Attribute Mismatches (282 errors)
**Root Cause**: Pydantic models in services don't match SQLAlchemy database models
**Pattern**: Accessing `.work_center_id` but model defines `.work_center`
**Fix**: Either update Pydantic models OR update code to use correct attributes

**Files to Fix**:
- backend/src/sensei/services/ops/today_screen_v2/shop_floor.py (111 errors)
- backend/src/sensei/services/ops/today_screen.py (81 errors)

**Specific Issues**:
- `WorkOrderAtRisk` missing: days_until_due, scheduled_ship_date, work_center_id, priority
- `CriticalAndon` missing: work_center_id, work_center_name, description, minutes_open, acknowledged
- `StationEfficiency` missing: work_center_id, current_efficiency, etc.
- `KanbanAlert` missing: material_code, work_center_id, days_overdue
- `ExpiringCertification` missing: user_id, certification_type, is_expired
- `CAPAVerification` missing: capa_number, days_until_due, is_overdue
- `ScheduledTraining` missing: scheduled_date, scheduled_time, is_user_enrolled

### 3. Setup Wizard - Function Signature Mismatches (80 errors)
**Root Cause**: Calling functions with wrong arguments
**Fix**: Update function calls to match signatures OR update function definitions

- backend/src/sensei/services/core/setup_wizard.py

### 4. Repository Pattern - ModelT Generic Issues (12 errors)
**Root Cause**: Generic `ModelT` type doesn't know about mixins (deleted_at, created_at)
**Fix**: Add proper type constraints or use Protocol classes

- backend/src/sensei/api/repository.py

### 5. SQLAlchemy Query Filters - Type Mismatch (150+ errors)  
**Root Cause**: `filters: List[bool] = []` but appending `ColumnElement[bool]`
**Pattern**: `filters.append(Model.field == value)`
**Fix**: Change to `filters: List[Any] = []` OR use proper SQLAlchemy types

**Files Affected**: Most API endpoint files (a3.py, obeya.py, ctq.py, etc.)

### 6. Import Stubs - Missing Type Information (54 errors)
**Pattern**: `Library stubs not installed for "jose"  [import-untyped]`
**Fix**: Install type stubs OR add `# type: ignore` comments
**Command**: `pip install types-psutil types-jose types-python-jose`

## RECOMMENDED FIX ORDER

1. **CRITICAL** - Fix remaining undefined variables (manual investigation needed)
   - backend/src/sensei/services/smart_ingestion.py
   - backend/src/sensei/services/ai/ai_reasoning.py (SearchResult, SearchChunk)

2. **HIGH** - Fix API endpoints object.id (307 errors - can be automated)
   - Add type annotations to all `current_user` parameters
   - Pattern replacement across all endpoint files

3. **HIGH** - Fix today_screen models (282 errors - needs data model review)
   - Review Pydantic model definitions in today_screen_models.py
   - Update to match database models OR vice versa

4. **MEDIUM** - Fix SQLAlchemy filter types (150+ errors - can be automated)
   - Change `List[bool]` to `List[Any]` in query building code

5. **MEDIUM** - Fix setup_wizard call-arg errors (80 errors)
   - Review function signatures and update calls

6. **LOW** - Install missing type stubs (54 errors)
   - Run pip install commands

7. **LOW** - Fix miscellaneous issues
   - Enum attributes, read-only properties, etc.

## AUTOMATION OPPORTUNITIES

Can be automated:
- API endpoint type annotations (bulk regex replacement)
- SQLAlchemy filter type hints (bulk regex replacement)
- Missing imports (targeted additions)

Needs manual review:
- Model attribute mismatches (business logic decision)
- Function signature changes (breaking changes)
- Undefined variables (logic errors)

## ESTIMATED EFFORT

- Automated fixes: ~60% of errors (1100+)
- Semi-automated: ~30% (560+)
- Manual fixes: ~10% (200+)

Total: Several hours of systematic work
