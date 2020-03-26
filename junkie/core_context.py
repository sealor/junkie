import inspect
import logging
from collections import OrderedDict
from contextlib import contextmanager, ExitStack
from typing import Union, Set, List, Dict, Callable, Tuple

import junkie


class CoreContext:
    def __init__(self):
        self.logger = logging.getLogger(junkie.__name__)

        self._instances = {}
        self._factories = {}

    def add_instances(self, instances: Dict[str, object]):
        self._instances.update(instances)

    def add_factories(self, factories: Dict[str, Callable]):
        self._factories.update(factories)

    @contextmanager
    def build_dict(self, names: Union[Set[str], List[str]]) -> Dict[str, object]:
        self.logger.debug("build(%s)", names)

        with ExitStack() as stack:
            instance_dict = {}

            for name in names:
                instance_dict[name] = self._build_instance_by_name(name, stack)

            yield instance_dict

    @contextmanager
    def build_instance_by_names(self, names: Tuple[str, ...]) -> Tuple[object]:
        self.logger.debug("build(%s)", names)

        with ExitStack() as stack:
            instances = []

            for name in names:
                instance = self._build_instance_by_name(name, stack)
                instances.append(instance)

            yield tuple(instances)

    @contextmanager
    def build_instance_by_name(self, name: str) -> object:
        self.logger.debug("build('%s')", name)

        with ExitStack() as stack:
            yield self._build_instance_by_name(name, stack)

    def _build_instance_by_name(self, name: str, stack: ExitStack):
        if name in self._instances:
            return self._instances[name]

        if name in self._factories:
            return self._call(self._factories[name], stack, name)

        raise Exception("Not found: {}".format(name))

    @contextmanager
    def build_instance_by_type(self, constructor: type) -> object:
        self.logger.debug("build(%s)", constructor.__name__)

        with ExitStack() as stack:
            yield self._call(constructor, stack, constructor.__name__)

    def _call(self, factory_func: Callable, stack: ExitStack, instance_name: str):
        args = OrderedDict()

        for name, annotation in inspect.signature(factory_func).parameters.items():
            if name in self._instances:
                arg = self._instances[name]

            elif name in self._factories:
                arg = self._call(self._factories[name], stack, name)

            elif annotation.default is not inspect.Parameter.empty:
                continue

            else:
                raise Exception("Not found: " + name)

            args[name] = arg

        self.logger.debug("%s = %s(%s)", instance_name, factory_func.__name__, list(args.keys()))
        instance = factory_func(**args)

        if hasattr(instance, "__enter__"):
            self.logger.debug("%s.__enter__()", instance_name)
            stack.push(lambda *exception_details: self.logger.debug("%s.__exit__()", instance_name))

            instance = stack.enter_context(instance)

        return instance
