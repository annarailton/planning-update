"""Temporal worker integration.

This module provides Temporal worker setup for the worker service.
It runs alongside the Redis Streams consumer.
"""

from .worker import create_temporal_worker

__all__ = ["create_temporal_worker"]
