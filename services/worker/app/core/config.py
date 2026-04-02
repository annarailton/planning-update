"""Worker configuration.

Uses the same environment variables as the backend for shared settings
(DATABASE_URL, ENV, DEBUG, LOG_LEVEL). Only worker-specific settings
are defined here.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Worker settings loaded from environment variables.

    Shared settings (same as backend):
    - DATABASE_URL: PostgreSQL connection string
    - ENV: Environment (development/production)
    - DEBUG: Enable debug mode
    - LOG_LEVEL: Logging level

    Worker-specific settings:
    - REDIS_URL: Redis connection string
    - WORKER_MAX_CONCURRENT_JOBS: Max parallel jobs
    - WORKER_JOB_TIMEOUT: Job execution timeout
    - WORKER_HEARTBEAT_INTERVAL: Heartbeat frequency
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # === Shared settings (same env vars as backend) ===
    database_url: Optional[str] = Field(default=None, description="PostgreSQL URL")
    env: str = Field(default="development", description="Environment")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # === LLM API Keys (shared with backend) ===
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")

    # === Worker-specific settings ===
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL",
    )
    worker_max_concurrent_jobs: int = Field(
        default=5,
        description="Maximum concurrent jobs",
    )
    worker_job_timeout: int = Field(
        default=300,
        description="Job execution timeout in seconds",
    )
    worker_heartbeat_interval: int = Field(
        default=15,
        description="Heartbeat interval in seconds",
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.env == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
