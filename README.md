---
title: kapro
description: Class-level, mixed, and cached descriptors for Python
---

# kapro

[ref: #kapro]

## Overview

[ref: #overview]

`kapro` is a small, focused Python library of property descriptors. It extends the standard `property` idea with class-level descriptors, mixed class and instance descriptors, several caching strategies, parent-aware overrides, and attribute forwarding.

The public API has three main entry points:

- `class_property` — class-level computed attributes.
- `mixed_property` — descriptors that receive either the class or the instance.
- `pin` — a family of instance and class cached properties.

`kapro.special.proxy_to` rounds out the library by delegating attributes to another object.

## Contents

[ref: #contents]

- [Overview](#overview)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Descriptors](#descriptors)
  - [`class_property`](#class-property)
  - [`mixed_property`](#mixed-property)
  - [`pin`](#pin)
    - [`pin.native`](#pin-native)
    - [`pin.cls`](#pin-cls)
    - [`pin.any`](#pin-any)
    - [`pin.pre`](#pin-pre)
    - [`pin.post`](#pin-post)
  - [Choosing the cache owner with `.here`](#here)
    - [`pin.cls.here`](#pin-cls-here)
    - [`pin.any.here`](#pin-any-here)
    - [`pin.pre.here`](#pin-pre-here)
    - [`pin.post.here`](#pin-post-here)
- [Parent-aware overrides with `with_parent`](#with-parent)
- [Attribute forwarding with `proxy_to`](#proxy-to)
- [Cache invalidation](#cache-invalidation)
- [Common gotchas](#common-gotchas)
- [Development](#development)

## Installation

[ref: #installation]

```bash
uv add kapro
```

Or with any PEP 517-compatible tool:

```bash
pip install kapro
```

`kapro` depends on [`kain`](https://pypi.org/project/kain/).

## Quick start

[ref: #quick-start]

```python
from zx.prop import class_property, mixed_property, pin


class Config:
    @class_property
    def name(cls) -> str:
        return "default"

    @mixed_property
    def label(node) -> str:
        if isinstance(node, type):
            return f"{node.__name__} model"
        return f"instance of {type(node).__name__}"

    @pin
    def value(self) -> int:
        return 42


assert Config.name == "default"
assert Config().label == "instance of Config"
assert Config().value == 42
```

## Descriptors

[ref: #descriptors]

### `class_property`

[ref: #class-property]

A class-level descriptor. The decorated function receives the class, and the result is computed every time it is accessed (no caching).

```python
from zx.prop import class_property


class Config:
    @class_property
    def name(cls) -> str:
        return cls.__name__.lower()


assert Config.name == "config"
assert Config().name == "config"
```

### `mixed_property`

[ref: #mixed-property]

A descriptor that is invoked both on class access and on instance access. The decorated function receives either the class or the instance.

```python
from zx.prop import mixed_property


class User:
    def __init__(self, id: int) -> None:
        self.id = id

    @mixed_property
    def label(node) -> str:
        if isinstance(node, type):
            return "User model"
        return f"user #{node.id}"


assert User.label == "User model"
assert User(7).label == "user #7"
```

### `pin`

[ref: #pin]

`pin` is the main entry point for cached properties. It is itself an instance-bound descriptor, and it exposes several flavors through class attributes:

| Decorator | Caches on | Access |
| --- | --- | --- |
| `@pin` | instance `__dict__` | instance only |
| `@pin.native` | instance `__instance_memoized__` | instance only |
| `@pin.cls` | accessed class | class + instance |
| `@pin.any` | class or instance | class + instance |
| `@pin.pre` | class only | class + instance |
| `@pin.post` | instance only | class + instance |

```python
from zx.prop import pin


class Service:
    @pin
    def config(self) -> dict:
        return {"debug": True}

    @pin.cls
    def version(cls) -> str:
        return "1.0"


s = Service()
assert s.config is s.config          # computed once per instance
assert Service.version == "1.0"      # computed once per accessed class
```

#### `pin.native`

[ref: #pin-native]

The standard instance-level cached property. Use it instead of plain `@pin` when you need the cache stored separately from the attribute name, or when the decorated function is a coroutine.

```python
from zx.prop import pin


class Sample:
    @pin.native
    def value(self) -> int:
        return expensive_computation()
```

#### `pin.cls`

[ref: #pin-cls]

A class-level cached property. Each accessed class gets its own cache, so subclasses do not share cached values with their parents.

```python
from zx.prop import pin


class Base:
    @pin.cls
    def value(cls) -> int:
        return 1


class Child(Base):
    pass


_ = Base.value
_ = Child.value
assert "__class_memoized__" in Base.__dict__
assert "__class_memoized__" in Child.__dict__
```

#### `pin.any`

[ref: #pin-any]

Caches on the accessed node: the instance for instance access, the accessed class for class access.

```python
from zx.prop import pin


class Sample:
    @pin.any
    def value(node) -> int:
        return 1


assert Sample().value == 1
assert Sample.value == 1
```

#### `pin.pre`

[ref: #pin-pre]

An asymmetric cached descriptor: it caches only on class access. Instance access recomputes every time.

```python
from zx.prop import pin


class Sample:
    @pin.pre
    def pre_value(cls) -> int:
        return compute()
```

#### `pin.post`

[ref: #pin-post]

An asymmetric cached descriptor: it caches only on instance access. Class access recomputes every time.

```python
from zx.prop import pin


class Sample:
    @pin.post
    def post_value(self) -> int:
        return compute()
```

### Choosing the cache owner with `.here`

[ref: #here]

By default, class-level `pin.*` flavors cache on the class that was accessed. Use `.here` when you want the cache to live on the class that defines the descriptor instead. This is useful when subclasses should share the parent's cached value.

#### `pin.cls.here`

[ref: #pin-cls-here]

`@pin.cls` caches on the accessed class; `@pin.cls.here` caches on the owner class.

```python
from zx.prop import pin


class Base:
    @pin.cls.here
    def value(cls) -> int:
        return 1


class Child(Base):
    pass


_ = Base.value
_ = Child.value
assert "__class_memoized__" in Base.__dict__
assert "__class_memoized__" not in Child.__dict__   # shared with owner
```

#### `pin.any.here`

[ref: #pin-any-here]

Instance access caches on the instance, but class access caches on the owner class.

```python
from zx.prop import pin


class Base:
    @pin.any.here
    def value(node) -> int:
        return 1


class Child(Base):
    pass


assert Base().value == 1
assert Child().value == 1
assert Base.value == 1
assert Child.value == 1
assert "__class_memoized__" in Base.__dict__
assert "__class_memoized__" not in Child.__dict__
```

#### `pin.pre.here`

[ref: #pin-pre-here]

Class access caches on the owner class, so subclasses share the same class-level cache.

```python
from zx.prop import pin


class Base:
    @pin.pre.here
    def value(cls) -> int:
        return compute()


class Child(Base):
    pass


assert Base.value == Child.value
assert "__class_memoized__" in Base.__dict__
assert "__class_memoized__" not in Child.__dict__
```

#### `pin.post.here`

[ref: #pin-post-here]

Instance access caches on the instance. Class access always recomputes, so there is no class-level cache to share.

```python
from zx.prop import pin


class Sample:
    @pin.post.here
    def value(self) -> int:
        return compute()


s = Sample()
assert s.value == s.value          # cached on the instance
assert Sample.value != Sample.value  # recomputed on every class access
```

## Parent-aware overrides with `with_parent`

[ref: #with-parent]

Every public descriptor supports `.with_parent`. Use it in a subclass to receive the parent descriptor's value as the second positional argument.

```python
from zx.prop import pin


class Parent:
    @pin
    def value(self) -> int:
        return 10


class Child(Parent):
    @pin.with_parent
    def value(self, parent_value: int) -> int:
        return parent_value + 5


assert Child().value == 15
```

The same works for `class_property`, `mixed_property`, and all `pin.*` flavors.

> **Note:** if both parent and child use `.with_parent` on the same name, you can get a `RecursionError` with the message *"couldn't reach parent descriptor"*.

## Attribute forwarding with `proxy_to`

[ref: #proxy-to]

`proxy_to` is a class decorator that forwards attribute access to a "pivot" object.

```python
from zx.prop.special import proxy_to


class Engine:
    def power(self) -> int:
        return 42


@proxy_to("engine", "power")
class Car:
    engine = Engine()


assert Car().power == 42
```

Arguments:

| Argument | Default | Meaning |
| --- | --- | --- |
| `pivot` | required | A string attribute name on the decorated class, or an external object. |
| `names` | required | One or more attribute names to proxy from the pivot. |
| `binder` | `bound_property` | Descriptor factory used to wrap the forwarding function. `None` attaches a raw lookup descriptor. |
| `getter` | `operator.attrgetter` | `(name) -> (obj) -> value` used to fetch from the pivot. |
| `default` | `Nothing` | Fallback value if the pivot or attribute is missing. |
| `post` | `None` | `value -> result` post-processor applied after fetching. |
| `safe` | `True` | Raise `TypeError` if the name already exists on the class. |

With the default binder, a proxied callable is invoked with no arguments and its return value is used:

```python
@proxy_to("engine", "power")
class Car:
    engine = Engine()


assert Car().power == 42        # result, not a bound method
```

Use `binder=None` when you need the raw attribute, for example to pass arguments:

```python
@proxy_to("target", "scale", binder=None)
class Proxy:
    class Target:
        def scale(self, value: int) -> int:
            return value * 3
    target = Target()


assert Proxy().scale(5) == 15
```

> **Note:** because attributes are attached dynamically, static analyzers will not infer forwarded attributes from the decorator call.

## Cache invalidation

[ref: #cache-invalidation]

Cached `pin.*` descriptors expose two helpers for cache invalidation:

### `.by(callback)`

Provide a custom freshness predicate:

```python
def always_actual(_self, _node, _stamp) -> bool:
    return True


class Sample:
    value = pin.cls.by(always_actual)(lambda cls: 1)
```

### `.ttl(seconds)`

Provide a numeric time-to-live (must be `> 0`):

```python
class Sample:
    value = pin.cls.ttl(60.0)(lambda cls: compute())
```

## Common gotchas

[ref: #common-gotchas]

- **Class access on instance-only descriptors raises `ContextFaultError`.**
  ```python
  class S:
      attr = pin.native(lambda self: 1)
  S.attr      # ContextFaultError
  ```

- **`pin` and `bound_property` need `__dict__`.** Slotted classes without `__dict__` raise `TypeError("has no __dict__")`.

- **Frozen dataclasses.** `pin` cannot cache on frozen instances and raises `FrozenInstanceError`. Use `binder=None` in `proxy_to` to forward raw attributes without caching.

- **Async properties.** Plain `pin` rejects coroutine functions. Use `@pin.native` for async properties instead.

- **`proxy_to` will not overwrite existing attributes** unless `safe=False`.

- **`with_parent` relies on matching names.** The overriding method must have the same name as the parent's property.

## Development

[ref: #development]

Clone the repository and install dependencies:

```bash
uv sync
```

Run the test suite:

```bash
make test
```

Run the full lint pipeline:

```bash
make lint
```

`kapro` targets Python 3.12+.
