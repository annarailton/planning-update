"""Centralized exception classes for the application.

Re-exports from shared packages/exceptions for backward compatibility.

Usage:
    from core.exceptions import NotFoundError, ValidationError, ServiceError

    # In services - raise domain exceptions
    if not resource:
        raise NotFoundError("User", user_id)

    if not valid:
        raise ValidationError("Email format is invalid")

    # In routers - exceptions are automatically handled by global handlers
    # No try/except needed for these exception types
"""

from packages.exceptions import (
    AppError,
    NotFoundError,
    ValidationError,
    ConflictError,
    ForbiddenError,
    UnauthorizedError,
    ServiceError,
    ServiceUnavailableError,
    RateLimitError,
    ExternalAPIError,
)

__all__ = [
    "AppError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "ForbiddenError",
    "UnauthorizedError",
    "ServiceError",
    "ServiceUnavailableError",
    "RateLimitError",
    "ExternalAPIError",
]
