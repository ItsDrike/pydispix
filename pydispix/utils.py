import asyncio
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


def resolve_url_endpoint(base_url: str, endpoint_url: str) -> str:
    """Add `endpoint_url` to the `base_url` and return the whole URL"""
    endpoint_url = endpoint_url.removeprefix("/")
    if endpoint_url.startswith("https://") or endpoint_url.startswith("http://"):
        if endpoint_url.startswith(base_url):
            return endpoint_url
        raise ValueError("`endpoint` referrs to unknown full url, that doesn't belong to the base url")
    else:
        return base_url + endpoint_url
