"""Optional Temporal workflow package for durable execution.

This package provides Temporal integration for long-running, reliable workflows.
It is OPTIONAL - the application works without it using Redis Streams.

The package gracefully handles the case where temporalio is not installed.

Usage:
    from packages.temporal import (
        is_temporal_enabled,
        get_temporal_client,
        TemporalConfig,
    )

    # Check if Temporal is available
    if is_temporal_enabled():
        client = await get_temporal_client()
        # Use Temporal workflows
    else:
        # Fall back to Redis Streams

Configuration:
    Set TEMPORAL_API_KEY to enable Temporal Cloud.
    Without it, connects to local Temporal (localhost:7233).

Local Development:
    Start Temporal with: docker compose --profile temporal up
    Access UI at: http://localhost:8233
"""

import os
import logging

logger = logging.getLogger(__name__)

# Check if temporalio is installed
try:
    from temporalio.client import Client
    TEMPORAL_AVAILABLE = True
except ImportError:
    TEMPORAL_AVAILABLE = False
    logger.debug("temporalio not installed - Temporal features disabled")


def is_temporal_enabled() -> bool:
    """Check if Temporal is enabled.

    Temporal is enabled when:
    1. temporalio package is installed
    2. FEATURE_TEMPORAL env var is true (feature flag)
    3. TEMPORAL_API_KEY is set (for Temporal Cloud)
       OR TEMPORAL_ADDRESS is set (local development)

    Returns:
        True if Temporal is enabled and available
    """
    if not TEMPORAL_AVAILABLE:
        return False

    # Check feature flag first (docker-compose always sets TEMPORAL_ADDRESS,
    # so we need the feature flag to control whether Temporal is actually enabled)
    feature_temporal = os.getenv("FEATURE_TEMPORAL", "false").lower() in ("true", "1", "yes")
    if not feature_temporal:
        return False

    # Check for Temporal Cloud API key
    if os.getenv("TEMPORAL_API_KEY"):
        return True

    # Check for local development (TEMPORAL_ADDRESS set)
    if os.getenv("TEMPORAL_ADDRESS"):
        return True

    return False


# Conditional imports - only available if temporalio is installed
if TEMPORAL_AVAILABLE:
    from .client import (
        TemporalConfig,
        get_temporal_client,
        close_temporal_client,
    )
    from .types.file_types import (
        ProcessFileInput,
        ProcessFileOutput,
        ProcessBatchFilesInput,
        ProcessBatchFilesOutput,
    )
    from .workflows import ProcessFileWorkflow
    from .activities import (
        download_file,
        calculate_hash,
        extract_metadata,
        generate_thumbnail,
        update_file_status,
    )

    __all__ = [
        # Feature check
        "is_temporal_enabled",
        "TEMPORAL_AVAILABLE",
        # Client
        "TemporalConfig",
        "get_temporal_client",
        "close_temporal_client",
        # Types
        "ProcessFileInput",
        "ProcessFileOutput",
        "ProcessBatchFilesInput",
        "ProcessBatchFilesOutput",
        # Workflows
        "ProcessFileWorkflow",
        # Activities
        "download_file",
        "calculate_hash",
        "extract_metadata",
        "generate_thumbnail",
        "update_file_status",
    ]
else:
    __all__ = [
        "is_temporal_enabled",
        "TEMPORAL_AVAILABLE",
    ]
