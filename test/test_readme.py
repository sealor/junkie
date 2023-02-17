import unittest


class ReadmeTest(unittest.TestCase):
    def test_example(self):
        from junkie import Junkie

        class App:
            def __init__(self, addressee):
                self.addressee = addressee

            def greets(self):
                return f"Hello {self.addressee}!"

        context = {"addressee": "World"}

        with Junkie(context).inject(App) as app:
            assert app.greets() == "Hello World!"

    def test_type_hints(self):
        from junkie import Junkie

        class Database:
            pass

        class App:
            def __init__(self, database: Database):
                self.database = database

        with Junkie().inject(App) as app:
            assert isinstance(app.database, Database)

    def test_integration_test(self):
        from junkie import Junkie

        APPLICATION_CONTEXT = {
            "database_url": "postgresql://scott:tiger@localhost:5432/production",
        }

        class App:
            def __init__(self, database_url):
                self.database_url = database_url

        test_context = {**APPLICATION_CONTEXT, "database_url": "sqlite://"}

        with Junkie(test_context).inject(App) as app:
            self.assertEqual(app.database_url, "sqlite://")

    def test_reuse(self):
        from junkie import Junkie

        class App:
            pass

        context = {
            "app": App,
        }

        with Junkie(context).inject("app", App, "app") as (app1, app2, app3):
            assert app1 == app3
            assert app1 != app2 != app3

    def test_lambdas(self):
        from junkie import Junkie

        class App:
            def __init__(self, greeting: str):
                self.greeting = greeting

        context = {
            # app1
            "app1": lambda: App("Hello Joe!"),
            # app2
            "greeting2": "Hello John!",
            "app2": lambda greeting2: App(greeting2),
            # app3
            "greeting3": lambda: "Hello Doe!",
            "app3": lambda greeting3: App(greeting3),
        }

        with Junkie(context).inject("app1", "app2", "app3") as (app1, app2, app3):
            assert app1.greeting == "Hello Joe!"
            assert app2.greeting == "Hello John!"
            assert app3.greeting == "Hello Doe!"

    def test_junkie_argument(self):
        from contextlib import contextmanager

        from junkie import Junkie

        class SqlDatabase:
            pass

        class FileDatabase:
            pass

        class App:
            def __init__(self, database):
                self.database = database

        @contextmanager
        def provide_database(_junkie, url: str):
            if url.startswith("file:"):
                with _junkie.inject(FileDatabase) as database:
                    yield database
            else:
                with _junkie.inject(SqlDatabase) as database:
                    yield database

        context = {
            "url": "file://local.db",
            "database": provide_database,
        }

        with Junkie(context).inject(App) as app:
            assert isinstance(app.database, FileDatabase)

    def test_inject_list(self):
        from junkie import Junkie, inject_list

        class CustomerDataSource:
            def __init__(self, connection_string: str):
                pass

        class ProductDataSource:
            pass

        class SupplierDataSource:
            pass

        class App:
            def __init__(self, data_sources):
                self.data_sources = data_sources

        context = {
            "customer_ds": lambda: CustomerDataSource("sqlite://"),
            "data_sources": inject_list("customer_ds", ProductDataSource, SupplierDataSource),
        }

        with Junkie(context).inject(App) as app:
            assert isinstance(app.data_sources[0], CustomerDataSource)
            assert isinstance(app.data_sources[1], ProductDataSource)
            assert isinstance(app.data_sources[2], SupplierDataSource)

    def test_pre_defined_callable(self):
        from junkie import Junkie

        class Database:
            def __call__(self, *args, **kwargs):
                return "called"

        class App:
            def __init__(self, database):
                self.database = database

        context = {
            "database": lambda: Database(),
        }

        with Junkie(context).inject(App) as app:
            assert app.database() == "called"

    def test_lambda_for_builtins(self):
        import sqlite3

        from junkie import Junkie, JunkieError

        context = {
            "database": ":memory:",
            "connection": sqlite3.connect,
            "working_connection": lambda database: sqlite3.connect(database)
        }

        try:
            # ValueError: no signature found for builtin <built-in function connect>
            with Junkie(context).inject("connection") as connection:
                pass
            assert False
        except JunkieError:
            pass

        with Junkie(context).inject("working_connection") as working_connection:
            pass
