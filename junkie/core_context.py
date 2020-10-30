import inspect
import logging
from collections import OrderedDict
from contextlib import contextmanager, ExitStack
from typing import Union, Dict, Callable, Tuple, overload

import junkie


class CoreContext:
    def __init__(self):
        self.logger = logging.getLogger(junkie.__name__)

        self._instances = {}
        self._factories = {}

        self._stack = None

    def add_instances(self, instances: Dict[str, object]):
        self._instances.update(instances)

    def add_factories(self, factories: Dict[str, Callable]):
        self._factories.update(factories)

    @contextmanager
    def build_element(self, target: Union[str, type, Callable]) -> object:
        assert isinstance(target, (str, type, Callable))

        with ExitStack() as self._stack:
            self.logger.debug("build_element(%r)", target)
            yield self._build_element(target)

    def _build_element(self, target: Union[str, type, Callable]):
        if isinstance(target, str):
            return self._build_element_by_name(target)

        if isinstance(target, (type, Callable)):
            return self._build_element_by_type(target)

        raise Exception("Not found: {}".format(target))

    def _build_element_by_name(self, target_name: str) -> object:
        if target_name in self._instances:
            return self._instances[target_name]

        if target_name in self._factories:
            return self._call(self._factories[target_name], target_name)

        raise Exception("Not found: {}".format(target_name))

    def _build_element_by_type(self, target_factory: Union[type, Callable]) -> object:
        return self._call(target_factory, target_factory.__name__)

    @overload
    def build_tuple(self, target_tuple: Tuple[Union[str, type, Callable], ...]) -> Tuple[object]:
        pass

    @overload
    def build_tuple(self, *target_args: Union[str, type, Callable]) -> Tuple[object]:
        pass

    @contextmanager
    def build_tuple(self, *args):
        with ExitStack() as self._stack:
            if len(args) == 1 and isinstance(args[0], tuple):
                target_tuple = args[0]
            else:
                target_tuple = args

            self.logger.debug("build_tuple(%r)", target_tuple)
            yield self._build_tuple(target_tuple)

    def _build_tuple(self, target_tuple: Tuple[Union[str, type, Callable], ...]) -> Tuple[object]:
        instances = []

        for target in target_tuple:
            instance = self._build_element(target)
            instances.append(instance)

        return tuple(instances)

    @overload
    def build_dict(self, target_dict: Dict[str, Union[str, type, Callable]]) -> Dict[str, object]:
        pass

    @overload
    def build_dict(self, **target_kwargs: Union[str, type, Callable]) -> Dict[str, object]:
        pass

    @contextmanager
    def build_dict(self, *args, **kwargs):
        with ExitStack() as self._stack:
            if len(args) == 1 and isinstance(args[0], dict):
                target_dict = args[0]
            else:
                target_dict = kwargs

            self.logger.debug("build_dict(%r)", target_dict)
            yield self._build_dict(target_dict)

    def _build_dict(self, target_dict: Dict[str, Union[str, type, Callable]]) -> Dict[str, object]:
        instance_dict = {}

        for name, target in target_dict.items():
            instance_dict[name] = self._build_element(target)

        return instance_dict

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
                if name in self._instances:
                    args = self._instances[name]
                elif name in self._factories:
                    args = self._call(self._factories[name], name)

            elif annotation.kind is inspect.Parameter.VAR_KEYWORD:
                if name in self._instances:
                    kwargs = self._instances[name]
                elif name in self._factories:
                    kwargs = self._call(self._factories[name], name)

            elif name in self._instances:
                argument_dict[name] = self._instances[name]

            elif name in self._factories:
                argument_dict[name] = self._call(self._factories[name], name)

            elif annotation.default is not inspect.Parameter.empty:
                argument_dict[name] = annotation.default

            else:
                raise Exception("Not found: " + name)

        return argument_dict, args, kwargs
