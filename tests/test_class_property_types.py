"""Static type assertions for zx.prop.class_property.

Run ``basedpyright tests/test_class_property_types.py`` or
``basedmypy tests/test_class_property_types.py`` to verify.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, assert_type, override

from faker import Faker

from zx.prop.class_property import class_property, mixed_property

TYPE_STUB_SEED: Final[int] = 0
_TYPE_FAKER = Faker(["en_US"])
_TYPE_FAKER.seed_instance(TYPE_STUB_SEED)


class Foo:
    @class_property
    def cls_prop(cls) -> int:
        return _TYPE_FAKER.pyint()

    @mixed_property
    def mixed_prop(self_or_cls) -> str:
        return _TYPE_FAKER.word()


def test_type_inference_dummy() -> None:
    """Runtime placeholder; real checking is done by static analyzers."""


class Parent:
    @class_property
    def cls_parent(cls) -> str:
        return _TYPE_FAKER.word()

    @mixed_property
    def mixed_parent(self_or_cls) -> str:
        return _TYPE_FAKER.word()


class Child(Parent):
    @class_property.with_parent  # type: ignore[assignment][any]
    @override
    def cls_parent(cls, parent_value: str) -> str:
        return f"{_TYPE_FAKER.word()}_{parent_value}"

    @mixed_property.with_parent  # type: ignore[assignment][any]
    @override
    def mixed_parent(self_or_cls, parent_value: str) -> str:
        return f"{_TYPE_FAKER.word()}_{parent_value}"


if TYPE_CHECKING:
    obj = Foo()

    # class_property access infers return type for both class and instance.
    assert_type(Foo.cls_prop, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(obj.cls_prop, int)  # pyright: ignore[reportUnusedCallResult]

    # mixed_property access infers return type for both class and instance.
    assert_type(Foo.mixed_prop, str)  # pyright: ignore[reportUnusedCallResult]
    assert_type(obj.mixed_prop, str)  # pyright: ignore[reportUnusedCallResult]

    # with_parent infers the return type through the wrapper.
    assert_type(
        Child.cls_parent,
        str,
    )  # pyright: ignore[reportUnusedCallResult]
    assert_type(
        Child().cls_parent,
        str,
    )  # pyright: ignore[reportUnusedCallResult]
    assert_type(
        Child.mixed_parent,
        str,
    )  # pyright: ignore[reportUnusedCallResult]
    assert_type(
        Child().mixed_parent,
        str,
    )  # pyright: ignore[reportUnusedCallResult]
