import sqlite3
import unittest

from junkie import Junkie, JunkieError


class ErrorTest(unittest.TestCase):
    def test_list_class_in_error_message(self):
        class Database:
            def __init__(self, _):
                pass

        class App:
            def __init__(self, database: Database):
                self.database = database

        message = (
            "\n"
            r'-> App\(\) at ".*/test/test_error.py:\d+"' '\n'
            r' -> Database\(\) at ".*/test/test_error.py:\d+"' '\n'
            r'JunkieError: Unable to find "_" for "Database\(\)"'
        )

        with self.assertRaisesRegex(JunkieError, message):
            with Junkie().inject(App):
                pass

    def test_list_function_in_error_message(self):
        def connect_database(_):
            pass

        class App:
            def __init__(self, database: connect_database):
                self.database = database

        message = (
            "\n"
            r'-> App\(\) at ".*/test/test_error.py:\d+"' '\n'
            r' -> connect_database\(\) at ".*/test/test_error.py:\d+"' '\n'
            r'JunkieError: Unable to find "_" for "connect_database\(\)"'
        )

        with self.assertRaisesRegex(JunkieError, message):
            with Junkie().inject(App):
                pass

    def test_list_lambda_in_error_message(self):
        class App:
            def __init__(self, database):
                self.database = database

        context = {
            "database": lambda unknown: unknown
        }

        message = (
            "\n"
            r'-> App\(\) at ".*/test/test_error.py:\d+"' '\n'
            r' -> <lambda>\(\) at ".*/test/test_error.py:\d+"' '\n'
            r'JunkieError: Unable to find "unknown" for "<lambda>\(\)"'
        )

        with self.assertRaisesRegex(JunkieError, message):
            with Junkie(context).inject(App):
                pass

    def test_list_unknown_in_error_message(self):
        class App:
            def __init__(self, database):
                self.database = database

        context = {
            "database": sqlite3.connect
        }

        message = (
            "\n"
            r'-> App\(\) at ".*/test/test_error.py:\d+"' '\n'
            r' -> connect\(\) at unknown source' '\n'
            r'(ValueError|RuntimeError): (no signature found for builtin <built-in function connect>)?'
        )

        with self.assertRaisesRegex(JunkieError, message):
            with Junkie(context).inject(App):
                pass

    def test_detect_dependency_cycle(self):
        class App:
            def __init__(self, app):
                app()

        context = {"app": App}

        with self.assertRaisesRegex(JunkieError, r'.*Dependency cycle detected with "App\(\)"'):
            with Junkie(context).inject(App):
                pass
