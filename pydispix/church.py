import logging
from abc import abstractmethod
from dataclasses import dataclass
from json.decoder import JSONDecodeError

from pydispix.errors import RateLimitBreached
from typing import Union

from pydispix.client import Client
from pydispix.color import Color
from pydispix.utils import resolve_url_endpoint
from pydispix.color import parse_color

logger = logging.getLogger("pydispix")


@dataclass
class ChurchTask:
    x: int
    y: int
    color: Union[int, str, tuple[int, int, int], Color]


class ChurchClient(Client):
    def __init__(
        self,
        pixel_api_token: str,
        church_token: str,
        base_church_url: str,
        *args,
        **kwargs
    ):
        super().__init__(pixel_api_token, *args, **kwargs)

        if not base_church_url.endswith("/"):
            base_church_url = base_church_url + "/"

        self.base_church_url = base_church_url
        self.church_token = church_token

    def resolve_church_endpoint(self, endpoint: str):
        return resolve_url_endpoint(self.base_church_url, endpoint)

    @abstractmethod
    def get_task(self, endpoint: str = "get_task", repeat_delay: int = 5) -> ChurchTask:
        """
        Get task from the church, this is an abstract method, you'll need
        to override this to get it to work with your church's specific API.

        `repeat_delay` is the time we will wait for, if the church currently
        doesn't have any aviable tasks for us.
        """

    @abstractmethod
    def submit_task(self, church_task: ChurchTask, endpoint: str = "submit_task") -> bool:
        """
        Submit a task to the church, this is an abstract method, you'll need
        to override this to get it to work with your church's specific API.
        """

    def run_task(
        self,
        submit_endpoint: str = "submit_task",
        show_progress: bool = False,
        repeat_delay: int = 5,
        repeat_on_ratelimit: bool = True,
    ):
        """
        Obtain the Church Task, put new pixel on the canvas and send the `submit_task` request.

        In case we hit initial rate limit from `set_pixel`, the rate limit is waited out,
        and we proceed with a new task, since the church's API time limit for that task
        has already likely expired.

        `repeat_delay` is the delay to wait, if the church doesn't have any more aviable tasks.
        """
        # This can't just use the `set_pixel`, because we need to send submit message to the church
        # before we wait for the rate limits, this is also why we use `make_raw_request` instead
        # of just using `make_requests` that handles the rate limits for us
        task = self.get_task(repeat_delay=repeat_delay)
        logger.info(f"Running church task: {task}")
        url = self.resolve_endpoint("set_pixel")
        try:
            response = self.make_raw_request(
                "POST", url,
                data={
                    "x": task.x,
                    "y": task.y,
                    "rgb": parse_color(task.color)
                }
            )
        except RateLimitBreached as exc:
            if not repeat_on_ratelimit:
                raise exc

            try:
                response_text = exc.response.json()
                response_text = response_text["data"]
            except JSONDecodeError:
                response_text = exc.response.content
            except KeyError:
                # If we can't get `data` key from obtained JSON,
                # just use the pure JSON that's already set.
                pass
            logger.warning(f"Hit pixels api rate limit, request failed ({response_text})")
            self.rate_limiter.wait(url, show_progress=show_progress)
            # There is no point in trying to fullfil this request now, just
            # rerunning and obtain a new request, the rate limit for set_pixel
            # is quite big, and would violate the rate limits of the church API.
            return self.run_task(
                submit_endpoint, show_progress=show_progress,
                repeat_on_ratelimit=False
            )
        data = response.json()
        # Log successful pixel placement just like `put_pixel` would
        logger.info(f"Success: {data['message']}")

        # Submit task before waiting out the pixels API limit, which is quite long
        # and will most likely lead to violations of the church API response time
        # limit for the given task.
        status = self.submit_task(task, endpoint=submit_endpoint)
        self.rate_limiter.wait(url, show_progress=show_progress)
        return status

    def run_tasks(
        self,
        submit_endpoint: str = "submit_task",
        show_progress: bool = False,
        repeat_delay: int = 5
    ):
        """Keep running church tasks forever."""
        while True:
            try:
                self.run_task(
                    submit_endpoint=submit_endpoint,
                    show_progress=show_progress,
                    repeat_delay=repeat_delay
                )
            except RateLimitBreached as exc:
                logger.exception("Got rate limited, ignoring exception and moving to the next task", exc_info=exc)
