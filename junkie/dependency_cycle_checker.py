from collections import OrderedDict


class DependencyCycleError(RuntimeError):
    pass


class DependencyCycleChecker:
    def __init__(self):
        self._instance_stack = OrderedDict()

    def push(self, instance_name: str) -> None:
        if instance_name in self._instance_stack:
            call_path = list(self._instance_stack.keys())
            call_path.append(instance_name)

            cycle_message = ""
            for number, name in enumerate(call_path):
                cycle_message += "\n{indentation}-> {name}".format(indentation="  " * number, name=name)

            raise DependencyCycleError("dependency cycle detected!" + cycle_message)

        self._instance_stack[instance_name] = None

    def pop(self) -> str:
        if len(self._instance_stack) == 0:
            raise IndexError("pop from an empty stack")

        return self._instance_stack.popitem()[0]
