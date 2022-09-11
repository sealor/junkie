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
