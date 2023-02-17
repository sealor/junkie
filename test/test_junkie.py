import logging
import random
import sys
import textwrap
import unittest
from contextlib import contextmanager
from unittest import skipIf

from junkie import Junkie, JunkieError, inject_list


class JunkieTest(unittest.TestCase):
    def test_resolve_instance_by_name(self):
        context = {"text": "abc"}

        with Junkie(context).inject("text") as instance:
            self.assertEqual("abc", instance)

    def test_resolve_instance_with_factory_by_name(self):
        context = {"text": lambda: "abc"}

        with Junkie(context).inject("text") as instance:
            self.assertEqual("abc", instance)

    def test_raise_exception_if_instance_name_is_unknown(self):
        with self.assertRaises(Exception) as exception_context:
            with Junkie().inject("instance_name"):
                pass

        self.assertEqual('Unable to find "instance_name"', str(exception_context.exception))

    def test_resolve_instance_with_factory_by_type(self):
        class AppClass:
            def __init__(self, text: str):
                self.text = text

        context = {"text": "abc"}

        with Junkie(context).inject(AppClass) as instance:
            self.assertEqual("abc", instance.text)

    def test_resolve_instance_with_factory_using_two_instances(self):
        context = {
            "prefix": "abc",
            "suffix": "def",
            "text": lambda prefix, suffix: prefix + " " + suffix
        }

        with Junkie(context).inject("text") as text:
            self.assertEqual("abc def", text)

    def test_resolve_instance_parameters(self):
        context = {
            "prefix": "abc",
            "suffix": "def",
            "text": lambda prefix, suffix: prefix + " " + suffix
        }

        with Junkie(context).inject("prefix", "suffix", "text") as (my_prefix, my_suffix, text):
            self.assertEqual(("abc", "def", "abc def"), (my_prefix, my_suffix, text))

    def test_resolve_None_as_parameter(self):
        class Class:
            def __init__(self, empty):
                self.empty = empty

        context = {"empty": None, "class": Class}

        with Junkie(context).inject("empty", "class") as (empty_value, class_value):
            self.assertIsNone(empty_value)
            self.assertIsNone(class_value.empty)

    def test_resolve_tuple_with_correct_order(self):
        def func(letter):
            def factory_func(logger):
                logger.append(letter)
                return letter

            return factory_func

        test_logger = []
        context = {
            "a": func("a"), "b": func("b"), "c": func("c"), "d": func("d"), "e": func("e"),
            "logger": test_logger
        }

        names = ["a", "b", "c", "d", "e"]
        random.shuffle(names)

        with Junkie(context).inject(*names):
            self.assertEqual(names, test_logger)

    def test_default_argument_usage(self):
        class MyClassWithDefaultArguments:
            def __init__(self, argument: str, default_argument: int = 10, default_argument2: str = None):
                self.argument = argument
                self.default_argument = default_argument
                self.default_argument2 = default_argument2 or "Hello"

        context = {"argument": "value"}

        with Junkie(context).inject(MyClassWithDefaultArguments) as instance:
            self.assertEqual("value", instance.argument)
            self.assertEqual(10, instance.default_argument)
            self.assertEqual("Hello", instance.default_argument2)

    def test_partial_default_arguments_usage(self):
        class MyClassWithDefaultArguments:
            def __init__(self, argument: str, default_argument: int = 10, default_argument2: str = None):
                self.argument = argument
                self.default_argument = default_argument
                self.default_argument2 = default_argument2 or "Hello"

        context = {"argument": "value", "default_argument2": "set from context"}

        with Junkie(context).inject(MyClassWithDefaultArguments) as instance:
            self.assertEqual("value", instance.argument)
            self.assertEqual(10, instance.default_argument)
            self.assertEqual("set from context", instance.default_argument2)

    def test_empty_args_usage(self):
        class MyClassWithKwargs:
            def __init__(self, *args):
                self.args = args

        with Junkie().inject(MyClassWithKwargs) as instance:
            self.assertEqual((), instance.args)

    def test_args_usage_with_tuple(self):
        class MyClassWithKwargs:
            def __init__(self, *my_tuple):
                self.my_tuple = my_tuple

        context = {"my_tuple": (1, 2, 3)}

        with Junkie(context).inject(MyClassWithKwargs) as instance:
            self.assertEqual((1, 2, 3), instance.my_tuple)

    def test_args_usage_with_list_as_tuple_input(self):
        class MyClassWithKwargs:
            def __init__(self, *my_tuple):
                self.my_tuple = my_tuple

        context = {"my_tuple": [1, 2, 3]}

        with Junkie(context).inject(MyClassWithKwargs) as instance:
            self.assertEqual((1, 2, 3), instance.my_tuple)

    def test_args_usage_with_factory_function(self):
        class MyClassWithKwargs:
            def __init__(self, *my_tuple):
                self.my_tuple = my_tuple

        context = {"my_tuple": lambda: (1, 2, 3)}

        with Junkie(context).inject(MyClassWithKwargs) as instance:
            self.assertEqual((1, 2, 3), instance.my_tuple)

    def test_empty_kwargs_usage(self):
        class MyClassWithKwargs:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        with Junkie().inject(MyClassWithKwargs) as instance:
            self.assertEqual({}, instance.kwargs)

    def test_kwargs_usage_with_dictionary(self):
        class MyClassWithKwargs:
            def __init__(self, **my_vars):
                self.my_vars = my_vars

        context = {"my_vars": {"a": "a"}}

        with Junkie(context).inject(MyClassWithKwargs) as instance:
            self.assertEqual({"a": "a"}, instance.my_vars)

    def test_kwargs_usage_with_factory_function(self):
        class MyClassWithKwargs:
            def __init__(self, **my_vars):
                self.my_vars = my_vars

        context = {"my_vars": lambda: {"a": "a"}}

        with Junkie(context).inject(MyClassWithKwargs) as instance:
            self.assertEqual({"a": "a"}, instance.my_vars)

    def test_extend(self):
        class MyClass:
            def __init__(self, var):
                self.var = var

        with Junkie().extend({"var": 7}).inject(MyClass) as my_class:
            self.assertEqual(7, my_class.var)

    def test_extended_objects_disappear_in_upper_scopes(self):
        class MyClass1:
            pass

        _junkie = Junkie()
        with _junkie.inject(MyClass1):
            _junkie.extend({"var": 7})
            self.assertIn("var", _junkie)
            self.assertEqual(7, _junkie["var"])

        self.assertNotIn("var", _junkie)

    def test_error_on_extend_when_overriding_the_context(self):
        context = {
            "var": 11,
        }

        with self.assertRaisesRegex(JunkieError, "^Instances for names {'var'} already exists$"):
            Junkie(context).extend({"var": 5})

    def test_error_on_extend_when_overriding_instances(self):
        class MyClass1:
            pass

        class MyClass2:
            def __init__(self, my_class1: MyClass1):
                assert my_class1 is not None

        with self.assertRaisesRegex(JunkieError, "^Instances for names {'my_class1'} already exists$"):
            with Junkie().inject(MyClass2, "_junkie") as (_, _junkie):
                _junkie.extend({"my_class1": MyClass1()})

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

        test_logger = []
        context = {
            "logger": test_logger,
            "message_service": MessageService,
            "database_context": create_database,
        }

        with Junkie(context).inject(Class) as instance:
            self.assertIsInstance(instance.message_service, MessageService)
            self.assertEqual("DB", instance.database_context)

            self.assertEqual(["connect", "open"], test_logger)

        self.assertEqual(["connect", "open", "close", "disconnect"], test_logger)

    @skipIf(sys.version_info < (3, 7), "@dataclass needs at least Python 3.7")
    def test_dataclass_decorator(self):
        exec(textwrap.dedent("""
            from dataclasses import dataclass

            @dataclass
            class Class:
                prefix: str
                suffix: str
                pass

                def __post_init__(self):
                    self.text = self.prefix + " " + self.suffix

            with Junkie({"prefix": "abc", "suffix": "def"}).inject(Class) as instance:
                self.assertEqual("abc def", instance.text)
        """))

    def test_unknown_type_exception(self):
        with self.assertRaises(RuntimeError) as error:
            # noinspection PyTypeChecker
            with Junkie().inject(1):
                pass

        self.assertEqual('Unknown type "1" (str, type or Callable expected)', str(error.exception))

    def test_logging(self):
        self.maxDiff = None

        class Class:
            def __init__(self, database_context, message_service, *args):
                self.database_context = database_context
                self.message_service = message_service
                self.args = args

        @contextmanager
        def create_database(connection_string, **kwargs):
            yield "DB: " + connection_string + str(kwargs)

        @contextmanager
        def create_message_service():
            yield "message-service"

        context = {
            "connection_string": lambda: "URL",
            "database_context": create_database,
            "message_service": create_message_service,
            "class": Class,
            "args": ["app_name"],
            "kwargs": {"engine": "sqlite"},
        }

        with self.assertLogs(level="DEBUG") as logging_context:
            with Junkie(context).inject("class", Class):
                logging.getLogger(__name__).info("execute context block")

        self.assertEqual((
            "DEBUG:inject(class, <class 'test.test_junkie.JunkieTest.test_logging.<locals>.Class'>)\n"
            "DEBUG:connection_string = <lambda>()\n"
            "DEBUG:database_context = create_database(connection_string, engine='sqlite')\n"
            "DEBUG:database_context.__enter__()\n"
            "DEBUG:message_service = create_message_service()\n"
            "DEBUG:message_service.__enter__()\n"
            "DEBUG:class = Class(database_context, message_service, app_name)\n"
            "DEBUG:_ = Class(database_context, message_service, app_name)\n"
            "INFO:test.test_junkie:execute context block\n"
            "DEBUG:message_service.__exit__()\n"
            "DEBUG:database_context.__exit__()"
        ), "\n".join(logging_context.output).replace(":junkie:", ":"))

    def test_auto_inject(self):
        class A:
            pass

        class B:
            def __init__(self, a: A):
                self.a = a

        class C:
            def __init__(self, b: B):
                self.b = b

        with Junkie().inject(C) as c_instance:
            self.assertIsInstance(c_instance, C)
            self.assertIsInstance(c_instance.b, B)
            self.assertIsInstance(c_instance.b.a, A)

    def test_no_auto_inject_for_default_arguments(self):
        class A:
            pass

        class B:
            def __init__(self, a: A = None):
                self.a = a

        with Junkie().inject(B) as b_instance:
            self.assertIsInstance(b_instance, B)
            self.assertIsNone(b_instance.a)

    def test_auto_inject_prioritize_named_from_context(self):
        class A:
            pass

        class B:
            def __init__(self, a: A):
                self.a = a

        context = {"a": "from context"}

        with Junkie(context).inject(B) as b:
            self.assertIsInstance(b, B)
            self.assertEqual("from context", b.a)

    def test_no_create_for_builtins(self):
        with self.assertRaises(JunkieError):
            with Junkie().inject(dict):
                pass

    def test_no_auto_inject_for_builtins(self):
        class B:
            def __init__(self, a: str):
                self.a = a

        with self.assertRaises(JunkieError) as error:
            with Junkie().inject(B):
                pass

        self.assertRegex(str(error.exception), 'Mapping for "a" of builtin type "str" is missing')

    def test_object_is_persisted(self):
        class A:
            pass

        context = {
            "a": A,
        }

        _junkie = Junkie(context)
        with _junkie.inject("a") as a1:
            with _junkie.inject("a") as a2:
                with _junkie.inject("a") as a3:
                    self.assertIs(a1, a2)
                    self.assertIs(a1, a3)

    def test_resolve_instance_per_context_key(self):
        class A:
            pass

        context = {
            "a": A,
            "b": A,
        }

        _junkie = Junkie(context)
        with _junkie.inject("a", "b") as (a1, b1):
            with _junkie.inject("a", "b") as (a2, b2):
                self.assertIsNot(a1, b1)
                self.assertIsNot(a2, b2)
                self.assertIs(a1, a2)
                self.assertIs(b1, b2)

    def test_type_as_key_in_mapping_is_ignored(self):
        class A:
            pass

        context = {
            A: "a",
        }

        # noinspection PyTypeChecker
        with Junkie(context).inject(A) as a:
            self.assertIsInstance(a, A)

    def test_auto_inject_same_instance_by_name(self):
        class A:
            pass

        class A1:
            pass

        class B:
            def __init__(self, a: A):
                self.a = a

        class C:
            def __init__(self, a: A1):
                self.a = a

        with Junkie().inject(B, C) as (b, c):
            self.assertIs(b.a, c.a)
            self.assertIsInstance(b.a, A)

        with Junkie().inject(C, B) as (c, b):
            self.assertIs(b.a, c.a)
            self.assertIsInstance(b.a, A1)

    def test_inject_junkie_reference(self):
        my_junkie = Junkie()

        with my_junkie.inject("_junkie") as injected_junkie:
            self.assertIs(injected_junkie, my_junkie)

    def test_inject_list(self):
        class A:
            pass

        class B:
            def __init__(self, a: A, some_value: str):
                self.a = a
                self.some_value = some_value

        context = {"some_value": "value", "my_list_1": inject_list(A, B), "my_list_2": inject_list(B)}

        with Junkie(context).inject("my_list_1", "my_list_2") as (my_list_1, my_list_2):
            self.assertIsInstance(my_list_1, list)
            self.assertIsInstance(my_list_2, list)
            self.assertIsInstance(my_list_1[0], A)
            self.assertIsInstance(my_list_1[1].a, A)
            self.assertEqual("value", my_list_1[1].some_value)
            self.assertEqual("value", my_list_2[0].some_value)
