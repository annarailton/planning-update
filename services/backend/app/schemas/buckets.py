"""Bucket schemas for Temasek POC Backend.

Defines Pydantic models for bucket-related API requests and responses.
"""

from uuid import UUID
from typing import Literal

from pydantic import BaseModel, Field


class BucketResponse(BaseModel):
    """Bucket response model."""

    id: UUID
    name: str
    slug: str
    provider: str
    is_public: bool
    created_by_id: UUID
    updated_by_id: UUID | None = None
    created_at: str
    updated_at: str

    @classmethod
    def from_bucket_model(cls, bucket) -> "BucketResponse":
        """Convert Bucket model to BucketResponse schema."""
        return cls(
            id=bucket.id,
            name=bucket.name,
            slug=bucket.slug,
            provider=bucket.provider,
            is_public=bucket.is_public,
            created_by_id=bucket.created_by_id,
            updated_by_id=bucket.updated_by_id,
            created_at=bucket.created_at.isoformat(),
            updated_at=bucket.updated_at.isoformat(),
        )


class BucketCreateRequest(BaseModel):
    """Bucket creation request model."""

    name: str = Field(
        ..., description="Actual bucket name (e.g., 'investment-reports-dev')"
    )
    slug: str = Field(
        ..., description="Human-readable slug for URLs (e.g., 'investment-reports')"
    )
    provider: Literal["gcp", "aws", "azure"] = Field(
        default="gcp", description="Cloud provider: 'gcp', 'aws', 'azure'"
    )
    is_public: bool = Field(
        default=False, description="Whether bucket contents are publicly accessible"
    )


class BucketUpdateRequest(BaseModel):
    """Bucket update request model."""

    name: str | None = Field(None, description="New bucket name")
    is_public: bool | None = Field(None, description="New public access setting")


class BucketListResponse(BaseModel):
    """Bucket list response model."""

    buckets: list[BucketResponse]
    total: int


# Export for easy imports
__all__ = [
    "BucketResponse",
    "BucketCreateRequest",
    "BucketUpdateRequest",
    "BucketListResponse",
]
