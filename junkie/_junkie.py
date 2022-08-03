import inspect
import logging
from collections import OrderedDict
from contextlib import contextmanager, ExitStack
from typing import Union, Tuple, Mapping, Any, Callable

import junkie


class JunkieError(RuntimeError):
    pass


class Junkie:
    def __init__(self, instances_and_factories: Mapping[str, Any] = None):
        self._mapping = instances_and_factories or {}
        self._exit_stack = None

        self.logger = logging.getLogger(junkie.__name__)

    @contextmanager
    def inject(self, *names_and_factories: Union[str, Callable]) -> Union[Any, Tuple[Any]]:
        with ExitStack() as self._exit_stack:
            if len(names_and_factories) == 1:
                self.logger.debug("inject(%r)", names_and_factories[0])
                yield self._build_instance(names_and_factories[0])
            else:
                self.logger.debug("inject(%r)", names_and_factories)
                yield self._build_tuple(*names_and_factories)

    def _build_tuple(self, *names_and_factories: Union[str, Callable]) -> Tuple[Any]:
        instances = []

        for name_or_factory in names_and_factories:
            instance = self._build_instance(name_or_factory)
            instances.append(instance)

        return tuple(instances)

    def _build_instance(self, name_or_factory: Union[str, Callable]) -> Any:
        if isinstance(name_or_factory, str):
            return self._build_by_instance_name(name_or_factory)

        elif callable(name_or_factory):
            return self._build_by_factory_function(name_or_factory, name_or_factory.__name__)

        raise JunkieError('Unknown type "{}" (str, type or Callable expected)'.format(name_or_factory))

    def _build_by_instance_name(self, instance_name: str, default=None) -> Any:
        if instance_name in self._mapping:
            value = self._mapping[instance_name]

            if callable(value):
                return self._build_by_factory_function(value, instance_name)
            else:
                return value

        if default is not None:
            return default

        raise JunkieError('Unable to find "{}"'.format(instance_name))

    def _build_by_factory_function(self, factory_function: Callable, instance_name: str) -> Any:
        parameters, args, kwargs = self._build_parameters(factory_function)

        self.logger.debug("%s = %s(%s)", instance_name, factory_function.__name__, list(parameters.keys()))
        instance = factory_function(*parameters.values(), *args, **kwargs)

        if hasattr(instance, "__enter__"):
            self.logger.debug("%s.__enter__()", instance_name)
            self._exit_stack.push(lambda *exception_details: self.logger.debug("%s.__exit__()", instance_name))

            instance = self._exit_stack.enter_context(instance)

        return instance

    def _build_parameters(self, factory_function: Callable) -> (OrderedDict, tuple, dict):
        parameters = OrderedDict()
        args = ()
        kwargs = {}

        for instance_name, annotation in inspect.signature(factory_function).parameters.items():
            if annotation.kind is inspect.Parameter.VAR_POSITIONAL:
                args = self._build_by_instance_name(instance_name, args)

            elif annotation.kind is inspect.Parameter.VAR_KEYWORD:
                kwargs = self._build_by_instance_name(instance_name, kwargs)

            elif instance_name in self._mapping:
                parameters[instance_name] = self._build_by_instance_name(instance_name)

            elif annotation.default is not inspect.Parameter.empty:
                parameters[instance_name] = annotation.default

            elif isinstance(annotation.annotation, Callable):
                parameters[instance_name] = self._build_by_factory_function(annotation.annotation, instance_name)

            else:
                raise JunkieError(
                    'Unable to find "{}" for "{}"'.format(instance_name, factory_function.__name__)
                )

        return parameters, args, kwargs
