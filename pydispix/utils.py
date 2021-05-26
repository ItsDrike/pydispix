import asyncio
import os
from functools import wraps
from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable)


def synchronize(func: F) -> F:
    """
    Function decorator that runs an asynchronous function in it's own isolated even loop.
    This effectively makes it run synchronously. Functions wrapped with this are virtually
    indistinguishable from regular synchronous functions to the user, and it gives us a way
    to support both async and sync versions.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


def get_token_from_env() -> str:
    """Try to obtain the token from environmental vars."""
    try:
        return os.environ['TOKEN']
    except KeyError:
        raise RuntimeError("Unable to load token, 'TOKEN' environmental variable not found.")
