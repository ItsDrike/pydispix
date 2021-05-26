import time
from typing import Optional
from collections import OrderedDict
from contextlib import contextmanager

from pydispix.client import Client


class MultiClient:
    def __init__(
        self,
        tokens: list,
        multiplex_amt: Optional[int] = None,
        multiplexed_positions: list[int] = None,
        *args, **kwargs
    ):
        """
        Use multiple tokens to speed up the tasks.

        We can also use `multiplex_amt` to define precise amount of multiplexed work to be done.
        This is usually done to share work with other servers, since we can only work on a portion
        of multiplexed work.

        The portion reserved for this machine to work on is defined with `multiplexed_positions`.
        This variable needs to be set if `multiplex_amt` is higher than amount of aviable `tokens`.
        This variable should hold the indices of multiplexed work:
            With `multiplex_amt` of 10 and 5 `tokens`, we could work on first 5 positions:
            `multiplexed_positions = [0,1,2,3,4]`
            With the second server holding other 5 tokens working on the remaining 5 positions:
            `multiplexed_positions = [5,6,7,8,9]`

        We can't have more `multiplexed_positions` than `tokens` (ValueError).
        If we have less `multiplexed_positions` than `tokens`, only first n tokens will be selected
        to work on given positions.
        `multiplexed_positions` defaults to first n positions, where `n` is the amount of `tokens`,
        or amount of `multiplexed_amt`, if that's less.
        """
        if multiplex_amt is None:
            multiplex_amt = len(tokens)
        if multiplexed_positions is None:
            if len(tokens) > multiplex_amt:
                multiplexed_positions = list(range(multiplex_amt))
            else:
                multiplexed_positions = list(range(len(tokens)))

        if len(tokens) < len(multiplexed_positions):
            raise ValueError(f"You can't support more positions than you have tokens. ({len(tokens)} < {len(multiplexed_positions)})")
        if len(tokens) == 0:
            raise ValueError("At least 1 token must be provided")

        self.tokens = tokens
        self.multiplex_amt = multiplex_amt
        self.multiplexed_positions = multiplexed_positions
        # Store all lists within a dict, with value representing if it's aviable
        self.clients = OrderedDict((Client(token, *args, **kwargs), True) for token in tokens)

    def get_free_clients(self):
        """get first n free clients"""
        for client, is_free in self.clients.items():
            if is_free:
                yield client

    def get_free_client(self, *, retry: bool = False, retry_delay: int = 5):
        """Get first aviable free client."""
        clients = self.get_free_clients()
        try:
            return next(clients)
        except StopIteration:
            if not retry:
                raise NoFreeClient("Unable to find unoccupied client.")
            time.sleep(retry_delay)
            return self.get_free_client(retry=retry, retry_delay=retry_delay)

    @contextmanager
    def with_free_client(self):
        client = self.get_free_client()
        self.clients[client] = False
        yield client
        self.clients[client] = True

    # These have to be defined manually, for type linting
    def put_pixel(self, *args, **kwargs) -> str:
        with self.with_free_client() as client:
            ret = client.put_pixel(*args, **kwargs)
        return ret

    def get_pixel(self, *args, **kwargs) -> str:
        with self.with_free_client() as client:
            ret = client.get_pixel(*args, **kwargs)
        return ret

    def get_canvas(self, *args, **kwargs) -> str:
        with self.with_free_client() as client:
            ret = client.get_canvas(*args, **kwargs)
        return ret

    def get_dimensions(self, *args, **kwargs) -> str:
        with self.with_free_client() as client:
            ret = client.get_dimensions(*args, **kwargs)
        return ret

    def make_request(self, *args, **kwargs) -> str:
        with self.with_free_client() as client:
            ret = client.make_request(*args, **kwargs)
        return ret


class NoFreeClient(Exception):
    pass
