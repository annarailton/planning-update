"""Development authentication helpers for local testing.

This module provides utilities for developers to easily test backend endpoints
without needing to go through the full Clerk authentication flow.

IMPORTANT: These endpoints are only available in development mode.
"""

from datetime import datetime, timedelta, UTC
from typing import Optional

import jwt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from core.config import get_settings
from core.dependencies import ClerkServiceDep
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/dev", tags=["Development"])


class DevTokenRequest(BaseModel):
    """Request model for development token generation."""

    user_id: Optional[str] = "dev_user_123"
    email: Optional[str] = "dev@example.com"
    expires_in_hours: Optional[int] = 24


class DevTokenResponse(BaseModel):
    """Response model for development token generation."""

    token: str
    user_id: str
    email: str
    message: str
    expires_in: str
    usage: str
    source: str  # "clerk_testing" or "local_dev"


@router.post(
    "/auth/token", response_model=DevTokenResponse, summary="Generate Dev Token"
)
async def generate_dev_token(
    request: DevTokenRequest = DevTokenRequest(), clerk_service: ClerkServiceDep = None
):
    """Generate a token for development testing.

    This endpoint will:
    1. Try to use Clerk's official testing token API if Clerk is configured
    2. Fall back to generating a local dev token if Clerk is not available

    Usage:
    1. Call this endpoint to get a token
    2. Copy the token from the response
    3. In Swagger UI, click "Authorize" button
    4. Paste the token as: Bearer <token>
    5. Test any authenticated endpoint

    Returns:
        DevTokenResponse: Token for development testing

    Raises:
        HTTPException: If not in development mode
    """
    settings = get_settings()

    # Only allow in development mode
    if settings.env != "development":
        logger.warning("Dev token endpoint accessed in non-development environment")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development endpoints only available in development mode",
        )

    # Try Clerk testing token first if Clerk is configured
    if clerk_service and clerk_service.is_configured():
        try:
            logger.info("Attempting to generate Clerk testing token")
            token_data = await clerk_service.create_testing_token()

            if token_data:
                # Calculate expiration
                expires_at = datetime.fromtimestamp(token_data["expires_at"], UTC)
                expires_in = expires_at - datetime.now(UTC)
                hours = int(expires_in.total_seconds() // 3600)
                minutes = int((expires_in.total_seconds() % 3600) // 60)
                expires_in_str = f"{hours}h {minutes}m"

                logger.info("Successfully generated Clerk testing token")

                return DevTokenResponse(
                    token=token_data["token"],
                    user_id="testing_token_user",
                    email="testing@clerk.dev",
                    message="Clerk testing token generated successfully",
                    expires_in=expires_in_str,
                    usage=f"Use in Swagger UI Authorization: Bearer {token_data['token'][:20]}...",
                    source="clerk_testing",
                )
        except Exception as e:
            logger.warning(
                f"Failed to generate Clerk testing token: {e}, falling back to local dev token"
            )

    # Fall back to local dev token
    logger.info("Generating local dev token")

    # Create token payload mimicking Clerk token structure
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=request.expires_in_hours)

    payload = {
        "sub": request.user_id,  # Subject (user ID)
        "email": request.email,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "nbf": int(now.timestamp()),
        "iss": "dev-token-generator",  # Issuer to identify dev tokens
        "azp": "http://localhost:3000",  # Authorized party (frontend URL)
        # Clerk-specific claims
        "clerk": {
            "user_id": request.user_id,
            "session_id": f"dev_session_{request.user_id}",
        },
    }

    # Generate token using a dev secret (in production, Clerk handles this)
    # Using a simple secret for dev - this is NOT secure for production
    dev_secret = settings.clerk_secret_key or "dev_secret_key_for_testing_only"
    token = jwt.encode(payload, dev_secret, algorithm="HS256")

    logger.info(f"Generated local dev token for user {request.user_id}")

    # Calculate human-readable expiration
    expires_in = expires_at - now
    hours = int(expires_in.total_seconds() // 3600)
    minutes = int((expires_in.total_seconds() % 3600) // 60)
    expires_in_str = f"{hours}h {minutes}m"

    return DevTokenResponse(
        token=token,
        user_id=request.user_id,
        email=request.email,
        message="Local development token generated successfully",
        expires_in=expires_in_str,
        usage=f"Use in Swagger UI Authorization: Bearer {token[:20]}...",
        source="local_dev",
    )


@router.get("/auth/info", summary="Dev Auth Info")
async def get_dev_auth_info(clerk_service: ClerkServiceDep = None):
    """Get information about development authentication setup.

    Returns setup instructions and current configuration status.
    """
    settings = get_settings()
    clerk_configured = clerk_service and clerk_service.is_configured()

    return {
        "environment": settings.env,
        "dev_mode_enabled": settings.env == "development",
        "clerk_configured": clerk_configured,
        "token_source": "clerk_testing" if clerk_configured else "local_dev",
        "instructions": {
            "setup": [
                "1. Ensure ENV=development in your .env file",
                "2. CLERK_SECRET_KEY is optional (enables Clerk testing tokens)",
                "3. Start the backend with docker compose up",
            ],
            "usage": [
                "1. Navigate to http://localhost:8080/docs",
                "2. Call POST /api/dev/auth/token to generate a token",
                "3. Copy the entire token from the response",
                "4. Click the 'Authorize' button in Swagger UI",
                "5. Enter: Bearer <your_token>",
                "6. Click 'Authorize' to apply",
                "7. Test any authenticated endpoint",
            ],
            "token_customization": (
                {
                    "note": "Only available when using local dev tokens (Clerk not configured)",
                    "user_id": "Specify custom user ID (default: dev_user_123)",
                    "email": "Specify custom email (default: dev@example.com)",
                    "expires_in_hours": "Token validity in hours (default: 24)",
                }
                if not clerk_configured
                else {
                    "note": "Using Clerk testing tokens - customization not available"
                }
            ),
        },
        "endpoints": {
            "token_generation": "/api/dev/auth/token",
            "auth_info": "/api/dev/auth/info",
            "swagger_ui": "/docs",
            "redoc": "/redoc",
        },
        "security_note": "⚠️ Dev tokens are for local development only. Never use in production!",
    }


@router.get("/test", summary="Test Endpoint")
async def test_endpoint():
    """Simple test endpoint to verify the dev router is working.

    This endpoint doesn't require authentication and can be used
    to verify the development router is properly mounted.
    """
    return {
        "status": "ok",
        "message": "Development router is working",
        "timestamp": datetime.now(UTC).isoformat(),
    }


# Export router
__all__ = ["router"]
