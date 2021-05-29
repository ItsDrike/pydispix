import logging
import random
import re
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

    def get_task(self, endpoint: str = "get_task") -> RickChurchTask:
        url = self.resolve_church_endpoint(endpoint)
        response = self.make_request("GET", url, params={"key": self.church_token})
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
        return self.make_request("POST", url, data=body, params={"key": self.church_token})

    def run_task(
        self,
        submit_endpoint: str = "submit_task",
        show_progress: bool = False,
        repeat_on_ratelimit: bool = True,
    ):
        try:
            return super().run_task(
                submit_endpoint=submit_endpoint,
                show_progress=show_progress,
                repeat_on_ratelimit=repeat_on_ratelimit
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
        except requests.HTTPError as exc:
            # Handle church not accepting the request
            # this could occur because the church's rate limit has expired,
            # or because someone managed to overwrite the pixel we were setting
            # before we submitted the task
            if exc.response.status_code == 400:
                try:
                    detail = exc.response.json()["detail"]
                except (JSONDecodeError, KeyError):
                    # If the response isn't json decodeable or doesn't contain detail key,
                    # it isn't from rick church
                    raise exc
                err_msg = (
                    "You did not complete this task properly, or it was fixed before "
                    "the server could verify it. You have not been credited for this task."
                )
                if detail != err_msg:
                    # If we didn't catch this error message, something else has ocurred
                    # or this wasn't an exception from the rick church, don't handle it
                    raise exc
                # If this was exception from the church, re-run the whole `run_task` function,
                # which obtains a new task and runs that one, this one has failed
                logger.warn(
                    "Church task failed, got code 400. Either you hit church's rate limit, "
                    "or someone managed to overwrite this pixel before you submitted church request."
                )
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

    def get_task(self, endpoint: str = "tasks") -> SQLiteChurchTask:
        url = self.resolve_church_endpoint(endpoint)
        response = self.make_request("GET", url)
        task = random.choice(response)
        return SQLiteChurchTask(**task)

    def submit_task(self, church_task: SQLiteChurchTask, endpoint: str = "submit_task"):
        url = self.resolve_church_endpoint(endpoint)
        body = {"task_id": church_task.id}
        return self.make_request("POST", url, data=body)
