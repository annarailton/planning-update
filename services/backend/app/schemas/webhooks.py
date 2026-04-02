"""Webhook-related schemas."""

from typing import Any, Dict, Optional

from pydantic import Field

from .base import CamelCaseModel


class WebhookResponse(CamelCaseModel):
    """Webhook processing response."""

    status: str = Field(..., description="Processing status", examples=["ok", "error"])
    message: str = Field(..., description="Status message")
    user_id: Optional[str] = Field(None, description="Internal user ID if applicable")
    clerk_user_id: Optional[str] = Field(
        None, description="Clerk user ID if applicable"
    )


class ClerkWebhookPayload(CamelCaseModel):
    """Clerk webhook payload structure.

    Note: We parse the full payload but only store minimal data (no PII).
    """

    type: str = Field(
        ...,
        description="Event type",
        examples=["user.created", "user.updated", "user.deleted"],
    )
    data: Dict[str, Any] = Field(
        ..., description="Event data containing user information"
    )
    object: Optional[str] = Field("event", description="Object type")


class ClerkWebhookEventData(CamelCaseModel):
    """Parsed Clerk event data from webhook.

    This schema is for parsing incoming webhook data only.
    We extract the Clerk ID and optionally use names to generate initials,
    but we do NOT store PII in our database.
    """

    id: str = Field(..., description="Clerk user ID (the only field we store)")
    email_addresses: Optional[list[Dict[str, Any]]] = Field(
        None, description="Email data (not stored)"
    )
    first_name: Optional[str] = Field(
        None, description="First name (used for initials only, not stored)"
    )
    last_name: Optional[str] = Field(
        None, description="Last name (used for initials only, not stored)"
    )
    username: Optional[str] = Field(None, description="Username (not stored)")
    created_at: Optional[int] = Field(
        None, description="Clerk creation timestamp (not stored)"
    )
    updated_at: Optional[int] = Field(
        None, description="Clerk update timestamp (not stored)"
    )
