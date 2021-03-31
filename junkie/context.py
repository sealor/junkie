import inspect
import logging
from collections import OrderedDict
from contextlib import contextmanager, ExitStack
from typing import Union, Callable, Tuple, Mapping, Any

import junkie


class Context:
    def __init__(self, instances_and_factories: Mapping[str, Any] = None):
        self._mapping = instances_and_factories or {}
        self._stack = None

        self.logger = logging.getLogger(junkie.__name__)

    @contextmanager
    def build(self, *names_and_types: Union[str, type, Callable]) -> Union[object, Tuple[object]]:
        with ExitStack() as self._stack:
            if len(names_and_types) == 1:
                self.logger.debug("build(%r)", names_and_types[0])
                yield self._build_element(names_and_types[0])
            else:
                self.logger.debug("build(%r)", names_and_types)
                yield self._build_tuple(*names_and_types)

    def _build_tuple(self, *names_and_types: Union[str, type, Callable]) -> Union[object, Tuple[object]]:
        instances = []

        for name_or_type in names_and_types:
            instance = self._build_element(name_or_type)
            instances.append(instance)

        return tuple(instances)

    def _build_element(self, name_or_type: Union[str, type, Callable]) -> object:
        if isinstance(name_or_type, str):
            return self._build_by_name(name_or_type)

        elif isinstance(name_or_type, (type, Callable)):
            return self._build_by_type(name_or_type, name_or_type.__name__)

        raise RuntimeError("Unknown type '{}' - str, type or Callable expected".format(name_or_type))

    def _build_by_name(self, name: str, default=None) -> object:
        if name in self._mapping:
            value = self._mapping[name]

            if isinstance(value, (type, Callable)):
                return self._build_by_type(value, name)
            else:
                return value

        if default is not None:
            return default

        raise RuntimeError("Not found: " + name)

    def _build_by_type(self, factory_func: Union[type, Callable], instance_name: str) -> object:
        parameters, args, kwargs = self._build_parameters(factory_func)

        self.logger.debug("%s = %s(%s)", instance_name, factory_func.__name__, list(parameters.keys()))
        instance = factory_func(*parameters.values(), *args, **kwargs)

        if hasattr(instance, "__enter__"):
            self.logger.debug("%s.__enter__()", instance_name)
            self._stack.push(lambda *exception_details: self.logger.debug("%s.__exit__()", instance_name))

            instance = self._stack.enter_context(instance)

        return instance

    def _build_parameters(self, factory_func: Union[type, Callable]) -> (OrderedDict, tuple, dict):
        argument_dict = OrderedDict()
        args = ()
        kwargs = {}

        for name, annotation in inspect.signature(factory_func).parameters.items():
            if annotation.kind is inspect.Parameter.VAR_POSITIONAL:
                args = self._build_by_name(name, args)

            elif annotation.kind is inspect.Parameter.VAR_KEYWORD:
                kwargs = self._build_by_name(name, kwargs)

            elif name in self._mapping:
                argument_dict[name] = self._build_by_name(name)

            elif annotation.default is not inspect.Parameter.empty:
                argument_dict[name] = annotation.default

            else:
                raise RuntimeError("Not found: " + name)

        return argument_dict, args, kwargs
