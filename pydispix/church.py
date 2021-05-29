import logging
from abc import abstractmethod
from dataclasses import dataclass
from functools import partial
from json.decoder import JSONDecodeError
from typing import Union

import requests

from pydispix.client import Client
from pydispix.color import Color, parse_color
from pydispix.errors import RateLimitBreached
from pydispix.utils import resolve_url_endpoint

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
    def submit_task(self, church_task: ChurchTask, endpoint: str = "submit_task") -> requests.Response:
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

        # Manual set_pixel, with submit before waiting for rate limits
        url = self.resolve_endpoint("set_pixel")
        try:
            response = self.make_request(
                "POST", url,
                data={
                    "x": task.x,
                    "y": task.y,
                    "rgb": parse_color(task.color)
                },
                ratelimit_after=True,
                task_after=partial(self.submit_task, task, endpoint=submit_endpoint),
                show_progress=show_progress
            )
        except RateLimitBreached as exc:
            try:
                response_text = exc.response.json()["message"]
            except (JSONDecodeError, KeyError):
                response_text = exc.response.content

            # This can occur first time we run this, since we're handling
            # rate limits after the request is made, `repeat_on_ratelimit`
            # should always be `True` initially. We can then wait out the
            # rate limit, and re-run the whole function with a new task,
            # since the time limit for the completion of this one has most
            # likely already expired.
            if repeat_on_ratelimit:
                logger.warning(f"Hit pixels api ratelimit: {response_text}, waiting it out and ignoring this task.")
                self.rate_limiter.wait(url, show_progress=show_progress)
                # Re-run the task only once, this rate breach should only occur
                # on initial request, if it happens again, it shouldn't be handled
                return self.run_task(
                    submit_endpoint=submit_endpoint,
                    show_progress=show_progress,
                    repeat_delay=repeat_delay,
                    repeat_on_ratelimit=False
                )
            raise exc

        # Return status of the submit task, or raise the exception that ocurred in it
        if hasattr(response, "task_exception"):
            raise response.task_exception
        return response.task_result

    def run_tasks(
        self,
        submit_endpoint: str = "submit_task",
        show_progress: bool = False,
        repeat_delay: int = 5
    ):
        """Keep running church tasks forever."""
        while True:
            self.run_task(
                submit_endpoint=submit_endpoint,
                show_progress=show_progress,
                repeat_delay=repeat_delay
            )
