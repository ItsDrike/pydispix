from typing import Union
from dataclasses import dataclass
from abc import abstractmethod

from pydispix.client import Client
from pydispix.color import Color
from pydispix.utils import resolve_url_endpoint


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

    def put_task_pixel(self, church_task: ChurchTask, show_progress: bool = False):
        """Add the corresponding pixel from the church_task."""
        self.put_pixel(church_task.x, church_task.y, church_task.color, show_progress=show_progress)

    def run_task(self, show_progress: bool = False):
        """Obtain, run and submit a single task to the church."""
        task = self.get_task()
        self.put_task_pixel(task, show_progress=show_progress)
        self.submit_task(task)

    def run_tasks(self, show_progress: bool = False):
        """Keep running church tasks forever."""
        while True:
            self.run_task(show_progress=show_progress)
