import sys
import textwrap
import unittest
from unittest import skipIf

from junkie.context import Context


class ContextTest(unittest.TestCase):
    def test_context_add_build(self):
        class Class:
            def __init__(self, prefix, suffix):
                self.text = prefix + suffix

        context = Context({
            "prefix": "abc",
            "suffix": "def",
            "text": lambda prefix, suffix: prefix + suffix
        })
        context.add(
            {"class": Class},
            {"suffix": "xyz"}
        )

        with context.build("class") as instance:
            self.assertEqual("abcxyz", instance.text)

    def test_add_none_context(self):
        context = Context({"value": "abc"}, None)
        context.add(None)

        with context.build("value") as value:
            self.assertEqual("abc", value)

    def test_all_possible_build_usages(self):
        class MyApp:
            def __init__(self, var1):
                self.var1 = var1

        context = Context({"var1": "text"})

        with context.build({"A": "var1", "B": MyApp}) as instance_dict:
            self.assertEqual("text", instance_dict["A"])
            self.assertEqual("text", instance_dict["B"].var1)

        with context.build(A="var1", B=MyApp) as instance_dict:
            self.assertEqual("text", instance_dict["A"])
            self.assertEqual("text", instance_dict["B"].var1)

        with context.build(("var1", MyApp)) as instance_tuple:
            self.assertEqual("text", instance_tuple[0])
            self.assertEqual("text", instance_tuple[1].var1)

        with context.build("var1", MyApp) as (instance1, instance2):
            self.assertEqual("text", instance1)
            self.assertEqual("text", instance2.var1)

        with context.build("var1") as instance:
            self.assertEqual("text", instance)

    def test_raise_exception_for_wrong_build_usage(self):
        class MyApp:
            pass

        context = Context({"var1": "text"})

        with self.assertRaises(Exception):
            context.build("var1", B=MyApp)

        with self.assertRaises(Exception):
            with context.build(["var1"], [MyApp]):
                pass

        with self.assertRaises(Exception):
            with context.build({"var1", MyApp}):
                pass

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
                    self.text = self.prefix + self.suffix

            with Context({"prefix": "abc", "suffix": "def"}).build(Class) as instance:
                self.assertEqual("abcdef", instance.text)
        """))
