"""Tests for the shared per-host download limiter."""

import threading
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from unittest.mock import MagicMock

import pytest

from papers2zim.core.host_limiter import (
    MAX_RETRY_AFTER_SECONDS,
    HostLimiter,
    retry_after_seconds,
)

URL = "https://open.umn.edu/opentextbooks/textbooks/1966.json"
SAME_HOST = "https://open.umn.edu:443/opentextbooks/textbooks/1986.json"
OTHER_HOST = "https://example.org/books/1.json"


class FakeClock:
    """Clock and sleep that advance together, without real waiting."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def limiter(clock):
    return HostLimiter(clock=clock, sleep=clock.sleep)


def test_throttle_pauses_every_worker_on_the_same_host(limiter, clock):
    limiter.throttle(URL, 5)

    limiter.wait(SAME_HOST)

    assert clock.sleeps == [5]
    limiter.wait(OTHER_HOST)
    assert clock.sleeps == [5]


def test_cooldown_grows_until_the_host_succeeds(limiter, clock):
    limiter.throttle(URL)
    limiter.wait(URL)
    limiter.throttle(URL)
    limiter.wait(URL)

    assert clock.sleeps == [1, 2]

    limiter.succeeded(URL)
    limiter.throttle(URL)
    limiter.wait(URL)
    assert clock.sleeps == [1, 2, 1]


def test_cooldown_extended_while_a_worker_is_waiting_is_honored(clock):
    def sleep(seconds: float) -> None:
        clock.sleep(seconds)
        if len(clock.sleeps) == 1:
            limiter.throttle(URL, 5)

    limiter = HostLimiter(clock=clock, sleep=sleep)
    limiter.throttle(URL, 10)
    limiter.wait(URL)

    assert clock.sleeps == [10, 5]


def _response(retry_after: str | None) -> MagicMock:
    response = MagicMock()
    response.headers = {} if retry_after is None else {"Retry-After": retry_after}
    return response


def test_workers_share_one_cooldown_across_threads():
    limiter = HostLimiter()
    started = threading.Event()
    proceeded = threading.Event()

    def worker():
        started.set()
        limiter.wait(URL)
        proceeded.set()

    limiter.throttle(URL, 0.1)
    thread = threading.Thread(target=worker)
    thread.start()
    try:
        assert started.wait(1)
        assert not proceeded.wait(0.01)
        assert proceeded.wait(1)
    finally:
        thread.join()


def test_retry_after_accepts_seconds_and_http_dates():
    assert retry_after_seconds(_response("7")) == 7
    http_date = format_datetime(datetime.now(UTC) + timedelta(seconds=30), usegmt=True)
    delay = retry_after_seconds(_response(http_date))
    assert delay is not None
    assert 25 <= delay <= 30


@pytest.mark.parametrize("header", ["tomorrow", "-5", "NaN", "999999999"])
def test_retry_after_ignores_unusable_values(header):
    value = retry_after_seconds(_response(header))
    assert value is None or value <= MAX_RETRY_AFTER_SECONDS


def test_retry_after_is_none_without_a_header_or_response():
    assert retry_after_seconds(None) is None
    assert retry_after_seconds(_response(None)) is None
