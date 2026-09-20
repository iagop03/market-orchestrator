import threading
import time


class RateLimiter:
    """Sync counterpart to a token-bucket-style limiter, for callables run off the
    event loop (e.g. via asyncio.to_thread). Enforces a minimum interval between
    successive acquire() calls, blocking with time.sleep — harmless off the loop.

    Distinct from retry.retry_sync: retry reacts to a failure that already happened;
    this prevents bursts that would trigger a rate limit in the first place.
    """

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._last_call = 0.0

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait = self.min_interval - (now - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()
