import logging
import unittest
from unittest.mock import Mock

from junkie import Junkie, JunkieError


class BugfixTest(unittest.TestCase):
    def test_error_on_missing_mapping(self):
        class App:
            def __init__(self, _):
                pass

        with self.assertRaises(JunkieError):
            with Junkie().inject(App):
                pass

    def test_no_error_for_callable_without_name(self):
        context = {
            "mock": Mock()
        }
        with self.assertLogs(level=logging.DEBUG) as log:
            with Junkie(context).inject("mock"):
                pass

        self.assertRegex(str(log.output), r"DEBUG:junkie:mock = <Mock id='\d+'>\(\)")

    def test_dependency_cycle_check_after_exception(self):
        def faulty_handler():
            raise ValueError()

        my_junkie = Junkie()

        with self.assertRaises(ValueError):
            with my_junkie.inject(faulty_handler):
                pass

        with self.assertRaises(ValueError):
            with my_junkie.inject(faulty_handler):
                pass
