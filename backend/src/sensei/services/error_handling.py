"""
Service Error Handling Utilities (#177-181).

Provides:
- A decorator for service methods that logs and optionally re-raises exceptions
- Standard error context for structured logging
- A ServiceError hierarchy for domain-specific errors

Usage:
    from sensei.services.error_handling import service_method, ServiceError

    class MyService:
        @service_method("MyService")
        def do_something(self, ...):
            ...
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class ServiceError(Exception):
    """Base exception for domain service errors."""

    def __init__(self, message: str, *, service: str = "", operation: str = "", details: dict[str, Any] | None = None):
        super().__init__(message)
        self.service = service
        self.operation = operation
        self.details = details or {}


class ValidationError(ServiceError):
    """Raised when input validation fails."""


class NotFoundError(ServiceError):
    """Raised when an entity is not found."""


class AuthorizationError(ServiceError):
    """Raised when a user lacks required role/permission."""


class ConflictError(ServiceError):
    """Raised on duplicate or conflicting state."""


def service_method(service_name: str, *, reraise: bool = True) -> Callable[[F], F]:
    """Decorator that wraps a service method with logging and error context.

    - Logs entry at DEBUG level
    - Logs exceptions at ERROR level with structured context
    - Re-raises the original exception (default) so FastAPI middleware handles it
    - If reraise=False, returns None on failure (use sparingly)
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            method_name = fn.__name__
            _logger = logging.getLogger(f"sensei.services.{service_name}")
            _logger.debug("%s.%s called", service_name, method_name)
            try:
                return fn(*args, **kwargs)
            except (ServiceError, ValueError, KeyError, TypeError) as exc:
                # Known/expected errors — log at WARNING
                _logger.warning(
                    "%s.%s failed: %s",
                    service_name,
                    method_name,
                    exc,
                    exc_info=False,
                )
                if reraise:
                    raise
                return None
            except Exception as exc:
                # Unexpected errors — log at ERROR with traceback
                _logger.error(
                    "%s.%s unexpected error: %s",
                    service_name,
                    method_name,
                    exc,
                    exc_info=True,
                )
                if reraise:
                    raise
                return None

        return wrapper  # type: ignore[return-value]

    return decorator


def async_service_method(service_name: str, *, reraise: bool = True) -> Callable[[F], F]:
    """Async version of service_method decorator."""

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            method_name = fn.__name__
            _logger = logging.getLogger(f"sensei.services.{service_name}")
            _logger.debug("%s.%s called", service_name, method_name)
            try:
                return await fn(*args, **kwargs)
            except (ServiceError, ValueError, KeyError, TypeError) as exc:
                _logger.warning(
                    "%s.%s failed: %s",
                    service_name,
                    method_name,
                    exc,
                    exc_info=False,
                )
                if reraise:
                    raise
                return None
            except Exception as exc:
                _logger.error(
                    "%s.%s unexpected error: %s",
                    service_name,
                    method_name,
                    exc,
                    exc_info=True,
                )
                if reraise:
                    raise
                return None

        return wrapper  # type: ignore[return-value]

    return decorator
