import asyncio
from typing import Callable, TypeVar
from functools import wraps

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
