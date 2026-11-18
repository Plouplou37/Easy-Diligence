"""In-memory throttling of failed logins.

Failed attempts are counted per account and per client address over a sliding
window. Past the limit, logins are refused until the oldest failure leaves the
window. State lives in the process: it resets on restart and is not shared
between workers, which is enough for the single backend process this
application runs as.
"""
import threading
import time
from collections import deque
from typing import Callable, Deque, Dict, Iterable, Tuple

from app.core.config import settings

# A client address gets more room than an account: several people can sit
# behind the same address (an office, a proxy).
ADDRESS_FACTOR = 4

# Above this many tracked keys, expired ones are swept on the next failure.
SWEEP_ABOVE_KEYS = 10_000


class LoginThrottle:
    def __init__(self, max_attempts: int, window_seconds: int,
                 clock: Callable[[], float] = time.monotonic):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._clock = clock
        self._failures: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def _keys(self, email: str, address: str | None) -> Iterable[Tuple[str, int]]:
        yield f"account:{email.strip().lower()}", self.max_attempts
        if address:
            yield f"address:{address}", self.max_attempts * ADDRESS_FACTOR

    def _recent(self, key: str, now: float) -> Deque[float]:
        failures = self._failures.get(key)
        if failures is None:
            return deque()
        while failures and now - failures[0] >= self.window_seconds:
            failures.popleft()
        if not failures:
            del self._failures[key]
        return failures

    def retry_after(self, email: str, address: str | None) -> int:
        """Seconds to wait before the next attempt; 0 if one is allowed now."""
        now = self._clock()
        wait = 0.0
        with self._lock:
            for key, limit in self._keys(email, address):
                failures = self._recent(key, now)
                if len(failures) >= limit:
                    wait = max(wait, self.window_seconds - (now - failures[0]))
        return int(wait) + 1 if wait > 0 else 0

    def record_failure(self, email: str, address: str | None) -> None:
        now = self._clock()
        with self._lock:
            if len(self._failures) > SWEEP_ABOVE_KEYS:
                # Keys of addresses and accounts never seen again would
                # otherwise stay forever: drop every expired one.
                for key in list(self._failures):
                    self._recent(key, now)
            for key, _limit in self._keys(email, address):
                self._recent(key, now)
                self._failures.setdefault(key, deque()).append(now)

    def record_success(self, email: str) -> None:
        """A good password clears the account's count (not the address's)."""
        with self._lock:
            self._failures.pop(f"account:{email.strip().lower()}", None)


login_throttle = LoginThrottle(settings.login_max_attempts, settings.login_window_seconds)
