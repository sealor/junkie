import unittest
from contextlib import contextmanager
from functools import wraps

from junkie import Context


class CacheTest(unittest.TestCase):
    def test_cached_instance(self):
        def create_object(arg):
            assert arg == "hello"
            return object()

        context = Context({
            "arg": "hello",
            "cached": cache(create_object)
        })

        with context.build_element("cached") as object1:
            with context.build_element("cached") as object2:
                self.assertIs(object1, object2)

    def test_cached_instance_from_context_manager(self):
        @contextmanager
        def create_object(arg):
            assert arg == "hello"
            yield object()

        context = Context({
            "arg": "hello",
            "cached": cache(create_object)
        })

        with context.build_element("cached") as object1:
            with context.build_element("cached") as object2:
                self.assertIs(object1, object2)

    # Failure
    # Exception: <object object at 0x7f688f068b10> is not <object object at 0x7f688f068af0>
    # problem:
    # - cache() does only work within the with-statement where the instance is needed - not overall
    # - it is hard to reason about the scope of the cache
    def test_cache_with_sequential_builds(self):
        context = Context({
            "other_object": "abc",
            "cached": cache(object)
        })

        with context.build("other_object"):
            with context.build("other_object"):
                with context.build("cached") as object1:
                    pass
            with context.build("cached") as object2:
                pass

            self.assertIs(object1, object2)


def cache(factory):
    cache_instance = None

    @contextmanager
    @wraps(factory)
    def factory_func(*args, **kwargs):
        nonlocal cache_instance

        if cache_instance:
            yield cache_instance
        else:
            with create_cache_instance(*args, **kwargs) as cache_instance:
                yield cache_instance
                cache_instance = None

    @contextmanager
    def create_cache_instance(*args, **kwargs):
        factory_instance = factory(*args, **kwargs)
        if hasattr(factory_instance, "__enter__"):
            with factory_instance as context_instance:
                yield context_instance
        else:
            yield factory_instance

    return factory_func
