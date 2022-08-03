import unittest


class ReadmeTest(unittest.TestCase):
    def test_example(self):
        from junkie import Junkie

        class App:
            def __init__(self, text: str):
                self.text = text

            def greets(self) -> str:
                return self.text

        context = Junkie({
            "greeting": "Hello",
            "name": "Joe",
            "text": lambda greeting, name: "{} {}!".format(greeting, name)
        })

        with context.inject(App) as app:
            assert app.greets() == "Hello Joe!"
