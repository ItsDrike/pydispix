import os
import requests
import logging
from collections import namedtuple
from typing import Union, Optional

from pydispix.ratelimits import RateLimiter, RateLimitBreached
from pydispix.canvas import Canvas, Pixel
from pydispix.color import Color, parse_color

logger = logging.getLogger('pydispix')
Dimensions = namedtuple('Dimensions', ('width', 'height'))


class Client:
    """HTTP client to the pixel API."""
    def __init__(self, token: Optional[str] = None, base_url="https://pixels.pythondiscord.com"):
        if token is None:
            try:
                token = os.environ['TOKEN']
            except KeyError:
                raise RuntimeError("Unable to load token, 'TOKEN' environmental variable not found.")

        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": "Bearer " + token,
            "User-Agent": "ItsDrike pydispix",
        }
        self.rate_limiter = RateLimiter()
        self.width, self.height = self.size = self.get_dimensions()

    def make_request(
        self,
        method: str,
        endpoint_url: str,
        *,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        parse_json: bool = True,
        ratelimit_after: bool = False,
        show_progress: bool = False,
    ) -> Union[bytes, dict]:
        if not endpoint_url.startswith("/"):
            endpoint_url = "/" + endpoint_url

        if not ratelimit_after:
            self.rate_limiter.wait(endpoint_url, show_progress=show_progress)

        logger.debug(f'Request: {method} {endpoint_url} data={data!r} params={params!r}.')

        response = requests.request(method, self.base_url + endpoint_url, json=data, headers=self.headers, params=params)
        self.rate_limiter.update_from_headers(endpoint_url, response.headers)
        if ratelimit_after:
            self.rate_limiter.wait(endpoint_url, show_progress=show_progress)

        if response.status_code == 429:
            # This can happen with first request when we're rate-limiting afterwards
            # Or when 2 machines are using the same token
            raise RateLimitBreached(
                "Got code 421, sent request while being rate limited. \n"
                "This occurs when you're sending first request with rate-limit waiting afterwards, "
                "or when multiple programs are using your token.",
                response=response
            )
        if response.status_code != 200:
            raise requests.HTTPError(f"Received code {response.status_code}", response=response)

        if parse_json:
            return response.json()
        else:
            return response.content

    def get_dimensions(self) -> Dimensions:
        data = self.make_request("GET", "get_size")
        return Dimensions(width=data["width"], height=data["height"])

    def get_canvas(self, show_progress: bool = False) -> Canvas:
        data = self.make_request("GET", "get_pixels", parse_json=False, show_progress=show_progress)
        return Canvas(self.size, data)

    def get_pixel(self, x: int, y: int, show_progress: bool = False) -> Pixel:
        data = self.make_request("GET", "get_pixel", params={"x": x, "y": y}, show_progress=show_progress)
        hex_color = data["rgb"]
        return Pixel.from_hex(hex_color)

    def put_pixel(
        self,
        x: int, y: int,
        color: Union[int, str, tuple[int, int, int], Color],
        show_progress: bool = False,
        retry_on_limit: bool = False,
    ) -> str:
        """Draw a pixel and return a message."""
        # Wait for ratelimits *after* making request, not before. This makes
        # sense because we don't know how the canvas may have changed by the
        # time we have finished waiting, whereas for GET endpoints, we want to
        # return the information as soon as it is given.
        try:
            data = self.make_request(
                'POST', 'set_pixel',
                data={
                    'x': x,
                    'y': y,
                    'rgb': parse_color(color)
                },
                ratelimit_after=True,
                show_progress=show_progress
            )
        except RateLimitBreached as exc:
            logger.error(f"Request failed: {exc}")
            if retry_on_limit:
                return self.put_pixel(x, y, color, show_progress=show_progress, retry_on_limit=retry_on_limit)
            else:
                raise exc

        logger.info('Success: {message}'.format(**data))
        return data['message']
