"""Static type assertions for kapro.special.proxy_to.

Run ``basedpyright tests/test_proxy_to_types.py`` or
``basedmypy tests/test_proxy_to_types.py`` to verify.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, assert_type

from kapro import pin
from kapro.cached import cached_property
from kapro.class_property import class_property, mixed_property
from kapro.primitives import bound_property
from kapro.special.proxy_to import proxy_to

TYPE_TEST_POWER = 42


class _Engine:
    def power(self) -> int:
        return TYPE_TEST_POWER


class _Config:
    data: ClassVar[dict[str, int]] = {"power": 42}


def test_type_inference_dummy() -> None:
    """Runtime placeholder; real checking is done by static analyzers."""


@proxy_to("engine", "power")
class BoundProxy:
    engine = _Engine()


@proxy_to("engine", "power", binder=pin)
class PinProxy:
    engine = _Engine()


@proxy_to("engine", "power", binder=pin.native)
class NativeProxy:
    engine = _Engine()


@proxy_to("engine", "power", binder=class_property)
class ClassProxy:
    engine = _Engine()


@proxy_to("engine", "power", binder=mixed_property)
class MixedProxy:
    engine = _Engine()


if TYPE_CHECKING:
    # Decorating a class preserves its type.
    assert_type(BoundProxy, type[BoundProxy])

    # bound_property instance access -> wrapped return type.
    assert_type(BoundProxy().power, int)
    # bound_property class access -> descriptor type.
    assert_type(
        BoundProxy.power,
        bound_property[int],
    )

    # pin instance access -> wrapped return type.
    assert_type(PinProxy().power, int)
    # pin class access -> descriptor type.
    assert_type(PinProxy.power, pin[int])

    # pin.native maps to cached_property.
    assert_type(NativeProxy().power, int)
    assert_type(NativeProxy.power, cached_property[int])

    # class_property works on both class and instance.
    assert_type(ClassProxy.power, int)
    assert_type(ClassProxy().power, int)

    # mixed_property works on both class and instance.
    assert_type(MixedProxy.power, int)
    assert_type(MixedProxy().power, int)
