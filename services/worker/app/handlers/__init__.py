"""Job handlers for different job types.

Each handler is an async function with signature:
    async def handler(payload: dict, on_progress: ProgressCallback) -> dict

The on_progress callback can be used to report progress:
    await on_progress(50, "Halfway done")  # 50%, optional message
"""

import asyncio
import logging
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

# Type for progress callback
ProgressCallback = Callable[[int | float, str | None], Awaitable[None]]

# Handler function type
HandlerFunc = Callable[[dict, ProgressCallback], Awaitable[Any]]


async def handle_echo(payload: dict, on_progress: ProgressCallback) -> dict:
    """Echo handler - returns the payload back. Useful for testing."""
    await on_progress(100, "Echo complete")
    return {"echoed": payload}


async def handle_slow_task(payload: dict, on_progress: ProgressCallback) -> dict:
    """Slow task handler - simulates a long-running job with progress updates."""
    duration = payload.get("duration", 5)  # seconds
    steps = payload.get("steps", 5)

    for i in range(steps):
        progress = int((i + 1) / steps * 100)
        await on_progress(progress, f"Step {i + 1}/{steps}")
        await asyncio.sleep(duration / steps)

    return {"completed": True, "steps": steps, "duration": duration}


# Job type -> handler function mapping
HANDLERS: dict[str, HandlerFunc] = {
    "echo": handle_echo,
    "slow_task": handle_slow_task,
}
