# Junkie

Junkie is a Dependency Injection library for beginners and professionals.

Installation: `pip install junkie`

Example:

```python
from junkie import Junkie


class App:
    def __init__(self, addressee):
        self.addressee = addressee

    def greets(self):
        return f"Hello {self.addressee}!"


context = {"addressee": "World"}

with Junkie(context).inject(App) as app:
    assert app.greets() == "Hello World!"
```

## What is Dependency Injection, and why should we use it?

Dependency Injection is a design pattern in which all dependent objects are created separately and handed over from
outside into the actual object. An object B depends on A if A calls a method of B.
Don't worry - it sounds more complicated than it really is.

Example:  
In traditional source code, object A creates B in the constructor or a method. That means it is hard to reuse B in other
objects because the reference of B is only known by A. When using Dependency Injection, an independent software
component creates B separately and hands it over to all objects which need it. This amazing software component is
`Junkie`!

Finally, Dependency Injection helps you to implement highly decoupled and testable code.

## How does Junkie work?

```python
from junkie import Junkie
```

Before using Junkie you need to prepare the so-called `context`. This context is a Python dictionary, describing how
objects get created or which pre-defined values to use. Every dictionary key represents an argument name.
The corresponding value defines the constructor or function which assembles the requested object. A dictionary value can
also provide a primitive value or a non-callable object.

Junkie also takes Python type hints into account. They are used if no mapping in the context for the argument name
exists.

Additionally, Python lambdas can be used to adjust object construction.

```python
from http.server import HTTPServer, SimpleHTTPRequestHandler

context = {
    "http_server": HTTPServer,  # constructor
    "server_address": ("0.0.0.0", 8080),  # pre-defined value
    "RequestHandlerClass": lambda: SimpleHTTPRequestHandler,  # pre-defined callable via lambda (special case)
}
```

Now, Junkie can create new objects and their dependencies. All dependencies are resolved via their argument name in the
constructor. Only one object is created per argument name and is shared with all other objects.

```python
with Junkie(context).inject(HTTPServer) as http_server:  # type: HTTPServer
    http_server.serve_forever()
```

Python context managers provide methods to prepare and finalize an object. All context managers are also handled in this
way by Junkie.

## Best practices

### Use type hints for object construction

Junkie uses constructor-based dependency injection. The constructor gets all references to dependent objects, and saves
them for later usage. The constructor should not do any work.

The argument names and their type hints are the easiest and recommended way to define object construction of
dependencies. The context dictionary should be used to handle more complicated situations.

```python
from junkie import Junkie


class Database:
    pass


class App:
    def __init__(self, database: Database):
        self.database = database


with Junkie().inject(App) as app:
    assert isinstance(app.database, Database)
```

### Write integration tests with modified application context

After defining the application context it is very easy to replace individual objects with test doubles for integration
tests.

```python
import unittest

from junkie import Junkie

APPLICATION_CONTEXT = {
    "database_url": "postgresql://scott:tiger@localhost:5432/production",
}


class App:
    def __init__(self, database_url):
        self.database_url = database_url


def main():
    with Junkie(APPLICATION_CONTEXT).inject(App) as app:
        assert app.database_url.startswith("postgresql:")


class AppTest(unittest.TestCase):
    def test(self):
        test_context = APPLICATION_CONTEXT | {"database_url": "sqlite://"}

        with Junkie(test_context).inject(App) as app:
            self.assertEqual(app.database_url, "sqlite://")
```

## Advanced usage

### Adjust object construction via lambdas

The following example code shows various ways to adjust object construction via Python lambdas.

```python
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
```

### The `_junkie` argument name

If you need Junkie in one of your classes or functions, you can use the argument name `_junkie`. This argument name is
reserved for the Junkie instance itself.

```python
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
```

### Instantiate list items

Sometimes you need a list of objects. This list can be instantiated with the `inject_list()` helper function. It works
similar to the `Junkie.inject()` method.

```python
from junkie import Junkie


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
    "data_sources": ["customer_ds", ProductDataSource, SupplierDataSource],
}

with Junkie().inject(App) as app:
    assert isinstance(app.data_sources[0], CustomerDataSource)
    assert isinstance(app.data_sources[1], ProductDataSource)
    assert isinstance(app.data_sources[2], SupplierDataSource)
```

### Callables as pre-defined context values

All requested context values are evaluated if they are callables. If you want to provide a callable object, wrap
it via lambda expression.

```python
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
    assert app.database == "called"
```

### Built-in functions as context values are not supported

Unfortunately, built-in functions (implemented in C) like `sqlite3.connect()` can not be inspected. That's why they are
not supported by Junkie as context values. Python lambdas help to work around this issue.

```python
import sqlite3

from junkie import Junkie

context = {
    "database": ":memory:",
    "connection": sqlite3.connect,
    "working_connection": lambda database: sqlite3.connect(database)
}

# ValueError: no signature found for builtin <built-in function connect>
with Junkie(context).inject("connection") as connection:
    pass

with Junkie(context).inject("working_connection") as working_connection:
    pass
```

# Collaboration

## Get Involved

You are warmly welcome to contribute to Junkie. Just initiate a pull request or report an issue.

## Authors

Junkie was written by [Stefan Richter](https://github.com/sealor). Special thanks go
to [Erik Türke](https://github.com/rollmops) for his valuable feedback and many helpful code snippets.

## Distribution

- Code: <https://github.com/sealor/junkie/>
- PyPI: <https://pypi.org/project/junkie/>

## License

MIT License

See [LICENSE](LICENSE) for full text.
