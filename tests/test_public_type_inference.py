"""Type inference playground for every public symbol in ``kapro.__all__``.

Run with a static analyzer to check inference:

    make lint

At runtime the tests use the seeded ``fake`` fixture and record every
computed value in a per-class ``history`` dict, so there are no hard-coded
assertions.
"""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING, ClassVar, assert_type, cast

from faker import Faker

from kapro import class_property, mixed_property, pin, special
from kapro.cached import cached_property


def _record[T](owner: object, name: str, value: T) -> T:
    """Append *value* to *owner.history[name]* and return it."""
    history = cast("dict[str, list[object]]", getattr(owner, "history"))  # noqa: B009
    history.setdefault(name, []).append(value)
    return value


class Parent:
    """Exercise all public kapro descriptors and ``pin`` flavors."""

    _faker: ClassVar[Faker]
    history: ClassVar[dict[str, list[object]]] = {}

    @class_property
    def name(cls) -> str:
        return _record(cls, "name", cls._faker.word())

    @mixed_property
    def label(node: object) -> str:
        return _record(Parent, "label", Parent._faker.word())

    @pin
    def value(self) -> int:
        return _record(Parent, "value", Parent._faker.pyint())

    @pin.native
    def native_value(self) -> int:
        return _record(Parent, "native_value", Parent._faker.pyint())

    @pin.cls
    def cls_value(cls) -> int:
        return _record(cls, "cls_value", cls._faker.pyint())

    @pin.any
    def any_value(node: object) -> int:
        return _record(Parent, "any_value", Parent._faker.pyint())

    @pin.pre
    def pre_value(node: object) -> int:
        return _record(Parent, "pre_value", Parent._faker.pyint())

    @pin.post
    def post_value(node: object) -> int:
        return _record(Parent, "post_value", Parent._faker.pyint())

    @pin.cls.here
    def cls_here_value(cls) -> int:
        return _record(cls, "cls_here_value", cls._faker.pyint())

    @pin.any.here
    def any_here_value(node: object) -> int:
        return _record(Parent, "any_here_value", Parent._faker.pyint())

    @pin.pre.here
    def pre_here_value(node: object) -> int:
        return _record(Parent, "pre_here_value", Parent._faker.pyint())

    @pin.post.here
    def post_here_value(node: object) -> int:
        return _record(Parent, "post_here_value", Parent._faker.pyint())


class Child(Parent):
    pass


class HereBase:
    """Test .here semantics with inheritance and overrides."""

    _faker: ClassVar[Faker]
    history: ClassVar[dict[str, list[object]]] = {}

    @pin.cls.here
    def cls_here(cls) -> int:
        return _record(cls, "cls_here", cls._faker.pyint())

    @pin.any.here
    def any_here(node: object) -> int:
        return _record(HereBase, "any_here", HereBase._faker.pyint())

    @pin.pre.here
    def pre_here(node: object) -> int:
        return _record(HereBase, "pre_here", HereBase._faker.pyint())

    @pin.post.here
    def post_here(node: object) -> int:
        return _record(HereBase, "post_here", HereBase._faker.pyint())


class HereChild(HereBase):
    pass


class HereGrandChild(HereChild):
    pass


class HereOverrideChild(HereBase):
    @pin.cls.here
    def cls_here(cls) -> int:
        return _record(cls, "cls_here", cls._faker.pyint())

    @pin.any.here
    def any_here(node: object) -> int:
        return _record(
            HereOverrideChild,
            "any_here",
            HereOverrideChild._faker.pyint(),
        )

    @pin.pre.here
    def pre_here(node: object) -> int:
        return _record(
            HereOverrideChild,
            "pre_here",
            HereOverrideChild._faker.pyint(),
        )

    @pin.post.here
    def post_here(node: object) -> int:
        return _record(
            HereOverrideChild,
            "post_here",
            HereOverrideChild._faker.pyint(),
        )


class Engine:
    """Target object for ``proxy_to``."""

    _faker: ClassVar[Faker]
    history: ClassVar[list[int]] = []

    def power(self) -> int:
        value = self._faker.pyint()
        self.history.append(value)
        return value


@special.proxy_to("engine", "power")
class DefaultProxy:
    engine: ClassVar[Engine] = Engine()


@special.proxy_to("engine", "power", binder=class_property)
class ClassProxy:
    engine: ClassVar[Engine] = Engine()


@special.proxy_to("engine", "power", binder=mixed_property)
class MixedProxy:
    engine: ClassVar[Engine] = Engine()


@special.proxy_to("engine", "power", binder=pin)
class PinProxy:
    engine: ClassVar[Engine] = Engine()


@special.proxy_to("engine", "power", binder=pin.native)
class NativeProxy:
    engine: ClassVar[Engine] = Engine()


@special.proxy_to("engine", "power", binder=pin.cls)
class ClsProxy:
    engine: ClassVar[Engine] = Engine()


@special.proxy_to("engine", "power", binder=pin.any)
class AnyProxy:
    engine: ClassVar[Engine] = Engine()


@special.proxy_to("engine", "power", binder=pin.pre)
class PreProxy:
    engine: ClassVar[Engine] = Engine()


@special.proxy_to("engine", "power", binder=pin.post)
class PostProxy:
    engine: ClassVar[Engine] = Engine()


def _reset_parent_state(fake: Faker) -> None:
    Parent._faker = fake  # pyright: ignore[reportPrivateUsage]
    for cls in (Parent, Child):
        cls.history = {}
        with suppress(AttributeError):
            delattr(cls, "__class_memoized__")


def _reset_here_state(fake: Faker) -> None:
    HereBase._faker = fake  # pyright: ignore[reportPrivateUsage]
    for cls in (
        HereBase,
        HereChild,
        HereGrandChild,
        HereOverrideChild,
    ):
        cls.history = {}
        with suppress(AttributeError):
            delattr(cls, "__class_memoized__")


def _reset_engine_state(fake: Faker) -> None:
    Engine._faker = fake  # pyright: ignore[reportPrivateUsage]
    Engine.history = []


def _call_power(proxy: object) -> int:
    """Return a proxied ``power`` value without triggering static errors.

    ``proxy_to`` does not currently expose forwarded attributes in its stub,
    so a plain ``proxy.power`` access would produce "unknown attribute".
    """
    return getattr(proxy, "power")  # noqa: B009  # pyright: ignore[reportAny]


def test_runtime_type_inference_playground(fake: Faker) -> None:
    """Runtime smoke test so the file also passes pytest."""

    _reset_parent_state(fake)
    cfg = Parent()

    # class_property / mixed_property: computed on every access, no caching.
    assert Parent.name == Parent.history["name"][-1]
    assert cfg.name == Parent.history["name"][-1]
    assert len(Parent.history["name"]) == 2

    assert Parent.label == Parent.history["label"][-1]
    assert cfg.label == Parent.history["label"][-1]
    assert len(Parent.history["label"]) == 2

    # pin (default bound_property): instance -> value, class -> descriptor.
    assert cfg.value == Parent.history["value"][-1]
    assert cfg.value == Parent.history["value"][-1]  # cached
    assert len(Parent.history["value"]) == 1

    # pin.native (cached_property): instance -> value, class -> descriptor.
    assert cfg.native_value == Parent.history["native_value"][-1]
    assert cfg.native_value == Parent.history["native_value"][-1]
    assert len(Parent.history["native_value"]) == 1

    # pin.cls (class_cached_property): always value, cached on accessed class.
    assert Parent.cls_value == Parent.history["cls_value"][-1]
    assert cfg.cls_value == Parent.history["cls_value"][-1]
    assert len(Parent.history["cls_value"]) == 1

    # pin.any (mixed_cached_property): caches both class and instance access.
    assert Parent.any_value == Parent.history["any_value"][-1]
    assert cfg.any_value == Parent.history["any_value"][-1]
    assert len(Parent.history["any_value"]) == 2

    # pin.pre: class caches, instance recomputes.
    assert Parent.pre_value == Parent.history["pre_value"][-1]
    assert cfg.pre_value == Parent.history["pre_value"][-1]
    assert len(Parent.history["pre_value"]) == 2

    # pin.post: class recomputes, instance caches.
    assert Parent.post_value == Parent.history["post_value"][-1]
    assert cfg.post_value == Parent.history["post_value"][-1]
    assert len(Parent.history["post_value"]) == 2


def test_proxy_to_with_all_binders(fake: Faker) -> None:
    """Runtime smoke test for ``special.proxy_to``."""

    _reset_engine_state(fake)

    # Non-raw binders return the computed value directly.
    assert _call_power(DefaultProxy()) == Engine.history[-1]
    assert _call_power(ClassProxy()) == Engine.history[-1]
    assert _call_power(MixedProxy()) == Engine.history[-1]
    assert _call_power(PinProxy()) == Engine.history[-1]
    assert _call_power(NativeProxy()) == Engine.history[-1]
    assert _call_power(ClsProxy()) == Engine.history[-1]
    assert _call_power(AnyProxy()) == Engine.history[-1]
    assert _call_power(PreProxy()) == Engine.history[-1]
    assert _call_power(PostProxy()) == Engine.history[-1]


def test_here_cls_inheritance(fake: Faker) -> None:
    """pin.cls.here caches on the owner and shares across the hierarchy."""

    _reset_here_state(fake)

    # Class cache lives on HereBase; descendants share it.
    assert HereBase.cls_here == HereBase.history["cls_here"][-1]
    assert HereChild.cls_here == HereBase.history["cls_here"][-1]
    assert HereGrandChild.cls_here == HereBase.history["cls_here"][-1]
    assert len(HereBase.history["cls_here"]) == 1

    base_inst = HereBase()
    child_inst = HereChild()
    grandchild_inst = HereGrandChild()
    assert base_inst.cls_here == HereBase.history["cls_here"][-1]
    assert child_inst.cls_here == HereBase.history["cls_here"][-1]
    assert grandchild_inst.cls_here == HereBase.history["cls_here"][-1]
    # still cached on owner class
    assert len(HereBase.history["cls_here"]) == 1


def test_here_any_inheritance(fake: Faker) -> None:
    """pin.any.here caches class access on the owner, instance per object."""

    _reset_here_state(fake)

    assert HereBase.any_here == HereBase.history["any_here"][-1]
    assert HereChild.any_here == HereBase.history["any_here"][-1]
    assert HereGrandChild.any_here == HereBase.history["any_here"][-1]
    assert len(HereBase.history["any_here"]) == 1

    base_inst = HereBase()
    child_inst = HereChild()
    grandchild_inst = HereGrandChild()
    base_value = base_inst.any_here
    child_value = child_inst.any_here
    grandchild_value = grandchild_inst.any_here
    assert base_value == HereBase.history["any_here"][-3]
    assert child_value == HereBase.history["any_here"][-2]
    assert grandchild_value == HereBase.history["any_here"][-1]
    assert base_inst.any_here == base_value  # cached on instance
    assert len(HereBase.history["any_here"]) == 4  # class + 3 instances


def test_here_pre_inheritance(fake: Faker) -> None:
    """pin.pre.here caches class access on the owner, never instance access."""

    _reset_here_state(fake)

    assert HereBase.pre_here == HereBase.history["pre_here"][-1]
    assert HereChild.pre_here == HereBase.history["pre_here"][-1]
    assert HereGrandChild.pre_here == HereBase.history["pre_here"][-1]
    assert len(HereBase.history["pre_here"]) == 1

    base_inst = HereBase()
    child_inst = HereChild()
    grandchild_inst = HereGrandChild()
    assert base_inst.pre_here == HereBase.history["pre_here"][-1]
    assert child_inst.pre_here == HereBase.history["pre_here"][-1]
    assert grandchild_inst.pre_here == HereBase.history["pre_here"][-1]
    # each instance access recomputes
    assert len(HereBase.history["pre_here"]) == 4


def test_here_post_inheritance(fake: Faker) -> None:
    """pin.post.here never caches class access, instance access is cached."""

    _reset_here_state(fake)

    assert HereBase.post_here == HereBase.history["post_here"][-1]
    assert HereChild.post_here == HereBase.history["post_here"][-1]
    assert HereGrandChild.post_here == HereBase.history["post_here"][-1]
    # each class access recomputes
    assert len(HereBase.history["post_here"]) == 3

    base_inst = HereBase()
    child_inst = HereChild()
    grandchild_inst = HereGrandChild()
    base_value = base_inst.post_here
    child_value = child_inst.post_here
    grandchild_value = grandchild_inst.post_here
    assert base_value == HereBase.history["post_here"][-3]
    assert child_value == HereBase.history["post_here"][-2]
    assert grandchild_value == HereBase.history["post_here"][-1]
    assert base_inst.post_here == base_value  # cached on instance
    # 3 class + 3 instance computations
    assert len(HereBase.history["post_here"]) == 6


def test_here_override_creates_independent_owner_cache(fake: Faker) -> None:
    """Overriding with .here makes the child the new owner."""

    _reset_here_state(fake)

    base_value = HereBase.cls_here
    override_value = HereOverrideChild.cls_here

    assert base_value == HereBase.history["cls_here"][-1]
    assert override_value == HereOverrideChild.history["cls_here"][-1]
    assert HereOverrideChild.cls_here == override_value  # cached
    assert HereBase.cls_here == base_value  # unchanged

    assert len(HereBase.history["cls_here"]) == 1
    assert len(HereOverrideChild.history["cls_here"]) == 1


if TYPE_CHECKING:
    cfg = Parent()

    # class_property: always returns the wrapped type.
    assert_type(Parent.name, str)  # pyright: ignore[reportUnusedCallResult]
    assert_type(cfg.name, str)  # pyright: ignore[reportUnusedCallResult]

    # mixed_property: always returns the wrapped type.
    assert_type(Parent.label, str)  # pyright: ignore[reportUnusedCallResult]
    assert_type(cfg.label, str)  # pyright: ignore[reportUnusedCallResult]

    # pin (default bound_property): instance -> value, class -> descriptor.
    assert_type(cfg.value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(Parent.value, pin[int])  # pyright: ignore[reportUnusedCallResult]

    # pin.native (cached_property): instance -> value, class -> descriptor.
    assert_type(cfg.native_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(Parent.native_value, cached_property[int])  # pyright: ignore[reportUnusedCallResult]

    # pin.cls (class_cached_property): always value.
    assert_type(Parent.cls_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(cfg.cls_value, int)  # pyright: ignore[reportUnusedCallResult]

    # pin.any (mixed_cached_property): always value.
    assert_type(Parent.any_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(cfg.any_value, int)  # pyright: ignore[reportUnusedCallResult]

    # pin.pre (pre_cached_property): always value.
    assert_type(Parent.pre_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(cfg.pre_value, int)  # pyright: ignore[reportUnusedCallResult]

    # pin.post (post_cached_property): always value.
    assert_type(Parent.post_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(cfg.post_value, int)  # pyright: ignore[reportUnusedCallResult]

    # .here variants (class access caches on the declaring/owning class).
    assert_type(Parent.cls_here_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(Child.cls_here_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(Parent().cls_here_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(Parent.any_here_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(Child.any_here_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(Parent().any_here_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(Parent.pre_here_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(Child.pre_here_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(Parent().pre_here_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(Parent.post_here_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(Child.post_here_value, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(Parent().post_here_value, int)  # pyright: ignore[reportUnusedCallResult]

    # NOTE: ``proxy_to`` currently does not expose forwarded attribute types
    # through its stub, so ``DefaultProxy().power`` and friends resolve as
    # ``Unknown``.  The runtime usage above is still valid; this is a typing
    # limitation of the decorator, not the binders.
