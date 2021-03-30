import inspect
import logging
from collections import OrderedDict
from contextlib import contextmanager, ExitStack
from typing import Union, Callable, Tuple, Mapping, Any

import junkie


class Context:
    def __init__(self, instances_and_factories: Mapping[str, Any] = None):
        self.logger = logging.getLogger(junkie.__name__)

        self._mapping = dict(instances_and_factories or {})
        self._stack = None

    @contextmanager
    def build(self, *names_and_types: Union[str, type, Callable]) -> Union[object, Tuple[object]]:
        with ExitStack() as self._stack:
            if len(names_and_types) == 1:
                yield self._build_element(names_and_types[0])
            else:
                yield self._build_tuple(names_and_types)

    def _build_element(self, target: Union[str, type, Callable]):
        self.logger.debug("build(%r)", target)

        if isinstance(target, str):
            return self._build_element_by_name(target)

        if isinstance(target, (type, Callable)):
            return self._build_element_by_type(target)

        raise Exception("Not found: {}".format(target))

    def _build_element_by_name(self, target_name: str) -> object:
        if target_name in self._mapping:
            target = self._mapping[target_name]

            if isinstance(target, (type, Callable)):
                return self._call(target, target_name)
            else:
                return target

        raise Exception("Not found: {}".format(target_name))

    def _build_element_by_type(self, target_factory: Union[type, Callable]) -> object:
        return self._call(target_factory, target_factory.__name__)

    def _build_tuple(self, target_tuple: Tuple[Union[str, type, Callable], ...]) -> Tuple[object]:
        self.logger.debug("build(%r)", target_tuple)

        instances = []

        for target in target_tuple:
            instance = self._build_element(target)
            instances.append(instance)

        return tuple(instances)

    def _call(self, factory_func: Callable, instance_name: str):
        argument_dict, args, kwargs = self._resolve_factory_arguments(factory_func)

        self.logger.debug("%s = %s(%s)", instance_name, factory_func.__name__, list(argument_dict.keys()))
        instance = factory_func(*argument_dict.values(), *args, **kwargs)

        if hasattr(instance, "__enter__"):
            self.logger.debug("%s.__enter__()", instance_name)
            self._stack.push(lambda *exception_details: self.logger.debug("%s.__exit__()", instance_name))

            instance = self._stack.enter_context(instance)

        return instance

    def _resolve_factory_arguments(self, factory_func):
        argument_dict = OrderedDict()
        args = ()
        kwargs = {}

        for name, annotation in inspect.signature(factory_func).parameters.items():
            if annotation.kind is inspect.Parameter.VAR_POSITIONAL:
                if name in self._mapping:
                    target = self._mapping[name]

                    if isinstance(target, (type, Callable)):
                        args = self._call(target, name)
                    else:
                        args = target

            elif annotation.kind is inspect.Parameter.VAR_KEYWORD:
                if name in self._mapping:
                    target = self._mapping[name]

                    if isinstance(target, (type, Callable)):
                        kwargs = self._call(target, name)
                    else:
                        kwargs = target

            elif name in self._mapping:
                target = self._mapping[name]

                if isinstance(target, (type, Callable)):
                    argument_dict[name] = self._call(target, name)
                else:
                    argument_dict[name] = target

            elif annotation.default is not inspect.Parameter.empty:
                argument_dict[name] = annotation.default

            else:
                raise Exception("Not found: " + name)

        return argument_dict, args, kwargs
