import logging
from contextlib import contextmanager
from typing import Optional, Union

from pydispix.client import Client
from pydispix.utils import get_token_from_env

logger = logging.getLogger('pydispix')


class SharedClient(Client):
    """
    Extend single Client class, that's unaware of any sharing/multi-usage data
    and add those additional parameters which will be used when allocating clients
    """
    def __init__(self, *args, position: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_free = True
        self.position = position

    @property
    def is_occupied(self) -> bool:
        return not self.is_free

    @is_occupied.setter
    def is_occupied(self, value: bool) -> None:
        self.is_free = value


class MultiClient:
    def __init__(
        self,
        tokens: Union[str, list] = None,
        total_tasks: Optional[int] = None,
        controlled_tasks: list[int] = None,
        *args, **kwargs
    ):
        """
        Use multiple tokens to speed up the tasks.

        `total_tasks` is the number of tasks our requests will be split to.
            - This defaults to the number of `tokens` passed.
            - If this number is lower, some tokens will remain unused
            - If this number is higher, this `MultiClient` will only use the `controlled_tasks`

        `controlled_tasks` is the list of indices, defining which tasks are controlled here
            - This defaults to all tasks up to amount of `tokens`, or up to `total_tasks` if less.
            - This is used mostly to allow others to collaborate on same program by having each
              `MultiClient` working on different chunks. It is important that we support all
              tasks that are aviable across these programs, otherwise some parts belonging to
              those indices won't be complete.
            - Example, with `total_tasks` = 10, and 5 tokens per `MultiClient`:
                First `MultiClient` (this machine): `controlled_tasks` = [0,1,2,3,4]
                Second `MultiClient` (collaborator): `controlled_tasks` = [5,6,7,8,9]
                Together, when running at the same time, these will never touch each others seconds
                and will only work on their designated controlled tasks.
            - Task division logic may differ depending on what is used, this class only holds these.

        NOTE: You should only ever use this with single token per machine and single controlled task,
        with different people owning each machine for collaboration purposes. Even though this is
        capable of using multiple tokens from a single machine, doing this might lead to additional
        rate limitation or even a ban from the API so it is highly discouraged!
        """
        if tokens is None:
            tokens = get_token_from_env()
        if not isinstance(tokens, list):
            tokens = [tokens]

        if total_tasks is None:
            total_tasks = len(tokens)

        if controlled_tasks is None:
            # We can't control more tasks than we have tokens, if this happens
            # we expect other `MultiClient` instance to join the work and do the rest
            # we can take up first tasks up to our token amount, but the other machine
            # will have to know this number and use the remaining ones
            if len(tokens) > total_tasks:
                total_tasks = list(range(len(tokens)))
            # If we have less or equal tasks to tokens, we can safely controll all of them
            else:
                controlled_tasks = list(range(total_tasks))

        if len(controlled_tasks) > len(tokens):
            raise ValueError(
                "We can't control more tasks than we have aviable tokens "
                f"({len(controlled_tasks)} tasks > {len(tokens)} tokens)"
            )

        if len(tokens) == 0:
            raise ValueError("At least 1 token must be provided")

        if len(tokens) > 1:
            logger.warning(
                "You passed more than 1 token, this means you will be oscillating requests from single machine with multiple tokens. "
                "This is against the API use conditions and will likely lead to more rate limits and possibly a ban to access the API."
            )

        if len(tokens) > len(controlled_tasks):
            logger.info("You passed more tokens than there is controlled_tasks, some tokens won't be used")

        self.tokens = tokens
        self.total_tasks = total_tasks
        self.controlled_tasks = controlled_tasks

        # Store all lists within a dict, with value representing it's id
        self.clients: dict[SharedClient] = {
            index: SharedClient(tokens[index], *args, position=index, **kwargs)
            for index in controlled_tasks
        }

    def get_free_clients(self):
        """get first n free clients"""
        for client in self.clients:
            if client.is_free:
                yield client

    def get_free_client(self):
        """Get first aviable free client."""
        clients = self.get_free_clients()
        try:
            return next(clients)
        except StopIteration:
            raise NoFreeClient("Unable to find unoccupied client.")

    @contextmanager
    def free_client(self):
        client = self.get_free_client()
        client.is_free = False
        yield client
        self.is_free = True

    # These have to be defined manually, for static type linting
    async def put_pixel(self, *args, **kwargs) -> str:
        with self.with_free_client() as client:
            return await client.async_put_pixel(*args, **kwargs)

    async def get_pixel(self, *args, **kwargs) -> str:
        with self.with_free_client() as client:
            return await client.async_get_pixel(*args, **kwargs)

    async def get_canvas(self, *args, **kwargs) -> str:
        with self.with_free_client() as client:
            return await client.async_get_canvas(*args, **kwargs)

    async def get_dimensions(self, *args, **kwargs) -> str:
        with self.with_free_client() as client:
            return await client.async_get_dimensions(*args, **kwargs)

    async def make_request(self, *args, **kwargs) -> str:
        with self.with_free_client() as client:
            return await client.async_make_request(*args, **kwargs)


class NoFreeClient(Exception):
    pass
