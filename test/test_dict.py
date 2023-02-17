import unittest

from junkie import Junkie


class DictTest(unittest.TestCase):
    def test_getitem(self):
        class App:
            pass

        context = {
            "app": App
        }

        with Junkie(context).inject("app", "_junkie") as (app, junkie):
            self.assertEqual(app, junkie["app"])

    def test_raise_error_on_missing_item(self):
        with self.assertRaisesRegex(KeyError, "'missing'"):
            _ = Junkie()["missing"]

    def test_contains(self):
        class App:
            pass

        context = {
            "app": App
        }

        with Junkie(context).inject("app", "_junkie") as (app, junkie):
            self.assertIn("app", junkie)

    def test_iter(self):
        class App:
            pass

        context = {
            "app": App
        }

        with Junkie(context).inject("app", "_junkie") as (app, junkie):
            self.assertEqual({"app": junkie["app"]}, dict(junkie))
