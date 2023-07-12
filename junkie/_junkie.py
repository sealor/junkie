import builtins
import inspect
import logging
from collections import OrderedDict
from contextlib import contextmanager, ExitStack
from typing import Union, Tuple, Mapping, Any, Callable, Optional, Iterator

import junkie

LOGGER = logging.getLogger(junkie.__name__)
BUILTINS = {item for item in vars(builtins).values() if isinstance(item, type)}


def get_factory_name(factory: Callable) -> str:
    return getattr(factory, "__name__", str(factory))


class JunkieError(RuntimeError):
    pass


class Junkie(Mapping[str, Any]):
    def __init__(self, instances_and_factories: Mapping[str, Any] = None):
        self._context = instances_and_factories or {}
        self._exit_stack: Optional[ExitStack] = None

        self._instances_by_name: dict = {}
        self._instances_by_name_stack: Junkie._Stack = Junkie._Stack()
        self._instances_by_name_stack.push(self._instances_by_name)

        self._instantiation_stack: Junkie._InstantiationStack = Junkie._InstantiationStack()
        self._cycle_detection_instance_set = set()

        self._context["_junkie"] = self

    def __getitem__(self, item):
        return self._instances_by_name[item]

    def __len__(self) -> int:
        return self._instances_by_name.__len__()

    def __iter__(self) -> Iterator:
        return self._instances_by_name.__iter__()

    def __contains__(self, item) -> bool:
        return self._instances_by_name.__contains__(item)

    def extend(self, instances: Mapping[str, Any]) -> "Junkie":
        if not instances.keys().isdisjoint(self._instances_by_name.keys() | self._context.keys()):
            duplicated_names = set(instances.keys()).intersection(self._instances_by_name.keys() | self._context.keys())
            raise JunkieError(f"Instances for names {duplicated_names} already exists")

        return Junkie({**self, **instances})

    @contextmanager
    def inject(self, *names_and_factories: Union[str, Callable]) -> Union[Any, Tuple[Any]]:
        LOGGER.debug("inject(%s)", Junkie._LogParams(*names_and_factories))

        with ExitStack() as self._exit_stack:
            self._instances_by_name = self._instances_by_name_stack.peek().copy()
            self._instances_by_name_stack.push(self._instances_by_name)

            if len(names_and_factories) == 1:
                yield self._build_instance(names_and_factories[0])
            else:
                yield self._build_tuple(*names_and_factories)

            self._instances_by_name_stack.pop()
            self._instances_by_name = self._instances_by_name_stack.peek()

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

        raise JunkieError(
            f"{self._instantiation_stack}" + f'Unknown type "{name_or_factory}" (str, type or Callable expected)'
        )

    def _build_by_instance_name(self, instance_name: str) -> Any:
        if instance_name in self._instances_by_name:
            return self._instances_by_name[instance_name]

        if instance_name in self._context:
            value = self._context[instance_name]

            if callable(value):
                return self._build_by_factory_function(value, instance_name)
            else:
                return value

        raise JunkieError(f"{self._instantiation_stack}" + f'Unable to find "{instance_name}"')

    def _build_by_factory_function(self, factory_function: Callable, instance_name: Union[str, None]) -> Any:
        if factory_function in BUILTINS:
            raise JunkieError(
                f"{self._instantiation_stack}"
                + f'Mapping for "{instance_name}" of builtin type "{get_factory_name(factory_function)}" is missing'
            )

        if factory_function in self._cycle_detection_instance_set:
            raise JunkieError(
                f"{self._instantiation_stack}"
                + f'Dependency cycle detected with "{get_factory_name(factory_function)}()"'
            )

        self._cycle_detection_instance_set.add(factory_function)
        self._instantiation_stack.push(factory_function)

        positional_params, args, keyword_params, kwargs = self._build_parameters(factory_function)

        if LOGGER.isEnabledFor(logging.DEBUG):
            log_params = Junkie._LogParams(*positional_params.keys(), *args, **keyword_params, **kwargs)
            LOGGER.debug("%s = %s(%s)", instance_name or "_", get_factory_name(factory_function), log_params)

        instance = factory_function(*positional_params.values(), *args, **keyword_params, **kwargs)

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
        positional_params = OrderedDict()
        args = ()
        keyword_params = OrderedDict()
        kwargs = {}
        positional_params_finished = False

        try:
            signature = inspect.signature(factory_function)
        except Exception as e:
            raise JunkieError(
                f"{self._instantiation_stack}"
                + f'Unable to inspect signature for "{get_factory_name(factory_function)}()"'
            ) from e

        for instance_name, annotation in signature.parameters.items():
            if instance_name in self._instances_by_name or instance_name in self._context:
                value = self._build_by_instance_name(instance_name)

            # *args
            elif annotation.kind is inspect.Parameter.VAR_POSITIONAL:
                continue

            # **kwargs
            elif annotation.kind is inspect.Parameter.VAR_KEYWORD:
                continue

            # arg="value"
            elif annotation.default is not inspect.Parameter.empty:
                positional_params_finished = True
                continue

            elif isinstance(annotation.annotation, Callable) and annotation.annotation != inspect.Parameter.empty:
                value = self._build_by_factory_function(annotation.annotation, instance_name)

            else:
                raise JunkieError(
                    f"{self._instantiation_stack}"
                    + f'Unable to find "{instance_name}" for "{get_factory_name(factory_function)}()"'
                )

            if annotation.kind is inspect.Parameter.POSITIONAL_ONLY:
                positional_params[instance_name] = value

            elif annotation.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD:
                if positional_params_finished:
                    keyword_params[instance_name] = value
                else:
                    positional_params[instance_name] = value

            elif annotation.kind is inspect.Parameter.VAR_POSITIONAL:
                args = value

            elif annotation.kind is inspect.Parameter.KEYWORD_ONLY:
                keyword_params[instance_name] = value

            elif annotation.kind is inspect.Parameter.VAR_KEYWORD:
                kwargs = value

            else:
                raise NotImplementedError(f'Unknown parameter type "{annotation.kind}"')

        return positional_params, args, keyword_params, kwargs

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
            if len(self._stack) == 0:
                return ""

            return "".join([
                f'\n{idx * " "}-> {get_factory_name(factory)}() at {self._get_source_info(factory)}'
                for idx, factory in enumerate(self._stack)
            ]) + "\n"

        @staticmethod
        def _get_source_info(factory: Callable) -> str:
            while hasattr(factory, "__wrapped__"):
                factory = factory.__wrapped__
            try:
                return f'"{inspect.getsourcefile(factory)}:{inspect.getsourcelines(factory)[1]}"'
            except:
                return "unknown source"


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
