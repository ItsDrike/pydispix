from typing import Any
import requests
import re

from pydispix.ratelimits import RateLimitedEndpoint


class PyDisPixError(Exception):
    """Parent class for all exceptions defined by this library"""


class RateLimitBreached(PyDisPixError):
    """Request failed due to rate limit breach."""
    def __init__(self, *args, response: requests.Response, **kwargs):
        super().__init__(*args, **kwargs)

        # Get time limits from headers with RateLimitedEndpoint
        temp_rate_limit = RateLimitedEndpoint()
        temp_rate_limit.update_from_headers(response.headers)

        self.requests_limit = temp_rate_limit.requests_limit
        self.reset_time = temp_rate_limit.reset_time
        self.remaining_requests = temp_rate_limit.remaining_requests
        self.cooldown_time = temp_rate_limit.cooldown_time

        # Store the expected wait and the original response which trigerred this exception
        self.expected_wait_time = temp_rate_limit.get_wait_time()
        self.response = response

    def __str__(self):
        s = super().__str__()
        s += f"\nresponse={self.response.content}"
        if self.expected_wait_time != 0:
            s += f"\nexpected_wait_time={self.expected_wait_time}"

        return s


class InvalidToken(PyDisPixError, requests.HTTPError):
    """Invalid token used."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class CanvasFormatError(PyDisPixError):
    """Exception raised when the canvas is badly formatted."""


class InvalidColor(PyDisPixError):
    """Invalid color format"""

    def __init__(self, *args, color: Any, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = color

    def __str__(self) -> str:
        s = super().__str__()
        return s + f" color={self.color}"


class OutOfBoundaries(PyDisPixError):
    """Status code 422 - tried to draw a pixel outside of the canvas"""


def handle_invalid_body(response: requests.HTTPError) -> PyDisPixError:
    """
    Invalid body can mean many things, this analyzed given response
    and returns appropriate exception for it.
    """
    if response.status_code != 422:
        raise ValueError("Invalid Body response must have 422 HTTP code.")

    detail = response.json()['detail']

    # Work with 1st entry only, we can't raise multiple errors anyway
    entry = detail[0]
    if entry["loc"][1] == "rgb":
        color = re.search(r"'(.+)' is not a valid color", entry["msg"]).groups()[0]
        return InvalidColor("Couldn't resolve color", color=color)
    if entry["loc"][1] in ("x", "y"):
        return OutOfBoundaries(entry["msg"])

    raise requests.HTTPError("Unrecognized 422 exception, please report this issue in the pydispix repository", response=response)
