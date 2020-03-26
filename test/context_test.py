import sys
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

        with context.build({"text", "prefix"}) as instance:
            self.assertEqual({"text": "abcxyz", "prefix": "abc"}, instance)

        with context.build(["text", "prefix"]) as instance:
            self.assertEqual({"text": "abcxyz", "prefix": "abc"}, instance)

        with context.build("class") as instance:
            self.assertEqual("abcxyz", instance.text)

        with context.build(Class) as instance:
            self.assertEqual("abcxyz", instance.text)

    @skipIf(sys.version_info.major <= 3 and sys.version_info.minor < 7, "@dataclass is new in version 3.7")
    def test_dataclass_decorator(self):
        from dataclasses import dataclass

        @dataclass
        class Class:
            prefix: str
            suffix: str

            def __post_init__(self):
                self.text = self.prefix + self.suffix

        with Context({"prefix": "abc", "suffix": "def"}).build(Class) as instance:
            self.assertEqual("abcdef", instance.text)
