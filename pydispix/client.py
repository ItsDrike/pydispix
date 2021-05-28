import os
import requests
import logging
from collections import namedtuple
from typing import Union, Optional

from pydispix.ratelimits import RateLimiter
from pydispix.canvas import Canvas, Pixel
from pydispix.color import Color, parse_color
from pydispix.errors import RateLimitBreached, InvalidToken, handle_invalid_body

logger = logging.getLogger('pydispix')
Dimensions = namedtuple('Dimensions', ('width', 'height'))


class Client:
    """HTTP client to the pixel API."""
    def __init__(self, token: Optional[str] = None, base_url: str = "https://pixels.pythondiscord.com/"):
        if token is None:
            try:
                token = os.environ['TOKEN']
            except KeyError:
                raise RuntimeError("Unable to load token, 'TOKEN' environmental variable not found.")

        if not base_url.endswith("/"):
            base_url = base_url + "/"

        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": "Bearer " + token,
            "User-Agent": "ItsDrike pydispix",
        }
        self.rate_limiter = RateLimiter()
        self.width, self.height = self.size = self.get_dimensions()

    def make_raw_request(
        self, method: str, url: str, *,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        update_rate_limits: bool = True,
    ) -> requests.Response:
        """
        This method is here purely to make an HTTP request and update the rate limiter.
        Even though this will update the rate limtis, it will not wait for them.
        """
        logger.debug(f"Request: {method} on {url} {data=} {params=}.")
        response = requests.request(
            method, url,
            json=data,
            params=params,
            headers=self.headers
        )

        if update_rate_limits:
            self.rate_limiter.update_from_headers(url, response.headers)

        if response.status_code == 429:
            logger.debug(f"Request: {method} on {url} {data=} {params=} has failed due to rate limitation.")
            raise RateLimitBreached(
                "Request didn't succeed because it was made during a rate-limit phase.",
                response=response
            )
        if response.status_code == 401:
            logger.error("Request failed with 401 (Forbidden) code. This means your API token is most likely invalid.")
            raise InvalidToken("Received 401 - FORBIDDEN: Is your API token correct?", response=response)

        if response.status_code == 422:
            exc = handle_invalid_body(response)
            if exc is not None:
                raise exc

        if response.status_code != 200:
            raise requests.HTTPError(f"Received code {response.status_code}", response=response)

        return response

    def make_request(
        self,
        method: str,
        url: str,
        *,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        parse_json: bool = True,
        ratelimit_after: bool = False,
        show_progress: bool = False,
    ) -> Union[bytes, dict]:
        """
        Make a `method` request to given `url`, while respecting the API rate limits.
        You can optionally pass JSON `data` and `parameters`.
        You can set `show_progress` to draw a progress bar while waiting for the rate limtis.

        For some requests, you may want to wait for the rate limit timeout *after* the request
        was made. This is needed because with some requests we want the most recent data we
        can get, after waiting out the limit (for example with get_canvas), but with others
        where we want to make our request as soon as possible, and only then wait for rate limits.
        """
        while True:
            if not ratelimit_after:
                self.rate_limiter.wait(url, show_progress=show_progress)

            try:
                response = self.make_raw_request(method, url, data=data, params=params)
            except RateLimitBreached:
                # This can happen with first request when we're rate-limiting afterwards
                # Or when 2 machines are using the same token. When this occurs we continue
                # and make the request again.
                logger.warning("Hit rate limit, repeating request")

                # Wait for the rate limit if we're limiting afterwards
                if ratelimit_after:
                    self.rate_limiter.wait(url, show_progress=show_progress)

                continue

            if ratelimit_after:
                self.rate_limiter.wait(url, show_progress=show_progress)

            if parse_json:
                return response.json()
            else:
                return response.content

    def resolve_endpoint(self, endpoint: str) -> str:
        """Resolve given `endpoint` to use the base_url"""
        endpoint = endpoint.removeprefix("/")
        if endpoint.startswith("https://") or endpoint.startswith("http://"):
            if endpoint.startswith(self.base_url):
                return endpoint
            raise ValueError("`endpoint` referrs to unknown full url, that doesn't belong to the base url")
        else:
            return self.base_url + endpoint

    def get_dimensions(self) -> Dimensions:
        """Make a request to obtain the canvas dimensions"""
        url = self.resolve_endpoint("get_size")
        data = self.make_request("GET", url)
        return Dimensions(width=data["width"], height=data["height"])

    def get_canvas(self, show_progress: bool = False) -> Canvas:
        """Fetch the whole canvas and return it in a `Canvas` object."""
        url = self.resolve_endpoint("get_pixels")
        data = self.make_request("GET", url, parse_json=False, show_progress=show_progress)
        return Canvas(self.size, data)

    def get_pixel(self, x: int, y: int, show_progress: bool = False) -> Pixel:
        """Fetch rgb data about a specific pixel"""
        url = self.resolve_endpoint("get_pixel")
        data = self.make_request("GET", url, params={"x": x, "y": y}, show_progress=show_progress)
        hex_color = data["rgb"]
        return Pixel.from_hex(hex_color)

    def put_pixel(
        self,
        x: int, y: int,
        color: Union[int, str, tuple[int, int, int], Color],
        show_progress: bool = False,
    ) -> str:
        """Draw a pixel and return a message."""
        url = self.resolve_endpoint("set_pixel")
        data = self.make_request(
            'POST', url,
            data={
                'x': x,
                'y': y,
                'rgb': parse_color(color)
            },
            show_progress=show_progress
        )

        logger.info('Success: {message}'.format(**data))
        return data['message']
