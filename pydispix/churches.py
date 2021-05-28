import logging
import random
from dataclasses import dataclass
from typing import Callable, Optional, Union

from pydispix.church import ChurchClient, ChurchTask

logger = logging.getLogger("pydispix")

SQLITE_CHURCH = "decorator-factory.su"
RICK_CHURCH = "https://pixel-tasks.scoder12.repl.co/api"


@dataclass
class RickChurchTask(ChurchTask):
    project_title: str
    start: float


@dataclass
class SQLiteChurchTask(ChurchTask):
    id: int
    issued_by: str


class RickChurchClient(ChurchClient):
    """Church Client designed to work specifically with rick church"""
    def __init__(
        self,
        pixel_api_token: str,
        church_token: str,
        base_church_url: str = RICK_CHURCH,
        *args,
        **kwargs
    ):
        super().__init__(pixel_api_token, church_token, base_church_url, *args, **kwargs)

    def make_request(
        self, method: str, url: str, *,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        parse_json: bool = True,
        ratelimit_after: bool = False,
        task_after: Optional[Callable] = None,
        show_progress: bool = False,
        repeat_on_ratelimit: bool = True,
    ) -> Union[bytes, dict]:
        """Extend regular make_request and add `key` parameter to the request"""
        if params is None:
            params = {}
        params["key"] = self.church_token

        return super().make_request(
            method, url,
            data=data,
            params=params,
            parse_json=parse_json,
            ratelimit_after=ratelimit_after,
            task_after=task_after,
            show_progress=show_progress
        )

    def get_task(self, endpoint: str = "get_task") -> RickChurchTask:
        url = self.resolve_church_endpoint(endpoint)
        response = self.make_request("GET", url)
        return RickChurchTask(**response["task"])

    def submit_task(self, church_task: RickChurchTask, endpoint: str = "submit_task") -> dict:
        url = self.resolve_church_endpoint(endpoint)
        body = {
            'project_title': church_task.project_title,
            'start': church_task.start,
            'x': church_task.x,
            'y': church_task.y,
            'color': church_task.color
        }
        return self.make_request("POST", url, data=body)


class SQLiteChurchClient(ChurchClient):
    """Church Client designed to work specifically with rick church"""
    def __init__(
            self,
            pixel_api_token: str,
            base_church_url: str = SQLITE_CHURCH,
            *args,
            **kwargs
    ):
        # SQLite Church API is open for everyone, it doesn't need a token
        church_token = None
        super().__init__(pixel_api_token, church_token, base_church_url, *args, **kwargs)

    def get_task(self, endpoint: str = "tasks") -> SQLiteChurchTask:
        url = self.resolve_church_endpoint(endpoint)
        response = self.make_request("GET", url)
        task_id = random.choice(list(response.keys()))
        task = response[task_id]
        return SQLiteChurchTask(**task)

    def submit_task(self, church_task: SQLiteChurchTask, endpoint: str = "submit_task"):
        url = self.resolve_church_endpoint(endpoint)
        body = {"task_id": church_task.id}
        return self.make_request("POST", url, data=body)
