import logging
from abc import abstractmethod
from dataclasses import dataclass
from functools import partial
from json.decoder import JSONDecodeError
from typing import Union

import requests

from pydispix.client import Client
from pydispix.color import Color
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
    def get_task(self, endpoint: str = "get_task") -> ChurchTask:
        """
        Get task from the church, this is an abstract method, you'll need
        to override this to get it to work with your church's specific API.
        """

    @abstractmethod
    def submit_task(self, church_task: ChurchTask, endpoint: str = "submit_task") -> bool:
        """
        Submit a task to the church, this is an abstract method, you'll need
        to override this to get it to work with your church's specific API.
        """

    def _put_and_submit(self, church_task: ChurchTask, endpoint: str = "submit_task", show_progress: bool = False):
        """
        Put new pixel on the canvas and send the `submit_task` request.
        These are done together here because `put_pixel` waits for API
        rate limits from Pixels API, while the church rate-limit on
        task submitting might be lower than the api cooldown time.
        Because of this, the submit task is ran as `task_after` to
        `put_pixel` function.
        """
        submit_task = partial(self.submit_task, church_task, endpoint)
        self.put_pixel(
            church_task.x, church_task.y, church_task.color,
            show_progress=show_progress,
            task_after=submit_task
        )

    def run_task(self, show_progress: bool = False) -> bool:
        """Obtain, run and submit a single task to the church."""
        task = self.get_task()
        logger.info(f"Running church task: {task}")

        # Handle 403s by resetting the pixel, these happen when somebody
        # managed to overwrite the pixel we set before we informed the server
        # that we actually set it, it's quite rare, but it can happen.
        while True:
            try:
                return self._put_and_submit(task, show_progress=show_progress)
            except requests.HTTPError as exc:
                resp = exc.response
                if resp.status_code == 403:
                    try:
                        log_detail = resp.json()
                    except JSONDecodeError:
                        raise exc
                    logger.warning(f"Repeating task, got 403: {log_detail}")
                raise exc

    def run_tasks(self, show_progress: bool = False):
        """Keep running church tasks forever."""
        while True:
            self.run_task(show_progress=show_progress)
