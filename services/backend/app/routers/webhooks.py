"""Webhook endpoints including Clerk authentication.

Uses Svix webhook signature verification as per Clerk's implementation.
"""

import base64
import hashlib
import hmac
import json
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, status

from core.config import get_settings
from core.constants import ErrorMessages, ResponseStatus, WebhookEvents
from core.dependencies import DatabaseDep, UserServiceDep
from core.logging import get_logger
from schemas.webhooks import WebhookResponse
from schemas.common import ErrorResponse

logger = get_logger(__name__)
router = APIRouter(tags=["Webhooks"])


def verify_svix_signature(
    body: bytes,
    svix_id: str,
    svix_timestamp: str,
    svix_signature: str,
    webhook_secret: str,
) -> bool:
    """Verify Svix webhook signature using HMAC-SHA256.

    Clerk uses Svix for webhook delivery. This verifies the signature
    according to Svix webhook signature verification spec.

    Args:
        body: Raw request body bytes
        svix_id: Webhook ID from Svix-Id header
        svix_timestamp: Timestamp from Svix-Timestamp header
        svix_signature: Signature from Svix-Signature header
        webhook_secret: Webhook signing secret from Clerk dashboard

    Returns:
        bool: True if signature is valid
    """
    try:
        # Clerk webhook secrets come in the format "whsec_xxxxx"
        # Extract the base64 part after the prefix and decode it
        if webhook_secret.startswith("whsec_"):
            # Remove the "whsec_" prefix and base64 decode
            secret_base64 = webhook_secret[6:]
            secret_bytes = base64.b64decode(secret_base64)
        else:
            # Fallback if no prefix (shouldn't happen with Clerk)
            secret_bytes = webhook_secret.encode("utf-8")

        # Construct the signed content according to Svix spec
        # Format: {svix_id}.{svix_timestamp}.{body}
        signed_content = f"{svix_id}.{svix_timestamp}.{body.decode('utf-8')}".encode()

        # Compute expected signature in base64 (Svix uses base64, not hex)
        expected_signature = base64.b64encode(
            hmac.new(secret_bytes, signed_content, hashlib.sha256).digest()
        ).decode()

        # Extract signatures from the header (format: "v1,signature1 v1,signature2")
        # We need to check each signature
        signatures = svix_signature.split(" ")
        for sig in signatures:
            if sig.startswith("v1,"):
                provided_signature = sig[3:]  # Remove "v1," prefix
                if hmac.compare_digest(expected_signature, provided_signature):
                    return True

        logger.warning(
            "Webhook signature verification failed - no valid signature found"
        )
        return False

    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False


@router.post(
    "/clerk",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Handle Clerk webhooks",
    description="Process Clerk webhook events for user lifecycle management",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Invalid webhook signature or missing headers",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid webhook payload",
        },
    },
)
async def handle_clerk_webhook(
    request: Request,
    db: DatabaseDep,
    user_service: UserServiceDep,
    svix_id: Optional[str] = Header(None, description="Svix webhook ID"),
    svix_timestamp: Optional[str] = Header(None, description="Svix timestamp"),
    svix_signature: Optional[str] = Header(None, description="Svix signature"),
) -> WebhookResponse:
    """Handle Clerk webhook events for user lifecycle management.

    Processes webhook events from Clerk for user synchronization:
    - user.created: Creates a new user record in the database
    - user.updated: Updates user information (future use)
    - user.deleted: Soft deletes the user from the database

    Returns:
        WebhookResponse: Processing result with status and user information
    """
    try:
        # Get raw body for signature verification
        body = await request.body()

        # Get webhook secret from settings
        settings = get_settings()
        webhook_secret = settings.clerk_webhook_secret

        # Verify signature - fail closed in production
        if not webhook_secret or webhook_secret.startswith("whsec_placeholder"):
            if settings.env == "production":
                logger.error(
                    "Webhook secret not configured in production - rejecting request"
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Webhook verification not configured",
                )
            else:
                logger.warning(
                    "Clerk webhook secret not configured - skipping signature verification (dev only)"
                )
        else:
            # Verify signature with real secret
            if not all([svix_id, svix_timestamp, svix_signature]):
                logger.warning("Missing required Svix headers for webhook verification")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=ErrorMessages.MISSING_WEBHOOK_HEADERS,
                )

            if not verify_svix_signature(
                body, svix_id, svix_timestamp, svix_signature, webhook_secret
            ):
                logger.warning("Invalid Clerk webhook signature")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=ErrorMessages.INVALID_WEBHOOK_SIGNATURE,
                )

        # Parse webhook payload
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorMessages.INVALID_JSON_PAYLOAD,
            )

        event_type = payload.get("type")
        event_data = payload.get("data", {})

        logger.info(f"Received Clerk webhook: {event_type}")
        logger.debug(f"Event data: {json.dumps(event_data, indent=2)}")

        # Handle different event types
        if event_type == WebhookEvents.USER_CREATED:
            # Extract user information
            clerk_user_id = event_data.get("id")

            if not clerk_user_id:
                logger.error("Missing user ID in webhook payload")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorMessages.MISSING_USER_ID,
                )

            # Log user details for debugging
            email_addresses = event_data.get("email_addresses", [])
            user_email = (
                email_addresses[0].get("email_address", "Unknown")
                if email_addresses
                else "Unknown"
            )
            logger.info(
                f"Processing user.created event for: {user_email} "
                f"(Clerk ID: {clerk_user_id})"
            )

            # Create or get user (handles both new and existing users)
            user = await user_service.create_or_get_user(
                clerk_user_id=clerk_user_id, db=db
            )

            # Check if this was a new user or existing
            if user.created_at == user.updated_at:
                logger.info(
                    f"Created new user from webhook: {user.id} (Clerk: {clerk_user_id})"
                )
                message = "User created"
            else:
                logger.info(f"User already exists for Clerk ID: {clerk_user_id}")
                message = "User already exists"

            return WebhookResponse(
                status=ResponseStatus.OK,
                message=message,
                user_id=str(user.id),
                clerk_user_id=clerk_user_id,
            )

        elif event_type == WebhookEvents.USER_UPDATED:
            # For now, we don't store any user details that need updating
            # This is here for future expansion
            clerk_user_id = event_data.get("id")
            logger.info(f"User updated event for Clerk ID: {clerk_user_id}")

            # Ensure user exists in our database
            if clerk_user_id:
                user = await user_service.get_user_by_clerk_id(clerk_user_id, db)
                if not user:
                    # Create user if they don't exist (in case webhook order is wrong)
                    user = await user_service.create_or_get_user(
                        clerk_user_id=clerk_user_id, db=db
                    )
                    logger.info(f"Created user from update event: {user.id}")

            return WebhookResponse(
                status=ResponseStatus.OK, message="User update acknowledged"
            )

        elif event_type == WebhookEvents.USER_DELETED:
            # Handle user deletion
            clerk_user_id = event_data.get("id")

            if not clerk_user_id:
                logger.error("Missing user ID in delete webhook")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorMessages.MISSING_USER_ID,
                )

            # Soft delete user from our database
            deleted = await user_service.delete_user(clerk_user_id, db)
            if deleted:
                logger.info(f"Successfully soft deleted user: {clerk_user_id}")
                return WebhookResponse(
                    status=ResponseStatus.OK,
                    message="User soft deleted",
                    clerk_user_id=clerk_user_id,
                )
            else:
                logger.warning(f"Delete event for unknown user: {clerk_user_id}")
                return WebhookResponse(
                    status=ResponseStatus.OK,
                    message="User not found, deletion acknowledged",
                )

        else:
            # Unknown event type - log and acknowledge
            logger.info(f"Unhandled Clerk webhook event: {event_type}")
            return WebhookResponse(
                status=ResponseStatus.OK, message=f"Event {event_type} acknowledged"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Clerk webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook",
        )
