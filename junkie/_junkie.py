import builtins
import inspect
import logging
from collections import OrderedDict
from contextlib import contextmanager, ExitStack
from typing import Union, Tuple, Mapping, Any, Callable, Optional

import junkie

LOGGER = logging.getLogger(junkie.__name__)
BUILTINS = {item for item in vars(builtins).values() if isinstance(item, type)}


def get_factory_name(factory: Callable) -> str:
    return getattr(factory, "__name__", str(factory))


class JunkieError(RuntimeError):
    pass


class Junkie:
    def __init__(self, instances_and_factories: Mapping[str, Any] = None):
        self._mapping = instances_and_factories or {}
        self._exit_stack: Optional[ExitStack] = None

        self._instances_by_name: dict = {}
        self._instances_by_name_stack: Junkie._Stack = Junkie._Stack()
        self._instances_by_name_stack.push(self._instances_by_name)

        self._instantiation_stack: Junkie._InstantiationStack = Junkie._InstantiationStack()
        self._cycle_detection_instance_set = set()

        self._mapping["_junkie"] = self

    @contextmanager
    def inject(self, *names_and_factories: Union[str, Callable]) -> Union[Any, Tuple[Any]]:
        LOGGER.debug("inject(%s)", Junkie._LogParams(*names_and_factories))

        with ExitStack() as self._exit_stack:
            self._instances_by_name = self._instances_by_name_stack.peek().copy()
            self._instances_by_name_stack.push(self._instances_by_name)

            with self._prepend_instantiation_stack_on_error():
                if len(names_and_factories) == 1:
                    yield self._build_instance(names_and_factories[0])
                else:
                    yield self._build_tuple(*names_and_factories)

            self._instances_by_name_stack.pop()

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
            return self._build_by_factory_function(name_or_factory, None)

        raise JunkieError('Unknown type "{}" (str, type or Callable expected)'.format(name_or_factory))

    def _build_by_instance_name(self, instance_name: str, default=None) -> Any:
        if instance_name in self._instances_by_name:
            return self._instances_by_name[instance_name]

        if instance_name in self._mapping:
            value = self._mapping[instance_name]

            if callable(value):
                return self._build_by_factory_function(value, instance_name)
            else:
                return value

        if default is not None:
            return default

        raise JunkieError('Unable to find "{}"'.format(instance_name))

    def _build_by_factory_function(self, factory_function: Callable, instance_name: Union[str, None]) -> Any:
        if factory_function in BUILTINS:
            raise JunkieError(
                'Mapping for "{}" of builtin type "{}" is missing'.format(
                    instance_name, get_factory_name(factory_function)))

        if factory_function in self._cycle_detection_instance_set:
            raise JunkieError(f'Dependency cycle detected with "{get_factory_name(factory_function)}()"')

        self._cycle_detection_instance_set.add(factory_function)
        self._instantiation_stack.push(factory_function)

        parameters, args, kwargs = self._build_parameters(factory_function)

        if LOGGER.isEnabledFor(logging.DEBUG):
            log_params = Junkie._LogParams(*parameters.keys(), *args, **kwargs)
            LOGGER.debug("%s = %s(%s)", instance_name or "_", get_factory_name(factory_function), log_params)

        instance = factory_function(*parameters.values(), *args, **kwargs)

        if hasattr(instance, "__enter__"):
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug("%s.__enter__()", instance_name or "_")
                self._exit_stack.push(lambda *exception_details: LOGGER.debug("%s.__exit__()", instance_name or "_"))

            instance = self._exit_stack.enter_context(instance)

        if instance_name is not None:
            self._instances_by_name[instance_name] = instance

        self._instantiation_stack.pop()
        self._cycle_detection_instance_set.remove(factory_function)

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

            elif instance_name in self._instances_by_name:
                parameters[instance_name] = self._instances_by_name[instance_name]

            elif instance_name in self._mapping:
                parameters[instance_name] = self._build_by_instance_name(instance_name)

            elif annotation.default is not inspect.Parameter.empty:
                parameters[instance_name] = annotation.default

            elif isinstance(annotation.annotation, Callable) and annotation.annotation != inspect.Parameter.empty:
                parameters[instance_name] = self._build_by_factory_function(annotation.annotation, instance_name)

            else:
                raise JunkieError(
                    'Unable to find "{}" for "{}()"'.format(instance_name, get_factory_name(factory_function))
                )

        return parameters, args, kwargs

    class _LogParams:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def __str__(self):
            arg_params = list(map(str, self.args))
            kwarg_params = list(map(str, [f"{key}={repr(value)}" for key, value in self.kwargs.items()]))
            return ", ".join(arg_params + kwarg_params)

    class _Stack:
        def __init__(self):
            self._stack = []

        def push(self, item):
            self._stack.append(item)

        def pop(self):
            return self._stack.pop()

        def peek(self):
            return self._stack[-1]

        def __len__(self):
            return self._stack.__len__()

    class _InstantiationStack(_Stack):
        def __str__(self):
            return "".join([
                f'\n{idx * " "}-> {get_factory_name(factory)}() at {self._get_source_info(factory)}'
                for idx, factory in enumerate(self._stack)
            ])

        @staticmethod
        def _get_source_info(factory: Callable) -> str:
            try:
                return f'"{inspect.getsourcefile(factory)}:{inspect.getsourcelines(factory)[1]}"'
            except:
                return "unknown source"

    @contextmanager
    def _prepend_instantiation_stack_on_error(self):
        try:
            yield
        except Exception as e:
            if len(self._instantiation_stack) == 0:
                raise e

            raise JunkieError(f"{self._instantiation_stack}\n{type(e).__name__}: {str(e)}")


def inject_list(*factories_or_names):
    """Can be used within the context to let junkie create a list of instances from a list of factories or names"""

    @contextmanager
    def wrapper(_junkie: Junkie):
        with _junkie.inject(*factories_or_names) as instances:
            if isinstance(instances, tuple):
                yield list(instances)
            else:
                yield [instances]

    return wrapper
