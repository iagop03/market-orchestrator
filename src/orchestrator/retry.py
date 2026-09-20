import asyncio
import logging
import random
import time
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_sync(
    operation: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """Sync counterpart to retry_async, for callables run off the event loop (e.g. via
    asyncio.to_thread) where blocking with time.sleep between attempts is harmless."""
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except retry_on:
            if attempt == attempts:
                raise
            delay = min(base_delay * 2 ** (attempt - 1), max_delay)
            delay += random.uniform(0, delay * 0.1)
            logger.warning("Attempt %d/%d failed; retrying in %.1fs", attempt, attempts, delay, exc_info=True)
            time.sleep(delay)


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """Calls the zero-argument async callable `operation`, retrying on failure.

    Exponential backoff (base_delay * 2**attempt) capped at max_delay, plus up to 10%
    jitter so concurrent callers don't all retry in lockstep. Re-raises the last
    exception once `attempts` is exhausted.
    """
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except retry_on:
            if attempt == attempts:
                raise
            delay = min(base_delay * 2 ** (attempt - 1), max_delay)
            delay += random.uniform(0, delay * 0.1)
            logger.warning("Attempt %d/%d failed; retrying in %.1fs", attempt, attempts, delay, exc_info=True)
            await asyncio.sleep(delay)
