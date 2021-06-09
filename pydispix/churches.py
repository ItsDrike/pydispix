import logging
import random
import time
from dataclasses import dataclass
from json.decoder import JSONDecodeError

import requests

from pydispix.church import ChurchClient, ChurchTask
from pydispix.errors import get_response_result

logger = logging.getLogger("pydispix")

SQLITE_CHURCH = "https://decorator-factory.su"
RICK_CHURCH = "http://localhost:8000"


@dataclass
class RickChurchTask(ChurchTask):
    project_name: str


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
        self.church_headers = {"Authorization": f"Bearer {self.church_token}"}

    def get_task(self, repeat_delay: int = 2) -> RickChurchTask:
        url = self.resolve_church_endpoint("task")
        while True:
            response = self.make_request("GET", url, headers=self.church_headers).json()

            if response.get("detail", None) == "No aviable tasks.":
                logger.info(f"Church doesn't currently have any aviable tasks, waiting {repeat_delay}s")
                time.sleep(repeat_delay)
                continue

            # Make response dict compliant with the task dataclass, we use `color`, not `rgb`
            response["color"] = response["rgb"]
            del response["rgb"]
            return RickChurchTask(**response)

    def submit_task(self, church_task: RickChurchTask) -> requests.Response:
        url = self.resolve_church_endpoint("task")
        body = {
            'project_name': church_task.project_name,
            'x': church_task.x,
            'y': church_task.y,
            'rgb': church_task.color
        }
        req = self.make_request("POST", url, data=body, headers=self.church_headers)
        logger.info("Task submitted to the church")
        return req

    def _handle_church_task_errors(self, exception: Exception) -> None:
        """
        Rick church can raise certain specific errors, handle
        them here or raise them back, if they shouldn't be handled.
        """
        if isinstance(exception, requests.HTTPError):
            try:
                detail: str = get_response_result(exception, "detail", error_on_fail=True)  # type: ignore - if it's not str, we handle it
            except (UnicodeDecodeError, JSONDecodeError, KeyError):
                # If we can't get the detail, this isn't the exception we're looking for
                return super()._handle_church_task_errors(exception)

            if exception.response.status_code == 409:
                invalid_task_msg = "This task doesn't belong to you, it has likely been reassigned since you took too long to complete it."
                validation_err_msg = "Validation error, you didn\'t actually complete this task"

                if detail == invalid_task_msg:
                    logger.warn("Church task doesn't belong to you, it has likely been reassigned since you took too long to complete it.")
                elif detail == validation_err_msg:
                    logger.warn("Church task verification failed, someone has overwritten the pixel before we could submit it.")
                else:
                    return super()._handle_church_task_errors(exception)
        else:
            # If we didn't find a rich church specific exception,
            # call the super's implementation of this, there could
            # be some other common errors
            return super()._handle_church_task_errors(exception)

    def get_projects(self) -> list:
        """Get project data from the church."""
        url = self.resolve_church_endpoint("projects")
        return self.make_request("GET", url, headers=self.church_headers).json()

    def check_mod(self) -> bool:
        """Check if this client is a moderator at church of rick."""
        url = self.resolve_church_endpoint("/mods/check")
        try:
            response = self.make_request("GET", url, headers=self.church_headers)
        except requests.HTTPError as exc:
            if exc.response.status_code == 403:
                return False
            raise exc

        msg = response.json()["message"]
        if msg == "You are a moderator!":
            return True
        raise ValueError(f"Got unexpected message from response: {msg}; response body: {response.content}")

    def promote(self, discord_user_id: int) -> requests.Response:
        """Add a new moderator to the church."""
        url = self.resolve_church_endpoint("/mods/promote")
        return self.make_request("POST", url, data={"user_id": discord_user_id}, headers=self.church_headers)

    def demote(self, discord_user_id: int) -> requests.Response:
        """Remove an existing moderator from the church."""
        url = self.resolve_church_endpoint("/mods/demote")
        return self.make_request("POST", url, data={"user_id": discord_user_id}, headers=self.church_headers)


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

    def get_task(self, repeat_delay: int = 2) -> SQLiteChurchTask:
        url = self.resolve_church_endpoint("tasks")
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

    def submit_task(self, church_task: SQLiteChurchTask) -> requests.Response:
        url = self.resolve_church_endpoint("submit_task")
        body = {"task_id": church_task.id}
        req = self.make_request("POST", url, data=body)
        logger.info("Task submitted to the church")
        return req
