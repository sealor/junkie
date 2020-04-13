from contextlib import contextmanager
from typing import Set, List
from typing import Union, Dict, Callable, Tuple, overload

from junkie.core_context import CoreContext


class Context(CoreContext):
    def __init__(self, *instances_and_factories_args: Union[Dict[str, object], Dict[str, Callable], None]):
        super().__init__()

        self.add(*instances_and_factories_args)

    def add(self, *instances_and_factories_args: Union[Dict[str, object], Dict[str, Callable], None]):
        for instances_and_factories in instances_and_factories_args:
            if instances_and_factories is None:
                continue

            for key, value in instances_and_factories.items():
                if callable(value):
                    self._factories[key] = value
                else:
                    self._instances[key] = value

    @contextmanager
    def build_instances(self, names_or_type: Union[Set[str], List[str], Tuple[str, ...], str, type]):
        if isinstance(names_or_type, (set, list)):
            with self.build_instance_dict(names_or_type) as instance_dict:
                yield instance_dict

        elif isinstance(names_or_type, tuple):
            with self.build_instance_by_names(names_or_type) as instance:
                yield instance

        elif isinstance(names_or_type, str):
            with self.build_instance_by_name(names_or_type) as instance:
                yield instance

        elif isinstance(names_or_type, type):
            with self.build_instance_by_type(names_or_type) as instance:
                yield instance

        else:
            raise Exception("Type not known (set, list, str or type/class expected): {}".format(type(names_or_type)))

    @overload
    def build(self, target: Union[str, type, Callable]) -> object:
        pass

    @overload
    def build(self, target_tuple: Tuple[Union[str, type, Callable], ...]) -> Tuple[object]:
        pass

    @overload
    def build(self, *target_args: Union[str, type, Callable]) -> Tuple[object]:
        pass

    @overload
    def build(self, target_dict: Dict[str, Union[str, type, Callable]]) -> Dict[str, object]:
        pass

    @overload
    def build(self, **target_kwargs: Union[str, type, Callable]) -> Dict[str, object]:
        pass

    def build(self, *args, **kwargs):
        if len(args) > 0 and len(kwargs) > 0:
            raise Exception("Combining args and kwargs is not allowed")

        if len(args) == 0 and len(kwargs) == 0:
            raise Exception("Parameter is missing")

        if len(args) > 0:
            return self._build_with_args(args)

        if len(kwargs) > 0:
            return self._build_with_kwargs(kwargs)

    def _build_with_args(self, target_args):
        if len(target_args) > 1:
            return self.build_tuple(target_args)

        target = target_args[0]

        if isinstance(target, dict):
            return self.build_dict(target)

        if isinstance(target, tuple):
            return self.build_tuple(target)

        return self.build_element(target)

    def _build_with_kwargs(self, target_dict):
        return self.build_dict(target_dict)
