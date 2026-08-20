---
title: kapro
description: Class-level, mixed, and pinned descriptors for Python
---

[ref: #kapro]

# kapro

`kapro` is a small Python library of property descriptors.

It gives you three public entry points:

- `class_property` — a descriptor that lives on the class and is shared by every instance.
- `mixed_property` — a descriptor that can be defined on the class but resolved per instance.
- `pin` — a cached instance property that stores its value in the instance dictionary.

[ref: #installation]

## Installation

Install with `uv`:

```bash
uv add kapro
```

Or with any PEP 517-compatible tool:

```bash
pip install kapro
```

[ref: #class-property]

## Class-level properties with `class_property`

`class_property` behaves like a class-level attribute, but it is computed lazily and cached on the class.

```python
from kapro import class_property

class Config:
    @class_property
    def name(cls) -> str:
        return "default"

assert Config.name == "default"
assert Config().name == "default"
```

The value is stored on the class, so every instance sees the same value.

[ref: #mixed-property]

## Mixed properties with `mixed_property`

`mixed_property` calls the same function with the class when accessed on the class and with the instance when accessed on an instance.

```python
from kapro import mixed_property

class User:
    def __init__(self, id: int) -> None:
        self.id = id

    @mixed_property
    def label(node) -> str:
        if isinstance(node, type):
            return "User model"
        return f"user: {node.id}"

assert User.label == "User model"
assert User(id=7).label == "user: 7"
```

[ref: #pin]

## Cached instance properties with `pin`

`pin` is the cached equivalent of a plain method-based property.
The first access computes the value and stores it in the instance dictionary.

```python
from kapro import pin

class Expensive:
    @pin
    def payload(self) -> dict:
        return {"loaded": True}

obj = Expensive()
assert obj.payload is obj.payload
```

[ref: #pin-flavors]

### `pin` flavors

`pin` exposes several variants through class attributes.

| Flavor | Decorator | Caches on |
| --- | --- | --- |
| `native` | `@pin` | instance (default) |
| `cls` | `@pin.cls` | class |
| `any` | `@pin.any` | class or instance |
| `pre` | `@pin.pre` | instance, runs before the underlying call |
| `post` | `@pin.post` | instance, runs after the underlying call |

```python
from kapro import pin

class Service:
    @pin.cls
    def version(cls) -> str:
        return "1.0"

assert Service.version == "1.0"
assert Service().version == "1.0"
```

[ref: #full-example]

## Full example

```python
from kapro import class_property, mixed_property, pin

class App:
    @class_property
    def name(cls) -> str:
        return "MyApp"

    @mixed_property
    def greeting(node) -> str:
        return f"Hello from {node.name}"

    @pin
    def config(self) -> dict:
        return {"debug": True}


assert App.name == "MyApp"
assert App.greeting == "Hello from MyApp"
assert App().greeting == "Hello from MyApp"

app = App()
assert app.config == {"debug": True}
assert app.config is app.config
```
