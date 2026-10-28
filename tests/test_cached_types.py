"""Static type assertions for zx.prop.cached.

Run ``basedpyright tests/test_cached_types.py`` or
``basedmypy tests/test_cached_types.py`` to verify.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, assert_type, override

from faker import Faker

from zx.prop.cached import (
    cached_property,
    class_cached_property,
    class_parent_cached_property,
    mixed_cached_property,
    mixed_parent_cached_property,
    post_cached_property,
    pre_cached_property,
)

TYPE_STUB_SEED: Final[int] = 0
_TYPE_FAKER = Faker(["en_US"])
_TYPE_FAKER.seed_instance(TYPE_STUB_SEED)


class Foo:
    @cached_property
    def inst_prop(self) -> int:
        return _TYPE_FAKER.pyint()

    @class_cached_property
    def cls_prop(cls) -> str:
        return _TYPE_FAKER.word()

    @class_parent_cached_property
    def cls_parent_prop(cls) -> str:
        return _TYPE_FAKER.word()

    @mixed_cached_property
    def mixed_prop(self_or_cls: object) -> int:
        return _TYPE_FAKER.pyint()

    @mixed_parent_cached_property
    def mixed_parent_prop(self_or_cls: object) -> int:
        return _TYPE_FAKER.pyint()

    @pre_cached_property
    def pre_prop(self_or_cls: object) -> str:
        return _TYPE_FAKER.word()

    @post_cached_property
    def post_prop(self_or_cls: object) -> str:
        return _TYPE_FAKER.word()


class Parent:
    @cached_property
    def inst_parent(self) -> int:
        return _TYPE_FAKER.pyint()

    @class_cached_property
    def cls_parent(self) -> str:
        return _TYPE_FAKER.word()

    @mixed_cached_property
    def mixed_parent(self_or_cls: object) -> int:
        return _TYPE_FAKER.pyint()


class Child(Parent):
    @cached_property.with_parent  # type: ignore[assignment][any]
    @override
    def inst_parent(self, parent_value: int) -> int:
        return parent_value + _TYPE_FAKER.pyint()

    @class_cached_property.with_parent  # type: ignore[assignment][any]
    @override
    def cls_parent(self, parent_value: str) -> str:
        return f"{_TYPE_FAKER.word()}_{parent_value}"

    @mixed_cached_property.with_parent  # type: ignore[assignment][any]
    @override
    def mixed_parent(self_or_cls: object, parent_value: int) -> int:
        return parent_value + _TYPE_FAKER.pyint()


def test_type_inference_dummy() -> None:
    """Runtime placeholder; real checking is done by static analyzers."""


if TYPE_CHECKING:
    obj = Foo()

    # cached_property instance access -> wrapped return type.
    assert_type(obj.inst_prop, int)  # pyright: ignore[reportUnusedCallResult]
    # cached_property class access -> descriptor type.
    assert_type(
        Foo.inst_prop,
        cached_property[int],
    )  # pyright: ignore[reportUnusedCallResult]

    # class_cached_property -> return type on both class and instance access.
    assert_type(Foo.cls_prop, str)  # pyright: ignore[reportUnusedCallResult]
    assert_type(obj.cls_prop, str)  # pyright: ignore[reportUnusedCallResult]

    # class_parent_cached_property -> return type on both
    # class and instance access.
    assert_type(
        Foo.cls_parent_prop,
        str,
    )  # pyright: ignore[reportUnusedCallResult]
    assert_type(
        obj.cls_parent_prop,
        str,
    )  # pyright: ignore[reportUnusedCallResult]

    # mixed_cached_property -> return type on both class and instance access.
    assert_type(Foo.mixed_prop, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(obj.mixed_prop, int)  # pyright: ignore[reportUnusedCallResult]

    # mixed_parent_cached_property -> return type on both
    # class and instance access.
    assert_type(
        Foo.mixed_parent_prop,
        int,
    )  # pyright: ignore[reportUnusedCallResult]
    assert_type(
        obj.mixed_parent_prop,
        int,
    )  # pyright: ignore[reportUnusedCallResult]

    # pre_cached_property -> return type on both class and instance access.
    assert_type(Foo.pre_prop, str)  # pyright: ignore[reportUnusedCallResult]
    assert_type(obj.pre_prop, str)  # pyright: ignore[reportUnusedCallResult]

    # post_cached_property -> return type on both class and instance access.
    assert_type(Foo.post_prop, str)  # pyright: ignore[reportUnusedCallResult]
    assert_type(obj.post_prop, str)  # pyright: ignore[reportUnusedCallResult]

    # with_parent infers the return type through the wrapper.
    assert_type(
        Child().inst_parent,
        int,
    )  # pyright: ignore[reportUnusedCallResult]
    assert_type(
        Child().cls_parent,
        str,
    )  # pyright: ignore[reportUnusedCallResult]
    assert_type(
        Child().mixed_parent,
        int,
    )  # pyright: ignore[reportUnusedCallResult]
    assert_type(
        Child.inst_parent,
        cached_property[int],
    )  # pyright: ignore[reportUnusedCallResult]
    assert_type(
        Child.cls_parent,
        str,
    )  # pyright: ignore[reportUnusedCallResult]
    assert_type(
        Child.mixed_parent,
        int,
    )  # pyright: ignore[reportUnusedCallResult]
