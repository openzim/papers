"""Shared per-host cooldowns for HTTP downloads.

When one host starts answering 429, every worker hitting it should back off,
not just the worker that saw the response. Otherwise N concurrent workers
keep requesting while one of them sleeps, and each of them can exhaust its
own retry budget: the run ends with "all books failed" even though the host
only needed a short pause.

`HostLimiter` holds one cooldown deadline per host. Threads call `wait()`
before a request and `throttle()` when a response asks them to slow down.
Waiting happens outside the lock, so another thread can extend the cooldown
while a worker is sleeping through it.
"""

import math
import threading
import time
from collections.abc import Callable
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import requests

DEFAULT_COOLDOWN_SECONDS = 1.0
MAX_COOLDOWN_SECONDS = 300.0
MAX_RETRY_AFTER_SECONDS = 300.0
RATE_LIMIT_STATUS_CODES = frozenset({429, 503})


def retry_after_seconds(response: requests.Response | None) -> float | None:
    """Return a usable `Retry-After` delay in seconds, or None.

    Both forms are accepted: a number of seconds and an HTTP-date. Invalid,
    negative and absurdly large values are ignored so a broken header cannot
    stall a run indefinitely.
    """
    if response is None:
        return None
    value = response.headers.get("Retry-After")
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    try:
        seconds = float(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except TypeError, ValueError, OverflowError:
            return None
        if retry_at.tzinfo is None:
            return None
        seconds = retry_at.timestamp() - time.time()
    if not math.isfinite(seconds) or seconds < 0:
        return None
    return min(seconds, MAX_RETRY_AFTER_SECONDS)


class HostLimiter:
    """Thread-safe cooldown state shared by all workers of one download engine."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._cooldown_until: dict[str, float] = {}
        self._strikes: dict[str, int] = {}

    @staticmethod
    def _host(url: str) -> str:
        return (urlsplit(url).hostname or "").lower()

    def wait(self, url: str) -> None:
        """Block until this URL's host is no longer in a shared cooldown."""
        host = self._host(url)
        while True:
            with self._lock:
                remaining = self._cooldown_until.get(host, 0.0) - self._clock()
            if remaining <= 0:
                return
            self._sleep(remaining)

    def throttle(self, url: str, seconds: float | None = None) -> None:
        """Pause this URL's host; use a growing cooldown when no hint is given."""
        host = self._host(url)
        with self._lock:
            strikes = self._strikes.get(host, 0)
            if seconds is None:
                delay = min(DEFAULT_COOLDOWN_SECONDS * 2**strikes, MAX_COOLDOWN_SECONDS)
            else:
                delay = min(seconds, MAX_COOLDOWN_SECONDS)
            self._strikes[host] = strikes + 1
            self._cooldown_until[host] = max(
                self._cooldown_until.get(host, 0.0), self._clock() + delay
            )

    def succeeded(self, url: str) -> None:
        """Forget previous throttling once the host answers successfully."""
        with self._lock:
            self._strikes.pop(self._host(url), None)
