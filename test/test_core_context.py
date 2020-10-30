import logging
import random
import unittest
from contextlib import contextmanager

import junkie
from junkie.core_context import CoreContext


class CoreContextTest(unittest.TestCase):
    def test_resolve_instance_by_name(self):
        context = CoreContext()
        context.add_instances({"text": "abc"})

        with context.build_element("text") as instance:
            self.assertEqual("abc", instance)

    def test_resolve_instance_with_factory_by_name(self):
        context = CoreContext()
        context.add_factories({"text": lambda: "abc"})

        with context.build_element("text") as instance:
            self.assertEqual("abc", instance)

    def test_raise_exception_if_instance_name_is_unknown(self):
        context = CoreContext()

        with self.assertRaises(Exception) as exception_context:
            with context.build_element("instance_name"):
                pass

        self.assertEqual("Not found: instance_name", str(exception_context.exception))

    def test_resolve_instance_with_factory_by_type(self):
        class AppClass:
            def __init__(self, text: str):
                self.text = text

        context = CoreContext()
        context.add_instances({"text": "abc"})

        with context.build_element(AppClass) as instance:
            self.assertEqual("abc", instance.text)

    def test_resolve_instance_with_factory_using_two_instances(self):
        context = CoreContext()
        context.add_instances({"prefix": "abc", "suffix": "def"})
        context.add_factories({"text": lambda prefix, suffix: prefix + suffix})

        with context.build_element("text") as text:
            self.assertEqual("abcdef", text)

    def test_resolve_instance_tuple(self):
        context = CoreContext()
        context.add_instances({"prefix": "abc", "suffix": "def"})
        context.add_factories({"text": lambda prefix, suffix: prefix + suffix})

        with context.build_tuple(("prefix", "suffix", "text")) as instance_tuple:
            self.assertEqual(("abc", "def", "abcdef"), instance_tuple)

    def test_resolve_instance_args(self):
        context = CoreContext()
        context.add_instances({"prefix": "abc", "suffix": "def"})
        context.add_factories({"text": lambda prefix, suffix: prefix + suffix})

        with context.build_tuple("prefix", "suffix", "text") as (prefix, suffix, text):
            self.assertEqual(("abc", "def", "abcdef"), (prefix, suffix, text))

    def test_resolve_tuple_with_correct_order(self):
        def func(letter):
            def factory_func(logger):
                logger.append(letter)
                return letter

            return factory_func

        test_logger = []
        context = CoreContext()
        context.add_factories({"a": func("a"), "b": func("b"), "c": func("c"), "d": func("d"), "e": func("e")})
        context.add_instances({"logger": test_logger})

        names = ["a", "b", "c", "d", "e"]
        random.shuffle(names)

        with context.build_tuple(tuple(names)):
            self.assertEqual(names, test_logger)

    def test_resolve_instance_dict(self):
        context = CoreContext()
        context.add_instances({"prefix": "abc", "suffix": "def"})
        context.add_factories({"text": lambda prefix, suffix: prefix + suffix})

        with context.build_dict({"A": "prefix", "B": "suffix", "C": "text"}) as instance_dict:
            self.assertEqual({"A": "abc", "B": "def", "C": "abcdef"}, instance_dict)

    def test_resolve_instance_arg_dict(self):
        context = CoreContext()
        context.add_instances({"prefix": "abc", "suffix": "def"})
        context.add_factories({"text": lambda prefix, suffix: prefix + suffix})

        with context.build_dict(A="prefix", B="suffix", C="text") as instance_dict:
            self.assertEqual({"A": "abc", "B": "def", "C": "abcdef"}, instance_dict)

    def test_default_argument_usage(self):
        class MyClassWithDefaultArguments:
            def __init__(self, argument: str, default_argument: int = 10, default_argument2: str = None):
                self.argument = argument
                self.default_argument = default_argument
                self.default_argument2 = default_argument2 or "Hello"

        core_context = CoreContext()
        core_context.add_instances({"argument": "value"})

        with core_context.build_element(MyClassWithDefaultArguments) as instance:
            self.assertEqual("value", instance.argument)
            self.assertEqual(10, instance.default_argument)
            self.assertEqual("Hello", instance.default_argument2)

    def test_partial_default_arguments_usage(self):
        class MyClassWithDefaultArguments:
            def __init__(self, argument: str, default_argument: int = 10, default_argument2: str = None):
                self.argument = argument
                self.default_argument = default_argument
                self.default_argument2 = default_argument2 or "Hello"

        core_context = CoreContext()
        core_context.add_instances({"argument": "value", "default_argument2": "set from context"})

        with core_context.build_element(MyClassWithDefaultArguments) as instance:
            self.assertEqual("value", instance.argument)
            self.assertEqual(10, instance.default_argument)
            self.assertEqual("set from context", instance.default_argument2)

    def test_empty_kwargs_usage(self):
        class MyClassWithKwargs:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        core_context = CoreContext()
        with core_context.build_element(MyClassWithKwargs) as instance:
            self.assertEqual({}, instance.kwargs)

    def test_kwargs_usage_with_dictionary(self):
        class MyClassWithKwargs:
            def __init__(self, **my_vars):
                self.my_vars = my_vars

        core_context = CoreContext()
        core_context.add_instances({"my_vars": {"a": "a"}})

        with core_context.build_element(MyClassWithKwargs) as instance:
            self.assertEqual({"a": "a"}, instance.my_vars)

    def test_kwargs_usage_with_factory_function(self):
        class MyClassWithKwargs:
            def __init__(self, **my_vars):
                self.my_vars = my_vars

        def create_kwargs():
            return {"a": "a"}

        core_context = CoreContext()
        core_context.add_factories({"my_vars": create_kwargs})

        with core_context.build_element(MyClassWithKwargs) as instance:
            self.assertEqual({"a": "a"}, instance.my_vars)

    def test_context_manager_enter_and_exit(self):
        class Class:
            def __init__(self, message_service, database_context):
                self.message_service = message_service
                self.database_context = database_context

        class MessageService:
            def __init__(self, logger):
                self.logger = logger

            def __enter__(self):
                self.logger.append("connect")
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.logger.append("disconnect")

        @contextmanager
        def create_database(logger):
            logger.append("open")
            yield "DB"
            logger.append("close")

        test_logger = list()
        context = CoreContext()
        context.add_instances({"logger": test_logger})
        context.add_factories({"message_service": MessageService, "database_context": create_database})

        with context.build_element(Class) as instance:
            self.assertEqual(MessageService, type(instance.message_service))
            self.assertEqual("DB", instance.database_context)

            self.assertEqual(["connect", "open"], test_logger)

        self.assertEqual(["connect", "open", "close", "disconnect"], test_logger)

    def test_logging(self):
        self.maxDiff = None

        class Class:
            def __init__(self, database_context, message_service, text):
                self.database_context = database_context
                self.message_service = message_service
                self.text = text

        @contextmanager
        def create_database(connection_string):
            yield "DB: " + connection_string

        @contextmanager
        def create_message_service():
            yield "message-service"

        context = CoreContext()
        context.add_instances({"text": "abc"})
        context.add_factories({
            "connection_string": lambda: "URL",
            "database_context": create_database,
            "message_service": create_message_service,
            "class": Class,
        })

        with self.assertLogs(level="DEBUG") as logging_context:
            with context.build_element("class"):
                logging.getLogger(__name__).info("execute context block")

        self.assertEqual([
            "DEBUG:{}:build_element('class')".format(junkie.__name__),
            "DEBUG:{}:connection_string = <lambda>([])".format(junkie.__name__),
            "DEBUG:{}:database_context = create_database(['connection_string'])".format(junkie.__name__),
            "DEBUG:{}:database_context.__enter__()".format(junkie.__name__),
            "DEBUG:{}:message_service = create_message_service([])".format(junkie.__name__),
            "DEBUG:{}:message_service.__enter__()".format(junkie.__name__),
            "DEBUG:{}:class = Class(['database_context', 'message_service', 'text'])".format(junkie.__name__),
            "INFO:{}:execute context block".format(__name__),
            "DEBUG:{}:message_service.__exit__()".format(junkie.__name__),
            "DEBUG:{}:database_context.__exit__()".format(junkie.__name__),
        ], logging_context.output)
