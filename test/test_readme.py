import unittest


class ReadmeTest(unittest.TestCase):
    def test_example(self):
        from junkie import Context

        class App:
            def __init__(self, text: str):
                self.text = text

            def greets(self) -> str:
                return self.text

        context = Context({
            "greeting": "Hello",
            "name": "Joe",
            "text": lambda greeting, name: "{} {}!".format(greeting, name)
        })

        with context.build(App) as app:
            assert app.greets() == "Hello Joe!"
