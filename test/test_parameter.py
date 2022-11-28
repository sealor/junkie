import sys
import textwrap
import unittest
from unittest import skipIf

from junkie import Junkie


# https://peps.python.org/pep-0570/#specification
class ParameterTest(unittest.TestCase):
    def test_parameters(self):
        class App:
            def __init__(self, positional_or_keyword_parameter, *args, **kwargs):
                self.positional_or_keyword_parameter = positional_or_keyword_parameter
                self.args = args
                self.kwargs = kwargs

        context = {
            "positional_or_keyword_parameter": "positional_or_keyword_parameter",
            "args": ["args"],
            "kwargs": {"kwargs": "kwargs"},
        }

        with Junkie(context).inject(App) as app:
            self.assertEqual("positional_or_keyword_parameter", app.positional_or_keyword_parameter)
            self.assertEqual(("args",), app.args)
            self.assertEqual({"kwargs": "kwargs"}, app.kwargs)

    def test_optional_parameters(self):
        class App:
            def __init__(self, positional_or_keyword_parameter="default", *args, **kwargs):
                self.positional_or_keyword_parameter = positional_or_keyword_parameter
                self.args = args
                self.kwargs = kwargs

        with Junkie().inject(App) as app:
            self.assertEqual("default", app.positional_or_keyword_parameter)
            self.assertEqual((), app.args)
            self.assertEqual({}, app.kwargs)

    @skipIf(sys.version_info < (3, 8), "Positional-only parameters need at least Python 3.8")
    def test_positional_and_keyword_parameters(self):
        exec(textwrap.dedent("""
            class App:
                def __init__(
                        self,
                        positional_only_parameter,
                        /,
                        positional_or_keyword_parameter,
                        *,
                        keyword_only_parameter
                ):
                    self.positional_only_parameter = positional_only_parameter
                    self.positional_or_keyword_parameter = positional_or_keyword_parameter
                    self.keyword_only_parameter = keyword_only_parameter
    
            context = {
                "positional_only_parameter": "positional_only_parameter",
                "positional_or_keyword_parameter": "positional_or_keyword_parameter",
                "keyword_only_parameter": "keyword_only_parameter",
            }
    
            with Junkie(context).inject(App) as app:
                self.assertEqual("positional_only_parameter", app.positional_only_parameter)
                self.assertEqual("positional_or_keyword_parameter", app.positional_or_keyword_parameter)
                self.assertEqual("keyword_only_parameter", app.keyword_only_parameter)
        """))

    @skipIf(sys.version_info < (3, 8), "Positional-only parameters need at least Python 3.8")
    def test_all_default_values(self):
        exec(textwrap.dedent("""
            class App:
                def __init__(
                        self,
                        positional_only_parameter="default_positional_only",
                        /,
                        positional_or_keyword_parameter="default_positional_or_keyword",
                        *,
                        keyword_only_parameter="default_keyword_only",
                ):
                    self.positional_only_parameter = positional_only_parameter
                    self.positional_or_keyword_parameter = positional_or_keyword_parameter
                    self.keyword_only_parameter = keyword_only_parameter
    
            with Junkie().inject(App) as app:
                self.assertEqual("default_positional_only", app.positional_only_parameter)
                self.assertEqual("default_positional_or_keyword", app.positional_or_keyword_parameter)
                self.assertEqual("default_keyword_only", app.keyword_only_parameter)
    
            context = {
                "positional_only_parameter": "positional_only_parameter",
                "positional_or_keyword_parameter": "positional_or_keyword_parameter",
                "keyword_only_parameter": "keyword_only_parameter",
            }
    
            with Junkie(context).inject(App) as app:
                self.assertEqual("positional_only_parameter", app.positional_only_parameter)
                self.assertEqual("positional_or_keyword_parameter", app.positional_or_keyword_parameter)
                self.assertEqual("keyword_only_parameter", app.keyword_only_parameter)
        """))
