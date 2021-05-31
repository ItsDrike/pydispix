import logging
import random
import re
import time
from dataclasses import dataclass
from json.decoder import JSONDecodeError

import requests

from pydispix.church import ChurchClient, ChurchTask
from pydispix.errors import RateLimitBreached, get_response_result

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

    def get_task(self, repeat_delay: int = 2) -> RickChurchTask:
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
        req = self.make_request("POST", url, data=body, params={"key": self.church_token})
        completed_tasks = self.get_personal_stats()["goodTasks"]
        logger.info(f"Task submitted to the church (tasks complete={completed_tasks}")
        return req

    def _handle_church_task_errors(self, exception: Exception) -> None:
        """
        Rick church can raise certain specific errors, handle
        them here or raise them back, if they shouldn't be handled.
        """
        if isinstance(exception, RateLimitBreached):
            try:
                detail: str = get_response_result(exception, "detail", error_on_fail=True)  # type: ignore
            except (UnicodeDecodeError, JSONDecodeError, KeyError):
                # If we can't get the detail, this isn't the exception we're looking for
                return super()._handle_church_task_errors(exception)

            match = re.search(
                r"You have not gotten a task yet or you took more than (\d+) seconds to submit your task",
                detail
            )
            if not match:
                # If the detail isn't matching, this isn't an exception from the rick church
                return super()._handle_church_task_errors(exception)

            # Log the exception and proceed cleanly
            logger.warning(f"Church task failed, task disassigned, submitting took over {match.groups()[0]} seconds")
        elif isinstance(exception, requests.HTTPError):
            try:
                detail: str = get_response_result(exception, "detail", error_on_fail=True)  # type: ignore - if it's not str, we handle it
            except (UnicodeDecodeError, JSONDecodeError, KeyError):
                # If we can't get the detail, this isn't the exception we're looking for
                return super()._handle_church_task_errors(exception)

            if exception.response.status_code == 409:
                if detail != "This is not the task you were assigned":
                    # If the detail isn't matching, this isn't an exception from the rick church
                    return super()._handle_church_task_errors(exception)

                # Log the exception and proceed cleanly
                logger.warning("Church task failed, this task already got reassigned to somebody else.")
            elif exception.response.status_code == 400:
                msg = (
                    "You did not complete this task properly, or it was fixed before the server could verify it. "
                    "You have not been credited for this task."
                )
                if detail != msg:
                    # If the detail isn't matching, this isn't an exception from the rick church
                    return super()._handle_church_task_errors(exception)

                # Log the exception and proceed cleanly
                logger.warning("Church task failed, check failed, someone has overwritten the pixel before we could submit it.")
        elif isinstance(exception, requests.exceptions.SSLError):
            url = exception.request.url
            if not url.startswith(self.base_church_url):
                # This error doesn't come from church of rick URL
                return super()._handle_church_task_errors(exception)

            # Log the exception and proceed cleanly
            logger.warning("Church task failed, SSL Error: Church of rick's SSL certificate wasn't valid. For some reason this sometimes occurs.")
        else:
            # If we didn't find a rich church specific exception,
            # call the super's implementation of this, there could
            # be some other common errors
            return super()._handle_church_task_errors(exception)

    # region: Add some misc endpoints which Church of Rick provides

    def get_personal_stats(self):
        """Get personal stats."""
        url = self.resolve_church_endpoint("user/stats")
        return self.make_request("GET", url, params={"key": self.church_token}).json()

    def get_church_stats(self):
        """Get church stats."""
        url = self.resolve_church_endpoint("overall_stats")
        return self.make_request("GET", url).json()

    def get_leaderboard(self) -> list:
        """Get church leaderboard."""
        url = self.resolve_church_endpoint("leaderboard")
        return self.make_request("GET", url).json()["leaderboard"]

    def get_uptime(self) -> float:
        """Uptime of the church of rick."""
        url = self.resolve_church_endpoint("leaderboard")
        return float(self.make_request("GET", url).json()["uptime"])

    def get_projects(self) -> list:
        """Get project data from the church."""
        url = self.resolve_church_endpoint("projects/stats")
        return self.make_request("GET", url).json()

    # endregion


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
        church_token = ""
        super().__init__(pixel_api_token, church_token, base_church_url, *args, **kwargs)

    def get_task(self, endpoint: str = "tasks", repeat_delay: int = 2) -> SQLiteChurchTask:
        url = self.resolve_church_endpoint(endpoint)
        while True:
            response = self.make_request("GET", url).json()

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
        req = self.make_request("POST", url, data=body)
        logger.info("Task submitted to the church")
        return req
