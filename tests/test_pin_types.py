"""Static type assertions for zx.prop.pin.

Run ``basedpyright tests/test_pin_types.py`` or
``basedmypy tests/test_pin_types.py`` to verify.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, assert_type

from faker import Faker

from zx.prop import pin
from zx.prop.cached import cached_property

TYPE_STUB_SEED: Final[int] = 0
_TYPE_FAKER = Faker(["en_US"])
_TYPE_FAKER.seed_instance(TYPE_STUB_SEED)


class Foo:
    @pin
    def inst_prop(self) -> int:
        return _TYPE_FAKER.pyint()

    @pin.native
    def native_prop(self) -> str:
        return _TYPE_FAKER.word()

    @pin.cls
    def cls_prop(cls) -> int:
        return _TYPE_FAKER.pyint()

    @pin.any
    def any_prop(self_or_cls: object) -> str:
        return _TYPE_FAKER.word()

    @pin.pre
    def pre_prop(self_or_cls: object) -> int:
        return _TYPE_FAKER.pyint()

    @pin.post
    def post_prop(self_or_cls: object) -> int:
        return _TYPE_FAKER.pyint()


def test_type_inference_dummy() -> None:
    """Runtime placeholder; real checking is done by static analyzers."""


if TYPE_CHECKING:
    obj = Foo()

    # pin instance access → wrapped return type.
    assert_type(obj.inst_prop, int)  # pyright: ignore[reportUnusedCallResult]
    # pin class access → descriptor type.
    assert_type(
        Foo.inst_prop,
        pin[int],
    )  # pyright: ignore[reportUnusedCallResult]

    # pin.native instance access → wrapped return type.
    assert_type(
        obj.native_prop,
        str,
    )  # pyright: ignore[reportUnusedCallResult]
    # pin.native class access → descriptor type (cached_property).
    assert_type(
        Foo.native_prop,
        cached_property[str],
    )  # pyright: ignore[reportUnusedCallResult]

    # pin.cls → return type on both class and instance access.
    assert_type(Foo.cls_prop, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(obj.cls_prop, int)  # pyright: ignore[reportUnusedCallResult]

    # pin.any → return type on both class and instance access.
    assert_type(Foo.any_prop, str)  # pyright: ignore[reportUnusedCallResult]
    assert_type(obj.any_prop, str)  # pyright: ignore[reportUnusedCallResult]

    # pin.pre → return type on both class and instance access.
    assert_type(Foo.pre_prop, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(obj.pre_prop, int)  # pyright: ignore[reportUnusedCallResult]

    # pin.post → return type on both class and instance access.
    assert_type(Foo.post_prop, int)  # pyright: ignore[reportUnusedCallResult]
    assert_type(obj.post_prop, int)  # pyright: ignore[reportUnusedCallResult]
