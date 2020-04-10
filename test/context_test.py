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

        with context.build_instances({"text", "prefix"}) as instance:
            self.assertEqual({"text": "abcxyz", "prefix": "abc"}, instance)

        with context.build_instances(["text", "prefix"]) as instance:
            self.assertEqual({"text": "abcxyz", "prefix": "abc"}, instance)

        with context.build_instances(("text", "prefix")) as (text, prefix):
            self.assertEqual("abcxyz", text)
            self.assertEqual("abc", prefix)

        with context.build_instances("class") as instance:
            self.assertEqual("abcxyz", instance.text)

        with context.build_instances(Class) as instance:
            self.assertEqual("abcxyz", instance.text)

    def test_add_none_context(self):
        context = Context({"value": "abc"}, None)
        context.add(None)

        with context.build_instances("value") as value:
            self.assertEqual("abc", value)

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

            with Context({"prefix": "abc", "suffix": "def"}).build_instances(Class) as instance:
                self.assertEqual("abcdef", instance.text)
        """))
