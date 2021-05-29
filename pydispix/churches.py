import logging
import random
import re
import time
from dataclasses import dataclass
from json.decoder import JSONDecodeError

import requests

from pydispix.church import ChurchClient, ChurchTask
from pydispix.errors import RateLimitBreached

logger = logging.getLogger("pydispix")

SQLITE_CHURCH = "https://decorator-factory.su"
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

    @property
    def personal_stats(self):
        """Get personal stats."""
        url = self.resolve_church_endpoint("user/stats")
        return self.make_request("GET", url, params={"key": self.church_token}).json()

    @property
    def church_stats(self):
        """Get church stats."""
        url = self.resolve_church_endpoint("overall_stats")
        return self.make_request("GET", url).json()

    @property
    def leaderboard(self) -> list:
        """Get church leaderboard."""
        url = self.resolve_church_endpoint("leaderboard")
        return self.make_request("GET", url).json()["leaderboard"]

    @property
    def uptime(self) -> float:
        """Uptime of the church of rick."""
        url = self.resolve_church_endpoint("leaderboard")
        return float(self.make_request("GET", url).json()["uptime"])

    @property
    def projects(self) -> list:
        """Get project data from the church."""
        url = self.resolve_church_endpoint("projects/stats")
        return self.make_request("GET", url).json()

    def get_task(self, repeat_delay: int = 5) -> RickChurchTask:
        url = self.resolve_church_endpoint("get_task")
        while True:
            response = self.make_request("GET", url, params={"key": self.church_token}).json()

            if response["task"] is None:
                logger.info(f"Church doesn't currently have any aviable tasks, waiting {repeat_delay}s")
                time.sleep(repeat_delay)
                continue
            return RickChurchTask(**response["task"])

    def submit_task(self, church_task: RickChurchTask, endpoint: str = "submit_task") -> requests.Response:
        url = self.resolve_church_endpoint(endpoint)
        body = {
            'project_title': church_task.project_title,
            'start': church_task.start,
            'x': church_task.x,
            'y': church_task.y,
            'color': church_task.color
        }
        return self.make_request("POST", url, data=body, params={"key": self.church_token})

    def run_task(
        self,
        submit_endpoint: str = "submit_task",
        show_progress: bool = False,
        repeat_delay: int = 5,
        repeat_on_ratelimit: bool = True,
    ) -> requests.Response:
        """
        Extend `run_task` to handle specific exceptions from the
        church of rick.
        """
        try:
            return super().run_task(
                submit_endpoint=submit_endpoint,
                show_progress=show_progress,
                repeat_delay=repeat_delay,
                repeat_on_ratelimit=repeat_on_ratelimit,
            )
        except RateLimitBreached as exc:
            # If we take longer to submit a request to the church, it will
            # result in RateLimitBreached
            try:
                details = exc.response.json()["detail"]
            except (JSONDecodeError, KeyError):
                # If response isn't json decodeable or doesn't contain a detail key,
                # it isn't from rick church
                raise exc
            if not re.search(
                r"You have not gotten a task yet or you took more than \d+ seconds to submit your task",
                details
            ):
                # If we didn't catch this error message, something else has ocurred
                # or this wasn't an exception from the rick church, don't handle it
                raise exc
            logger.warn("Church task failed, got rate limited: submitting task took too long")
            return self.run_task(
                submit_endpoint=submit_endpoint,
                show_progress=show_progress,
                repeat_on_ratelimit=repeat_on_ratelimit
            )


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

    def get_task(self, endpoint: str = "tasks", repeat_delay: int = 5) -> SQLiteChurchTask:
        url = self.resolve_church_endpoint(endpoint)
        while True:
            response = self.make_request("GET", url)

            if len(response) == 0:
                logger.info(f"Church doesn't currently have any aviable tasks, waiting {repeat_delay}s")
                time.sleep(repeat_delay)
                continue
            # SQLite church returns a list of aviable tasks to complete, it doesn't assign
            # specific tasks to members, since there is no unique API key. Best we can do is
            # Therefore to pick a task randomly from this list
            task = random.choice(response)
            return SQLiteChurchTask(**task)

    def submit_task(self, church_task: SQLiteChurchTask, endpoint: str = "submit_task") -> requests.Response:
        url = self.resolve_church_endpoint(endpoint)
        body = {"task_id": church_task.id}
        return self.make_request("POST", url, data=body)
