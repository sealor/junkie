from contextlib import contextmanager
from typing import Union, Dict, Callable, Set, List

from junkie.core_context import CoreContext


class Context(CoreContext):
    def __init__(self, *singletons_and_factories: Union[Dict[str, object], Dict[str, Callable]]):
        super().__init__()

        self.add(*singletons_and_factories)

    def add(self, *singletons_and_factories: Union[Dict[str, object], Dict[str, Callable]]):
        for singletons_and_factories_element in singletons_and_factories:
            for key, value in singletons_and_factories_element.items():
                if callable(value):
                    self._factories[key] = value
                else:
                    self._singletons[key] = value

    @contextmanager
    def build(self, instances: Union[Set[str], List[str], type, str]):
        if isinstance(instances, set) or isinstance(instances, list):
            with self.build_dict(instances) as instance_dict:
                yield instance_dict

        elif isinstance(instances, str):
            with self.build_object_by_name(instances) as instance_object:
                yield instance_object

        elif isinstance(instances, type):
            with self.build_object_by_type(instances) as instance_object:
                yield instance_object

        else:
            raise Exception("Type not known (set, list, str or type/class expected): {}".format(type(instances)))
