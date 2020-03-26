from typing import Callable

from junkie.context import Context


def cache(factory: Callable) -> Callable:
    try:
        setattr(factory, "__junkie_cached__", True)
    except AttributeError:
        raise CanNotBeCachedException(factory)

    return factory


class CanNotBeCachedException(Exception):
    pass
