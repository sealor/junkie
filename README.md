# junkie

Junkie is a dependency injection library for beginners. It is easy to use and has no magic hidden state.

Core features:

- injects instances via parameter name and if not available via type annotation
- handles context managers when creating objects
- provides simple configuration with dictionaries
- can be easily combined with any other object instantiation approach
- supports a flexible way to define scopes

Example:

```python
from junkie import Context

class App:
    def __init__(self, text: str):
        self.text = text

    def greets(self) -> str:
        return self.text

context = Context({
    "greeting": "Hello",
    "name": "Joe",
    "text": lambda greeting, name: f"{greeting} {name}!"
})

with context.build(App) as app:
    assert app.greets() == "Hello Joe!"
```
