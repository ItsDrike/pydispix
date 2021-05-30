import logging
import sys
import time
from typing import Union

from requests.models import CaseInsensitiveDict

logger = logging.getLogger('pydispix')


class RateLimitedEndpoint:
    def __init__(self, endpoint: str, default_delay: int = 0):
        self.endpoint = endpoint

        self.requests_limit = None          # Total number of requests before reset time wait
        self.requests_period = None         # Period we have for making `self.requests_limit` requests
        self.remaining_requests = 1         # Remaining number of requests before reset time wait
        self.reset_time = 0                 # How much time to wait on reset
        self.cooldown_time = 0              # Some endpoints force longer cooldown times
        self.default_delay = default_delay  # If no other limit is found, how long should we wait
        self.anti_spam_delay = 0            # This is hit when multiple tokens are used

    def update_from_headers(self, headers: CaseInsensitiveDict):
        # Static values for given endpoint
        if "requests-limit" in headers:
            self.requests_limit = int(headers["requests-limit"])
        if "requests-period" in headers:
            self.requests_period = float(headers["requests-period"])

        # Current values for given endpoint
        self.remaining_requests = int(headers.get('requests-remaining', 1))
        self.reset_time = float(headers.get('requests-reset', 0))
        self.cooldown_time = float(headers.get('cooldown-reset', 0))
        self.anti_spam_delay = float(headers.get('retry-after', 0))

        logger.debug(
            f"Rates updated for {self.endpoint}: {self.remaining_requests=}, {self.reset_time=}, "
            f"{self.cooldown_time=}, {self.anti_spam_delay=}"
        )

    def get_wait_time(self):
        if self.anti_spam_delay != 0:
            return self.anti_spam_delay
        if self.cooldown_time != 0:
            return self.cooldown_time
        if self.remaining_requests == 0:
            return self.reset_time

        return self.default_delay

    def sleep(self, seconds: Union[int, float], *, show_progress: bool = False):
        # Progress bars shouldn't appear if we're waiting less than 5 seconds
        # it tends to be spammy and doesn't really provide much value
        if not show_progress or seconds < 5:
            return time.sleep(seconds)

        toolbar_width = 40

        # Setup toolbar
        sys.stdout.write(f"[{' ' * toolbar_width}]")
        sys.stdout.flush()
        sys.stdout.write("\b" * (toolbar_width + 1))  # return to start of line, after '['

        for _ in range(toolbar_width):
            time.sleep(seconds / toolbar_width)
            sys.stdout.write("#")
            sys.stdout.flush()
        sys.stdout.write("]\n")  # this ends the progress bar

    def wait(self, *, show_progress: bool = False):
        if self.anti_spam_delay != 0:
            logger.warning(f"Sleeping for {self.anti_spam_delay}s, anti-spam cooldown triggered! ({self.endpoint})")
            return self.sleep(self.anti_spam_delay, show_progress=show_progress)
        if self.cooldown_time != 0:
            logger.warning(f"Sleeping {self.cooldown_time}s, cooldown trigerred! ({self.endpoint})")
            return self.sleep(self.cooldown_time, show_progress=show_progress)
        if self.remaining_requests == 0:
            logger.info(f"Sleeping {self.reset_time}s, on reset. ({self.endpoint})")
            return self.sleep(self.reset_time, show_progress=show_progress)

        logger.debug(f"Sleeping default delay ({self.default_delay}), {self.remaining_requests} requests remaining. ({self.endpoint})")
        return self.sleep(self.default_delay, show_progress=show_progress)


class RateLimiter:
    def __init__(self):
        self.rate_limits = {}

    def update_from_headers(self, endpoint: str, headers: CaseInsensitiveDict):
        self.rate_limits.setdefault(endpoint, RateLimitedEndpoint(endpoint))
        limiter = self.rate_limits[endpoint]
        limiter.update_from_headers(headers)

    def wait(self, endpoint: str, show_progress: bool = False):
        self.rate_limits.setdefault(endpoint, RateLimitedEndpoint(endpoint))
        limiter = self.rate_limits[endpoint]
        limiter.wait(show_progress=show_progress)
