"""Static type assertions for kapro.class_property.

Run ``basedpyright tests/test_class_property_types.py`` or
``basedmypy tests/test_class_property_types.py`` to verify.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, assert_type, override

from kapro.class_property import class_property, mixed_property


class Foo:
    @class_property
    def cls_prop(cls) -> int:
        return 42

    @mixed_property
    def mixed_prop(self_or_cls) -> str:
        return "hello"


def test_type_inference_dummy() -> None:
    """Runtime placeholder; real checking is done by static analyzers."""


class Parent:
    @class_property
    def cls_parent(cls) -> str:
        return "parent"

    @mixed_property
    def mixed_parent(self_or_cls) -> str:
        return "parent"


class Child(Parent):
    @class_property.with_parent  # type: ignore[assignment][any]
    @override
    def cls_parent(cls, parent_value: str) -> str:
        return f"child_{parent_value}"

    @mixed_property.with_parent  # type: ignore[assignment][any]
    @override
    def mixed_parent(self_or_cls, parent_value: str) -> str:
        return f"child_{parent_value}"


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
