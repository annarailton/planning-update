"""Shared exception classes for backend and worker services.

Usage:
    from packages.exceptions import NotFoundError, ValidationError, ServiceError

    # In services - raise domain exceptions
    if not resource:
        raise NotFoundError("User", user_id)

    if not valid:
        raise ValidationError("Email format is invalid")

    # In backend routers - exceptions are automatically handled by global handlers
    # In worker - catch and handle as appropriate for background jobs
"""

from typing import Any, Optional
from uuid import UUID


class AppError(Exception):
    """Base exception for all application errors.

    All custom exceptions inherit from this class.
    In backend: global exception handlers catch these and convert to HTTP responses.
    In worker: catch and handle appropriately for background jobs.
    """

    def __init__(
        self,
        message: str,
        detail: Optional[Any] = None,
        status_code: int = 500,
    ):
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found.

    HTTP 404 Not Found in backend.

    Usage:
        raise NotFoundError("User", user_id)
        raise NotFoundError("File", file_id, "File may have been deleted")
    """

    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[str | UUID] = None,
        detail: Optional[str] = None,
    ):
        message = f"{resource_type} not found"
        if resource_id:
            message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(message=message, detail=detail, status_code=404)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ValidationError(AppError):
    """Request validation failed.

    HTTP 400 Bad Request in backend.
    Use for domain validation that Pydantic can't catch.

    Usage:
        raise ValidationError("Email already registered")
        raise ValidationError("Invalid date range", {"start": start, "end": end})
    """

    def __init__(self, message: str, detail: Optional[Any] = None):
        super().__init__(message=message, detail=detail, status_code=400)


class ConflictError(AppError):
    """Resource conflict (duplicate, already exists).

    HTTP 409 Conflict in backend.

    Usage:
        raise ConflictError("User with this email already exists")
        raise ConflictError("Bucket name already taken", {"name": bucket_name})
    """

    def __init__(self, message: str, detail: Optional[Any] = None):
        super().__init__(message=message, detail=detail, status_code=409)


class ForbiddenError(AppError):
    """Action not allowed for current user.

    HTTP 403 Forbidden in backend.
    Use when user is authenticated but lacks permission.

    Usage:
        raise ForbiddenError("Cannot delete another user's bucket")
        raise ForbiddenError("Admin access required")
    """

    def __init__(self, message: str = "Access denied", detail: Optional[Any] = None):
        super().__init__(message=message, detail=detail, status_code=403)


class UnauthorizedError(AppError):
    """Authentication required or failed.

    HTTP 401 Unauthorized in backend.

    Usage:
        raise UnauthorizedError("Invalid token")
        raise UnauthorizedError("Token expired")
    """

    def __init__(
        self, message: str = "Authentication required", detail: Optional[Any] = None
    ):
        super().__init__(message=message, detail=detail, status_code=401)


class ServiceError(AppError):
    """External service or internal operation failed.

    HTTP 500 Internal Server Error by default in backend.
    Can be configured for 502 Bad Gateway or 503 Service Unavailable.

    Usage:
        raise ServiceError("Database connection failed")
        raise ServiceError("Storage service unavailable", status_code=503)
        raise ServiceError("LLM API error", detail={"provider": "openai"})
    """

    def __init__(
        self,
        message: str,
        detail: Optional[Any] = None,
        status_code: int = 500,
    ):
        super().__init__(message=message, detail=detail, status_code=status_code)


class ServiceUnavailableError(AppError):
    """Service is not configured or temporarily unavailable.

    HTTP 503 Service Unavailable in backend.

    Usage:
        raise ServiceUnavailableError("LLM")
        raise ServiceUnavailableError("Storage", "Configure GCS credentials")
    """

    def __init__(self, service_name: str, detail: Optional[str] = None):
        message = f"{service_name} service not configured"
        super().__init__(message=message, detail=detail, status_code=503)
        self.service_name = service_name


class RateLimitError(AppError):
    """Rate limit exceeded.

    HTTP 429 Too Many Requests in backend.

    Usage:
        raise RateLimitError("API rate limit exceeded", retry_after=60)
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        detail: Optional[Any] = None,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message=message, detail=detail, status_code=429)
        self.retry_after = retry_after


class ExternalAPIError(AppError):
    """External API call failed.

    HTTP 502 Bad Gateway in backend.

    Usage:
        raise ExternalAPIError("OpenAI", "Request timeout")
        raise ExternalAPIError("Clerk", "Invalid response", {"status": 500})
    """

    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        detail: Optional[Any] = None,
    ):
        full_message = f"{service_name} API error"
        if message:
            full_message = f"{service_name}: {message}"
        super().__init__(message=full_message, detail=detail, status_code=502)
        self.service_name = service_name


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
