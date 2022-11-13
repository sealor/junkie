import unittest

from junkie import Junkie, JunkieError


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

    def test_setitem(self):
        junkie = Junkie()
        junkie["string"] = "my string"
        with junkie.inject("string") as string:
            self.assertEqual("my string", string)

    def test_setitem_for_current_scope_only(self):
        junkie = Junkie()
        with junkie.inject():
            junkie["number"] = 7

            with junkie.inject("number") as number:
                self.assertEqual(7, number)

        self.assertNotIn("number", junkie)

    def test_raise_error_on_setitem_when_overriding(self):
        class App:
            def __init__(self, database):
                self.database = database

        context = {
            "database": "sqlite://"
        }

        with Junkie(context).inject(App, "_junkie") as (app, junkie):
            with self.assertRaisesRegex(JunkieError, '^Instance for "database" already exists in context$'):
                junkie["database"] = "postgres://"

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
