import re
from json.decoder import JSONDecodeError
from typing import Any, Optional, Union

import requests

from pydispix.ratelimits import RateLimitedEndpoint


class PyDisPixError(Exception):
    """Parent class for all exceptions defined by this library"""


class RateLimitBreached(PyDisPixError):
    """Request failed due to rate limit breach."""
    def __init__(self, *args, response: requests.Response, **kwargs):
        super().__init__(*args, **kwargs)

        # Get time limits from headers with RateLimitedEndpoint
        temp_rate_limit = RateLimitedEndpoint(response.url)
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


def handle_invalid_body(response: requests.Response) -> Union[PyDisPixError, requests.HTTPError]:
    """
    Handle 442 (invalid body) error code. This code can mean many things,
    this function analyzes what exactly does the 442 refer to, and returns
    an appropriate exception for it.
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


def get_response_result(
    exception: Union[requests.HTTPError, RateLimitBreached],
    key: Optional[str] = None,
    error_on_fail: bool = False
) -> Union[str, dict, list]:
    if not hasattr(exception, "response"):
        raise ValueError("This exception doesn't have a `response` attribute.")

    try:
        response = exception.response.json()
    except JSONDecodeError as exc:
        if error_on_fail:
            raise exc
        # Return the `content` message, this isn't JSON docodeable
        # If we can't decode to str text, don't bother with bytes, just raise `UnicodeDecodeError`
        return exception.response.content.decode("utf-8")

    if key is not None:
        try:
            response = response[key]
        except KeyError as exc:
            if error_on_fail:
                raise exc
            # Return the whole json, it doesn't contain wanted key
            return response

    return response
