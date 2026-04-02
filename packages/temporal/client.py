"""Temporal client configuration.

Provides a configured Temporal client that works with both:
- Local development (docker-compose Temporal server)
- Production (Temporal Cloud with API key auth)

This module is shared between backend and worker services.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Optional

from temporalio.client import Client

logger = logging.getLogger(__name__)

# Global client instance (lazy initialization with lock for thread safety)
_client: Optional[Client] = None
_client_lock = asyncio.Lock()


@dataclass
class TemporalConfig:
    """Configuration for Temporal connection.

    Attributes:
        address: Temporal server address (host:port)
        namespace: Temporal namespace
        api_key: API key for Temporal Cloud (optional, production only)
        task_queue: Default task queue name
    """

    address: str = "localhost:7233"
    namespace: str = "default"
    api_key: Optional[str] = None
    task_queue: str = "default-tasks"

    @classmethod
    def from_env(cls) -> "TemporalConfig":
        """Create config from environment variables.

        Environment variables:
        - TEMPORAL_ADDRESS: Server address (default: localhost:7233)
        - TEMPORAL_NAMESPACE: Namespace (default: default)
        - TEMPORAL_API_KEY: API key for Temporal Cloud
        - TEMPORAL_TASK_QUEUE: Task queue name (default: default-tasks)
        """
        return cls(
            address=os.getenv("TEMPORAL_ADDRESS", "localhost:7233"),
            namespace=os.getenv("TEMPORAL_NAMESPACE", "default"),
            api_key=os.getenv("TEMPORAL_API_KEY"),
            task_queue=os.getenv("TEMPORAL_TASK_QUEUE", "default-tasks"),
        )


async def get_temporal_client(config: Optional[TemporalConfig] = None) -> Client:
    """Get or create a Temporal client.

    Uses double-check locking pattern to ensure thread-safe singleton initialization.

    Args:
        config: Optional configuration. If not provided, loads from environment.

    Returns:
        Configured Temporal client

    Raises:
        Exception: If connection fails
    """
    global _client

    # Fast path - already initialized
    if _client is not None:
        return _client

    # Slow path - need to initialize with lock
    async with _client_lock:
        # Double-check after acquiring lock
        if _client is not None:
            return _client

        if config is None:
            config = TemporalConfig.from_env()

        logger.info(f"Connecting to Temporal at {config.address}")

        if config.api_key:
            # Temporal Cloud with API key authentication
            logger.info("Using Temporal Cloud with API key auth")
            client = await Client.connect(
                config.address,
                namespace=config.namespace,
                api_key=config.api_key,
                tls=True,
            )
        else:
            # Local development - no authentication
            logger.info("Using local Temporal server (no auth)")
            client = await Client.connect(
                config.address,
                namespace=config.namespace,
            )

        logger.info(f"Connected to Temporal namespace: {config.namespace}")
        _client = client
        return _client


async def close_temporal_client() -> None:
    """Close the Temporal client connection."""
    global _client

    if _client is not None:
        # Note: Temporal Python SDK client doesn't require explicit close
        # but we clear the reference for clean shutdown
        _client = None
        logger.info("Temporal client closed")
