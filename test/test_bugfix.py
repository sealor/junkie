import unittest

from junkie import Junkie, JunkieError


class BugfixTest(unittest.TestCase):
    def test_error_on_missing_mapping(self):
        class App:
            def __init__(self, _):
                pass

        with self.assertRaises(JunkieError):
            with Junkie().inject(App):
                pass
