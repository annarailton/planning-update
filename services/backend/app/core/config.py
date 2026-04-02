"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    env: str = Field(default="development", description="Environment")
    debug: bool = Field(default=False, description="Debug mode")
    port: int = Field(default=8080, description="Server port", alias="PORT")
    backend_port: int = Field(
        default=8080, description="Backend port (deprecated, use port)"
    )

    # Database
    database_url: Optional[str] = Field(default=None, description="PostgreSQL URL")

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379", description="Redis connection URL"
    )
    redis_key_prefix: str = Field(
        default="",
        description="Redis key prefix for environment isolation (e.g., 'prod:', 'staging:')",
    )

    # CORS - stored as string, converted to list
    cors_origins: str = Field(
        default="http://localhost:3000", description="Comma-separated CORS origins"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Clerk Authentication
    clerk_secret_key: Optional[str] = Field(
        default=None, description="Clerk secret key"
    )
    clerk_webhook_secret: Optional[str] = Field(
        default=None, description="Clerk webhook secret"
    )

    # LLM Providers
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(
        default=None, description="Anthropic API key for Claude models"
    )
    gemini_api_key: Optional[str] = Field(
        default=None, description="Google Gemini API key"
    )

    # Langfuse - LLM Observability (optional)
    langfuse_public_key: Optional[str] = Field(
        default=None, description="Langfuse public key"
    )
    langfuse_secret_key: Optional[str] = Field(
        default=None, description="Langfuse secret key"
    )
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com", description="Langfuse host URL"
    )

    # Storage Configuration
    storage_provider: str = Field(
        default="gcp", description="Storage provider (gcp, aws, azure)"
    )
    gcp_project_id: Optional[str] = Field(default=None, description="GCP project ID")
    gcs_bucket_name: str = Field(default="test-bucket", description="GCS bucket name")
    storage_env_prefix: Optional[str] = Field(
        default=None, description="Storage environment prefix"
    )
    google_service_account_json: Optional[str] = Field(
        default=None, description="GCP service account JSON credentials"
    )

    # Cloud Run Detection
    k_service: Optional[str] = Field(
        default=None,
        description="Cloud Run service name (set automatically by Cloud Run)",
    )

    # Worker Configuration (for HTTP activation of scale-to-zero workers)
    worker_url: Optional[str] = Field(
        default=None,
        description="Worker service URL for HTTP activation (enables scale-to-zero)",
    )

    # Temporal Configuration (optional - for workflow orchestration)
    temporal_address: Optional[str] = Field(
        default=None, description="Temporal server address"
    )
    temporal_namespace: str = Field(default="default", description="Temporal namespace")
    temporal_api_key: Optional[str] = Field(
        default=None, description="Temporal Cloud API key"
    )
    temporal_task_queue: str = Field(
        default="default-tasks", description="Temporal task queue name"
    )

    # Feature Flags (set via features.json -> CI/CD -> env vars)
    feature_redis: bool = Field(
        default=False, description="Enable Redis (caching, pub/sub)"
    )
    feature_worker: bool = Field(
        default=False, description="Enable background worker service"
    )
    feature_temporal: bool = Field(
        default=False, description="Enable Temporal workflow orchestration"
    )
    feature_llm_openai: bool = Field(
        default=True, description="Enable OpenAI LLM provider"
    )
    feature_llm_anthropic: bool = Field(
        default=False, description="Enable Anthropic LLM provider"
    )
    feature_llm_gemini: bool = Field(
        default=False, description="Enable Gemini LLM provider"
    )
    feature_langfuse: bool = Field(
        default=False, description="Enable Langfuse LLM observability"
    )

    @property
    def is_temporal_cloud(self) -> bool:
        """Check if using Temporal Cloud (has API key)."""
        return self.temporal_api_key is not None

    @property
    def is_redis_enabled(self) -> bool:
        """Check if Redis features are enabled and configured."""
        return self.feature_redis and bool(self.redis_url)

    @property
    def is_temporal_enabled(self) -> bool:
        """Check if Temporal is enabled and configured."""
        return self.feature_temporal and (
            bool(self.temporal_address) or bool(self.temporal_api_key)
        )

    @property
    def is_worker_enabled(self) -> bool:
        """Check if worker service is enabled."""
        return self.feature_worker

    @property
    def is_langfuse_enabled(self) -> bool:
        """Check if Langfuse is enabled and configured."""
        return (
            self.feature_langfuse
            and bool(self.langfuse_public_key)
            and bool(self.langfuse_secret_key)
        )

    def get_cors_origins(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.env == "development"

    @property
    def is_cloud_run(self) -> bool:
        """Check if running on Cloud Run."""
        return self.k_service is not None

    @property
    def has_gcs_credentials(self) -> bool:
        """Check if GCS credentials are available."""
        return bool(self.google_service_account_json) or self.is_cloud_run


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_storage_bucket_name() -> str:
    """Get the storage bucket name from settings."""
    return get_settings().gcs_bucket_name
