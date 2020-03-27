from contextlib import contextmanager
from typing import Union, Dict, Callable, Set, List, Tuple

from junkie.core_context import CoreContext


class Context(CoreContext):
    def __init__(self, *instances_and_factories_args: Union[Dict[str, object], Dict[str, Callable]]):
        super().__init__()

        self.add(*instances_and_factories_args)

    def add(self, *instances_and_factories_args: Union[Dict[str, object], Dict[str, Callable]]):
        for instances_and_factories in instances_and_factories_args:
            for key, value in instances_and_factories.items():
                if callable(value):
                    self._factories[key] = value
                else:
                    self._instances[key] = value

    @contextmanager
    def build(self, names_or_type: Union[Set[str], List[str], Tuple[str, ...], str, type]):
        if isinstance(names_or_type, (set, list)):
            with self.build_dict(names_or_type) as instance_dict:
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
