# Sensei OS - Full Backend Audit Report

**Date:** 2026-01-23 10:44:41
**Total Errors Found:** 1907
**Files Affected:** 188

## Executive Summary
This report details critical wiring issues found during the static analysis audit of the backend codebase. The primary issues found are `[attr-defined]` (attributes missing on classes) and `[call-arg]` (incorrect function signatures). These indicate a mismatch between the Data Models/SQLAlchemy schemas and the Service layer business logic.

## Detailed Error Log by File

### `backend/src/sensei/api/deps.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 16 | `Library stubs not installed for "jose"  [import-untyped]` |
| 31 | `The return type of an async generator function should be "AsyncGenerator" or one of its supertypes  [misc]` |
| 396 | `Incompatible default for argument "requests" (default has type "None", argument has type "int")  [assignment]` |
| 397 | `Incompatible default for argument "window" (default has type "None", argument has type "int")  [assignment]` |

### `backend/src/sensei/api/exceptions.py`
**Errors:** 6

| Line | Error Message |
|------|---------------|
| 503 | `Argument 2 to "add_exception_handler" of "Starlette" has incompatible type "Callable[[Request, SenseiException], Coroutine[Any, Any, JSONResponse]]"; expected "Callable[[Request, Exception], Response \| Awaitable[Response]] \| Callable[[WebSocket, Exception], Awaitable[None]]"  [arg-type]` |
| 506 | `Argument 2 to "add_exception_handler" of "Starlette" has incompatible type "Callable[[Request, HTTPException], Coroutine[Any, Any, JSONResponse]]"; expected "Callable[[Request, Exception], Response \| Awaitable[Response]] \| Callable[[WebSocket, Exception], Awaitable[None]]"  [arg-type]` |
| 509 | `Argument 2 to "add_exception_handler" of "Starlette" has incompatible type "Callable[[Request, RequestValidationError], Coroutine[Any, Any, JSONResponse]]"; expected "Callable[[Request, Exception], Response \| Awaitable[Response]] \| Callable[[WebSocket, Exception], Awaitable[None]]"  [arg-type]` |
| 510 | `Argument 2 to "add_exception_handler" of "Starlette" has incompatible type "Callable[[Request, ValidationError], Coroutine[Any, Any, JSONResponse]]"; expected "Callable[[Request, Exception], Response \| Awaitable[Response]] \| Callable[[WebSocket, Exception], Awaitable[None]]"  [arg-type]` |
| 513 | `Argument 2 to "add_exception_handler" of "Starlette" has incompatible type "Callable[[Request, IntegrityError], Coroutine[Any, Any, JSONResponse]]"; expected "Callable[[Request, Exception], Response \| Awaitable[Response]] \| Callable[[WebSocket, Exception], Awaitable[None]]"  [arg-type]` |
| 514 | `Argument 2 to "add_exception_handler" of "Starlette" has incompatible type "Callable[[Request, SQLAlchemyError], Coroutine[Any, Any, JSONResponse]]"; expected "Callable[[Request, Exception], Response \| Awaitable[Response]] \| Callable[[WebSocket, Exception], Awaitable[None]]"  [arg-type]` |

### `backend/src/sensei/api/repository.py`
**Errors:** 12

| Line | Error Message |
|------|---------------|
| 103 | `"type[ModelT]" has no attribute "deleted_at"  [attr-defined]` |
| 172 | `"type[ModelT]" has no attribute "deleted_at"  [attr-defined]` |
| 201 | `"type[ModelT]" has no attribute "deleted_at"  [attr-defined]` |
| 245 | `"type[ModelT]" has no attribute "deleted_at"  [attr-defined]` |
| 246 | `"type[ModelT]" has no attribute "deleted_at"  [attr-defined]` |
| 282 | `"type[ModelT]" has no attribute "created_at"  [attr-defined]` |
| 309 | `"type[ModelT]" has no attribute "deleted_at"  [attr-defined]` |
| 326 | `"type[ModelT]" has no attribute "deleted_at"  [attr-defined]` |
| 623 | `"ModelT" has no attribute "deleted_at"  [attr-defined]` |
| 626 | `"ModelT" has no attribute "deleted_at"  [attr-defined]` |
| 699 | `"type[ModelT]" has no attribute "deleted_at"  [attr-defined]` |
| 734 | `"type[ModelT]" has no attribute "deleted_at"  [attr-defined]` |

### `backend/src/sensei/api/v1/endpoints/a3.py`
**Errors:** 55

| Line | Error Message |
|------|---------------|
| 273 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 287 | `"object" has no attribute "id"  [attr-defined]` |
| 298 | `"object" has no attribute "id"  [attr-defined]` |
| 341 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 380 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 382 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 384 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 386 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 388 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 391 | `Argument 1 to "append" of "list" has incompatible type "BinaryExpression[bool]"; expected "bool"  [arg-type]` |
| 395 | `Argument 1 to "append" of "list" has incompatible type "BinaryExpression[bool]"; expected "bool"  [arg-type]` |
| 399 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 401 | `Argument 1 to "append" of "list" has incompatible type "BinaryExpression[bool]"; expected "bool"  [arg-type]` |
| 410 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 412 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 412 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 419 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 419 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 458 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 471 | `"object" has no attribute "id"  [attr-defined]` |
| 496 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 503 | `Property "is_deleted" defined in "SoftDeleteMixin" is read-only  [misc]` |
| 505 | `"object" has no attribute "id"  [attr-defined]` |
| 528 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 540 | `"object" has no attribute "id"  [attr-defined]` |
| 565 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 576 | `"object" has no attribute "id"  [attr-defined]` |
| 638 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 647 | `"object" has no attribute "id"  [attr-defined]` |
| 673 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 684 | `"object" has no attribute "id"  [attr-defined]` |
| 688 | `"object" has no attribute "id"  [attr-defined]` |
| 714 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 727 | `"object" has no attribute "id"  [attr-defined]` |
| 752 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 763 | `"object" has no attribute "id"  [attr-defined]` |
| 788 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 800 | `"object" has no attribute "id"  [attr-defined]` |
| 825 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 836 | `"object" has no attribute "id"  [attr-defined]` |
| 869 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 993 | `"object" has no attribute "id"  [attr-defined]` |
| 1079 | `"object" has no attribute "id"  [attr-defined]` |
| 1151 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1182 | `"object" has no attribute "id"  [attr-defined]` |
| 1183 | `"object" has no attribute "id"  [attr-defined]` |
| 1184 | `"object" has no attribute "id"  [attr-defined]` |
| 1188 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1188 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1195 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1195 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1236 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1236 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1243 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1243 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |

### `backend/src/sensei/api/v1/endpoints/accounts.py`
**Errors:** 7

| Line | Error Message |
|------|---------------|
| 576 | `"object" has no attribute "id"  [attr-defined]` |
| 676 | `"object" has no attribute "id"  [attr-defined]` |
| 714 | `"object" has no attribute "is_superuser"  [attr-defined]` |
| 722 | `"object" has no attribute "id"  [attr-defined]` |
| 756 | `"object" has no attribute "id"  [attr-defined]` |
| 791 | `"object" has no attribute "is_superuser"  [attr-defined]` |
| 798 | `"object" has no attribute "id"  [attr-defined]` |

### `backend/src/sensei/api/v1/endpoints/ai_health.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 35 | `"UserRole" has no attribute "name"  [attr-defined]` |

### `backend/src/sensei/api/v1/endpoints/analytics.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 23 | `Variable "sensei.api.v1.endpoints.analytics.AllowAnalytics" is not valid as a type  [valid-type]` |
| 32 | `Variable "sensei.api.v1.endpoints.analytics.AllowAnalytics" is not valid as a type  [valid-type]` |
| 115 | `Variable "sensei.api.v1.endpoints.analytics.AllowAnalytics" is not valid as a type  [valid-type]` |

### `backend/src/sensei/api/v1/endpoints/andon.py`
**Errors:** 36

| Line | Error Message |
|------|---------------|
| 457 | `"object" has no attribute "id"  [attr-defined]` |
| 459 | `"object" has no attribute "id"  [attr-defined]` |
| 460 | `"object" has no attribute "id"  [attr-defined]` |
| 516 | `Need type annotation for "signals_by_category" (hint: "signals_by_category: dict[<type>, <type>] = ...")  [var-annotated]` |
| 569 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 587 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 593 | `"object" has no attribute "id"  [attr-defined]` |
| 613 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 616 | `"object" has no attribute "id"  [attr-defined]` |
| 635 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 639 | `"object" has no attribute "id"  [attr-defined]` |
| 665 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 672 | `"object" has no attribute "id"  [attr-defined]` |
| 674 | `"object" has no attribute "id"  [attr-defined]` |
| 695 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 705 | `"object" has no attribute "id"  [attr-defined]` |
| 707 | `"object" has no attribute "id"  [attr-defined]` |
| 729 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 738 | `"object" has no attribute "id"  [attr-defined]` |
| 748 | `"object" has no attribute "id"  [attr-defined]` |
| 769 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 775 | `"object" has no attribute "id"  [attr-defined]` |
| 799 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 829 | `"object" has no attribute "id"  [attr-defined]` |
| 855 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 880 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 909 | `"object" has no attribute "id"  [attr-defined]` |
| 932 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 961 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 1025 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 1063 | `"object" has no attribute "id"  [attr-defined]` |
| 1064 | `"object" has no attribute "id"  [attr-defined]` |
| 1087 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 1099 | `Incompatible default for argument "db" (default has type "None", argument has type "AsyncSession")  [assignment]` |
| 1109 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 1113 | `"object" has no attribute "id"  [attr-defined]` |

### `backend/src/sensei/api/v1/endpoints/attachments.py`
**Errors:** 29

| Line | Error Message |
|------|---------------|
| 255 | `"object" has no attribute "id"  [attr-defined]` |
| 287 | `"object" has no attribute "id"  [attr-defined]` |
| 294 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 300 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 341 | `"object" has no attribute "id"  [attr-defined]` |
| 349 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 355 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 380 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 442 | `Incompatible return value type (got "PaginatedResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 481 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 514 | `"object" has no attribute "id"  [attr-defined]` |
| 518 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 547 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 596 | `"object" has no attribute "id"  [attr-defined]` |
| 602 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 625 | `"object" has no attribute "id"  [attr-defined]` |
| 636 | `"object" has no attribute "id"  [attr-defined]` |
| 645 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 675 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 701 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 751 | `"object" has no attribute "id"  [attr-defined]` |
| 755 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 774 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 814 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 830 | `"object" has no attribute "id"  [attr-defined]` |
| 853 | `Incompatible return value type (got "PaginatedResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 877 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 899 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 934 | `Incompatible return value type (got "PaginatedResponse[Any]", expected "dict[str, Any]")  [return-value]` |

### `backend/src/sensei/api/v1/endpoints/audit_logs.py`
**Errors:** 13

| Line | Error Message |
|------|---------------|
| 92 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 160 | `Incompatible return value type (got "PaginatedResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 207 | `Incompatible return value type (got "PaginatedResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 254 | `Incompatible return value type (got "PaginatedResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 276 | `"object" has no attribute "id"  [attr-defined]` |
| 300 | `Incompatible return value type (got "PaginatedResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 351 | `Incompatible return value type (got "PaginatedResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 401 | `Incompatible return value type (got "PaginatedResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 488 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 513 | `Incompatible return value type (got "APIResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 557 | `Incompatible return value type (got "PaginatedResponse[Any]", expected "dict[str, Any]")  [return-value]` |
| 586 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "BinaryExpression[bool]"  [arg-type]` |
| 604 | `Incompatible return value type (got "PaginatedResponse[Any]", expected "dict[str, Any]")  [return-value]` |

### `backend/src/sensei/api/v1/endpoints/auditor.py`
**Errors:** 11

| Line | Error Message |
|------|---------------|
| 220 | `Unsupported operand types for + ("object" and "int")  [operator]` |
| 222 | `Unsupported operand types for + ("object" and "int")  [operator]` |
| 223 | `"object" has no attribute "add"  [attr-defined]` |
| 237 | `Unsupported operand types for * ("object" and "int")  [operator]` |
| 241 | `Argument 1 to "len" has incompatible type "object"; expected "Sized"  [arg-type]` |
| 313 | `Argument 1 to "AuditResponse" has incompatible type "**dict[str, int \| str \| None]"; expected "str"  [arg-type]` |
| 313 | `Argument 1 to "AuditResponse" has incompatible type "**dict[str, int \| str \| None]"; expected "str \| None"  [arg-type]` |
| 313 | `Argument 1 to "AuditResponse" has incompatible type "**dict[str, int \| str \| None]"; expected "int"  [arg-type]` |
| 414 | `Argument 1 to "AuditFindingResponse" has incompatible type "**dict[str, int \| str \| None]"; expected "str"  [arg-type]` |
| 414 | `Argument 1 to "AuditFindingResponse" has incompatible type "**dict[str, int \| str \| None]"; expected "str \| None"  [arg-type]` |
| 414 | `Argument 1 to "AuditFindingResponse" has incompatible type "**dict[str, int \| str \| None]"; expected "int"  [arg-type]` |

### `backend/src/sensei/api/v1/endpoints/auth.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 259 | `Name "settings" is not defined  [name-defined]` |
| 260 | `Name "settings" is not defined  [name-defined]` |
| 282 | `Unexpected keyword argument "message" for "TokenResponse"  [call-arg]` |

### `backend/src/sensei/api/v1/endpoints/cognitive_obeya.py`
**Errors:** 5

| Line | Error Message |
|------|---------------|
| 26 | `Invalid type comment or annotation  [valid-type]` |
| 53 | `"type[WorkOrder]" has no attribute "actual_end_date"  [attr-defined]` |
| 53 | `"type[WorkOrder]" has no attribute "due_date"  [attr-defined]` |
| 56 | `Unsupported operand types for / ("None" and "int")  [operator]` |
| 98 | `Invalid type comment or annotation  [valid-type]` |

### `backend/src/sensei/api/v1/endpoints/common_thread.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 68 | `Incompatible default for argument "current_user" (default has type "None", argument has type "User")  [assignment]` |
| 107 | `Incompatible default for argument "current_user" (default has type "None", argument has type "User")  [assignment]` |

### `backend/src/sensei/api/v1/endpoints/contacts.py`
**Errors:** 7

| Line | Error Message |
|------|---------------|
| 518 | `"object" has no attribute "id"  [attr-defined]` |
| 612 | `"object" has no attribute "id"  [attr-defined]` |
| 646 | `"object" has no attribute "is_superuser"  [attr-defined]` |
| 653 | `"object" has no attribute "id"  [attr-defined]` |
| 685 | `"object" has no attribute "id"  [attr-defined]` |
| 719 | `"object" has no attribute "is_superuser"  [attr-defined]` |
| 726 | `"object" has no attribute "id"  [attr-defined]` |

### `backend/src/sensei/api/v1/endpoints/context_bus.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 54 | `Incompatible default for argument "current_user" (default has type "None", argument has type "User")  [assignment]` |

### `backend/src/sensei/api/v1/endpoints/ctq.py`
**Errors:** 36

| Line | Error Message |
|------|---------------|
| 295 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 344 | `"object" has no attribute "id"  [attr-defined]` |
| 368 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 403 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 405 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 407 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 409 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 411 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 413 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 421 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 423 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 423 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 430 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 430 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 465 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 480 | `"object" has no attribute "id"  [attr-defined]` |
| 502 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 509 | `Property "is_deleted" defined in "SoftDeleteMixin" is read-only  [misc]` |
| 511 | `"object" has no attribute "id"  [attr-defined]` |
| 534 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 545 | `"object" has no attribute "id"  [attr-defined]` |
| 567 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 578 | `"object" has no attribute "id"  [attr-defined]` |
| 600 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 611 | `"object" has no attribute "id"  [attr-defined]` |
| 613 | `"object" has no attribute "id"  [attr-defined]` |
| 635 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 643 | `"object" has no attribute "id"  [attr-defined]` |
| 673 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 688 | `"object" has no attribute "id"  [attr-defined]` |
| 731 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 879 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 909 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 909 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 916 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 916 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |

### `backend/src/sensei/api/v1/endpoints/data_lineage.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 52 | `Incompatible default for argument "current_user" (default has type "None", argument has type "User")  [assignment]` |

### `backend/src/sensei/api/v1/endpoints/disaster_recovery_drill.py`
**Errors:** 6

| Line | Error Message |
|------|---------------|
| 459 | `Argument "description" to "set_rpo_target" of "DisasterRecoveryDrillService" has incompatible type "str \| None"; expected "str"  [arg-type]` |
| 483 | `Argument "description" to "set_rto_target" of "DisasterRecoveryDrillService" has incompatible type "str \| None"; expected "str"  [arg-type]` |
| 623 | `Argument "tables_included" to "BackupInfo" has incompatible type "list[str] \| None"; expected "list[str]"  [arg-type]` |
| 629 | `Argument "executed_by" to "start_drill" of "DisasterRecoveryDrillService" has incompatible type "str \| None"; expected "str"  [arg-type]` |
| 630 | `Argument "notes" to "start_drill" of "DisasterRecoveryDrillService" has incompatible type "str \| None"; expected "str"  [arg-type]` |
| 693 | `Argument "error_message" to "execute_step" of "DisasterRecoveryDrillService" has incompatible type "str \| None"; expected "str"  [arg-type]` |

### `backend/src/sensei/api/v1/endpoints/executive_intel.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 94 | `Variable "sensei.api.v1.endpoints.executive_intel.AllowExec" is not valid as a type  [valid-type]` |
| 141 | `Variable "sensei.api.v1.endpoints.executive_intel.AllowExec" is not valid as a type  [valid-type]` |
| 181 | `Variable "sensei.api.v1.endpoints.executive_intel.AllowExec" is not valid as a type  [valid-type]` |

### `backend/src/sensei/api/v1/endpoints/finance.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 205 | `Argument "rate" to "upsert_fx_rate" of "CurrencySettingsService" has incompatible type "float"; expected "Decimal"  [arg-type]` |
| 234 | `Argument "material_unit_cost" to "upsert_standard_cost" of "CostRollupService" has incompatible type "float"; expected "Decimal"  [arg-type]` |
| 235 | `Argument "labor_unit_cost" to "upsert_standard_cost" of "CostRollupService" has incompatible type "float"; expected "Decimal"  [arg-type]` |
| 236 | `Argument "overhead_unit_cost" to "upsert_standard_cost" of "CostRollupService" has incompatible type "float"; expected "Decimal"  [arg-type]` |

### `backend/src/sensei/api/v1/endpoints/it_monitoring.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 8 | `Library stubs not installed for "psutil"  [import-untyped]` |
| 133 | `Argument 1 to "where" of "Select" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 222 | `Argument 1 to "where" of "Select" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |

### `backend/src/sensei/api/v1/endpoints/kanban.py`
**Errors:** 37

| Line | Error Message |
|------|---------------|
| 545 | `"object" has no attribute "id"  [attr-defined]` |
| 546 | `"object" has no attribute "id"  [attr-defined]` |
| 578 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 599 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 635 | `"object" has no attribute "id"  [attr-defined]` |
| 658 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 661 | `"object" has no attribute "id"  [attr-defined]` |
| 765 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 811 | `"object" has no attribute "id"  [attr-defined]` |
| 812 | `"object" has no attribute "id"  [attr-defined]` |
| 843 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 864 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 882 | `"object" has no attribute "id"  [attr-defined]` |
| 889 | `"object" has no attribute "id"  [attr-defined]` |
| 912 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 915 | `"object" has no attribute "id"  [attr-defined]` |
| 945 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 973 | `"object" has no attribute "id"  [attr-defined]` |
| 996 | `"object" has no attribute "id"  [attr-defined]` |
| 1021 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 1031 | `"object" has no attribute "id"  [attr-defined]` |
| 1039 | `"object" has no attribute "id"  [attr-defined]` |
| 1066 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 1076 | `"object" has no attribute "id"  [attr-defined]` |
| 1084 | `"object" has no attribute "id"  [attr-defined]` |
| 1112 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 1128 | `"object" has no attribute "id"  [attr-defined]` |
| 1136 | `"object" has no attribute "id"  [attr-defined]` |
| 1162 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 1174 | `"object" has no attribute "id"  [attr-defined]` |
| 1182 | `"object" has no attribute "id"  [attr-defined]` |
| 1209 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 1212 | `"object" has no attribute "id"  [attr-defined]` |
| 1214 | `"object" has no attribute "id"  [attr-defined]` |
| 1246 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 1292 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |
| 1336 | `Argument 2 to "NotFoundError" has incompatible type "int"; expected "str \| None"  [arg-type]` |

### `backend/src/sensei/api/v1/endpoints/learning.py`
**Errors:** 28

| Line | Error Message |
|------|---------------|
| 423 | `"object" has no attribute "id"  [attr-defined]` |
| 426 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 494 | `Argument 1 to "where" of "Select" has incompatible type "ColumnElement[bool] \| bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 501 | `Argument 1 to "where" of "Select" has incompatible type "ColumnElement[bool] \| bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 550 | `"object" has no attribute "id"  [attr-defined]` |
| 584 | `"object" has no attribute "id"  [attr-defined]` |
| 675 | `"object" has no attribute "id"  [attr-defined]` |
| 678 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 753 | `Argument 1 to "where" of "Select" has incompatible type "ColumnElement[bool] \| bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 760 | `Argument 1 to "where" of "Select" has incompatible type "ColumnElement[bool] \| bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 812 | `"object" has no attribute "id"  [attr-defined]` |
| 846 | `"object" has no attribute "id"  [attr-defined]` |
| 900 | `"object" has no attribute "id"  [attr-defined]` |
| 947 | `"object" has no attribute "id"  [attr-defined]` |
| 985 | `"object" has no attribute "id"  [attr-defined]` |
| 1004 | `"object" has no attribute "id"  [attr-defined]` |
| 1011 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 1037 | `"object" has no attribute "id"  [attr-defined]` |
| 1086 | `"object" has no attribute "id"  [attr-defined]` |
| 1141 | `"object" has no attribute "id"  [attr-defined]` |
| 1144 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 1204 | `"object" has no attribute "id"  [attr-defined]` |
| 1276 | `"object" has no attribute "id"  [attr-defined]` |
| 1279 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 1340 | `Argument 1 to "where" of "Select" has incompatible type "ColumnElement[bool] \| bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1347 | `Argument 1 to "where" of "Select" has incompatible type "ColumnElement[bool] \| bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1393 | `"object" has no attribute "id"  [attr-defined]` |
| 1466 | `"SenseiReasoningEngine" has no attribute "generate_socratic_prompts"  [attr-defined]` |

### `backend/src/sensei/api/v1/endpoints/maintenance.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 44 | `Argument 1 to "get_asset" of "PersistentMaintenanceService" has incompatible type "str"; expected "UUID"  [arg-type]` |

### `backend/src/sensei/api/v1/endpoints/mrp.py`
**Errors:** 9

| Line | Error Message |
|------|---------------|
| 207 | `Incompatible default for argument "db" (default has type "None", argument has type "AsyncSession")  [assignment]` |
| 225 | `"Product" has no attribute "sku"  [attr-defined]` |
| 252 | `"object" has no attribute "id"  [attr-defined]` |
| 332 | `"object" has no attribute "id"  [attr-defined]` |
| 333 | `"object" has no attribute "id"  [attr-defined]` |
| 334 | `"object" has no attribute "id"  [attr-defined]` |
| 335 | `"object" has no attribute "id"  [attr-defined]` |
| 347 | `"Product" has no attribute "sku"  [attr-defined]` |
| 349 | `"Product" has no attribute "unit_cost"  [attr-defined]` |

### `backend/src/sensei/api/v1/endpoints/obeya.py`
**Errors:** 53

| Line | Error Message |
|------|---------------|
| 301 | `"object" has no attribute "id"  [attr-defined]` |
| 302 | `"object" has no attribute "id"  [attr-defined]` |
| 305 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 329 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 364 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 366 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 368 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 370 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 372 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 378 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 381 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 381 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 389 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 389 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 424 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 448 | `"object" has no attribute "id"  [attr-defined]` |
| 472 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 481 | `"object" has no attribute "id"  [attr-defined]` |
| 504 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 516 | `"object" has no attribute "id"  [attr-defined]` |
| 541 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 554 | `"object" has no attribute "id"  [attr-defined]` |
| 577 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 590 | `"object" has no attribute "id"  [attr-defined]` |
| 613 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 625 | `"object" has no attribute "id"  [attr-defined]` |
| 649 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 664 | `"object" has no attribute "id"  [attr-defined]` |
| 687 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 699 | `"object" has no attribute "id"  [attr-defined]` |
| 723 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 738 | `"object" has no attribute "id"  [attr-defined]` |
| 761 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 776 | `"object" has no attribute "id"  [attr-defined]` |
| 800 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 811 | `"object" has no attribute "id"  [attr-defined]` |
| 864 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 874 | `"object" has no attribute "id"  [attr-defined]` |
| 881 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 908 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1039 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1039 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1046 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1046 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1086 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1086 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1093 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1093 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1125 | `"object" has no attribute "id"  [attr-defined]` |
| 1178 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1178 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1185 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1185 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |

### `backend/src/sensei/api/v1/endpoints/opportunities.py`
**Errors:** 50

| Line | Error Message |
|------|---------------|
| 408 | `"type[Opportunity]" has no attribute "assigned_to_id"  [attr-defined]` |
| 409 | `"type[Opportunity]" has no attribute "assigned_to_id"  [attr-defined]` |
| 413 | `Argument 1 to "where" of "Select" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 414 | `Argument 1 to "where" of "Select" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 465 | `Argument "total" to "build_paginated_response" has incompatible type "int \| None"; expected "int"  [arg-type]` |
| 499 | `"object" has no attribute "id"  [attr-defined]` |
| 500 | `"object" has no attribute "id"  [attr-defined]` |
| 506 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 573 | `"object" has no attribute "id"  [attr-defined]` |
| 606 | `"object" has no attribute "is_superuser"  [attr-defined]` |
| 611 | `"object" has no attribute "id"  [attr-defined]` |
| 662 | `Property "is_closed" defined in "Opportunity" is read-only  [misc]` |
| 664 | `Incompatible types in assignment (expression has type "date", variable has type "SQLCoreOperations[datetime \| None] \| datetime \| None")  [assignment]` |
| 666 | `Property "is_closed" defined in "Opportunity" is read-only  [misc]` |
| 668 | `Incompatible types in assignment (expression has type "date", variable has type "SQLCoreOperations[datetime \| None] \| datetime \| None")  [assignment]` |
| 670 | `"object" has no attribute "id"  [attr-defined]` |
| 678 | `"object" has no attribute "id"  [attr-defined]` |
| 680 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 718 | `Property "is_closed" defined in "Opportunity" is read-only  [misc]` |
| 721 | `Incompatible types in assignment (expression has type "date", variable has type "SQLCoreOperations[datetime \| None] \| datetime \| None")  [assignment]` |
| 723 | `"object" has no attribute "id"  [attr-defined]` |
| 731 | `"object" has no attribute "id"  [attr-defined]` |
| 733 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 771 | `Property "is_closed" defined in "Opportunity" is read-only  [misc]` |
| 774 | `Incompatible types in assignment (expression has type "date", variable has type "SQLCoreOperations[datetime \| None] \| datetime \| None")  [assignment]` |
| 778 | `"object" has no attribute "id"  [attr-defined]` |
| 791 | `"object" has no attribute "id"  [attr-defined]` |
| 793 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 840 | `Property "is_closed" defined in "Opportunity" is read-only  [misc]` |
| 845 | `"object" has no attribute "id"  [attr-defined]` |
| 852 | `"object" has no attribute "id"  [attr-defined]` |
| 854 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 939 | `"object" has no attribute "id"  [attr-defined]` |
| 942 | `"add" of "AsyncSession" does not return a value (it only ever returns None)  [func-returns-value]` |
| 981 | `"OpportunityNote" has no attribute "updated_by_id"; maybe "created_by_id"?  [attr-defined]` |
| 981 | `"object" has no attribute "id"  [attr-defined]` |
| 1044 | `"type[Opportunity]" has no attribute "assigned_to_id"  [attr-defined]` |
| 1054 | `Argument 1 to "where" of "Select" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1072 | `Unsupported operand types for + ("int" and "Callable[[Any], int]")  [operator]` |
| 1112 | `"type[Opportunity]" has no attribute "assigned_to_id"  [attr-defined]` |
| 1116 | `Argument 1 to "where" of "Select" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1131 | `Unsupported operand types for + ("object" and "int")  [operator]` |
| 1132 | `Unsupported operand types for + ("object" and "Decimal")  [operator]` |
| 1135 | `Unsupported operand types for + ("object" and "int")  [operator]` |
| 1136 | `Unsupported operand types for + ("object" and "Decimal")  [operator]` |
| 1139 | `Unsupported operand types for + ("object" and "int")  [operator]` |
| 1140 | `Unsupported operand types for + ("object" and "Decimal")  [operator]` |
| 1149 | `Argument 1 to "float" has incompatible type "object"; expected "str \| Buffer \| SupportsFloat \| SupportsIndex"  [arg-type]` |
| 1153 | `Argument 1 to "float" has incompatible type "object"; expected "str \| Buffer \| SupportsFloat \| SupportsIndex"  [arg-type]` |
| 1157 | `Argument 1 to "float" has incompatible type "object"; expected "str \| Buffer \| SupportsFloat \| SupportsIndex"  [arg-type]` |

### `backend/src/sensei/api/v1/endpoints/production_cells.py`
**Errors:** 6

| Line | Error Message |
|------|---------------|
| 584 | `Argument "average_oee" to "CellStatsResponse" has incompatible type "Decimal \| float \| None"; expected "Decimal \| None"  [arg-type]` |
| 585 | `Argument "average_efficiency" to "CellStatsResponse" has incompatible type "Decimal \| float \| None"; expected "Decimal \| None"  [arg-type]` |
| 1247 | `Argument "average_oee" to "CellDailyOEEResponse" has incompatible type "Decimal \| float \| None"; expected "Decimal \| None"  [arg-type]` |
| 1248 | `Argument "average_availability" to "CellDailyOEEResponse" has incompatible type "Decimal \| float \| None"; expected "Decimal \| None"  [arg-type]` |
| 1249 | `Argument "average_performance" to "CellDailyOEEResponse" has incompatible type "Decimal \| float \| None"; expected "Decimal \| None"  [arg-type]` |
| 1250 | `Argument "average_quality" to "CellDailyOEEResponse" has incompatible type "Decimal \| float \| None"; expected "Decimal \| None"  [arg-type]` |

### `backend/src/sensei/api/v1/endpoints/products.py`
**Errors:** 11

| Line | Error Message |
|------|---------------|
| 601 | `"object" has no attribute "id"  [attr-defined]` |
| 678 | `"object" has no attribute "id"  [attr-defined]` |
| 712 | `"object" has no attribute "is_superuser"  [attr-defined]` |
| 719 | `"object" has no attribute "id"  [attr-defined]` |
| 784 | `"object" has no attribute "id"  [attr-defined]` |
| 806 | `"object" has no attribute "id"  [attr-defined]` |
| 828 | `"object" has no attribute "id"  [attr-defined]` |
| 921 | `"object" has no attribute "id"  [attr-defined]` |
| 967 | `"object" has no attribute "id"  [attr-defined]` |
| 1081 | `"object" has no attribute "id"  [attr-defined]` |
| 1135 | `"object" has no attribute "id"  [attr-defined]` |

### `backend/src/sensei/api/v1/endpoints/project_management.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 224 | `"type[Base]" has no attribute "ref"  [attr-defined]` |
| 224 | `"type[Base]" has no attribute "project_id"  [attr-defined]` |

### `backend/src/sensei/api/v1/endpoints/purchase.py`
**Errors:** 21

| Line | Error Message |
|------|---------------|
| 243 | `"object" has no attribute "id"  [attr-defined]` |
| 248 | `"object" has no attribute "id"  [attr-defined]` |
| 249 | `"object" has no attribute "id"  [attr-defined]` |
| 250 | `"object" has no attribute "id"  [attr-defined]` |
| 312 | `"object" has no attribute "id"  [attr-defined]` |
| 344 | `"object" has no attribute "id"  [attr-defined]` |
| 385 | `"object" has no attribute "id"  [attr-defined]` |
| 386 | `"object" has no attribute "id"  [attr-defined]` |
| 387 | `"object" has no attribute "id"  [attr-defined]` |
| 410 | `Incompatible types in assignment (expression has type "PurchaseRequisition", variable has type "PurchaseOrder")  [assignment]` |
| 479 | `"object" has no attribute "id"  [attr-defined]` |
| 480 | `"object" has no attribute "id"  [attr-defined]` |
| 481 | `"object" has no attribute "id"  [attr-defined]` |
| 559 | `"object" has no attribute "id"  [attr-defined]` |
| 592 | `"object" has no attribute "id"  [attr-defined]` |
| 661 | `"object" has no attribute "id"  [attr-defined]` |
| 686 | `Incompatible types in assignment (expression has type "PurchaseOrder", variable has type "GoodsReceipt")  [assignment]` |
| 749 | `"object" has no attribute "id"  [attr-defined]` |
| 750 | `"object" has no attribute "id"  [attr-defined]` |
| 751 | `"object" has no attribute "id"  [attr-defined]` |
| 847 | `Argument "grn_total" to "MatchingResult" has incompatible type "Decimal \| Literal[0]"; expected "Decimal"  [arg-type]` |

### `backend/src/sensei/api/v1/endpoints/quality.py`
**Errors:** 8

| Line | Error Message |
|------|---------------|
| 2205 | `Name "close_non_conformance" already defined on line 2040  [no-redef]` |
| 2424 | `"type[VerificationStatus]" has no attribute "VERIFIED"  [attr-defined]` |
| 2540 | `"type[CAPAStatus]" has no attribute "IN_PROGRESS"  [attr-defined]` |
| 2560 | `"type[CAPAStatus]" has no attribute "VERIFICATION"  [attr-defined]` |
| 2581 | `"type[VerificationStatus]" has no attribute "VERIFIED"  [attr-defined]` |
| 2585 | `"type[CAPAStatus]" has no attribute "EFFECTIVENESS_CHECK"  [attr-defined]` |
| 2606 | `"type[VerificationStatus]" has no attribute "REJECTED"  [attr-defined]` |
| 2607 | `"type[CAPAStatus]" has no attribute "IN_PROGRESS"  [attr-defined]` |

### `backend/src/sensei/api/v1/endpoints/quotes.py`
**Errors:** 29

| Line | Error Message |
|------|---------------|
| 435 | `Argument "quantity" to "LineItemResponse" has incompatible type "Decimal"; expected "int"  [arg-type]` |
| 457 | `"QuoteVersion" has no attribute "status"  [attr-defined]` |
| 459 | `"QuoteVersion" has no attribute "change_summary"  [attr-defined]` |
| 656 | `Argument "total" to "build_paginated_response" has incompatible type "int \| None"; expected "int"  [arg-type]` |
| 688 | `"object" has no attribute "id"  [attr-defined]` |
| 689 | `"object" has no attribute "id"  [attr-defined]` |
| 694 | `Incompatible types in assignment (expression has type "date", variable has type "SQLCoreOperations[datetime \| None] \| datetime \| None")  [assignment]` |
| 802 | `"object" has no attribute "id"  [attr-defined]` |
| 844 | `"object" has no attribute "is_superuser"  [attr-defined]` |
| 849 | `"object" has no attribute "id"  [attr-defined]` |
| 1091 | `"object" has no attribute "id"  [attr-defined]` |
| 1114 | `Variable "sensei.api.v1.endpoints.quotes.AllowQuoteApproval" is not valid as a type  [valid-type]` |
| 1138 | `"object" has no attribute "id"  [attr-defined]` |
| 1149 | `"object" has no attribute "id"  [attr-defined]` |
| 1196 | `"object" has no attribute "id"  [attr-defined]` |
| 1285 | `"object" has no attribute "id"  [attr-defined]` |
| 1310 | `"object" has no attribute "id"  [attr-defined]` |
| 1311 | `"object" has no attribute "id"  [attr-defined]` |
| 1312 | `"object" has no attribute "id"  [attr-defined]` |
| 1321 | `"QuoteLineItem" has no attribute "sku"  [attr-defined]` |
| 1322 | `"QuoteLineItem" has no attribute "product_name"  [attr-defined]` |
| 1345 | `Incompatible types in assignment (expression has type "dict[str, Any]", variable has type "QuoteResponse")  [assignment]` |
| 1380 | `"object" has no attribute "id"  [attr-defined]` |
| 1452 | `"object" has no attribute "id"  [attr-defined]` |
| 1546 | `"object" has no attribute "id"  [attr-defined]` |
| 1619 | `Value of type "object" is not indexable  [index]` |
| 1620 | `Value of type "object" is not indexable  [index]` |
| 1621 | `Value of type "object" is not indexable  [index]` |
| 1622 | `Value of type "object" is not indexable  [index]` |

### `backend/src/sensei/api/v1/endpoints/rfqs.py`
**Errors:** 20

| Line | Error Message |
|------|---------------|
| 484 | `"RFQQuestion" has no attribute "asked_at"  [attr-defined]` |
| 487 | `"RFQQuestion" has no attribute "answered_by_id"; maybe "answered_by" or "asked_by_id"?  [attr-defined]` |
| 619 | `Argument "total" to "build_paginated_response" has incompatible type "int \| None"; expected "int"  [arg-type]` |
| 683 | `Item "None" of "datetime \| None" has no attribute "isoformat"  [union-attr]` |
| 717 | `"object" has no attribute "id"  [attr-defined]` |
| 718 | `"object" has no attribute "id"  [attr-defined]` |
| 806 | `"object" has no attribute "id"  [attr-defined]` |
| 840 | `"object" has no attribute "is_superuser"  [attr-defined]` |
| 845 | `"object" has no attribute "id"  [attr-defined]` |
| 881 | `"object" has no attribute "id"  [attr-defined]` |
| 898 | `Variable "sensei.api.v1.endpoints.rfqs.AllowRFQDecision" is not valid as a type  [valid-type]` |
| 923 | `"object" has no attribute "id"  [attr-defined]` |
| 940 | `Variable "sensei.api.v1.endpoints.rfqs.AllowRFQDecision" is not valid as a type  [valid-type]` |
| 967 | `"object" has no attribute "id"  [attr-defined]` |
| 984 | `Variable "sensei.api.v1.endpoints.rfqs.AllowRFQDecision" is not valid as a type  [valid-type]` |
| 1007 | `"object" has no attribute "id"  [attr-defined]` |
| 1086 | `"object" has no attribute "id"  [attr-defined]` |
| 1134 | `"RFQQuestion" has no attribute "answered_by_id"; maybe "answered_by" or "asked_by_id"?  [attr-defined]` |
| 1134 | `"object" has no attribute "id"  [attr-defined]` |
| 1454 | `"object" has no attribute "id"  [attr-defined]` |

### `backend/src/sensei/api/v1/endpoints/risk.py`
**Errors:** 50

| Line | Error Message |
|------|---------------|
| 283 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 329 | `"object" has no attribute "id"  [attr-defined]` |
| 330 | `"object" has no attribute "id"  [attr-defined]` |
| 358 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 392 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 394 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 396 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 398 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 405 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 408 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 408 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 416 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 416 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 447 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 477 | `"object" has no attribute "id"  [attr-defined]` |
| 501 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 510 | `"object" has no attribute "id"  [attr-defined]` |
| 533 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 545 | `"object" has no attribute "id"  [attr-defined]` |
| 568 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 581 | `"object" has no attribute "id"  [attr-defined]` |
| 605 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 628 | `"object" has no attribute "id"  [attr-defined]` |
| 652 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 665 | `"object" has no attribute "id"  [attr-defined]` |
| 688 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 701 | `"object" has no attribute "id"  [attr-defined]` |
| 725 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 741 | `"object" has no attribute "id"  [attr-defined]` |
| 765 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 776 | `"object" has no attribute "id"  [attr-defined]` |
| 806 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 831 | `"object" has no attribute "id"  [attr-defined]` |
| 832 | `"object" has no attribute "id"  [attr-defined]` |
| 861 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 963 | `"object" has no attribute "id"  [attr-defined]` |
| 1010 | `"object" has no attribute "id"  [attr-defined]` |
| 1068 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1104 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1104 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1111 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1111 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1150 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1150 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1157 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1157 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1201 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1201 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1208 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1208 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |

### `backend/src/sensei/api/v1/endpoints/sales.py`
**Errors:** 20

| Line | Error Message |
|------|---------------|
| 202 | `Incompatible default for argument "db" (default has type "None", argument has type "AsyncSession")  [assignment]` |
| 307 | `"object" has no attribute "id"  [attr-defined]` |
| 308 | `"object" has no attribute "id"  [attr-defined]` |
| 309 | `"object" has no attribute "id"  [attr-defined]` |
| 387 | `"object" has no attribute "id"  [attr-defined]` |
| 420 | `"object" has no attribute "id"  [attr-defined]` |
| 469 | `"object" has no attribute "id"  [attr-defined]` |
| 470 | `"object" has no attribute "id"  [attr-defined]` |
| 471 | `"object" has no attribute "id"  [attr-defined]` |
| 480 | `"QuoteLineItem" has no attribute "sku"  [attr-defined]` |
| 480 | `"QuoteLineItem" has no attribute "product_name"  [attr-defined]` |
| 481 | `"QuoteLineItem" has no attribute "product_name"  [attr-defined]` |
| 557 | `"object" has no attribute "id"  [attr-defined]` |
| 558 | `"object" has no attribute "id"  [attr-defined]` |
| 559 | `"object" has no attribute "id"  [attr-defined]` |
| 621 | `"object" has no attribute "id"  [attr-defined]` |
| 622 | `"object" has no attribute "id"  [attr-defined]` |
| 623 | `"object" has no attribute "id"  [attr-defined]` |
| 645 | `Incompatible types in assignment (expression has type "SalesOrder", variable has type "CustomerInvoice")  [assignment]` |
| 698 | `"object" has no attribute "id"  [attr-defined]` |

### `backend/src/sensei/api/v1/endpoints/saved_views.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 411 | `Argument "team_ids" to "create_view" of "SavedViewsService" has incompatible type "list[UUID \| None]"; expected "list[UUID] \| None"  [arg-type]` |
| 644 | `Argument "team_ids" to "update_view" of "SavedViewsService" has incompatible type "list[UUID \| None] \| None"; expected "list[UUID] \| None"  [arg-type]` |

### `backend/src/sensei/api/v1/endpoints/standard_work.py`
**Errors:** 61

| Line | Error Message |
|------|---------------|
| 235 | `Argument 3 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 262 | `"object" has no attribute "id"  [attr-defined]` |
| 292 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 334 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 336 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 338 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 340 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 348 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 353 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 356 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 362 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 365 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 372 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 372 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 380 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 380 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 422 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 442 | `"object" has no attribute "id"  [attr-defined]` |
| 470 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 479 | `Property "is_deleted" defined in "SoftDeleteMixin" is read-only  [misc]` |
| 481 | `"object" has no attribute "id"  [attr-defined]` |
| 507 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 521 | `"object" has no attribute "id"  [attr-defined]` |
| 523 | `"object" has no attribute "id"  [attr-defined]` |
| 552 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 571 | `Argument 4 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 578 | `"object" has no attribute "id"  [attr-defined]` |
| 582 | `"object" has no attribute "id"  [attr-defined]` |
| 585 | `"object" has no attribute "id"  [attr-defined]` |
| 594 | `"object" has no attribute "id"  [attr-defined]` |
| 626 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 642 | `"object" has no attribute "id"  [attr-defined]` |
| 671 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 690 | `Argument 3 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 703 | `"object" has no attribute "id"  [attr-defined]` |
| 732 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 746 | `"object" has no attribute "id"  [attr-defined]` |
| 780 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 798 | `Item "None" of "list[ContentStep] \| None" has no attribute "__iter__" (not iterable)  [union-attr]` |
| 804 | `"object" has no attribute "id"  [attr-defined]` |
| 840 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 933 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 933 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 941 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 941 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 991 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 991 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 999 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 999 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1049 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1049 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1057 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1057 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1103 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1103 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1111 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1111 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1156 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1156 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1164 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1164 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |

### `backend/src/sensei/api/v1/endpoints/tasks.py`
**Errors:** 61

| Line | Error Message |
|------|---------------|
| 232 | `"object" has no attribute "id"  [attr-defined]` |
| 265 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 301 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 303 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 305 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 307 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 309 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 311 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 318 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 320 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 320 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 327 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 327 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 358 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 378 | `"object" has no attribute "id"  [attr-defined]` |
| 401 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 410 | `"object" has no attribute "id"  [attr-defined]` |
| 433 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 447 | `"object" has no attribute "id"  [attr-defined]` |
| 472 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 486 | `"object" has no attribute "id"  [attr-defined]` |
| 509 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 523 | `"object" has no attribute "id"  [attr-defined]` |
| 546 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 558 | `"object" has no attribute "id"  [attr-defined]` |
| 581 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 595 | `"object" has no attribute "id"  [attr-defined]` |
| 618 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 630 | `"object" has no attribute "id"  [attr-defined]` |
| 653 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 667 | `"object" has no attribute "id"  [attr-defined]` |
| 696 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 705 | `"object" has no attribute "id"  [attr-defined]` |
| 729 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 752 | `"object" has no attribute "id"  [attr-defined]` |
| 781 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 791 | `"object" has no attribute "id"  [attr-defined]` |
| 821 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 831 | `"object" has no attribute "id"  [attr-defined]` |
| 861 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 984 | `"object" has no attribute "id"  [attr-defined]` |
| 1036 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1036 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1043 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1043 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1075 | `"object" has no attribute "id"  [attr-defined]` |
| 1120 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1120 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1127 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1127 | `Argument 1 to "and_" has incompatible type "*list[object]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1157 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1169 | `"type[TaskStatus]" has no attribute "OPEN"  [attr-defined]` |
| 1179 | `"object" has no attribute "id"  [attr-defined]` |
| 1180 | `"object" has no attribute "id"  [attr-defined]` |
| 1206 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1217 | `"object" has no attribute "id"  [attr-defined]` |
| 1240 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1251 | `"object" has no attribute "id"  [attr-defined]` |
| 1276 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1282 | `Property "is_deleted" defined in "SoftDeleteMixin" is read-only  [misc]` |
| 1284 | `"object" has no attribute "id"  [attr-defined]` |

### `backend/src/sensei/api/v1/endpoints/today.py`
**Errors:** 15

| Line | Error Message |
|------|---------------|
| 554 | `"object" has no attribute "id"  [attr-defined]` |
| 560 | `"object" has no attribute "id"  [attr-defined]` |
| 574 | `"object" has no attribute "id"  [attr-defined]` |
| 597 | `"object" has no attribute "id"  [attr-defined]` |
| 614 | `"object" has no attribute "id"  [attr-defined]` |
| 649 | `"object" has no attribute "id"  [attr-defined]` |
| 670 | `"object" has no attribute "id"  [attr-defined]` |
| 696 | `"object" has no attribute "id"  [attr-defined]` |
| 723 | `"object" has no attribute "id"  [attr-defined]` |
| 738 | `"object" has no attribute "id"  [attr-defined]` |
| 755 | `"object" has no attribute "id"  [attr-defined]` |
| 781 | `"object" has no attribute "id"  [attr-defined]` |
| 804 | `Incompatible types in "await" (actual type "list[MicroDrill]", expected type "Awaitable[Any]")  [misc]` |
| 821 | `"object" has no attribute "id"  [attr-defined]` |
| 948 | `Incompatible types in "await" (actual type "TodayScreenData", expected type "Awaitable[Any]")  [misc]` |

### `backend/src/sensei/api/v1/endpoints/training.py`
**Errors:** 64

| Line | Error Message |
|------|---------------|
| 424 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 444 | `"object" has no attribute "id"  [attr-defined]` |
| 467 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 498 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 500 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 502 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 509 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 511 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 511 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 518 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 518 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 553 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 564 | `"object" has no attribute "id"  [attr-defined]` |
| 585 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 592 | `Property "is_deleted" defined in "SoftDeleteMixin" is read-only  [misc]` |
| 594 | `"object" has no attribute "id"  [attr-defined]` |
| 624 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 649 | `"object" has no attribute "id"  [attr-defined]` |
| 666 | `"object" has no attribute "id"  [attr-defined]` |
| 676 | `"object" has no attribute "id"  [attr-defined]` |
| 720 | `Incompatible types in assignment (expression has type "bool", variable has type "ColumnElement[bool]")  [assignment]` |
| 789 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 816 | `"object" has no attribute "id"  [attr-defined]` |
| 831 | `"object" has no attribute "id"  [attr-defined]` |
| 841 | `"object" has no attribute "id"  [attr-defined]` |
| 868 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 903 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 905 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 907 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 909 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 911 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 918 | `Argument 1 to "append" of "list" has incompatible type "ColumnElement[bool]"; expected "bool"  [arg-type]` |
| 920 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 920 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 927 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "Literal[True] \| ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 927 | `Argument 1 to "and_" has incompatible type "*list[bool]"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 965 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 976 | `"object" has no attribute "id"  [attr-defined]` |
| 999 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1006 | `Property "is_deleted" defined in "SoftDeleteMixin" is read-only  [misc]` |
| 1008 | `"object" has no attribute "id"  [attr-defined]` |
| 1031 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1044 | `"object" has no attribute "id"  [attr-defined]` |
| 1067 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1080 | `"object" has no attribute "id"  [attr-defined]` |
| 1103 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1114 | `"object" has no attribute "id"  [attr-defined]` |
| 1146 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1175 | `"object" has no attribute "id"  [attr-defined]` |
| 1191 | `"object" has no attribute "id"  [attr-defined]` |
| 1201 | `"object" has no attribute "id"  [attr-defined]` |
| 1290 | `"object" has no attribute "id"  [attr-defined]` |
| 1333 | `"object" has no attribute "id"  [attr-defined]` |
| 1393 | `Argument 2 to "and_" has incompatible type "bool"; expected "ColumnElement[bool] \| _HasClauseElement[bool] \| SQLCoreOperations[bool] \| ExpressionElementRole[bool] \| TypedColumnsClauseRole[bool] \| Callable[[], ColumnElement[bool]] \| LambdaElement"  [arg-type]` |
| 1416 | `"object" has no attribute "id"  [attr-defined]` |
| 1432 | `"object" has no attribute "id"  [attr-defined]` |
| 1442 | `"object" has no attribute "id"  [attr-defined]` |
| 1493 | `Incompatible types in assignment (expression has type "bool", variable has type "ColumnElement[bool]")  [assignment]` |
| 1549 | `"object" has no attribute "id"  [attr-defined]` |
| 1584 | `"object" has no attribute "id"  [attr-defined]` |
| 1587 | `"object" has no attribute "id"  [attr-defined]` |
| 1603 | `"object" has no attribute "id"  [attr-defined]` |
| 1642 | `"object" has no attribute "id"  [attr-defined]` |
| 1656 | `"object" has no attribute "id"  [attr-defined]` |

### `backend/src/sensei/api/v1/endpoints/training_matrix.py`
**Errors:** 6

| Line | Error Message |
|------|---------------|
| 301 | `Argument "user_stations" to "generate_matrix" of "TrainingMatrixService" has incompatible type "dict[str, list[dict[str, Any]]] \| None"; expected "dict[UUID, list[dict[str, Any]]] \| None"  [arg-type]` |
| 387 | `Incompatible default for argument "request" (default has type "None", argument has type "GapAnalysisRequest")  [assignment]` |
| 407 | `Argument "user_stations" to "analyze_gaps" of "TrainingMatrixService" has incompatible type "dict[str, list[dict[str, Any]]] \| None"; expected "dict[UUID, list[dict[str, Any]]] \| None"  [arg-type]` |
| 436 | `Incompatible default for argument "request" (default has type "None", argument has type "ExpirationCheckRequest")  [assignment]` |
| 507 | `Incompatible default for argument "request" (default has type "None", argument has type "UserSkillSummaryRequest")  [assignment]` |
| 536 | `Incompatible default for argument "request" (default has type "None", argument has type "StationReadinessRequest")  [assignment]` |

### `backend/src/sensei/api/v1/endpoints/users.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 514 | `Argument "total" to "UserListResponse" has incompatible type "int \| None"; expected "int"  [arg-type]` |
| 517 | `Unsupported operand types for + ("None" and "int")  [operator]` |

### `backend/src/sensei/api/v1/endpoints/websockets.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 26 | `Incompatible types in assignment (expression has type "User \| None", variable has type "User")  [assignment]` |

### `backend/src/sensei/api/v1/endpoints/work_centers.py`
**Errors:** 13

| Line | Error Message |
|------|---------------|
| 494 | `"object" has no attribute "id"  [attr-defined]` |
| 495 | `"object" has no attribute "id"  [attr-defined]` |
| 586 | `"object" has no attribute "id"  [attr-defined]` |
| 623 | `"object" has no attribute "id"  [attr-defined]` |
| 653 | `"object" has no attribute "id"  [attr-defined]` |
| 677 | `Incompatible types in assignment (expression has type "ColumnElement[bool]", variable has type "BinaryExpression[bool]")  [assignment]` |
| 872 | `"object" has no attribute "id"  [attr-defined]` |
| 873 | `"object" has no attribute "id"  [attr-defined]` |
| 969 | `"object" has no attribute "id"  [attr-defined]` |
| 1012 | `"object" has no attribute "id"  [attr-defined]` |
| 1044 | `"object" has no attribute "id"  [attr-defined]` |
| 1104 | `"object" has no attribute "id"  [attr-defined]` |
| 1105 | `"object" has no attribute "id"  [attr-defined]` |

### `backend/src/sensei/api/v1/endpoints/work_orders.py`
**Errors:** 5

| Line | Error Message |
|------|---------------|
| 526 | `"int" has no attribute "is_late"  [attr-defined]` |
| 529 | `"int" has no attribute "is_late"  [attr-defined]` |
| 532 | `Argument 1 to "work_order_to_list_response" has incompatible type "int"; expected "WorkOrder"  [arg-type]` |
| 652 | `Incompatible types in assignment (expression has type "ColumnElement[bool]", variable has type "BinaryExpression[bool]")  [assignment]` |
| 1223 | `Argument 1 to "operation_to_response" has incompatible type "int"; expected "WorkOrderOperation"  [arg-type]` |

### `backend/src/sensei/cli/knowledge.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 25 | `Module "sensei.core.database" has no attribute "async_session_maker"; maybe "async_sessionmaker" or "async_session_factory"?  [attr-defined]` |
| 53 | `Function "sensei.cli.knowledge.list" is not valid as a type  [valid-type]` |
| 76 | `Function "sensei.cli.knowledge.list" is not valid as a type  [valid-type]` |
| 405 | `Function "sensei.cli.knowledge.list" is not valid as a type  [valid-type]` |

### `backend/src/sensei/core/auth.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 197 | `Argument 1 to "verify_totp" has incompatible type "str \| None"; expected "str"  [arg-type]` |
| 232 | `Argument 2 to "_store_refresh_token" of "AuthService" has incompatible type "str \| None"; expected "str"  [arg-type]` |
| 294 | `Argument 2 to "_store_refresh_token" of "AuthService" has incompatible type "str \| None"; expected "str"  [arg-type]` |
| 672 | `Incompatible types in "await" (actual type "Awaitable[int] \| int", expected type "Awaitable[Any]")  [misc]` |

### `backend/src/sensei/core/celery_app.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 1 | `Skipping analyzing "celery": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |

### `backend/src/sensei/core/config.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 160 | `Missing named argument "SECRET_KEY" for "Settings"  [call-arg]` |
| 160 | `Missing named argument "DATABASE_URL" for "Settings"  [call-arg]` |
| 160 | `Missing named argument "DATABASE_URL_SYNC" for "Settings"  [call-arg]` |

### `backend/src/sensei/core/redis.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 29 | `Incompatible types in "await" (actual type "Awaitable[bool] \| bool", expected type "Awaitable[Any]")  [misc]` |

### `backend/src/sensei/core/security.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 18 | `Library stubs not installed for "qrcode"  [import-untyped]` |
| 19 | `Library stubs not installed for "qrcode.image.svg"  [import-untyped]` |
| 19 | `Library stubs not installed for "qrcode.image"  [import-untyped]` |
| 22 | `Library stubs not installed for "jose"  [import-untyped]` |

### `backend/src/sensei/core/storage.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 12 | `Skipping analyzing "boto3": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 13 | `Skipping analyzing "botocore.config": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 14 | `Skipping analyzing "botocore.exceptions": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |

### `backend/src/sensei/main.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 71 | `Unexpected keyword argument "storage_client" for "DatabaseBackupService"  [call-arg]` |

### `backend/src/sensei/ml/cbm_predictor.py`
**Errors:** 12

| Line | Error Message |
|------|---------------|
| 13 | `Library stubs not installed for "pandas"  [import-untyped]` |
| 16 | `Skipping analyzing "sklearn.ensemble": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 17 | `Skipping analyzing "sklearn.preprocessing": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 18 | `Skipping analyzing "joblib": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 26 | `Module "sensei.models.production" has no attribute "Equipment"  [attr-defined]` |
| 26 | `Module "sensei.models.production" has no attribute "MaintenanceRecord"  [attr-defined]` |
| 26 | `Module "sensei.models.production" has no attribute "ConditionReading"  [attr-defined]` |
| 105 | `Skipping analyzing "sklearn.model_selection": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 229 | `Item "None" of "Any \| None" has no attribute "predict"  [union-attr]` |
| 280 | `Need type annotation for "equipment_readings" (hint: "equipment_readings: dict[<type>, <type>] = ...")  [var-annotated]` |
| 281 | `Need type annotation for "equipment_maintenance" (hint: "equipment_maintenance: dict[<type>, <type>] = ...")  [var-annotated]` |
| 423 | `Need type annotation for "critical_issues" (hint: "critical_issues: list[<type>] = ...")  [var-annotated]` |

### `backend/src/sensei/ml/evaluation.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 13 | `Library stubs not installed for "pandas"  [import-untyped]` |
| 17 | `Skipping analyzing "sklearn.metrics": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 26 | `Skipping analyzing "sklearn.calibration": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |

### `backend/src/sensei/ml/evidence_detector.py`
**Errors:** 16

| Line | Error Message |
|------|---------------|
| 16 | `Skipping analyzing "sklearn.feature_extraction.text": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 17 | `Skipping analyzing "sklearn.ensemble": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 18 | `Skipping analyzing "joblib": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 124 | `Skipping analyzing "sklearn.model_selection": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 183 | `"object" has no attribute "append"  [attr-defined]` |
| 194 | `"object" has no attribute "append"  [attr-defined]` |
| 198 | `"object" has no attribute "append"  [attr-defined]` |
| 203 | `"object" has no attribute "append"  [attr-defined]` |
| 207 | `"object" has no attribute "append"  [attr-defined]` |
| 212 | `"object" has no attribute "append"  [attr-defined]` |
| 216 | `"object" has no attribute "append"  [attr-defined]` |
| 220 | `"object" has no attribute "append"  [attr-defined]` |
| 229 | `"object" has no attribute "append"  [attr-defined]` |
| 328 | `Item "None" of "Any \| None" has no attribute "transform"  [union-attr]` |
| 333 | `Item "None" of "Any \| None" has no attribute "predict_proba"  [union-attr]` |
| 354 | `Incompatible return value type (got "floating[Any]", expected "float")  [return-value]` |

### `backend/src/sensei/ml/lesson_recommender.py`
**Errors:** 11

| Line | Error Message |
|------|---------------|
| 13 | `Library stubs not installed for "pandas"  [import-untyped]` |
| 16 | `Skipping analyzing "sklearn.feature_extraction.text": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 17 | `Skipping analyzing "sklearn.metrics.pairwise": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 18 | `Skipping analyzing "sklearn.preprocessing": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 19 | `Skipping analyzing "joblib": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 24 | `Module "sensei.models.training" has no attribute "Lesson"  [attr-defined]` |
| 24 | `Module "sensei.models.training" has no attribute "LessonCompletion"  [attr-defined]` |
| 258 | `Value of type "ndarray[tuple[Any, ...], dtype[Any]] \| None" is not indexable  [index]` |
| 270 | `Value of type "ndarray[tuple[Any, ...], dtype[Any]] \| None" is not indexable  [index]` |
| 316 | `Need type annotation for "user_completions" (hint: "user_completions: dict[<type>, <type>] = ...")  [var-annotated]` |
| 387 | `Need type annotation for "user_completions" (hint: "user_completions: dict[<type>, <type>] = ...")  [var-annotated]` |

### `backend/src/sensei/ml/mlops.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 177 | `Incompatible return value type (got "Coroutine[Any, Any, str]", expected "str")  [return-value]` |
| 422 | `Incompatible types in "await" (actual type "str", expected type "Awaitable[Any]")  [misc]` |
| 502 | `Incompatible return value type (got "None", expected "str")  [return-value]` |

### `backend/src/sensei/ml/safety_gates.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 266 | `Unsupported operand types for <= ("float" and "None")  [operator]` |
| 279 | `Unsupported operand types for >= ("float" and "None")  [operator]` |
| 408 | `Argument 1 to "len" has incompatible type "dict[str, float] \| None"; expected "Sized"  [arg-type]` |
| 493 | `Argument "inference_metrics" to "check_all_gates" of "MLSafetyGates" has incompatible type "dict[str, int]"; expected "dict[str, float] \| None"  [arg-type]` |

### `backend/src/sensei/models/admin.py`
**Errors:** 5

| Line | Error Message |
|------|---------------|
| 14 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |
| 28 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |
| 43 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |
| 57 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |
| 71 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/models/andon.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 81 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 287 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 358 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/models/attachment.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 195 | `Incompatible types in assignment (expression has type "float", variable has type "int")  [assignment]` |
| 287 | `Incompatible types in assignment (expression has type "float", variable has type "int")  [assignment]` |

### `backend/src/sensei/models/audit_log.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 52 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/models/base.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 50 | `Need type annotation for "attrs" (hint: "attrs: list[<type>] = ...")  [var-annotated]` |

### `backend/src/sensei/models/cognitive_obeya.py`
**Errors:** 6

| Line | Error Message |
|------|---------------|
| 16 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 30 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |
| 44 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |
| 59 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |
| 73 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |
| 87 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/models/exception.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 16 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/models/kanban.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 91 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 235 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 426 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 463 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/models/knowledge_pack.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 29 | `Skipping analyzing "pgvector.sqlalchemy": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |

### `backend/src/sensei/models/maintenance.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 246 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 274 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/models/product.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 78 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 193 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 279 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/models/production.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 57 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 105 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 158 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 291 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/models/quality.py`
**Errors:** 6

| Line | Error Message |
|------|---------------|
| 222 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 432 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 457 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 681 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 757 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 865 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/models/quote.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 515 | `Name "SupplierQuoteStatus" already defined on line 87  [no-redef]` |

### `backend/src/sensei/models/rfq.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 492 | `Incompatible types in assignment (expression has type "float", variable has type "int")  [assignment]` |

### `backend/src/sensei/models/standard_work.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 70 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 273 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/models/strategic.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 18 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |
| 30 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 42 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/models/tps.py`
**Errors:** 5

| Line | Error Message |
|------|---------------|
| 16 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |
| 32 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |
| 46 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |
| 59 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |
| 74 | `Incompatible types in assignment (expression has type "str", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/models/training.py`
**Errors:** 5

| Line | Error Message |
|------|---------------|
| 114 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 220 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 282 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 401 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 472 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/models/work_center.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 86 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 166 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/models/work_order.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 95 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |
| 290 | `Incompatible types in assignment (expression has type "int", base class "Base" defined the type as "UUID")  [assignment]` |

### `backend/src/sensei/services/ai/ai_content_drafting.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 453 | `Argument "id" to "KnowledgeSource" has incompatible type "Sequence[str]"; expected "str"  [arg-type]` |
| 455 | `Argument "title" to "KnowledgeSource" has incompatible type "Sequence[str]"; expected "str"  [arg-type]` |
| 456 | `Argument "content_snippet" to "KnowledgeSource" has incompatible type "Sequence[str]"; expected "str"  [arg-type]` |

### `backend/src/sensei/services/ai/ai_email_drafting.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 163 | `Argument "default_factory" to "field" has incompatible type "type[EmailContext]"; expected "Callable[[], EmailContext]"  [arg-type]` |
| 455 | `Generator has incompatible item type "list[str]"; expected "str"  [misc]` |

### `backend/src/sensei/services/ai/ai_learning_recommendations.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 692 | `Incompatible types in assignment (expression has type "LearningUnitInfo \| None", variable has type "LearningUnitInfo")  [assignment]` |

### `backend/src/sensei/services/ai/ai_qualification_advisory.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 610 | `Need type annotation for "risks" (hint: "risks: list[<type>] = ...")  [var-annotated]` |
| 772 | `Item "float" of "Decimal \| float" has no attribute "quantize"  [union-attr]` |

### `backend/src/sensei/services/ai/ai_readiness.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 144 | `"Sequence[str]" has no attribute "append"  [attr-defined]` |
| 149 | `"Sequence[str]" has no attribute "append"  [attr-defined]` |
| 151 | `Incompatible types in assignment (expression has type "float", target has type "Sequence[str]")  [assignment]` |

### `backend/src/sensei/services/ai/ai_reasoning.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 92 | `Name "SearchResult" is not defined  [name-defined]` |
| 102 | `Name "SearchChunk" is not defined  [name-defined]` |
| 142 | `Incompatible default for argument "recommendations" (default has type "None", argument has type "list[str]")  [assignment]` |
| 143 | `Name "Any" is not defined  [name-defined]` |

### `backend/src/sensei/services/ai/continuous_learning.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 483 | `Skipping analyzing "sklearn.linear_model": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 484 | `Skipping analyzing "sklearn.naive_bayes": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 774 | `Skipping analyzing "sklearn.metrics": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |

### `backend/src/sensei/services/ai/distilled_knowledge/tps_lean_knowledge_ar.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 142 | `"Sequence[str]" has no attribute "lower"  [attr-defined]` |
| 167 | `"Sequence[str]" has no attribute "lower"  [attr-defined]` |
| 186 | `Argument "key" to "sort" of "list" has incompatible type "Callable[[dict[str, object]], object]"; expected "Callable[[dict[str, object]], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |
| 186 | `Incompatible return value type (got "object", expected "SupportsDunderLT[Any] \| SupportsDunderGT[Any]")  [return-value]` |

### `backend/src/sensei/services/ai/distilled_knowledge/tps_lean_knowledge_de.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 691 | `"Sequence[str]" has no attribute "lower"  [attr-defined]` |
| 716 | `"Sequence[str]" has no attribute "lower"  [attr-defined]` |
| 735 | `Argument "key" to "sort" of "list" has incompatible type "Callable[[dict[str, object]], object]"; expected "Callable[[dict[str, object]], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |
| 735 | `Incompatible return value type (got "object", expected "SupportsDunderLT[Any] \| SupportsDunderGT[Any]")  [return-value]` |

### `backend/src/sensei/services/ai/distilled_knowledge/tps_lean_knowledge_en.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 5041 | `"Sequence[str]" has no attribute "lower"  [attr-defined]` |
| 5066 | `"Sequence[str]" has no attribute "lower"  [attr-defined]` |
| 5085 | `Argument "key" to "sort" of "list" has incompatible type "Callable[[dict[str, object]], object]"; expected "Callable[[dict[str, object]], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |
| 5085 | `Incompatible return value type (got "object", expected "SupportsDunderLT[Any] \| SupportsDunderGT[Any]")  [return-value]` |

### `backend/src/sensei/services/ai/distilled_knowledge/tps_lean_knowledge_es.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 271 | `"Sequence[str]" has no attribute "lower"  [attr-defined]` |
| 296 | `"Sequence[str]" has no attribute "lower"  [attr-defined]` |
| 315 | `Argument "key" to "sort" of "list" has incompatible type "Callable[[dict[str, object]], object]"; expected "Callable[[dict[str, object]], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |
| 315 | `Incompatible return value type (got "object", expected "SupportsDunderLT[Any] \| SupportsDunderGT[Any]")  [return-value]` |

### `backend/src/sensei/services/ai/distilled_knowledge/tps_lean_knowledge_fr.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 1521 | `"Sequence[str]" has no attribute "lower"  [attr-defined]` |
| 1546 | `"Sequence[str]" has no attribute "lower"  [attr-defined]` |
| 1565 | `Argument "key" to "sort" of "list" has incompatible type "Callable[[dict[str, object]], object]"; expected "Callable[[dict[str, object]], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |
| 1565 | `Incompatible return value type (got "object", expected "SupportsDunderLT[Any] \| SupportsDunderGT[Any]")  [return-value]` |

### `backend/src/sensei/services/ai/distilled_knowledge/unified_reasoning_engine.py`
**Errors:** 8

| Line | Error Message |
|------|---------------|
| 127 | `Argument "key" to "sort" of "list" has incompatible type "Callable[[dict[str, object]], object]"; expected "Callable[[dict[str, object]], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |
| 127 | `Incompatible return value type (got "object", expected "SupportsDunderLT[Any] \| SupportsDunderGT[Any]")  [return-value]` |
| 211 | `Unsupported target for indexed assignment ("object")  [index]` |
| 212 | `Unsupported operand types for + ("object" and "int")  [operator]` |
| 217 | `Unsupported right operand type for in ("object")  [operator]` |
| 218 | `Unsupported target for indexed assignment ("object")  [index]` |
| 219 | `Value of type "object" is not indexable  [index]` |
| 219 | `Unsupported target for indexed assignment ("object")  [index]` |

### `backend/src/sensei/services/ai/document_intelligence.py`
**Errors:** 21

| Line | Error Message |
|------|---------------|
| 465 | `Skipping analyzing "onnxruntime": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 470 | `Incompatible types in assignment (expression has type "bool", variable has type "None")  [assignment]` |
| 479 | `Incompatible types in assignment (expression has type "bool", variable has type "None")  [assignment]` |
| 514 | `Cannot find implementation or library stub for module named "cv2"  [import-not-found]` |
| 523 | `"None" has no attribute "get_inputs"  [attr-defined]` |
| 524 | `"None" has no attribute "run"  [attr-defined]` |
| 618 | `Incompatible types in assignment (expression has type "OCREngine", variable has type "None")  [assignment]` |
| 619 | `Incompatible types in assignment (expression has type "bool", variable has type "None")  [assignment]` |
| 668 | `"None" has no attribute "get_inputs"  [attr-defined]` |
| 669 | `"None" has no attribute "run"  [attr-defined]` |
| 690 | `"None" has no attribute "extract_text"  [attr-defined]` |
| 741 | `Incompatible types in assignment (expression has type "OCREngine", variable has type "None")  [assignment]` |
| 743 | `"None" has no attribute "extract_text"  [attr-defined]` |
| 845 | `Name "cells" is not defined  [name-defined]` |
| 848 | `Name "headers" is not defined  [name-defined]` |
| 849 | `Name "table_bbox" is not defined  [name-defined]` |
| 877 | `Cannot find implementation or library stub for module named "pytesseract"  [import-not-found]` |
| 963 | `Need type annotation for "words" (hint: "words: list[<type>] = ...")  [var-annotated]` |
| 1191 | `Argument "key" to "max" has incompatible type overloaded function; expected "Callable[[DocumentType], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |
| 1255 | `Need type annotation for "results" (hint: "results: list[<type>] = ...")  [var-annotated]` |
| 1438 | `Incompatible types in assignment (expression has type "None", variable has type "VisionLLMEnricher")  [assignment]` |

### `backend/src/sensei/services/ai/enhanced_ml_pipeline.py`
**Errors:** 11

| Line | Error Message |
|------|---------------|
| 905 | `Incompatible types in assignment (expression has type "int \| str", variable has type "int \| None")  [assignment]` |
| 972 | `Unsupported target for indexed assignment ("object")  [index]` |
| 985 | `Unsupported target for indexed assignment ("object")  [index]` |
| 1417 | `Need type annotation for "all_metrics" (hint: "all_metrics: set[<type>] = ...")  [var-annotated]` |
| 1428 | `"Collection[Any]" has no attribute "append"  [attr-defined]` |
| 1437 | `Value of type "Collection[Any]" is not indexable  [index]` |
| 1490 | `Skipping analyzing "sklearn.model_selection": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 1491 | `Skipping analyzing "sklearn.ensemble": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 1492 | `Skipping analyzing "sklearn.linear_model": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 1791 | `Skipping analyzing "joblib": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 1874 | `Name "os" is not defined  [name-defined]` |

### `backend/src/sensei/services/ai/knowledge_embeddings.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 70 | `Incompatible types in assignment (expression has type "SentenceTransformer", variable has type "None")  [assignment]` |

### `backend/src/sensei/services/ai/knowledge_enrichment.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 783 | `Name "ingest_content" already defined on line 444  [no-redef]` |
| 860 | `Need type annotation for "current" (hint: "current: list[<type>] = ...")  [var-annotated]` |

### `backend/src/sensei/services/ai/knowledge_ingestion.py`
**Errors:** 9

| Line | Error Message |
|------|---------------|
| 331 | `Need type annotation for "current_section"  [var-annotated]` |
| 332 | `Need type annotation for "heading_stack" (hint: "heading_stack: list[<type>] = ...")  [var-annotated]` |
| 339 | `Item "list[Any]" of "list[Any] \| str \| None" has no attribute "strip"  [union-attr]` |
| 339 | `Item "None" of "list[Any] \| str \| None" has no attribute "strip"  [union-attr]` |
| 357 | `No overload variant of "__add__" of "list" matches argument type "str"  [operator]` |
| 357 | `Unsupported left operand type for + ("None")  [operator]` |
| 360 | `Item "list[Any]" of "list[Any] \| str \| None" has no attribute "strip"  [union-attr]` |
| 360 | `Item "None" of "list[Any] \| str \| None" has no attribute "strip"  [union-attr]` |
| 665 | `Need type annotation for "existing_texts" (hint: "existing_texts: list[<type>] = ...")  [var-annotated]` |

### `backend/src/sensei/services/ai/meta_sensei.py`
**Errors:** 6

| Line | Error Message |
|------|---------------|
| 354 | `Argument "key" to "max" has incompatible type overloaded function; expected "Callable[[str], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |
| 1265 | `Argument 1 to "sub" has incompatible type "str \| RegexFlag"; expected "str \| Pattern[str]"  [arg-type]` |
| 1265 | `Argument 2 to "sub" has incompatible type "str \| RegexFlag"; expected "str \| Callable[[Match[str]], str]"  [arg-type]` |
| 1265 | `Argument "flags" to "sub" has incompatible type "str \| RegexFlag \| int"; expected "int \| RegexFlag"  [arg-type]` |
| 1301 | `Argument 1 to "search" has incompatible type "str \| RegexFlag"; expected "str \| Pattern[str]"  [arg-type]` |
| 1301 | `Argument "flags" to "search" has incompatible type "str \| RegexFlag \| int"; expected "int \| RegexFlag"  [arg-type]` |

### `backend/src/sensei/services/ai/nlp_command_palette.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 653 | `Incompatible types in assignment (expression has type "Match[str] \| None", variable has type "SymbolMatch")  [assignment]` |
| 657 | `"SymbolMatch" has no attribute "group"  [attr-defined]` |
| 659 | `"SymbolMatch" has no attribute "start"  [attr-defined]` |
| 660 | `"SymbolMatch" has no attribute "end"  [attr-defined]` |

### `backend/src/sensei/services/ai/onnx_cross_encoder.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 226 | `Skipping analyzing "onnxruntime": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 320 | `Skipping analyzing "onnxruntime.quantization": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |

### `backend/src/sensei/services/ai/onnx_model_init.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 160 | `Skipping analyzing "onnxruntime": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 212 | `Incompatible types in assignment (expression has type "type[signedinteger[_64Bit]]", variable has type "type[floating[_32Bit]]")  [assignment]` |
| 214 | `Incompatible types in assignment (expression has type "type[signedinteger[_32Bit]]", variable has type "type[floating[_32Bit]]")  [assignment]` |
| 437 | `"ONNXTextEmbedder" has no attribute "is_loaded"  [attr-defined]` |

### `backend/src/sensei/services/ai/onnx_text_embeddings.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 70 | `Skipping analyzing "onnxruntime": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 150 | `Skipping analyzing "onnxruntime.quantization": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |

### `backend/src/sensei/services/ai/reasoning_engine.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 935 | `Argument "key" to "max" has incompatible type overloaded function; expected "Callable[[str], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |

### `backend/src/sensei/services/ai/virtual_assistant.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 370 | `Incompatible types in assignment (expression has type "float", variable has type "int")  [assignment]` |

### `backend/src/sensei/services/ai/visual_quality_inspection.py`
**Errors:** 12

| Line | Error Message |
|------|---------------|
| 338 | `Cannot find implementation or library stub for module named "cv2"  [import-not-found]` |
| 434 | `Argument 1 to "_is_in_zone" of "VisionEnrichmentSuite" has incompatible type "BoundingBox \| None"; expected "BoundingBox"  [arg-type]` |
| 636 | `Incompatible types in assignment (expression has type "ndarray[tuple[Any, ...], dtype[Any]]", variable has type "list[ndarray[tuple[Any, ...], dtype[Any]]]")  [assignment]` |
| 703 | `Incompatible types in assignment (expression has type "ndarray[tuple[Any, ...], dtype[Any]]", variable has type "list[Any]")  [assignment]` |
| 712 | `"list[Any]" has no attribute "reshape"  [attr-defined]` |
| 730 | `Argument "memory_bank" to "savez" has incompatible type "ndarray[tuple[Any, ...], dtype[Any]] \| None"; expected "Buffer \| _SupportsArray[dtype[Any]] \| _NestedSequence[_SupportsArray[dtype[Any]]] \| complex \| bytes \| str \| _NestedSequence[complex \| bytes \| str]"  [arg-type]` |
| 731 | `Argument "image_size" to "savez" has incompatible type "tuple[int, int] \| None"; expected "Buffer \| _SupportsArray[dtype[Any]] \| _NestedSequence[_SupportsArray[dtype[Any]]] \| complex \| bytes \| str \| _NestedSequence[complex \| bytes \| str]"  [arg-type]` |
| 800 | `Incompatible types in assignment (expression has type "bool", variable has type "None")  [assignment]` |
| 1151 | `Name "UUID" is not defined  [name-defined]` |
| 1172 | `Name "func" is not defined  [name-defined]` |
| 1188 | `Missing positional argument "created_at" in call to "TrainingDataset"  [call-arg]` |
| 1223 | `Signature of "record_feedback" incompatible with supertype "AsyncContinuousLearningManager"  [override]` |

### `backend/src/sensei/services/ai/visual_quality_v2/detectors.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 205 | `Cannot find implementation or library stub for module named "cv2"  [import-not-found]` |
| 227 | `Need type annotation for "defects" (hint: "defects: list[<type>] = ...")  [var-annotated]` |

### `backend/src/sensei/services/ai/visual_quality_v2/generators.py`
**Errors:** 8

| Line | Error Message |
|------|---------------|
| 38 | `Cannot find implementation or library stub for module named "cv2"  [import-not-found]` |
| 65 | `Argument 1 to "max" has incompatible type "int"; expected "tuple[Any, ...]"  [arg-type]` |
| 65 | `Argument 2 to "max" has incompatible type "int"; expected "tuple[Any, ...]"  [arg-type]` |
| 75 | `Argument 1 to "max" has incompatible type "int"; expected "tuple[Any, ...]"  [arg-type]` |
| 75 | `Argument 2 to "max" has incompatible type "int"; expected "tuple[Any, ...]"  [arg-type]` |
| 83 | `Incompatible types in assignment (expression has type "int", variable has type "tuple[Any, ...]")  [assignment]` |
| 98 | `Argument 1 to "max" has incompatible type "int"; expected "tuple[Any, ...]"  [arg-type]` |
| 98 | `Argument 2 to "max" has incompatible type "int"; expected "tuple[Any, ...]"  [arg-type]` |

### `backend/src/sensei/services/ai/visual_quality_v2/service.py`
**Errors:** 7

| Line | Error Message |
|------|---------------|
| 282 | `Signature of "record_feedback" incompatible with supertype "AsyncContinuousLearningManager"  [override]` |
| 334 | `Incompatible types in assignment (expression has type "ndarray[tuple[Any, ...], dtype[Any]]", variable has type "list[ndarray[tuple[Any, ...], dtype[Any]]]")  [assignment]` |
| 367 | `Incompatible types in assignment (expression has type "ndarray[tuple[Any, ...], dtype[Any]]", variable has type "list[Any]")  [assignment]` |
| 374 | `"list[Any]" has no attribute "reshape"  [attr-defined]` |
| 393 | `Argument "image_size" to "savez" has incompatible type "tuple[int, int] \| None"; expected "Buffer \| _SupportsArray[dtype[Any]] \| _NestedSequence[_SupportsArray[dtype[Any]]] \| complex \| bytes \| str \| _NestedSequence[complex \| bytes \| str]"  [arg-type]` |
| 435 | `Incompatible types in assignment (expression has type "bool", variable has type "None")  [assignment]` |
| 663 | `"VisionEnrichmentSuite" has no attribute "enrich_inspection"  [attr-defined]` |

### `backend/src/sensei/services/ai/world_class_document_ai.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 505 | `Too many arguments for "from_pixel_coords" of "BoundingBox"  [call-arg]` |
| 1153 | `Argument "key" to "max" has incompatible type overloaded function; expected "Callable[[DocumentCategory], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |
| 1333 | `Need type annotation for "gdt_callouts" (hint: "gdt_callouts: list[<type>] = ...")  [var-annotated]` |
| 1334 | `Need type annotation for "dimensions" (hint: "dimensions: list[<type>] = ...")  [var-annotated]` |

### `backend/src/sensei/services/autosave_drafts.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 790 | `Unsupported right operand type for in ("object")  [operator]` |
| 791 | `Unsupported target for indexed assignment ("object")  [index]` |
| 792 | `Value of type "object" is not indexable  [index]` |
| 792 | `Unsupported target for indexed assignment ("object")  [index]` |

### `backend/src/sensei/services/bulk_actions.py`
**Errors:** 18

| Line | Error Message |
|------|---------------|
| 216 | `Incompatible types in assignment (expression has type "UUID", target has type "str")  [assignment]` |
| 234 | `Incompatible types in assignment (expression has type "UUID", target has type "str")  [assignment]` |
| 391 | `Argument 1 to "_get_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |
| 399 | `Argument 1 to "_save_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |
| 412 | `Argument 1 to "_get_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |
| 420 | `Argument 1 to "_save_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |
| 433 | `Argument 1 to "_get_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |
| 441 | `Argument 1 to "_save_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |
| 454 | `Argument 1 to "_get_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |
| 462 | `Argument 1 to "_save_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |
| 475 | `Argument 1 to "_get_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |
| 484 | `Argument 1 to "_save_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |
| 497 | `Argument 1 to "_get_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |
| 506 | `Argument 1 to "_save_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |
| 518 | `Argument 1 to "_get_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |
| 529 | `Argument 1 to "_save_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |
| 541 | `Argument 1 to "_get_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |
| 552 | `Argument 1 to "_save_entity" of "BulkActionsService" has incompatible type "Any \| None"; expected "EntityType"  [arg-type]` |

### `backend/src/sensei/services/certification_tracking.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 485 | `Incompatible return value type (got "Coroutine[Any, Any, list[dict[str, Any]]]", expected "list[dict[str, Any]]")  [return-value]` |
| 521 | `Incompatible types in assignment (expression has type "str \| AwaitableValue[str]", variable has type "str")  [assignment]` |
| 543 | `Argument 1 to "get_access_logs" of "PIIControlsService" has incompatible type "AsyncSession"; expected "UUID \| None"  [arg-type]` |

### `backend/src/sensei/services/content_scanning.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 747 | `Incompatible types in assignment (expression has type "bool", variable has type "Match[str] \| None")  [assignment]` |
| 837 | `Incompatible types in assignment (expression has type "bool", variable has type "Match[str] \| None")  [assignment]` |

### `backend/src/sensei/services/core/backup_scheduler.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 14 | `Skipping analyzing "apscheduler.schedulers.background": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 15 | `Skipping analyzing "apscheduler.triggers.cron": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 16 | `Skipping analyzing "apscheduler.triggers.interval": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 267 | `Unexpected keyword argument "metadata" for "create_backup" of "DatabaseBackupService"  [call-arg]` |

### `backend/src/sensei/services/core/context_bus.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 200 | `Dict entry 11 has incompatible type "str": "float \| None"; expected "str": "str \| list[Any] \| int \| None"  [dict-item]` |

### `backend/src/sensei/services/core/data_retention.py`
**Errors:** 6

| Line | Error Message |
|------|---------------|
| 276 | `Argument "name" to "RetentionPolicy" has incompatible type "object"; expected "str"  [arg-type]` |
| 277 | `Argument "description" to "RetentionPolicy" has incompatible type "object"; expected "str"  [arg-type]` |
| 278 | `Argument "entity_type" to "RetentionPolicy" has incompatible type "object"; expected "EntityType"  [arg-type]` |
| 279 | `Argument "retention_days" to "RetentionPolicy" has incompatible type "object"; expected "int"  [arg-type]` |
| 280 | `Argument "action" to "RetentionPolicy" has incompatible type "object"; expected "RetentionAction"  [arg-type]` |
| 281 | `Argument "exclude_statuses" to "RetentionPolicy" has incompatible type "object"; expected "list[str] \| None"  [arg-type]` |

### `backend/src/sensei/services/core/database_backup.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 366 | `Argument 1 to "_create_test_database" of "DatabaseBackupService" has incompatible type "str \| None"; expected "str"  [arg-type]` |
| 420 | `Argument 1 to "_drop_test_database" of "DatabaseBackupService" has incompatible type "str \| None"; expected "str"  [arg-type]` |
| 475 | `Incompatible default for argument "retention_days" (default has type "None", argument has type "int")  [assignment]` |
| 569 | `Unsupported operand types for >= ("int" and "None")  [operator]` |

### `backend/src/sensei/services/core/edge_ai.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 434 | `Incompatible types in assignment (expression has type "ONNXEdgeInference", variable has type "None")  [assignment]` |
| 435 | `"None" has no attribute "is_ready"  [attr-defined]` |
| 438 | `"None" has no attribute "is_using_onnx"  [attr-defined]` |

### `backend/src/sensei/services/core/factory_launchpad.py`
**Errors:** 8

| Line | Error Message |
|------|---------------|
| 299 | `Dict entry 0 has incompatible type "str": "MaturityLevel"; expected "str": "dict[str, int]"  [dict-item]` |
| 300 | `Dict entry 1 has incompatible type "str": "MaturityLevel"; expected "str": "dict[str, int]"  [dict-item]` |
| 301 | `Dict entry 2 has incompatible type "str": "MaturityLevel"; expected "str": "dict[str, int]"  [dict-item]` |
| 302 | `Dict entry 3 has incompatible type "str": "MaturityLevel"; expected "str": "dict[str, int]"  [dict-item]` |
| 303 | `Dict entry 4 has incompatible type "str": "MaturityLevel"; expected "str": "dict[str, int]"  [dict-item]` |
| 861 | `Unsupported operand types for < ("MaturityLevel" and "dict[str, int]")  [operator]` |
| 869 | `Argument 1 to "MaturityLevel" has incompatible type "dict[str, int]"; expected "int"  [arg-type]` |
| 937 | `Argument "visible" to "FeatureAccess" has incompatible type "MaturityLevel \| bool \| None"; expected "bool"  [arg-type]` |

### `backend/src/sensei/services/core/health_checks.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 26 | `Library stubs not installed for "psutil"  [import-untyped]` |

### `backend/src/sensei/services/core/local_first_infrastructure.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 122 | `Library stubs not installed for "psutil"  [import-untyped]` |
| 670 | `Skipping analyzing "onnxruntime": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 921 | `Skipping analyzing "onnxruntime.quantization": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 1008 | `Skipping analyzing "onnxruntime.transformers": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |

### `backend/src/sensei/services/core/notification_triggers.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 693 | `Need type annotation for "notifications" (hint: "notifications: list[<type>] = ...")  [var-annotated]` |

### `backend/src/sensei/services/core/onnx_edge_inference.py`
**Errors:** 7

| Line | Error Message |
|------|---------------|
| 91 | `Skipping analyzing "onnxruntime": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 167 | `Argument 2 to "export" has incompatible type "Tensor"; expected "tuple[Any, ...]"  [arg-type]` |
| 182 | `Skipping analyzing "onnxruntime.quantization": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 197 | `"None" has no attribute "run"  [attr-defined]` |
| 217 | `Incompatible types in assignment (expression has type "EdgeCNN1D", variable has type "None")  [assignment]` |
| 263 | `"None" has no attribute "run"  [attr-defined]` |
| 332 | `"None" has no attribute "run"  [attr-defined]` |

### `backend/src/sensei/services/core/pii_controls.py`
**Errors:** 17

| Line | Error Message |
|------|---------------|
| 224 | `Argument 1 to "len" has incompatible type "T"; expected "Sized"  [arg-type]` |
| 230 | `Unsupported right operand type for in ("T")  [operator]` |
| 1178 | `Incompatible return value type (got "T", expected "AwaitableValue[T]")  [return-value]` |
| 1385 | `Argument 1 to "_wrap_coro" of "PIIControlsService" has incompatible type "Coroutine[Any, Any, list[PIIField]]"; expected "Awaitable[list[MemoryPIIField \| PIIField]]"  [arg-type]` |
| 1395 | `Argument 1 to "_wrap" of "PIIControlsService" has incompatible type "list[MemoryPIIField]"; expected "list[MemoryPIIField \| PIIField]"  [arg-type]` |
| 1501 | `Argument 1 to "_wrap_coro" of "PIIControlsService" has incompatible type "Coroutine[Any, Any, list[DataSubject]]"; expected "Awaitable[list[MemoryDataSubject \| DataSubject]]"  [arg-type]` |
| 1510 | `Argument 1 to "_wrap" of "PIIControlsService" has incompatible type "list[MemoryDataSubject]"; expected "list[MemoryDataSubject \| DataSubject]"  [arg-type]` |
| 1607 | `Argument 1 to "_wrap_coro" of "PIIControlsService" has incompatible type "Coroutine[Any, Any, list[Consent]]"; expected "Awaitable[list[MemoryConsent \| Consent]]"  [arg-type]` |
| 1616 | `Argument 1 to "_wrap" of "PIIControlsService" has incompatible type "list[MemoryConsent]"; expected "list[MemoryConsent \| Consent]"  [arg-type]` |
| 1786 | `Argument 1 to "_wrap_coro" of "PIIControlsService" has incompatible type "Coroutine[Any, Any, list[PIIAccessLog]]"; expected "Awaitable[list[MemoryAccessLog \| PIIAccessLog]]"  [arg-type]` |
| 1793 | `Argument 1 to "_wrap" of "PIIControlsService" has incompatible type "list[MemoryAccessLog]"; expected "list[MemoryAccessLog \| PIIAccessLog]"  [arg-type]` |
| 1858 | `Argument 1 to "_wrap_coro" of "PIIControlsService" has incompatible type "Coroutine[Any, Any, list[DeletionRequest]]"; expected "Awaitable[list[MemoryDeletionRequest \| DeletionRequest]]"  [arg-type]` |
| 1861 | `Argument 1 to "_wrap" of "PIIControlsService" has incompatible type "list[MemoryDeletionRequest]"; expected "list[MemoryDeletionRequest \| DeletionRequest]"  [arg-type]` |
| 1901 | `Argument "consents" to "PIIReport" has incompatible type "list[MemoryConsent]"; expected "list[Consent]"  [arg-type]` |
| 1902 | `Argument "access_logs" to "PIIReport" has incompatible type "list[MemoryAccessLog]"; expected "list[PIIAccessLog]"  [arg-type]` |
| 1929 | `Argument 1 to "_wrap_coro" of "PIIControlsService" has incompatible type "Coroutine[Any, Any, list[Consent]]"; expected "Awaitable[list[MemoryConsent \| Consent]]"  [arg-type]` |
| 1936 | `Argument 1 to "_wrap" of "PIIControlsService" has incompatible type "list[MemoryConsent]"; expected "list[MemoryConsent \| Consent]"  [arg-type]` |

### `backend/src/sensei/services/core/rbac_security_audit.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 658 | `Incompatible types in assignment (expression has type "UserRoleAssignment \| None", variable has type "UserRoleAssignment")  [assignment]` |

### `backend/src/sensei/services/core/role_insights_config.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 585 | `Need type annotation for "accessible" (hint: "accessible: set[<type>] = ...")  [var-annotated]` |

### `backend/src/sensei/services/core/search.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 607 | `Incompatible types in assignment (expression has type "list[int]", variable has type "range")  [assignment]` |

### `backend/src/sensei/services/core/setup_wizard.py`
**Errors:** 81

| Line | Error Message |
|------|---------------|
| 289 | `Missing named argument "is_active" for "PipelineStage"  [call-arg]` |
| 298 | `Missing named argument "is_active" for "PipelineStage"  [call-arg]` |
| 307 | `Missing named argument "is_active" for "PipelineStage"  [call-arg]` |
| 316 | `Missing named argument "is_active" for "PipelineStage"  [call-arg]` |
| 385 | `Missing named argument "is_required" for "LSWChecklistItem"  [call-arg]` |
| 393 | `Missing named argument "is_required" for "LSWChecklistItem"  [call-arg]` |
| 401 | `Missing named argument "is_required" for "LSWChecklistItem"  [call-arg]` |
| 409 | `Missing named argument "is_required" for "LSWChecklistItem"  [call-arg]` |
| 420 | `Missing named argument "is_required" for "LSWChecklistItem"  [call-arg]` |
| 428 | `Missing named argument "is_required" for "LSWChecklistItem"  [call-arg]` |
| 436 | `Missing named argument "is_required" for "LSWChecklistItem"  [call-arg]` |
| 444 | `Missing named argument "is_required" for "LSWChecklistItem"  [call-arg]` |
| 455 | `Missing named argument "is_required" for "LSWChecklistItem"  [call-arg]` |
| 463 | `Missing named argument "is_required" for "LSWChecklistItem"  [call-arg]` |
| 471 | `Missing named argument "is_required" for "LSWChecklistItem"  [call-arg]` |
| 479 | `Missing named argument "is_required" for "LSWChecklistItem"  [call-arg]` |
| 577 | `Generator has incompatible item type "int"; expected "bool"  [misc]` |
| 578 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 578 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 578 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 585 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 585 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 585 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 610 | `Missing named argument "completed_at" for "WizardProgress"  [call-arg]` |
| 726 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 726 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 726 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 777 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 777 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 777 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 795 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 795 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 795 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 800 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 800 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 800 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 805 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 805 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 805 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 810 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 810 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 810 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 815 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 815 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 815 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 820 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 820 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 820 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 825 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 825 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 825 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 839 | `Missing named argument "redirect_url" for "CompleteWizardResponse"  [call-arg]` |
| 848 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 848 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 848 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 853 | `Missing named argument "redirect_url" for "CompleteWizardResponse"  [call-arg]` |
| 866 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 866 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 866 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 870 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 870 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 870 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 874 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 874 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 874 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 878 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 878 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 878 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 882 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 882 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 882 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 886 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 886 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 886 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 890 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 890 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 890 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |
| 901 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 959 | `Missing named argument "status" for "WizardStepData"  [call-arg]` |
| 959 | `Missing named argument "started_at" for "WizardStepData"  [call-arg]` |
| 959 | `Missing named argument "completed_at" for "WizardStepData"  [call-arg]` |

### `backend/src/sensei/services/core/template_cloning.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 782 | `Argument 2 to "_get_entity" of "TemplateCloningService" has incompatible type "UUID \| None"; expected "UUID"  [arg-type]` |
| 785 | `Argument 2 to "_save_entity" of "TemplateCloningService" has incompatible type "UUID \| None"; expected "UUID"  [arg-type]` |
| 794 | `Need type annotation for "versions" (hint: "versions: list[<type>] = ...")  [var-annotated]` |

### `backend/src/sensei/services/ehs_safety.py`
**Errors:** 11

| Line | Error Message |
|------|---------------|
| 979 | `Need type annotation for "matrix" (hint: "matrix: dict[<type>, <type>] = ...")  [var-annotated]` |
| 1025 | `"object" has no attribute "append"  [attr-defined]` |
| 1032 | `"object" has no attribute "append"  [attr-defined]` |
| 1041 | `"object" has no attribute "append"  [attr-defined]` |
| 1043 | `"object" has no attribute "append"  [attr-defined]` |
| 1258 | `Dict entry 3 has incompatible type "str": "int"; expected "str": "str"  [dict-item]` |
| 1259 | `Dict entry 4 has incompatible type "str": "int"; expected "str": "str"  [dict-item]` |
| 1260 | `Dict entry 5 has incompatible type "str": "bool"; expected "str": "str"  [dict-item]` |
| 1272 | `Dict entry 5 has incompatible type "str": "str \| None"; expected "str": "str"  [dict-item]` |
| 1287 | `Dict entry 4 has incompatible type "str": "bool"; expected "str": "str"  [dict-item]` |
| 1336 | `Incompatible types in assignment (expression has type "CertificationStatus", variable has type "IncidentStatus")  [assignment]` |

### `backend/src/sensei/services/erp_integration.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 1370 | `Need type annotation for "conflicts" (hint: "conflicts: list[<type>] = ...")  [var-annotated]` |

### `backend/src/sensei/services/escalation_policy.py`
**Errors:** 10

| Line | Error Message |
|------|---------------|
| 747 | `Item "None" of "Any \| None" has no attribute "isoformat"  [union-attr]` |
| 1233 | `Unsupported operand types for + ("object" and "int")  [operator]` |
| 1234 | `Unsupported operand types for + ("object" and "int")  [operator]` |
| 1235 | `"object" has no attribute "extend"  [attr-defined]` |
| 1238 | `Value of type "object" is not indexable  [index]` |
| 1238 | `Unsupported target for indexed assignment ("object")  [index]` |
| 1239 | `Value of type "object" is not indexable  [index]` |
| 1239 | `Unsupported target for indexed assignment ("object")  [index]` |
| 1240 | `Value of type "object" is not indexable  [index]` |
| 1240 | `Unsupported target for indexed assignment ("object")  [index]` |

### `backend/src/sensei/services/exceptions_aggregator.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 307 | `Incompatible types in "await" (actual type "list[ExceptionItem]", expected type "Awaitable[Any]")  [misc]` |

### `backend/src/sensei/services/external/starz_ingestion.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 204 | `Incompatible types in assignment (expression has type "float", variable has type "SQLCoreOperations[Decimal \| None] \| Decimal \| None")  [assignment]` |
| 286 | `Incompatible types in assignment (expression has type "float", variable has type "SQLCoreOperations[Decimal] \| Decimal")  [assignment]` |

### `backend/src/sensei/services/finance/fixed_assets.py`
**Errors:** 12

| Line | Error Message |
|------|---------------|
| 781 | `Item "None" of "Any \| None" has no attribute "create_journal_entry"  [union-attr]` |
| 795 | `Item "None" of "Any \| None" has no attribute "approve_journal_entry"  [union-attr]` |
| 801 | `Item "None" of "Any \| None" has no attribute "post_journal_entry"  [union-attr]` |
| 837 | `Item "None" of "Any \| None" has no attribute "create_journal_entry"  [union-attr]` |
| 851 | `Item "None" of "Any \| None" has no attribute "approve_journal_entry"  [union-attr]` |
| 857 | `Item "None" of "Any \| None" has no attribute "post_journal_entry"  [union-attr]` |
| 895 | `Item "None" of "Any \| None" has no attribute "create_journal_entry"  [union-attr]` |
| 910 | `Item "None" of "Any \| None" has no attribute "approve_journal_entry"  [union-attr]` |
| 916 | `Item "None" of "Any \| None" has no attribute "post_journal_entry"  [union-attr]` |
| 997 | `Item "None" of "Any \| None" has no attribute "create_journal_entry"  [union-attr]` |
| 1012 | `Item "None" of "Any \| None" has no attribute "approve_journal_entry"  [union-attr]` |
| 1018 | `Item "None" of "Any \| None" has no attribute "post_journal_entry"  [union-attr]` |

### `backend/src/sensei/services/guardrails_performance.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 854 | `Incompatible types in assignment (expression has type "float", variable has type "int")  [assignment]` |

### `backend/src/sensei/services/hr/employee_lifecycle.py`
**Errors:** 5

| Line | Error Message |
|------|---------------|
| 403 | `Incompatible return value type (got "Coroutine[Any, Any, EmployeeProfile \| None]", expected "EmployeeProfile \| None")  [return-value]` |
| 427 | `Argument "email" to "replace" of "EmployeeProfile" has incompatible type "str \| AwaitableValue[str] \| None"; expected "str \| None"  [arg-type]` |
| 427 | `Argument "phone" to "replace" of "EmployeeProfile" has incompatible type "str \| AwaitableValue[str] \| None"; expected "str \| None"  [arg-type]` |
| 646 | `Argument "filename" to "replace" of "PersonnelDocument" has incompatible type "str \| AwaitableValue[str]"; expected "str"  [arg-type]` |
| 662 | `Incompatible types in assignment (expression has type "list[MemoryAccessLog \| PIIAccessLog]", variable has type "AwaitableValue[list[MemoryAccessLog \| PIIAccessLog]]")  [assignment]` |

### `backend/src/sensei/services/incident_flow.py`
**Errors:** 7

| Line | Error Message |
|------|---------------|
| 785 | `Incompatible types in assignment (expression has type "list[Incident]", variable has type "dict_values[str, Incident]")  [assignment]` |
| 787 | `Incompatible types in assignment (expression has type "list[Incident]", variable has type "dict_values[str, Incident]")  [assignment]` |
| 789 | `Incompatible types in assignment (expression has type "list[Incident]", variable has type "dict_values[str, Incident]")  [assignment]` |
| 814 | `Generator has incompatible item type "float \| Any"; expected "bool"  [misc]` |
| 814 | `Unsupported left operand type for - ("None")  [operator]` |
| 825 | `Generator has incompatible item type "float \| Any"; expected "bool"  [misc]` |
| 825 | `Unsupported left operand type for - ("None")  [operator]` |

### `backend/src/sensei/services/inline_comments.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 1030 | `Argument "key" to "sort" of "list" has incompatible type "Callable[[dict[str, object]], object]"; expected "Callable[[dict[str, object]], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |
| 1030 | `Incompatible return value type (got "object", expected "SupportsDunderLT[Any] \| SupportsDunderGT[Any]")  [return-value]` |

### `backend/src/sensei/services/maintenance/maintenance_tpm.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 1030 | `Argument 1 to "float" has incompatible type "Decimal \| None"; expected "str \| Buffer \| SupportsFloat \| SupportsIndex"  [arg-type]` |
| 1045 | `Argument 1 to "float" has incompatible type "Decimal \| None"; expected "str \| Buffer \| SupportsFloat \| SupportsIndex"  [arg-type]` |
| 1168 | `Argument 1 to "get" of "dict" has incompatible type "Any \| None"; expected "str"  [arg-type]` |

### `backend/src/sensei/services/ops/cognitive_obeya.py`
**Errors:** 18

| Line | Error Message |
|------|---------------|
| 319 | `"WorkOrder" has no attribute "description"  [attr-defined]` |
| 321 | `"WorkOrder" has no attribute "actual_end_date"; maybe "actual_end"?  [attr-defined]` |
| 321 | `"WorkOrder" has no attribute "due_date"  [attr-defined]` |
| 338 | `"RFQ" has no attribute "customer_name"; maybe "customer_notes"?  [attr-defined]` |
| 615 | `Signature of "record_metric" incompatible with supertype "AsyncPrescriptiveMetricAnalyzer"  [override]` |
| 618 | `Signature of "get_metric_history" incompatible with supertype "AsyncPrescriptiveMetricAnalyzer"  [override]` |
| 675 | `Signature of "find_causal_links" incompatible with supertype "AsyncPrescriptiveMetricAnalyzer"  [override]` |
| 701 | `Signature of "analyze_trend" incompatible with supertype "AsyncPrescriptiveMetricAnalyzer"  [override]` |
| 951 | `Need type annotation for "suggestions" (hint: "suggestions: list[<type>] = ...")  [var-annotated]` |
| 1046 | `Name "analyze_resource_rebalancing" already defined on line 950  [no-redef]` |
| 1053 | `Need type annotation for "suggestions" (hint: "suggestions: list[<type>] = ...")  [var-annotated]` |
| 1152 | `Name "get_active_silo_alerts" already defined on line 947  [no-redef]` |
| 1345 | `Name "get_all_suggestions" already defined on line 1272  [no-redef]` |
| 1375 | `Signature of "analyze_volume_leveling" incompatible with supertype "AsyncHeijunkaAdvisor"  [override]` |
| 1566 | `"AsyncCrossFunctionalSynergyEngine" has no attribute "analyze_resource_rebalancing"  [attr-defined]` |
| 1614 | `"type[HeijunkaSuggestionRecord]" has no attribute "status"  [attr-defined]` |
| 1715 | `Missing positional argument "db" in call to "get_all_suggestions" of "AsyncHeijunkaAdvisor"  [call-arg]` |
| 1715 | `"Coroutine[Any, Any, list[HeijunkaSuggestion]]" has no attribute "__iter__" (not iterable)  [attr-defined]` |

### `backend/src/sensei/services/ops/erp_integration.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 75 | `Item "None" of "GLAccount \| None" has no attribute "id"  [union-attr]` |
| 87 | `Item "None" of "GLAccount \| None" has no attribute "id"  [union-attr]` |

### `backend/src/sensei/services/ops/jit_lean_learning.py`
**Errors:** 13

| Line | Error Message |
|------|---------------|
| 607 | `Signature of "mark_viewed" incompatible with supertype "AsyncMicroLessonEngine"  [override]` |
| 615 | `Signature of "mark_completed" incompatible with supertype "AsyncMicroLessonEngine"  [override]` |
| 634 | `Signature of "get_delivery_stats" incompatible with supertype "AsyncMicroLessonEngine"  [override]` |
| 901 | `"Sequence[str]" has no attribute "append"  [attr-defined]` |
| 904 | `"Sequence[str]" has no attribute "append"  [attr-defined]` |
| 907 | `"Sequence[str]" has no attribute "append"  [attr-defined]` |
| 1116 | `Signature of "draft_update_from_a3" incompatible with supertype "AsyncStandardWorkEvolutionEngine"  [override]` |
| 1145 | `Signature of "approve_draft" incompatible with supertype "AsyncStandardWorkEvolutionEngine"  [override]` |
| 1184 | `Signature of "get_pending_drafts" incompatible with supertype "AsyncStandardWorkEvolutionEngine"  [override]` |
| 1230 | `Incompatible types in assignment (expression has type "str", target has type "None")  [assignment]` |
| 1251 | `Incompatible types in assignment (expression has type "dict[str, str]", target has type "None")  [assignment]` |
| 1431 | `Incompatible types in assignment (expression has type "str", target has type "None")  [assignment]` |
| 1435 | `Incompatible types in assignment (expression has type "dict[str, str]", target has type "None")  [assignment]` |

### `backend/src/sensei/services/ops/kpi_metrics.py`
**Errors:** 10

| Line | Error Message |
|------|---------------|
| 104 | `Cannot call function of unknown type  [operator]` |
| 108 | `Incompatible types in assignment (expression has type "type[unaryop]", variable has type "type[operator]")  [assignment]` |
| 113 | `Cannot call function of unknown type  [operator]` |
| 125 | `Cannot call function of unknown type  [operator]` |
| 129 | `Incompatible return value type (got "list[float]", expected "float")  [return-value]` |
| 133 | `Incompatible return value type (got "tuple[float, ...]", expected "float")  [return-value]` |
| 885 | `Item "None" of "KPIValue \| None" has no attribute "value"  [union-attr]` |
| 886 | `Item "None" of "KPIValue \| None" has no attribute "value"  [union-attr]` |
| 887 | `Item "None" of "KPIValue \| None" has no attribute "value"  [union-attr]` |
| 1124 | `Incompatible types in assignment (expression has type "dict[str, dict[str, str] \| float \| str \| dict[str, str \| float \| int] \| None]", target has type "str")  [assignment]` |

### `backend/src/sensei/services/ops/muda_nudging_scheduler.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 17 | `Skipping analyzing "apscheduler.schedulers.background": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 18 | `Skipping analyzing "apscheduler.triggers.interval": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 133 | `Argument "on_deliver" to "run" of "MudaNudgingJobRunner" has incompatible type "Callable[[MudaNudge], Task[Any]]"; expected "Callable[[MudaNudge], None] \| None"  [arg-type]` |

### `backend/src/sensei/services/ops/sensei_autopilot.py`
**Errors:** 9

| Line | Error Message |
|------|---------------|
| 725 | `"Sequence[str]" has no attribute "append"  [attr-defined]` |
| 733 | `"Sequence[str]" has no attribute "append"  [attr-defined]` |
| 740 | `"Sequence[str]" has no attribute "append"  [attr-defined]` |
| 748 | `Generator has incompatible item type "int"; expected "bool"  [misc]` |
| 749 | `Invalid index type "str" for "str"; expected type "SupportsIndex \| slice[Any, Any, Any]"  [index]` |
| 1203 | `"Sequence[str]" has no attribute "append"  [attr-defined]` |
| 1214 | `"Sequence[str]" has no attribute "append"  [attr-defined]` |
| 1222 | `"Sequence[str]" has no attribute "append"  [attr-defined]` |
| 1232 | `"Sequence[str]" has no attribute "append"  [attr-defined]` |

### `backend/src/sensei/services/ops/sensei_nudges.py`
**Errors:** 9

| Line | Error Message |
|------|---------------|
| 495 | `Argument 1 to "get" of "dict" has incompatible type "Any \| None"; expected "str"  [arg-type]` |
| 507 | `Argument 1 to "float" has incompatible type "Any \| None"; expected "str \| Buffer \| SupportsFloat \| SupportsIndex"  [arg-type]` |
| 510 | `Argument 1 to "float" has incompatible type "Any \| None"; expected "str \| Buffer \| SupportsFloat \| SupportsIndex"  [arg-type]` |
| 513 | `Argument 1 to "float" has incompatible type "Any \| None"; expected "str \| Buffer \| SupportsFloat \| SupportsIndex"  [arg-type]` |
| 516 | `Argument 1 to "float" has incompatible type "Any \| None"; expected "str \| Buffer \| SupportsFloat \| SupportsIndex"  [arg-type]` |
| 525 | `Unsupported right operand type for in ("Any \| None")  [operator]` |
| 528 | `Unsupported operand types for in ("Any \| None" and "str")  [operator]` |
| 538 | `Unsupported operand types for <= ("int" and "None")  [operator]` |
| 544 | `Unsupported operand types for > ("int" and "None")  [operator]` |

### `backend/src/sensei/services/ops/today_screen.py`
**Errors:** 188

| Line | Error Message |
|------|---------------|
| 98 | `Name "RiskCategory" already defined (possibly by an import)  [no-redef]` |
| 109 | `Name "AbnormalityType" already defined (possibly by an import)  [no-redef]` |
| 140 | `Name "CommitmentType" already defined (possibly by an import)  [no-redef]` |
| 166 | `Name "PriorityLevel" already defined (possibly by an import)  [no-redef]` |
| 174 | `Name "LSWChecklistStatus" already defined (possibly by an import)  [no-redef]` |
| 183 | `Name "ShopFloorAreaType" already defined (possibly by an import)  [no-redef]` |
| 193 | `Name "ShopFloorAlertSeverity" already defined (possibly by an import)  [no-redef]` |
| 202 | `Name "Priority" already defined (possibly by an import)  [no-redef]` |
| 220 | `Name "Risk" already defined (possibly by an import)  [no-redef]` |
| 241 | `Name "Commitment" already defined (possibly by an import)  [no-redef]` |
| 262 | `Name "Abnormality" already defined (possibly by an import)  [no-redef]` |
| 281 | `Name "MicroDrill" already defined (possibly by an import)  [no-redef]` |
| 295 | `Name "LSWChecklistSummary" already defined (possibly by an import)  [no-redef]` |
| 312 | `Name "QuickMetric" already defined (possibly by an import)  [no-redef]` |
| 329 | `Name "WorkOrderAtRisk" already defined (possibly by an import)  [no-redef]` |
| 348 | `Name "CriticalAndon" already defined (possibly by an import)  [no-redef]` |
| 368 | `Name "StationEfficiency" already defined (possibly by an import)  [no-redef]` |
| 385 | `Name "CellOEE" already defined (possibly by an import)  [no-redef]` |
| 402 | `Name "KanbanAlert" already defined (possibly by an import)  [no-redef]` |
| 420 | `Name "ExpiringCertification" already defined (possibly by an import)  [no-redef]` |
| 436 | `Name "WIPViolation" already defined (possibly by an import)  [no-redef]` |
| 452 | `Name "CAPAVerification" already defined (possibly by an import)  [no-redef]` |
| 469 | `Name "ScheduledTraining" already defined (possibly by an import)  [no-redef]` |
| 487 | `Name "ShopFloorSummary" already defined (possibly by an import)  [no-redef]` |
| 527 | `Name "TodayScreenData" already defined (possibly by an import)  [no-redef]` |
| 589 | `Incompatible types in "await" (actual type "Coroutine[Any, Any, dict[str, Any]] \| Awaitable[dict[Any, Any]] \| dict[Any, Any]", expected type "Awaitable[Any]")  [misc]` |
| 609 | `Incompatible types in "await" (actual type "Coroutine[Any, Any, None] \| Awaitable[int] \| int", expected type "Awaitable[Any]")  [misc]` |
| 616 | `Incompatible types in "await" (actual type "Coroutine[Any, Any, dict[str, Any]] \| Awaitable[dict[Any, Any]] \| dict[Any, Any]", expected type "Awaitable[Any]")  [misc]` |
| 628 | `Incompatible types in "await" (actual type "Coroutine[Any, Any, None] \| Awaitable[int] \| int", expected type "Awaitable[Any]")  [misc]` |
| 763 | `Unexpected keyword argument "risk_score" for "Risk"  [call-arg]` |
| 968 | `Argument "severity" to "Abnormality" has incompatible type "int"; expected "PriorityLevel"  [arg-type]` |
| 1133 | `Argument "question" to "MicroDrill" has incompatible type "object"; expected "str"  [arg-type]` |
| 1134 | `Argument "answer" to "MicroDrill" has incompatible type "object"; expected "str"  [arg-type]` |
| 1135 | `Argument "hint" to "MicroDrill" has incompatible type "object"; expected "str \| None"  [arg-type]` |
| 1136 | `Argument "category" to "MicroDrill" has incompatible type "object"; expected "str"  [arg-type]` |
| 1137 | `Argument "difficulty" to "MicroDrill" has incompatible type "object"; expected "int"  [arg-type]` |
| 1319 | `Unexpected keyword argument "quantity" for "WorkOrderAtRisk"  [call-arg]` |
| 1319 | `Unexpected keyword argument "days_at_risk" for "WorkOrderAtRisk"  [call-arg]` |
| 1319 | `Unexpected keyword argument "work_center_id" for "WorkOrderAtRisk"  [call-arg]` |
| 1319 | `Unexpected keyword argument "work_center_name" for "WorkOrderAtRisk"  [call-arg]` |
| 1319 | `Unexpected keyword argument "reason" for "WorkOrderAtRisk"  [call-arg]` |
| 1319 | `Unexpected keyword argument "assigned_to_id" for "WorkOrderAtRisk"  [call-arg]` |
| 1319 | `Unexpected keyword argument "assigned_to_name" for "WorkOrderAtRisk"  [call-arg]` |
| 1353 | `"WorkOrderAtRisk" has no attribute "work_center_id"  [attr-defined]` |
| 1362 | `"WorkOrderAtRisk" has no attribute "days_at_risk"  [attr-defined]` |
| 1369 | `Incompatible types in "await" (actual type "Awaitable[int] \| int", expected type "Awaitable[Any]")  [misc]` |
| 1383 | `Unexpected keyword argument "title" for "CriticalAndon"  [call-arg]` |
| 1383 | `Unexpected keyword argument "description" for "CriticalAndon"  [call-arg]` |
| 1383 | `Unexpected keyword argument "work_center_id" for "CriticalAndon"  [call-arg]` |
| 1383 | `Unexpected keyword argument "work_center_name" for "CriticalAndon"  [call-arg]` |
| 1383 | `Unexpected keyword argument "raised_at" for "CriticalAndon"  [call-arg]` |
| 1383 | `Unexpected keyword argument "minutes_open" for "CriticalAndon"  [call-arg]` |
| 1383 | `Unexpected keyword argument "acknowledged" for "CriticalAndon"; did you mean "is_acknowledged"?  [call-arg]` |
| 1383 | `Unexpected keyword argument "acknowledged_by_id" for "CriticalAndon"  [call-arg]` |
| 1383 | `Unexpected keyword argument "acknowledged_by_name" for "CriticalAndon"  [call-arg]` |
| 1390 | `Argument "station_id" to "CriticalAndon" has incompatible type "UUID \| None"; expected "UUID"  [arg-type]` |
| 1391 | `Argument "station_name" to "CriticalAndon" has incompatible type "str \| None"; expected "str"  [arg-type]` |
| 1416 | `"CriticalAndon" has no attribute "acknowledged"; maybe "is_acknowledged"?  [attr-defined]` |
| 1417 | `"CriticalAndon" has no attribute "acknowledged_by_id"  [attr-defined]` |
| 1418 | `"CriticalAndon" has no attribute "acknowledged_by_name"  [attr-defined]` |
| 1435 | `Incompatible types in "await" (actual type "Awaitable[int] \| int", expected type "Awaitable[Any]")  [misc]` |
| 1455 | `"CriticalAndon" has no attribute "minutes_open"  [attr-defined]` |
| 1455 | `"CriticalAndon" has no attribute "raised_at"  [attr-defined]` |
| 1457 | `"CriticalAndon" has no attribute "work_center_id"  [attr-defined]` |
| 1459 | `"CriticalAndon" has no attribute "acknowledged"; maybe "is_acknowledged"?  [attr-defined]` |
| 1464 | `"CriticalAndon" has no attribute "acknowledged"; maybe "is_acknowledged"?  [attr-defined]` |
| 1464 | `"CriticalAndon" has no attribute "minutes_open"  [attr-defined]` |
| 1485 | `Unexpected keyword argument "work_center_id" for "StationEfficiency"  [call-arg]` |
| 1485 | `Unexpected keyword argument "work_center_name" for "StationEfficiency"  [call-arg]` |
| 1485 | `Unexpected keyword argument "current_efficiency" for "StationEfficiency"  [call-arg]` |
| 1485 | `Unexpected keyword argument "target_efficiency" for "StationEfficiency"  [call-arg]` |
| 1485 | `Unexpected keyword argument "variance" for "StationEfficiency"  [call-arg]` |
| 1485 | `Unexpected keyword argument "trend" for "StationEfficiency"  [call-arg]` |
| 1485 | `Unexpected keyword argument "is_below_target" for "StationEfficiency"  [call-arg]` |
| 1485 | `Unexpected keyword argument "operator_id" for "StationEfficiency"  [call-arg]` |
| 1485 | `Unexpected keyword argument "operator_name" for "StationEfficiency"  [call-arg]` |
| 1513 | `"StationEfficiency" has no attribute "work_center_id"  [attr-defined]` |
| 1516 | `"StationEfficiency" has no attribute "current_efficiency"  [attr-defined]` |
| 1518 | `"StationEfficiency" has no attribute "is_below_target"  [attr-defined]` |
| 1522 | `"StationEfficiency" has no attribute "variance"  [attr-defined]` |
| 1540 | `Unexpected keyword argument "work_center_id" for "CellOEE"  [call-arg]` |
| 1540 | `Unexpected keyword argument "work_center_name" for "CellOEE"  [call-arg]` |
| 1540 | `Unexpected keyword argument "current_oee" for "CellOEE"  [call-arg]` |
| 1540 | `Unexpected keyword argument "target_oee" for "CellOEE"  [call-arg]` |
| 1540 | `Unexpected keyword argument "is_below_threshold" for "CellOEE"  [call-arg]` |
| 1540 | `Unexpected keyword argument "variance" for "CellOEE"  [call-arg]` |
| 1568 | `"CellOEE" has no attribute "work_center_id"  [attr-defined]` |
| 1571 | `"CellOEE" has no attribute "current_oee"  [attr-defined]` |
| 1573 | `"CellOEE" has no attribute "is_below_threshold"  [attr-defined]` |
| 1577 | `"CellOEE" has no attribute "variance"  [attr-defined]` |
| 1605 | `Unexpected keyword argument "material_code" for "KanbanAlert"  [call-arg]` |
| 1605 | `Unexpected keyword argument "material_name" for "KanbanAlert"  [call-arg]` |
| 1605 | `Unexpected keyword argument "bin_location" for "KanbanAlert"; did you mean "location"?  [call-arg]` |
| 1605 | `Unexpected keyword argument "work_center_id" for "KanbanAlert"  [call-arg]` |
| 1605 | `Unexpected keyword argument "work_center_name" for "KanbanAlert"  [call-arg]` |
| 1605 | `Unexpected keyword argument "unit" for "KanbanAlert"  [call-arg]` |
| 1605 | `Unexpected keyword argument "days_overdue" for "KanbanAlert"  [call-arg]` |
| 1605 | `Unexpected keyword argument "supplier_name" for "KanbanAlert"  [call-arg]` |
| 1605 | `Unexpected keyword argument "replenishment_status" for "KanbanAlert"  [call-arg]` |
| 1612 | `Argument "quantity_needed" to "KanbanAlert" has incompatible type "float"; expected "int"  [arg-type]` |
| 1614 | `Argument "due_date" to "KanbanAlert" has incompatible type "date"; expected "datetime \| None"  [arg-type]` |
| 1644 | `Incompatible types in "await" (actual type "Awaitable[int] \| int", expected type "Awaitable[Any]")  [misc]` |
| 1661 | `"KanbanAlert" has no attribute "days_overdue"  [attr-defined]` |
| 1661 | `No overload variant of "__sub__" of "date" matches argument type "None"  [operator]` |
| 1663 | `"KanbanAlert" has no attribute "work_center_id"  [attr-defined]` |
| 1665 | `"KanbanAlert" has no attribute "days_overdue"  [attr-defined]` |
| 1669 | `"KanbanAlert" has no attribute "days_overdue"  [attr-defined]` |
| 1687 | `Unexpected keyword argument "user_id" for "ExpiringCertification"  [call-arg]` |
| 1687 | `Unexpected keyword argument "user_name" for "ExpiringCertification"  [call-arg]` |
| 1687 | `Unexpected keyword argument "certification_type" for "ExpiringCertification"; did you mean "certification_name"?  [call-arg]` |
| 1687 | `Unexpected keyword argument "expiration_date" for "ExpiringCertification"; did you mean "expiry_date"?  [call-arg]` |
| 1687 | `Unexpected keyword argument "is_expired" for "ExpiringCertification"  [call-arg]` |
| 1687 | `Unexpected keyword argument "required_for_work_centers" for "ExpiringCertification"  [call-arg]` |
| 1687 | `Unexpected keyword argument "renewal_training_id" for "ExpiringCertification"  [call-arg]` |
| 1720 | `"ExpiringCertification" has no attribute "expiration_date"; maybe "expiry_date"?  [attr-defined]` |
| 1721 | `"ExpiringCertification" has no attribute "is_expired"  [attr-defined]` |
| 1721 | `"ExpiringCertification" has no attribute "expiration_date"; maybe "expiry_date"?  [attr-defined]` |
| 1723 | `"ExpiringCertification" has no attribute "user_id"  [attr-defined]` |
| 1726 | `"ExpiringCertification" has no attribute "is_expired"  [attr-defined]` |
| 1733 | `"ExpiringCertification" has no attribute "is_expired"  [attr-defined]` |
| 1739 | `Incompatible types in "await" (actual type "Awaitable[int] \| int", expected type "Awaitable[Any]")  [misc]` |
| 1751 | `Unexpected keyword argument "work_center_id" for "WIPViolation"  [call-arg]` |
| 1751 | `Unexpected keyword argument "work_center_name" for "WIPViolation"  [call-arg]` |
| 1751 | `Unexpected keyword argument "cell_id" for "WIPViolation"  [call-arg]` |
| 1751 | `Unexpected keyword argument "cell_name" for "WIPViolation"  [call-arg]` |
| 1751 | `Unexpected keyword argument "violation_amount" for "WIPViolation"  [call-arg]` |
| 1751 | `Unexpected keyword argument "started_at" for "WIPViolation"  [call-arg]` |
| 1751 | `Unexpected keyword argument "duration_minutes" for "WIPViolation"  [call-arg]` |
| 1785 | `"WIPViolation" has no attribute "duration_minutes"  [attr-defined]` |
| 1785 | `"WIPViolation" has no attribute "started_at"  [attr-defined]` |
| 1787 | `"WIPViolation" has no attribute "work_center_id"  [attr-defined]` |
| 1792 | `"WIPViolation" has no attribute "violation_amount"  [attr-defined]` |
| 1798 | `Incompatible types in "await" (actual type "Awaitable[int] \| int", expected type "Awaitable[Any]")  [misc]` |
| 1816 | `Unexpected keyword argument "capa_number" for "CAPAVerification"; did you mean "ncr_number"?  [call-arg]` |
| 1816 | `Unexpected keyword argument "title" for "CAPAVerification"  [call-arg]` |
| 1816 | `Unexpected keyword argument "capa_type" for "CAPAVerification"  [call-arg]` |
| 1816 | `Unexpected keyword argument "verification_due_date" for "CAPAVerification"  [call-arg]` |
| 1816 | `Unexpected keyword argument "days_until_due" for "CAPAVerification"  [call-arg]` |
| 1816 | `Unexpected keyword argument "is_overdue" for "CAPAVerification"  [call-arg]` |
| 1816 | `Unexpected keyword argument "owner_id" for "CAPAVerification"  [call-arg]` |
| 1816 | `Unexpected keyword argument "original_nc_id" for "CAPAVerification"  [call-arg]` |
| 1816 | `Unexpected keyword argument "effectiveness_check" for "CAPAVerification"  [call-arg]` |
| 1850 | `"CAPAVerification" has no attribute "days_until_due"  [attr-defined]` |
| 1850 | `"CAPAVerification" has no attribute "verification_due_date"  [attr-defined]` |
| 1851 | `"CAPAVerification" has no attribute "is_overdue"  [attr-defined]` |
| 1851 | `"CAPAVerification" has no attribute "verification_due_date"  [attr-defined]` |
| 1853 | `"CAPAVerification" has no attribute "owner_id"  [attr-defined]` |
| 1856 | `"CAPAVerification" has no attribute "is_overdue"  [attr-defined]` |
| 1859 | `"CAPAVerification" has no attribute "days_until_due"  [attr-defined]` |
| 1863 | `"CAPAVerification" has no attribute "is_overdue"  [attr-defined]` |
| 1863 | `"CAPAVerification" has no attribute "days_until_due"  [attr-defined]` |
| 1869 | `Incompatible types in "await" (actual type "Awaitable[int] \| int", expected type "Awaitable[Any]")  [misc]` |
| 1886 | `Unexpected keyword argument "title" for "ScheduledTraining"  [call-arg]` |
| 1886 | `Unexpected keyword argument "description" for "ScheduledTraining"  [call-arg]` |
| 1886 | `Unexpected keyword argument "training_type" for "ScheduledTraining"; did you mean "training_name"?  [call-arg]` |
| 1886 | `Unexpected keyword argument "scheduled_date" for "ScheduledTraining"; did you mean "scheduled_at"?  [call-arg]` |
| 1886 | `Unexpected keyword argument "scheduled_time" for "ScheduledTraining"; did you mean "scheduled_at"?  [call-arg]` |
| 1886 | `Unexpected keyword argument "instructor_name" for "ScheduledTraining"  [call-arg]` |
| 1886 | `Unexpected keyword argument "max_attendees" for "ScheduledTraining"  [call-arg]` |
| 1886 | `Unexpected keyword argument "is_user_enrolled" for "ScheduledTraining"  [call-arg]` |
| 1894 | `Argument "location" to "ScheduledTraining" has incompatible type "str \| None"; expected "str"  [arg-type]` |
| 1921 | `"ScheduledTraining" has no attribute "is_user_enrolled"  [attr-defined]` |
| 1925 | `"ScheduledTraining" has no attribute "scheduled_date"; maybe "scheduled_at"?  [attr-defined]` |
| 1927 | `"ScheduledTraining" has no attribute "scheduled_date"; maybe "scheduled_at"?  [attr-defined]` |
| 1931 | `"ScheduledTraining" has no attribute "scheduled_date"; maybe "scheduled_at"?  [attr-defined]` |
| 1931 | `"ScheduledTraining" has no attribute "scheduled_time"; maybe "scheduled_at"?  [attr-defined]` |
| 1967 | `"CriticalAndon" has no attribute "acknowledged"; maybe "is_acknowledged"?  [attr-defined]` |
| 1969 | `"CriticalAndon" has no attribute "minutes_open"  [attr-defined]` |
| 1988 | `"ExpiringCertification" has no attribute "is_expired"  [attr-defined]` |
| 1989 | `"ExpiringCertification" has no attribute "is_expired"  [attr-defined]` |
| 1996 | `"CAPAVerification" has no attribute "is_overdue"  [attr-defined]` |
| 2002 | `Unexpected keyword argument "work_orders_at_risk_count" for "ShopFloorSummary"; did you mean "work_orders_at_risk"?  [call-arg]` |
| 2002 | `Unexpected keyword argument "unacknowledged_andon_count" for "ShopFloorSummary"  [call-arg]` |
| 2002 | `Unexpected keyword argument "avg_andon_response_minutes" for "ShopFloorSummary"  [call-arg]` |
| 2002 | `Unexpected keyword argument "pending_kanban_count" for "ShopFloorSummary"  [call-arg]` |
| 2002 | `Unexpected keyword argument "expired_certification_count" for "ShopFloorSummary"; did you mean "expiring_certifications"?  [call-arg]` |
| 2002 | `Unexpected keyword argument "expiring_soon_count" for "ShopFloorSummary"  [call-arg]` |
| 2002 | `Unexpected keyword argument "total_wip_violation_count" for "ShopFloorSummary"  [call-arg]` |
| 2002 | `Unexpected keyword argument "overdue_capa_count" for "ShopFloorSummary"  [call-arg]` |
| 2002 | `Unexpected keyword argument "training_sessions_today" for "ShopFloorSummary"  [call-arg]` |
| 2222 | `"type[CommitmentType]" has no attribute "PROJECT_MILESTONE_DUE"  [attr-defined]` |
| 2267 | `"type[CommitmentType]" has no attribute "USER_STORY_DUE"  [attr-defined]` |
| 2309 | `Value of type "Coroutine[Any, Any, MicroDrill]" must be used  [unused-coroutine]` |
| 2309 | `Argument 1 to "add_micro_drill" of "AsyncTodayScreenService" has incompatible type "**dict[str, object]"; expected "UUID"  [arg-type]` |
| 2309 | `Argument 1 to "add_micro_drill" of "AsyncTodayScreenService" has incompatible type "**dict[str, object]"; expected "str"  [arg-type]` |
| 2309 | `Argument 1 to "add_micro_drill" of "AsyncTodayScreenService" has incompatible type "**dict[str, object]"; expected "int"  [arg-type]` |
| 2309 | `Argument 1 to "add_micro_drill" of "AsyncTodayScreenService" has incompatible type "**dict[str, object]"; expected "str \| None"  [arg-type]` |
| 2309 | `Argument 1 to "add_micro_drill" of "AsyncTodayScreenService" has incompatible type "**dict[str, object]"; expected "UUID \| None"  [arg-type]` |

### `backend/src/sensei/services/ops/today_screen_v2/abnormalities.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 47 | `Argument "severity" to "Abnormality" has incompatible type "int"; expected "PriorityLevel"  [arg-type]` |

### `backend/src/sensei/services/ops/today_screen_v2/drills.py`
**Errors:** 5

| Line | Error Message |
|------|---------------|
| 112 | `Argument "question" to "MicroDrill" has incompatible type "object"; expected "str"  [arg-type]` |
| 113 | `Argument "answer" to "MicroDrill" has incompatible type "object"; expected "str"  [arg-type]` |
| 114 | `Argument "hint" to "MicroDrill" has incompatible type "object"; expected "str \| None"  [arg-type]` |
| 115 | `Argument "category" to "MicroDrill" has incompatible type "object"; expected "str"  [arg-type]` |
| 116 | `Argument "difficulty" to "MicroDrill" has incompatible type "object"; expected "int"  [arg-type]` |

### `backend/src/sensei/services/ops/today_screen_v2/service.py`
**Errors:** 6

| Line | Error Message |
|------|---------------|
| 85 | `Argument 2 to "get_risks_by_category" of "RiskManager" has incompatible type "int"; expected "RiskCategory \| None"  [arg-type]` |
| 102 | `Incompatible return value type (got "Commitment \| None", expected "bool")  [return-value]` |
| 279 | `Incompatible default for argument "store_name" (default has type "None", argument has type "str")  [assignment]` |
| 378 | `Unexpected keyword argument "shop_floor" for "TodayScreenData"  [call-arg]` |
| 453 | `"type[CommitmentType]" has no attribute "PROJECT_MILESTONE_DUE"  [attr-defined]` |
| 498 | `"type[CommitmentType]" has no attribute "USER_STORY_DUE"  [attr-defined]` |

### `backend/src/sensei/services/ops/today_screen_v2/shop_floor.py`
**Errors:** 171

| Line | Error Message |
|------|---------------|
| 57 | `Unexpected keyword argument "work_order_id" for "WorkOrderAtRisk"  [call-arg]` |
| 57 | `Unexpected keyword argument "job_name" for "WorkOrderAtRisk"  [call-arg]` |
| 57 | `Unexpected keyword argument "scheduled_ship_date" for "WorkOrderAtRisk"  [call-arg]` |
| 57 | `Unexpected keyword argument "days_until_due" for "WorkOrderAtRisk"  [call-arg]` |
| 57 | `Unexpected keyword argument "current_operation" for "WorkOrderAtRisk"  [call-arg]` |
| 57 | `Unexpected keyword argument "work_center_id" for "WorkOrderAtRisk"  [call-arg]` |
| 57 | `Unexpected keyword argument "work_center_name" for "WorkOrderAtRisk"  [call-arg]` |
| 57 | `Unexpected keyword argument "reason_at_risk" for "WorkOrderAtRisk"  [call-arg]` |
| 57 | `Unexpected keyword argument "estimated_delay_hours" for "WorkOrderAtRisk"  [call-arg]` |
| 57 | `Unexpected keyword argument "priority" for "WorkOrderAtRisk"  [call-arg]` |
| 72 | `Too many arguments for "_save_global_item" of "BaseRedisStore"  [call-arg]` |
| 72 | `"WorkOrderAtRisk" has no attribute "work_order_id"  [attr-defined]` |
| 81 | `Too many arguments for "_get_global_store" of "BaseRedisStore"  [call-arg]` |
| 92 | `"WorkOrderAtRisk" has no attribute "days_until_due"  [attr-defined]` |
| 92 | `"WorkOrderAtRisk" has no attribute "scheduled_ship_date"  [attr-defined]` |
| 94 | `"WorkOrderAtRisk" has no attribute "work_center_id"  [attr-defined]` |
| 99 | `"WorkOrderAtRisk" has no attribute "priority"  [attr-defined]` |
| 99 | `"WorkOrderAtRisk" has no attribute "days_until_due"  [attr-defined]` |
| 121 | `Unexpected keyword argument "work_center_id" for "CriticalAndon"  [call-arg]` |
| 121 | `Unexpected keyword argument "work_center_name" for "CriticalAndon"  [call-arg]` |
| 121 | `Unexpected keyword argument "description" for "CriticalAndon"  [call-arg]` |
| 121 | `Unexpected keyword argument "raised_at" for "CriticalAndon"  [call-arg]` |
| 121 | `Unexpected keyword argument "raised_by_id" for "CriticalAndon"  [call-arg]` |
| 121 | `Unexpected keyword argument "raised_by_name" for "CriticalAndon"  [call-arg]` |
| 121 | `Unexpected keyword argument "minutes_open" for "CriticalAndon"  [call-arg]` |
| 121 | `Unexpected keyword argument "acknowledged" for "CriticalAndon"; did you mean "is_acknowledged"?  [call-arg]` |
| 121 | `Unexpected keyword argument "acknowledged_by_id" for "CriticalAndon"  [call-arg]` |
| 121 | `Unexpected keyword argument "acknowledged_by_name" for "CriticalAndon"  [call-arg]` |
| 139 | `Too many arguments for "_save_global_item" of "BaseRedisStore"  [call-arg]` |
| 149 | `Too many arguments for "_get_global_store" of "BaseRedisStore"  [call-arg]` |
| 154 | `"CriticalAndon" has no attribute "acknowledged"; maybe "is_acknowledged"?  [attr-defined]` |
| 155 | `"CriticalAndon" has no attribute "acknowledged_by_id"  [attr-defined]` |
| 156 | `"CriticalAndon" has no attribute "acknowledged_by_name"  [attr-defined]` |
| 157 | `Too many arguments for "_save_global_item" of "BaseRedisStore"  [call-arg]` |
| 163 | `Too many arguments for "_save_global_item" of "BaseRedisStore"  [call-arg]` |
| 182 | `Too many arguments for "_get_global_store" of "BaseRedisStore"  [call-arg]` |
| 193 | `"CriticalAndon" has no attribute "minutes_open"  [attr-defined]` |
| 193 | `"CriticalAndon" has no attribute "raised_at"  [attr-defined]` |
| 195 | `"CriticalAndon" has no attribute "work_center_id"  [attr-defined]` |
| 197 | `"CriticalAndon" has no attribute "acknowledged"; maybe "is_acknowledged"?  [attr-defined]` |
| 202 | `"CriticalAndon" has no attribute "acknowledged"; maybe "is_acknowledged"?  [attr-defined]` |
| 202 | `"CriticalAndon" has no attribute "minutes_open"  [attr-defined]` |
| 225 | `Unexpected keyword argument "work_center_id" for "StationEfficiency"  [call-arg]` |
| 225 | `Unexpected keyword argument "work_center_name" for "StationEfficiency"  [call-arg]` |
| 225 | `Unexpected keyword argument "current_efficiency" for "StationEfficiency"  [call-arg]` |
| 225 | `Unexpected keyword argument "target_efficiency" for "StationEfficiency"  [call-arg]` |
| 225 | `Unexpected keyword argument "variance" for "StationEfficiency"  [call-arg]` |
| 225 | `Unexpected keyword argument "trend" for "StationEfficiency"  [call-arg]` |
| 225 | `Unexpected keyword argument "is_below_target" for "StationEfficiency"  [call-arg]` |
| 225 | `Unexpected keyword argument "operator_id" for "StationEfficiency"  [call-arg]` |
| 225 | `Unexpected keyword argument "operator_name" for "StationEfficiency"  [call-arg]` |
| 239 | `Too many arguments for "_save_global_item" of "BaseRedisStore"  [call-arg]` |
| 248 | `Too many arguments for "_get_global_store" of "BaseRedisStore"  [call-arg]` |
| 253 | `"StationEfficiency" has no attribute "work_center_id"  [attr-defined]` |
| 256 | `"StationEfficiency" has no attribute "current_efficiency"  [attr-defined]` |
| 258 | `"StationEfficiency" has no attribute "is_below_target"  [attr-defined]` |
| 262 | `"StationEfficiency" has no attribute "variance"  [attr-defined]` |
| 282 | `Unexpected keyword argument "work_center_id" for "CellOEE"  [call-arg]` |
| 282 | `Unexpected keyword argument "work_center_name" for "CellOEE"  [call-arg]` |
| 282 | `Unexpected keyword argument "current_oee" for "CellOEE"  [call-arg]` |
| 282 | `Unexpected keyword argument "target_oee" for "CellOEE"  [call-arg]` |
| 282 | `Unexpected keyword argument "is_below_threshold" for "CellOEE"  [call-arg]` |
| 282 | `Unexpected keyword argument "variance" for "CellOEE"  [call-arg]` |
| 296 | `Too many arguments for "_save_global_item" of "BaseRedisStore"  [call-arg]` |
| 305 | `Too many arguments for "_get_global_store" of "BaseRedisStore"  [call-arg]` |
| 310 | `"CellOEE" has no attribute "work_center_id"  [attr-defined]` |
| 313 | `"CellOEE" has no attribute "current_oee"  [attr-defined]` |
| 315 | `"CellOEE" has no attribute "is_below_threshold"  [attr-defined]` |
| 319 | `"CellOEE" has no attribute "variance"  [attr-defined]` |
| 324 | `Too many arguments for "_get_global_store" of "BaseRedisStore"  [call-arg]` |
| 349 | `Unexpected keyword argument "material_code" for "KanbanAlert"  [call-arg]` |
| 349 | `Unexpected keyword argument "material_name" for "KanbanAlert"  [call-arg]` |
| 349 | `Unexpected keyword argument "bin_location" for "KanbanAlert"; did you mean "location"?  [call-arg]` |
| 349 | `Unexpected keyword argument "work_center_id" for "KanbanAlert"  [call-arg]` |
| 349 | `Unexpected keyword argument "work_center_name" for "KanbanAlert"  [call-arg]` |
| 349 | `Unexpected keyword argument "unit" for "KanbanAlert"  [call-arg]` |
| 349 | `Unexpected keyword argument "days_overdue" for "KanbanAlert"  [call-arg]` |
| 349 | `Unexpected keyword argument "supplier_name" for "KanbanAlert"  [call-arg]` |
| 349 | `Unexpected keyword argument "replenishment_status" for "KanbanAlert"  [call-arg]` |
| 356 | `Argument "quantity_needed" to "KanbanAlert" has incompatible type "float"; expected "int"  [arg-type]` |
| 358 | `Argument "due_date" to "KanbanAlert" has incompatible type "date"; expected "datetime \| None"  [arg-type]` |
| 364 | `Too many arguments for "_save_global_item" of "BaseRedisStore"  [call-arg]` |
| 373 | `Too many arguments for "_get_global_store" of "BaseRedisStore"  [call-arg]` |
| 378 | `Too many arguments for "_save_global_item" of "BaseRedisStore"  [call-arg]` |
| 396 | `Too many arguments for "_get_global_store" of "BaseRedisStore"  [call-arg]` |
| 405 | `"KanbanAlert" has no attribute "days_overdue"  [attr-defined]` |
| 405 | `No overload variant of "__sub__" of "date" matches argument type "None"  [operator]` |
| 407 | `"KanbanAlert" has no attribute "work_center_id"  [attr-defined]` |
| 409 | `"KanbanAlert" has no attribute "days_overdue"  [attr-defined]` |
| 413 | `"KanbanAlert" has no attribute "days_overdue"  [attr-defined]` |
| 433 | `Unexpected keyword argument "user_id" for "ExpiringCertification"  [call-arg]` |
| 433 | `Unexpected keyword argument "user_name" for "ExpiringCertification"  [call-arg]` |
| 433 | `Unexpected keyword argument "certification_type" for "ExpiringCertification"; did you mean "certification_name"?  [call-arg]` |
| 433 | `Unexpected keyword argument "expiration_date" for "ExpiringCertification"; did you mean "expiry_date"?  [call-arg]` |
| 433 | `Unexpected keyword argument "is_expired" for "ExpiringCertification"  [call-arg]` |
| 433 | `Unexpected keyword argument "required_for_work_centers" for "ExpiringCertification"  [call-arg]` |
| 433 | `Unexpected keyword argument "renewal_training_id" for "ExpiringCertification"  [call-arg]` |
| 446 | `Too many arguments for "_save_global_item" of "BaseRedisStore"  [call-arg]` |
| 457 | `Too many arguments for "_get_global_store" of "BaseRedisStore"  [call-arg]` |
| 466 | `"ExpiringCertification" has no attribute "expiration_date"; maybe "expiry_date"?  [attr-defined]` |
| 467 | `"ExpiringCertification" has no attribute "is_expired"  [attr-defined]` |
| 467 | `"ExpiringCertification" has no attribute "expiration_date"; maybe "expiry_date"?  [attr-defined]` |
| 469 | `"ExpiringCertification" has no attribute "user_id"  [attr-defined]` |
| 472 | `"ExpiringCertification" has no attribute "is_expired"  [attr-defined]` |
| 479 | `"ExpiringCertification" has no attribute "is_expired"  [attr-defined]` |
| 499 | `Unexpected keyword argument "work_center_id" for "WIPViolation"  [call-arg]` |
| 499 | `Unexpected keyword argument "work_center_name" for "WIPViolation"  [call-arg]` |
| 499 | `Unexpected keyword argument "cell_id" for "WIPViolation"  [call-arg]` |
| 499 | `Unexpected keyword argument "cell_name" for "WIPViolation"  [call-arg]` |
| 499 | `Unexpected keyword argument "violation_amount" for "WIPViolation"  [call-arg]` |
| 499 | `Unexpected keyword argument "started_at" for "WIPViolation"  [call-arg]` |
| 499 | `Unexpected keyword argument "duration_minutes" for "WIPViolation"  [call-arg]` |
| 513 | `Too many arguments for "_save_global_item" of "BaseRedisStore"  [call-arg]` |
| 522 | `Too many arguments for "_get_global_store" of "BaseRedisStore"  [call-arg]` |
| 533 | `"WIPViolation" has no attribute "duration_minutes"  [attr-defined]` |
| 533 | `"WIPViolation" has no attribute "started_at"  [attr-defined]` |
| 535 | `"WIPViolation" has no attribute "work_center_id"  [attr-defined]` |
| 540 | `"WIPViolation" has no attribute "violation_amount"  [attr-defined]` |
| 566 | `Unexpected keyword argument "capa_number" for "CAPAVerification"; did you mean "ncr_number"?  [call-arg]` |
| 566 | `Unexpected keyword argument "title" for "CAPAVerification"  [call-arg]` |
| 566 | `Unexpected keyword argument "capa_type" for "CAPAVerification"  [call-arg]` |
| 566 | `Unexpected keyword argument "verification_due_date" for "CAPAVerification"  [call-arg]` |
| 566 | `Unexpected keyword argument "days_until_due" for "CAPAVerification"  [call-arg]` |
| 566 | `Unexpected keyword argument "is_overdue" for "CAPAVerification"  [call-arg]` |
| 566 | `Unexpected keyword argument "owner_id" for "CAPAVerification"  [call-arg]` |
| 566 | `Unexpected keyword argument "original_nc_id" for "CAPAVerification"  [call-arg]` |
| 566 | `Unexpected keyword argument "effectiveness_check" for "CAPAVerification"  [call-arg]` |
| 580 | `Too many arguments for "_save_global_item" of "BaseRedisStore"  [call-arg]` |
| 591 | `Too many arguments for "_get_global_store" of "BaseRedisStore"  [call-arg]` |
| 600 | `"CAPAVerification" has no attribute "days_until_due"  [attr-defined]` |
| 600 | `"CAPAVerification" has no attribute "verification_due_date"  [attr-defined]` |
| 601 | `"CAPAVerification" has no attribute "is_overdue"  [attr-defined]` |
| 601 | `"CAPAVerification" has no attribute "verification_due_date"  [attr-defined]` |
| 603 | `"CAPAVerification" has no attribute "owner_id"  [attr-defined]` |
| 606 | `"CAPAVerification" has no attribute "is_overdue"  [attr-defined]` |
| 609 | `"CAPAVerification" has no attribute "days_until_due"  [attr-defined]` |
| 613 | `"CAPAVerification" has no attribute "is_overdue"  [attr-defined]` |
| 613 | `"CAPAVerification" has no attribute "days_until_due"  [attr-defined]` |
| 638 | `Unexpected keyword argument "title" for "ScheduledTraining"  [call-arg]` |
| 638 | `Unexpected keyword argument "description" for "ScheduledTraining"  [call-arg]` |
| 638 | `Unexpected keyword argument "training_type" for "ScheduledTraining"; did you mean "training_name"?  [call-arg]` |
| 638 | `Unexpected keyword argument "scheduled_date" for "ScheduledTraining"; did you mean "scheduled_at"?  [call-arg]` |
| 638 | `Unexpected keyword argument "scheduled_time" for "ScheduledTraining"; did you mean "scheduled_at"?  [call-arg]` |
| 638 | `Unexpected keyword argument "instructor_name" for "ScheduledTraining"  [call-arg]` |
| 638 | `Unexpected keyword argument "max_attendees" for "ScheduledTraining"  [call-arg]` |
| 638 | `Unexpected keyword argument "is_user_enrolled" for "ScheduledTraining"  [call-arg]` |
| 646 | `Argument "location" to "ScheduledTraining" has incompatible type "str \| None"; expected "str"  [arg-type]` |
| 653 | `Too many arguments for "_save_global_item" of "BaseRedisStore"  [call-arg]` |
| 664 | `Too many arguments for "_get_global_store" of "BaseRedisStore"  [call-arg]` |
| 673 | `"ScheduledTraining" has no attribute "is_user_enrolled"  [attr-defined]` |
| 677 | `"ScheduledTraining" has no attribute "scheduled_date"; maybe "scheduled_at"?  [attr-defined]` |
| 679 | `"ScheduledTraining" has no attribute "scheduled_date"; maybe "scheduled_at"?  [attr-defined]` |
| 683 | `"ScheduledTraining" has no attribute "scheduled_date"; maybe "scheduled_at"?  [attr-defined]` |
| 683 | `"ScheduledTraining" has no attribute "scheduled_time"; maybe "scheduled_at"?  [attr-defined]` |
| 688 | `Too many arguments for "_get_global_store" of "BaseRedisStore"  [call-arg]` |
| 697 | `Too many arguments for "_save_global_item" of "BaseRedisStore"  [call-arg]` |
| 721 | `"CriticalAndon" has no attribute "acknowledged"; maybe "is_acknowledged"?  [attr-defined]` |
| 723 | `"CriticalAndon" has no attribute "minutes_open"  [attr-defined]` |
| 734 | `Too many arguments for "_get_global_store" of "BaseRedisStore"  [call-arg]` |
| 742 | `"ExpiringCertification" has no attribute "is_expired"  [attr-defined]` |
| 743 | `"ExpiringCertification" has no attribute "is_expired"  [attr-defined]` |
| 750 | `"CAPAVerification" has no attribute "is_overdue"  [attr-defined]` |
| 756 | `Unexpected keyword argument "work_orders_at_risk_count" for "ShopFloorSummary"; did you mean "work_orders_at_risk"?  [call-arg]` |
| 756 | `Unexpected keyword argument "unacknowledged_andon_count" for "ShopFloorSummary"  [call-arg]` |
| 756 | `Unexpected keyword argument "avg_andon_response_minutes" for "ShopFloorSummary"  [call-arg]` |
| 756 | `Unexpected keyword argument "pending_kanban_count" for "ShopFloorSummary"  [call-arg]` |
| 756 | `Unexpected keyword argument "expired_certification_count" for "ShopFloorSummary"; did you mean "expiring_certifications"?  [call-arg]` |
| 756 | `Unexpected keyword argument "expiring_soon_count" for "ShopFloorSummary"  [call-arg]` |
| 756 | `Unexpected keyword argument "total_wip_violation_count" for "ShopFloorSummary"  [call-arg]` |
| 756 | `Unexpected keyword argument "overdue_capa_count" for "ShopFloorSummary"  [call-arg]` |
| 756 | `Unexpected keyword argument "training_sessions_today" for "ShopFloorSummary"  [call-arg]` |

### `backend/src/sensei/services/ops/tps_knowledge_sources.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 1594 | `Need type annotation for "by_category" (hint: "by_category: dict[<type>, <type>] = ...")  [var-annotated]` |
| 1598 | `Need type annotation for "by_license" (hint: "by_license: dict[<type>, <type>] = ...")  [var-annotated]` |
| 1602 | `Need type annotation for "topic_counts" (hint: "topic_counts: dict[<type>, <type>] = ...")  [var-annotated]` |

### `backend/src/sensei/services/ops/tps_teacher.py`
**Errors:** 19

| Line | Error Message |
|------|---------------|
| 276 | `Need type annotation for "artifacts"  [var-annotated]` |
| 576 | `"AsyncImprovementKataAssistant" has no attribute "sessions"  [attr-defined]` |
| 591 | `"AsyncImprovementKataAssistant" has no attribute "sessions"  [attr-defined]` |
| 609 | `"AsyncImprovementKataAssistant" has no attribute "sessions"  [attr-defined]` |
| 622 | `"AsyncImprovementKataAssistant" has no attribute "sessions"  [attr-defined]` |
| 897 | `Cannot determine type of "detections"  [has-type]` |
| 901 | `Cannot determine type of "detections"  [has-type]` |
| 902 | `Need type annotation for "detections" (hint: "detections: list[<type>] = ...")  [var-annotated]` |
| 963 | `"object" has no attribute "get"  [attr-defined]` |
| 972 | `"AsyncJidokaMentor" has no attribute "_assess_quality_impact"  [attr-defined]` |
| 1058 | `Unsupported left operand type for - ("None")  [operator]` |
| 1065 | `Unsupported left operand type for - ("None")  [operator]` |
| 1085 | `"AsyncJidokaMentor" has no attribute "andon_events"  [attr-defined]` |
| 1166 | `Incompatible return value type (got "Coroutine[Any, Any, dict[str, Any]]", expected "dict[str, Any]")  [return-value]` |
| 1213 | `Incompatible return value type (got "Coroutine[Any, Any, dict[str, Any]]", expected "dict[str, Any]")  [return-value]` |
| 1271 | `Need type annotation for "artifacts"  [var-annotated]` |
| 1668 | `"object" has no attribute "get"  [attr-defined]` |
| 1727 | `Unsupported left operand type for - ("None")  [operator]` |
| 1731 | `Unsupported left operand type for - ("None")  [operator]` |

### `backend/src/sensei/services/ot_network_safety_db.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 448 | `Unsupported target for indexed assignment ("object")  [index]` |
| 448 | `"object" has no attribute "get"  [attr-defined]` |
| 451 | `Unsupported target for indexed assignment ("object")  [index]` |
| 451 | `"object" has no attribute "get"  [attr-defined]` |

### `backend/src/sensei/services/plm_drawing_control.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 645 | `Need type annotation for "impacts" (hint: "impacts: list[<type>] = ...")  [var-annotated]` |
| 982 | `Argument "plm_document_id" to "PLMSyncRecord" has incompatible type "str \| None"; expected "str"  [arg-type]` |
| 1092 | `Need type annotation for "by_type" (hint: "by_type: dict[<type>, <type>] = ...")  [var-annotated]` |
| 1097 | `Need type annotation for "by_status" (hint: "by_status: dict[<type>, <type>] = ...")  [var-annotated]` |

### `backend/src/sensei/services/production/label_printing.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 626 | `Need type annotation for "result"  [var-annotated]` |
| 635 | `Unsupported target for indexed assignment ("dict[Any, Any] \| str \| None")  [index]` |

### `backend/src/sensei/services/production/persistent_mrp.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 37 | `Incompatible default for argument "user_id" (default has type "None", argument has type "UUID")  [assignment]` |

### `backend/src/sensei/services/production/productionization.py`
**Errors:** 14

| Line | Error Message |
|------|---------------|
| 116 | `Invalid base class "Generic"  [misc]` |
| 143 | `Name "GLAccountModel" already defined (possibly by an import)  [no-redef]` |
| 158 | `Name "OpeningBalanceModel" already defined (possibly by an import)  [no-redef]` |
| 228 | `Name "InventoryLevelModel" already defined (possibly by an import)  [no-redef]` |
| 499 | `Argument "key" to "sort" of "list" has incompatible type "Callable[[dict[str, object]], object]"; expected "Callable[[dict[str, object]], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |
| 499 | `Incompatible return value type (got "object", expected "SupportsDunderLT[Any] \| SupportsDunderGT[Any]")  [return-value]` |
| 755 | `"Product" has no attribute "sku"  [attr-defined]` |
| 757 | `"Product" has no attribute "category"  [attr-defined]` |
| 1312 | `Argument "key" to "sort" of "list" has incompatible type "Callable[[dict[str, object]], object]"; expected "Callable[[dict[str, object]], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |
| 1312 | `Incompatible return value type (got "object", expected "SupportsDunderLT[Any] \| SupportsDunderGT[Any]")  [return-value]` |
| 1386 | `Argument "key" to "sort" of "list" has incompatible type "Callable[[dict[str, bool \| str \| None]], bool \| str \| None]"; expected "Callable[[dict[str, bool \| str \| None]], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |
| 1386 | `Incompatible return value type (got "bool \| str \| None", expected "SupportsDunderLT[Any] \| SupportsDunderGT[Any]")  [return-value]` |
| 1462 | `Argument "key" to "sort" of "list" has incompatible type "Callable[[dict[str, object]], object]"; expected "Callable[[dict[str, object]], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |
| 1462 | `Incompatible return value type (got "object", expected "SupportsDunderLT[Any] \| SupportsDunderGT[Any]")  [return-value]` |

### `backend/src/sensei/services/production/scheduling_maintenance_sync.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 61 | `Incompatible types in assignment (expression has type "Callable[[str], str \| None]", variable has type "def _default_asset_to_station(self, asset_id: str) -> str \| None")  [assignment]` |

### `backend/src/sensei/services/production/spc_scrap_rework.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 1034 | `Incompatible types in assignment (expression has type "ReworkRecord", variable has type "ScrapRecord")  [assignment]` |
| 1035 | `"ScrapRecord" has no attribute "completed_at"  [attr-defined]` |

### `backend/src/sensei/services/production/wms_integration.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 1121 | `Argument 1 to "get" of "dict" has incompatible type "str \| None"; expected "str"  [arg-type]` |
| 1287 | `Argument "system_quantity" to "CycleCount" has incompatible type "Decimal \| Literal[0]"; expected "Decimal"  [arg-type]` |
| 1345 | `Argument "new_quantity" to "adjust_inventory" of "WMSIntegrationService" has incompatible type "Decimal \| None"; expected "Decimal"  [arg-type]` |

### `backend/src/sensei/services/quality/npi_risk_register.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 793 | `Unsupported operand types for + ("None" and "timedelta")  [operator]` |
| 793 | `Incompatible types in assignment (expression has type "datetime \| timedelta", variable has type "datetime \| None")  [assignment]` |
| 1249 | `Need type annotation for "by_category" (hint: "by_category: dict[<type>, <type>] = ...")  [var-annotated]` |
| 1255 | `Need type annotation for "by_phase" (hint: "by_phase: dict[<type>, <type>] = ...")  [var-annotated]` |

### `backend/src/sensei/services/quality/qms_quality.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 1432 | `Name "Any" is not defined  [name-defined]` |

### `backend/src/sensei/services/runbooks.py`
**Errors:** 10

| Line | Error Message |
|------|---------------|
| 490 | `Argument "title" to "Runbook" has incompatible type "object"; expected "str"  [arg-type]` |
| 491 | `Argument "description" to "Runbook" has incompatible type "object"; expected "str"  [arg-type]` |
| 492 | `Argument "category" to "Runbook" has incompatible type "object"; expected "RunbookCategory"  [arg-type]` |
| 493 | `Argument "owner_team" to "Runbook" has incompatible type "object"; expected "str"  [arg-type]` |
| 494 | `Argument "related_services" to "Runbook" has incompatible type "object"; expected "list[str]"  [arg-type]` |
| 495 | `Argument "applicable_severities" to "Runbook" has incompatible type "object"; expected "list[RunbookSeverity]"  [arg-type]` |
| 496 | `Argument "steps" to "Runbook" has incompatible type "object"; expected "list[RunbookStep]"  [arg-type]` |
| 497 | `Argument "tags" to "Runbook" has incompatible type "object"; expected "list[str]"  [arg-type]` |
| 1040 | `Need type annotation for "by_category" (hint: "by_category: dict[<type>, <type>] = ...")  [var-annotated]` |
| 1045 | `Need type annotation for "by_status" (hint: "by_status: dict[<type>, <type>] = ...")  [var-annotated]` |

### `backend/src/sensei/services/sales/multi_agent_rfq.py`
**Errors:** 9

| Line | Error Message |
|------|---------------|
| 395 | `Need type annotation for "findings" (hint: "findings: list[<type>] = ...")  [var-annotated]` |
| 1221 | `"BaseAgent" has no attribute "analyze"  [attr-defined]` |
| 1269 | `"DebateResult" has no attribute "rounds"  [attr-defined]` |
| 1271 | `"DebateResult" has no attribute "consensus_score"  [attr-defined]` |
| 1272 | `"DebateResult" has no attribute "debate_log"  [attr-defined]` |
| 1350 | `Need type annotation for "position_counts"  [var-annotated]` |
| 1380 | `Need type annotation for "weighted_positions"  [var-annotated]` |
| 1520 | `Incompatible types in assignment (expression has type "dict[str, Any]", variable has type "list[dict[str, Any]]")  [assignment]` |
| 1521 | `Argument 2 to "register_customer_history" of "CommercialAgent" has incompatible type "list[dict[str, Any]]"; expected "dict[str, Any]"  [arg-type]` |

### `backend/src/sensei/services/sales/predictive_win_loss.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 424 | `Item "None" of "dict[str, float] \| None" has no attribute "get"  [union-attr]` |
| 429 | `Item "None" of "dict[str, float] \| None" has no attribute "get"  [union-attr]` |
| 763 | `"object" has no attribute "keys"  [attr-defined]` |
| 764 | `Argument 2 to "analyze_scenario" of "CounterfactualAnalyzer" has incompatible type "object"; expected "dict[str, float]"  [arg-type]` |

### `backend/src/sensei/services/sales/rfq_time_tracking.py`
**Errors:** 8

| Line | Error Message |
|------|---------------|
| 655 | `Dict entry 4 has incompatible type "str": "float \| int"; expected "str": "int \| str"  [dict-item]` |
| 945 | `Incompatible types in assignment (expression has type "float", variable has type "int")  [assignment]` |
| 948 | `Incompatible types in assignment (expression has type "float", variable has type "int")  [assignment]` |
| 1084 | `Argument "key" to "sort" of "list" has incompatible type "Callable[[dict[str, object]], object]"; expected "Callable[[dict[str, object]], SupportsDunderLT[Any] \| SupportsDunderGT[Any]]"  [arg-type]` |
| 1084 | `Incompatible return value type (got "object", expected "SupportsDunderLT[Any] \| SupportsDunderGT[Any]")  [return-value]` |
| 1087 | `Incompatible types in assignment (expression has type "dict[str, object]", variable has type "TaskPerformanceStats \| None")  [assignment]` |
| 1088 | `Unsupported target for indexed assignment ("TaskPerformanceStats \| None")  [index]` |
| 1167 | `Incompatible types in assignment (expression has type "TaskSession \| None", variable has type "TaskSession")  [assignment]` |

### `backend/src/sensei/services/sales/smart_supplier_matchmaker.py`
**Errors:** 4

| Line | Error Message |
|------|---------------|
| 1320 | `Argument 1 to "_score_supplier" of "SmartSupplierMatchmaker" has incompatible type "Supplier \| None"; expected "Supplier"  [arg-type]` |
| 1324 | `Item "None" of "Supplier \| None" has no attribute "supplier_id"  [union-attr]` |
| 1325 | `Item "None" of "Supplier \| None" has no attribute "name"  [union-attr]` |
| 1327 | `Item "None" of "Supplier \| None" has no attribute "tier"  [union-attr]` |

### `backend/src/sensei/services/saved_views.py`
**Errors:** 3

| Line | Error Message |
|------|---------------|
| 183 | `Incompatible types in assignment (expression has type "Any \| None", variable has type "dict[str, Any]")  [assignment]` |
| 501 | `Incompatible types in assignment (expression has type "Any \| None", variable has type "dict[str, Any]")  [assignment]` |
| 937 | `Incompatible types in assignment (expression has type "SavedView \| None", variable has type "SavedView")  [assignment]` |

### `backend/src/sensei/services/segment_views_db.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 475 | `"Result[Any]" has no attribute "rowcount"  [attr-defined]` |

### `backend/src/sensei/services/smart_ingestion.py`
**Errors:** 10

| Line | Error Message |
|------|---------------|
| 583 | `Cannot find implementation or library stub for module named "fitz"  [import-not-found]` |
| 611 | `Cannot find implementation or library stub for module named "pdfplumber"  [import-not-found]` |
| 614 | `Name "pages" already defined on line 586  [no-redef]` |
| 615 | `Name "full_text_parts" already defined on line 587  [no-redef]` |
| 653 | `Cannot find implementation or library stub for module named "pytesseract"  [import-not-found]` |
| 769 | `Incompatible types in assignment (expression has type "int", variable has type "str")  [assignment]` |
| 781 | `Incompatible types in assignment (expression has type "float", variable has type "str")  [assignment]` |
| 790 | `Incompatible types in assignment (expression has type "datetime", variable has type "str")  [assignment]` |
| 1634 | `"str" has no attribute "id"  [attr-defined]` |
| 1739 | `"str" has no attribute "id"  [attr-defined]` |

### `backend/src/sensei/services/supply_chain/predictive_utility_forecasting.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 896 | `Incompatible types in assignment (expression has type "dict[str, float \| str]", target has type "float \| str")  [assignment]` |
| 1093 | `Unsupported target for indexed assignment ("object")  [index]` |

### `backend/src/sensei/services/supply_chain/supplier_portal_token.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 1108 | `Generator has incompatible item type "float \| Any"; expected "bool"  [misc]` |
| 1108 | `Unsupported left operand type for - ("None")  [operator]` |

### `backend/src/sensei/services/supply_chain/supply_chain_simulation.py`
**Errors:** 7

| Line | Error Message |
|------|---------------|
| 439 | `Invalid index type "tuple[str, ...]" for "dict[tuple[str, str], float]"; expected type "tuple[str, str]"  [index]` |
| 504 | `Need type annotation for "active" (hint: "active: list[<type>] = ...")  [var-annotated]` |
| 513 | `Argument 1 to "get" of "dict" has incompatible type "tuple[str, ...]"; expected "tuple[str, str]"  [arg-type]` |
| 791 | `Argument "description" to "MitigationRecommendation" has incompatible type "object"; expected "str"  [arg-type]` |
| 792 | `Argument "effectiveness" to "MitigationRecommendation" has incompatible type "object"; expected "float"  [arg-type]` |
| 793 | `Unsupported operand types for * ("float" and "object")  [operator]` |
| 794 | `Argument "implementation_time_days" to "MitigationRecommendation" has incompatible type "object"; expected "int"  [arg-type]` |

### `backend/src/sensei/services/utils/chaos_testing.py`
**Errors:** 9

| Line | Error Message |
|------|---------------|
| 587 | `"object" has no attribute "append"  [attr-defined]` |
| 596 | `"object" has no attribute "append"  [attr-defined]` |
| 607 | `"object" has no attribute "append"  [attr-defined]` |
| 610 | `"object" has no attribute "__iter__"; maybe "__dir__" or "__str__"? (not iterable)  [attr-defined]` |
| 952 | `Incompatible types in assignment (expression has type "CircuitBreakerTest", variable has type "JobRetryTest")  [assignment]` |
| 953 | `"JobRetryTest" has no attribute "actual_state_after"  [attr-defined]` |
| 956 | `"JobRetryTest" has no attribute "component"  [attr-defined]` |
| 959 | `Argument 1 to "append" of "list" has incompatible type "JobRetryTest"; expected "CircuitBreakerTest"  [arg-type]` |
| 961 | `"JobRetryTest" has no attribute "passed"  [attr-defined]` |

### `backend/src/sensei/services/utils/csv_export.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 376 | `Argument 1 to "get" of "dict" has incompatible type "str \| None"; expected "str"  [arg-type]` |

### `backend/src/sensei/services/utils/csv_import.py`
**Errors:** 2

| Line | Error Message |
|------|---------------|
| 403 | `Incompatible return value type (got "tuple[Sequence[str], list[dict[str \| Any, str \| Any]]]", expected "tuple[list[str], list[dict[str, Any]]]")  [return-value]` |
| 431 | `Argument 2 to "_find_best_match" of "CSVImportService" has incompatible type "dict_keys[str, FieldMapping]"; expected "list[str] \| set[str]"  [arg-type]` |

### `backend/src/sensei/services/utils/industrial_ux.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 189 | `Function "builtins.callable" is not valid as a type  [valid-type]` |

### `backend/src/sensei/services/utils/integration_tests.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 1397 | `Need type annotation for "coverage"  [var-annotated]` |

### `backend/src/sensei/services/utils/pdf_generation.py`
**Errors:** 11

| Line | Error Message |
|------|---------------|
| 24 | `Skipping analyzing "weasyprint": module is installed, but missing library stubs or py.typed marker  [import-untyped]` |
| 878 | `Need type annotation for "document"  [var-annotated]` |
| 900 | `Item "dict[str, float \| str]" of "list[Any] \| dict[str, float \| str] \| dict[str, str \| None] \| str" has no attribute "append"  [union-attr]` |
| 900 | `Item "dict[str, str \| None]" of "list[Any] \| dict[str, float \| str] \| dict[str, str \| None] \| str" has no attribute "append"  [union-attr]` |
| 900 | `Item "str" of "list[Any] \| dict[str, float \| str] \| dict[str, str \| None] \| str" has no attribute "append"  [union-attr]` |
| 911 | `Incompatible types in assignment (expression has type "dict[str, object]", target has type "list[Any] \| dict[str, float \| str] \| dict[str, str \| None] \| str")  [assignment]` |
| 928 | `Incompatible types in assignment (expression has type "dict[str, object]", target has type "list[Any] \| dict[str, float \| str] \| dict[str, str \| None] \| str")  [assignment]` |
| 940 | `Incompatible types in assignment (expression has type "dict[str, object]", target has type "list[Any] \| dict[str, float \| str] \| dict[str, str \| None] \| str")  [assignment]` |
| 951 | `Incompatible types in assignment (expression has type "dict[str, object]", target has type "list[Any] \| dict[str, float \| str] \| dict[str, str \| None] \| str")  [assignment]` |
| 964 | `Incompatible types in assignment (expression has type "dict[str, object]", target has type "list[Any] \| dict[str, float \| str] \| dict[str, str \| None] \| str")  [assignment]` |
| 976 | `Incompatible types in assignment (expression has type "dict[str, object]", target has type "list[Any] \| dict[str, float \| str] \| dict[str, str \| None] \| str")  [assignment]` |

### `backend/src/sensei/services/utils/ui_backend_integration.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 206 | `"type[UIActionAuditRecord]" has no attribute "timestamp"  [attr-defined]` |

### `backend/src/sensei/services/utils/uiux_verification.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 198 | `"object" has no attribute "get"  [attr-defined]` |

### `backend/src/sensei/services/whatif_simulation.py`
**Errors:** 5

| Line | Error Message |
|------|---------------|
| 348 | `Argument 1 to "_calculate_simulated_discount" of "WhatIfSimulationService" has incompatible type "Decimal \| Literal[0]"; expected "Decimal"  [arg-type]` |
| 375 | `Argument 2 to "_build_comparison" of "WhatIfSimulationService" has incompatible type "Decimal \| Literal[0]"; expected "Decimal"  [arg-type]` |
| 379 | `Argument 6 to "_build_comparison" of "WhatIfSimulationService" has incompatible type "Decimal \| Literal[0]"; expected "Decimal"  [arg-type]` |
| 391 | `Argument "simulated_subtotal" to "SimulationResult" has incompatible type "Decimal \| Literal[0]"; expected "Decimal"  [arg-type]` |
| 395 | `Argument "simulated_total_cost" to "SimulationResult" has incompatible type "Decimal \| Literal[0]"; expected "Decimal"  [arg-type]` |

### `backend/src/sensei/tasks/ml_tasks.py`
**Errors:** 1

| Line | Error Message |
|------|---------------|
| 52 | `Incompatible return value type (got "Coroutine[Any, Any, str]", expected "str")  [return-value]` |

