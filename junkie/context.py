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

    @overload
    def build(self, element: Union[str, type, Callable]) -> object:
        pass

    @overload
    def build(self, *args: Union[str, type, Callable]) -> Tuple[object]:
        pass

    def build(self, *args):
        if len(args) == 1:
            return self.build_element(*args)
        else:
            return self.build_tuple(*args)
