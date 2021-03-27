import unittest

from junkie import DependencyCycleError
from junkie.dependency_cycle_checker import DependencyCycleChecker


class DependencyCycleCheckerTest(unittest.TestCase):
    def test_pop_raises_error_on_empty_instance_stack(self):
        with self.assertRaisesRegex(IndexError, "pop from an empty stack"):
            DependencyCycleChecker().pop()

    def test_push_and_pop(self):
        checker = DependencyCycleChecker()
        checker.push("a")
        item = checker.pop()

        self.assertEqual("a", item)

    def test_detect_cycle(self):
        checker = DependencyCycleChecker()
        checker.push("a")
        checker.push("b")
        checker.push("c")

        with self.assertRaises(DependencyCycleError):
            checker.push("a")
