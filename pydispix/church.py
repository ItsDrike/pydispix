from collections import namedtuple

from pydispix.client import Client
from pydispix.utils import resolve_url_endpoint

ChurchTask = namedtuple("ChurchTask", ("x", "y", "color"))


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

    def get_task(self, endpoint="get_task") -> ChurchTask:
        """
        Get task from the church, this is designed to work out of the box
        only for the church of rick, you will probably need to override
        this method to get it to work for your church.
        """
        url = self.resolve_church_endpoint(endpoint)
        data = self.make_request("GET", url, params={"key": self.church_token})
        color = data["task"]["color"]
        x = data["task"]["x"]
        y = data["task"]["y"]
        return ChurchTask(x=x, y=y, color=color)

    def run_task(self, church_task: ChurchTask, show_progress: bool = False):
        self.put_pixel(church_task.x, church_task.y, church_task.color, show_progress=show_progress)
