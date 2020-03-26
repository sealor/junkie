import logging
import random
import unittest
from contextlib import contextmanager

import junkie
from junkie.core_context import CoreContext


class CoreContextTest(unittest.TestCase):
    def test_simple_singleton(self):
        context = CoreContext()
        context.add_singletons({"text": "abc"})

        with context.build_dict({"text"}) as instances:
            self.assertEqual({"text": "abc"}, instances)

    def test_simple_factory(self):
        context = CoreContext()
        context.add_factories({"text": lambda: "abc"})

        with context.build_dict({"text"}) as instances:
            self.assertEqual({"text": "abc"}, instances)

    def test_factory_using_other_factory(self):
        context = CoreContext()
        context.add_singletons({"prefix": "abc", "suffix": "def"})
        context.add_factories({"text": lambda prefix, suffix: prefix + suffix})

        with context.build_dict({"text", "prefix"}) as instances:
            self.assertEqual({"text": "abcdef", "prefix": "abc"}, instances)

    def test_build_object_by_dict_with_list_in_right_order(self):
        def func(letter):
            def factory_func(logger):
                logger.append(letter)
                return letter

            return factory_func

        test_logger = []
        context = CoreContext()
        context.add_factories({"a": func("a"), "b": func("b"), "c": func("c"), "d": func("d"), "e": func("e")})
        context.add_singletons({"logger": test_logger})

        names = ["a", "b", "c", "d", "e"]
        random.shuffle(names)

        with context.build_dict(names):
            self.assertEqual(names, test_logger)

    def test_build_object_by_type(self):
        class Class:
            def __init__(self, prefix, suffix):
                self.text = prefix + suffix

        context = CoreContext()
        context.add_singletons({"prefix": "abc", "suffix": "def"})

        with context.build_object_by_type(Class) as instance:
            self.assertEqual("abcdef", instance.text)

    def test_build_object_by_name(self):
        class Class:
            def __init__(self, prefix, suffix):
                self.text = prefix + suffix

        context = CoreContext()
        context.add_singletons({"prefix": "abc", "suffix": "def"})
        context.add_factories({"text": Class})

        with context.build_object_by_name("text")as instance:
            self.assertEqual("abcdef", instance.text)

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
        context.add_singletons({"logger": test_logger})
        context.add_factories({"message_service": MessageService, "database_context": create_database})

        with context.build_object_by_type(Class) as instance:
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
        context.add_singletons({"text": "abc"})
        context.add_factories({
            "connection_string": lambda: "URL",
            "database_context": create_database,
            "message_service": create_message_service,
            "class": Class,
        })

        with self.assertLogs(level="DEBUG") as logging_context:
            with context.build_object_by_type(Class):
                logging.getLogger(__name__).info("execute context block")

        self.assertEqual([
            "DEBUG:{}:build(Class)".format(junkie.__name__),
            "DEBUG:{}:connection_string = <lambda>([])".format(junkie.__name__),
            "DEBUG:{}:database_context = create_database(['connection_string'])".format(junkie.__name__),
            "DEBUG:{}:database_context.__enter__()".format(junkie.__name__),
            "DEBUG:{}:message_service = create_message_service([])".format(junkie.__name__),
            "DEBUG:{}:message_service.__enter__()".format(junkie.__name__),
            "DEBUG:{}:Class = Class(['database_context', 'message_service', 'text'])".format(junkie.__name__),
            "INFO:{}:execute context block".format(__name__),
            "DEBUG:{}:message_service.__exit__()".format(junkie.__name__),
            "DEBUG:{}:database_context.__exit__()".format(junkie.__name__),
        ], logging_context.output)
