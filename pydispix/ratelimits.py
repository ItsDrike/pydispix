import time
import logging
from collections import defaultdict
from requests.models import CaseInsensitiveDict

logger = logging.getLogger('pydispix')


class RateLimitedEndpoint:
    def __init__(self, default_delay: int = 0):
        self.rate_limited = True            # Not all endpoints are rate-limited
        self.requests_limit = None          # Total number of requests before reset time wait
        self.remaining_requests = 1          # Remaining number of requests before reset time wait
        self.reset_time = 0                 # How much time to wait once we hit reset
        self.cooldown_time = 0              # Some endpoints force longer cooldown times
        self.default_delay = default_delay  # If no other limit is found, how long should we wait

    def update_from_headers(self, headers: CaseInsensitiveDict[str]):
        if 'requests-remaining' not in headers:
            self.rate_limited = False
            return

        self.remaining_requests = int(headers.get('requests-remaining', 1))
        self.reset_time = int(headers.get('requests-reset', 0))
        self.cooldown_time = int(headers.get('cooldown-reset', 0))
        if "requests-limit" in headers:
            self.requests_limit = int(headers["requests-limit"])

    def get_wait_time(self):
        if not self.rate_limited:
            return self.default_delay
        if self.cooldown_time != 0:
            return self.cooldown_time
        if self.remaining_requests == 0:
            return self.reset_time

        return self.default_delay

    def wait(self):
        if not self.rate_limited:
            logger.debug("Sleeping default delay, not rate limited.")
            return time.sleep(self.default_delay)
        if self.cooldown_time != 0:
            logger.warning(f"Sleeping {self.cooldown_time}s, on cooldown.")
            return time.sleep(self.cooldown_time)
        if self.remaining_requests == 0:
            logger.warning(f"Sleeping {self.reset_time}s, on reset.")
            return time.sleep(self.reset_time)

        logger.debug(f"Sleeping default delay, {self.remaining_requests} requests remaining.")
        return time.sleep(self.default_delay)


class RateLimiter:
    def __init__(self):
        self.rate_limits = defaultdict(RateLimitedEndpoint)

    def update_from_headers(self, endpoint: str, headers: CaseInsensitiveDict[str]):
        limiter = self.rate_limits[endpoint]
        limiter.update_from_headers(headers)

    def wait(self, endpoint: str):
        limiter = self.rate_limits[endpoint]
        limiter.wait()
