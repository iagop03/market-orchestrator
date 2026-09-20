import time

from orchestrator.rate_limit import RateLimiter


def test_first_acquire_does_not_wait():
    limiter = RateLimiter(min_interval=10.0)
    start = time.monotonic()
    limiter.acquire()
    assert time.monotonic() - start < 0.05


def test_second_acquire_waits_out_the_remaining_interval(monkeypatch):
    slept = []
    monkeypatch.setattr("orchestrator.rate_limit.time.sleep", lambda seconds: slept.append(seconds))

    limiter = RateLimiter(min_interval=5.0)
    limiter.acquire()
    limiter.acquire()

    assert len(slept) == 1
    assert 0 < slept[0] <= 5.0


def test_acquire_does_not_wait_once_enough_time_has_passed():
    limiter = RateLimiter(min_interval=0.05)
    limiter.acquire()
    time.sleep(0.1)

    start = time.monotonic()
    limiter.acquire()
    assert time.monotonic() - start < 0.05
