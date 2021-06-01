import logging
import os
from typing import Callable, Optional

import requests

from pydispix.canvas import Canvas, Dimensions, Pixel
from pydispix.color import ResolvableColor, parse_color
from pydispix.errors import InvalidToken, RateLimitBreached, handle_invalid_body
from pydispix.ratelimits import RateLimiter
from pydispix.utils import resolve_url_endpoint

logger = logging.getLogger("pydispix")


class Client:
    """HTTP client to the pixel API."""

    def __init__(self, token: Optional[str] = None, base_url: str = "https://pixels.pythondiscord.com/"):
        if token is None:
            try:
                token = os.environ["TOKEN"]
            except KeyError:
                raise RuntimeError("Unable to load token, 'TOKEN' environmental variable not found.")

        if not base_url.endswith("/"):
            base_url = base_url + "/"

        self.token = token
        self.base_url = base_url
        self.headers = {"Authorization": "Bearer " + token}
        self.rate_limiter = RateLimiter()

    def make_raw_request(
        self, method: str, url: str, *,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        update_rate_limits: bool = True,
    ) -> requests.Response:
        """
        This method is here purely to make an HTTP request and update the rate limiter.
        Even though this will update the rate limtis, it will not wait for them.
        """
        logger.debug(f"Request: {method} on {url} {data=} {params=}.")

        if headers is None:
            headers = {}

        # Set the user-agent, if not set to something else
        headers.setdefault("User-Agent", "ItsDrike pydispix")

        response = requests.request(
            method, url,
            json=data,
            params=params,
            headers=headers
        )

        if update_rate_limits:
            self.rate_limiter.update_from_headers(url, response.headers)

        if response.status_code == 429:
            logger.debug(f"Request failed (rate limitation): {method} on {url} {data=} {params=}")
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
        self, method: str, url: str, *,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        ratelimit_after: bool = False,
        task_after: Optional[Callable] = None,
        head_ratelimit_update: bool = False,
        repeat_on_ratelimit: bool = False,
        show_progress: bool = False,
    ) -> requests.Response:
        """
        This method handles making a request on a rate-limited endpoint.

        `ratelimit_after`: Wait for rate limits after making the request, this is handy
        for some requests, which should be ran as soon as possible, and wait out the rate
        limit after it was made.

        `task_after`: This is a function that will run after the request was made. This is
        useful when reporting that some task was fullfilled to external API (like to a church)
        where we can't afford to wait out the rate limit first. This is usually combined with
        ratelimit_after`, since there's no point in using it if we wait out the rate limit first.
        The result of this task will be stored in the response under `task_result` variable.
        In case any exception would occur in this task, it will be handled and stored in
        in the response under `task_exception` variable.

        `head_ratelimit_update`: Some APIs allow sending HEAD type requests, which don't actually
        trigger interfere with the API, and are here purely to obtain the rate limits, so that we
        can wait it out before we make an actual request. This can only be used when `ratelimit_after`
        isn't being used, since if it is, we'll obtain rate-limits from the original made request,
        instead of the HEAD.

        `repeat_on_ratelimit`: This can be used to repeat this request if request gives us
        `RateLimitBreached` exception. This will re-run the whole function again one more time, but
        if the second request fails too, `RateLimitBreached` will be raised anyway. (To avoid infinite
        loops). This option can't be used with `ratelimit_after` since if we breached rate limit, we
        have to wait it out, and we can't wait it out after the request we made has failed.
        """
        if repeat_on_ratelimit and ratelimit_after:
            raise ValueError(
                "Can't combine `ratelimit_after` with `repeat_on_ratelimit` (If we breached rate-limit, "
                "we have to wait it out, and that's impossible to do after a failed request)"
            )

        if not ratelimit_after:
            if head_ratelimit_update:
                self.make_raw_request("HEAD", url, headers=headers, update_rate_limits=True)
            self.rate_limiter.wait(url, show_progress=show_progress)

        try:
            response = self.make_raw_request(
                method, url,
                data=data,
                params=params,
                headers=headers,
                update_rate_limits=True
            )
        except RateLimitBreached as exc:
            if repeat_on_ratelimit:
                logger.warning(f"Hit rate limit, repeating request ({exc.response.content})")
                # There's no point in using `head_ratelimit_update` here, since the failed
                # request has already updated the rate limits.
                return self.make_request(
                    method, url,
                    data=data,
                    params=params,
                    headers=headers,
                    ratelimit_after=False,
                    task_after=task_after, head_ratelimit_update=False,
                    repeat_on_ratelimit=False, show_progress=show_progress
                )
            raise exc

        if task_after:
            try:
                result = task_after()
            except Exception as exc:
                response.task_exception = exc  # type: ignore - type is unknown, because it's a new property we're adding
            else:
                response.task_result = result  # type: ignore - type is unknown, because it's a new property we're adding

        if ratelimit_after:
            self.rate_limiter.wait(url, show_progress=show_progress)

        return response

    def resolve_endpoint(self, endpoint: str) -> str:
        """Resolve given `endpoint` to use the base_url"""
        return resolve_url_endpoint(self.base_url, endpoint)

    def get_dimensions(self) -> Dimensions:
        """Make a request to obtain the canvas dimensions"""
        url = self.resolve_endpoint("get_size")
        data = self.make_request("GET", url).json()
        return Dimensions(width=data["width"], height=data["height"])

    def get_canvas(self, show_progress: bool = False) -> Canvas:
        """Fetch the whole canvas and return it in a `Canvas` object."""
        url = self.resolve_endpoint("get_pixels")
        data = self.make_request("GET", url, headers=self.headers, show_progress=show_progress).content
        size = self.get_dimensions()
        return Canvas(size, data)

    def get_pixel(self, x: int, y: int, show_progress: bool = False) -> Pixel:
        """Fetch rgb data about a specific pixel"""
        url = self.resolve_endpoint("get_pixel")
        data = self.make_request(
            "GET", url, params={"x": x, "y": y}, headers=self.headers,
            show_progress=show_progress
        ).json()
        hex_color = data["rgb"]
        return Pixel.from_hex(hex_color)

    def put_pixel(
        self,
        x: int, y: int,
        color: ResolvableColor,
        show_progress: bool = False,
    ) -> str:
        """
        Draw a pixel and return a message.

        If you are reporting to some church, you may want to set
        `task_after` to the completion request for your church.
        This way, the task will be executed instantly, before
        waiting for the rate limitation
        """
        url = self.resolve_endpoint("set_pixel")
        data = self.make_request(
            "POST", url,
            data={
                "x": x,
                "y": y,
                "rgb": parse_color(color)
            },
            headers=self.headers,
            head_ratelimit_update=True,
            show_progress=show_progress,
        )

        msg = data.json()["message"]
        logger.info(f"Success: {msg}")
        return msg

    set_pixel = put_pixel
