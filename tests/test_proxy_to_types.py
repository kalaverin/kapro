"""Static type assertions for zx.prop.special.proxy_to.

Run ``basedpyright tests/test_proxy_to_types.py`` or
``basedmypy tests/test_proxy_to_types.py`` to verify.

NOTE: ``proxy_to`` attaches attributes dynamically, so static analyzers
cannot infer the forwarded attributes from the decorator call.  The tests
below only verify that the decorated class itself keeps its type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, assert_type

from faker import Faker

from zx.prop.special.proxy_to import proxy_to

TYPE_STUB_SEED: Final[int] = 0
_TYPE_FAKER = Faker(["en_US"])
_TYPE_FAKER.seed_instance(TYPE_STUB_SEED)


class _Engine:
    def power(self) -> int:
        return _TYPE_FAKER.pyint()


@proxy_to("engine", "power")
class BoundProxy:
    engine = _Engine()


@proxy_to("engine", "power", binder=None)
class RawProxy:
    engine = _Engine()


def test_type_inference_dummy() -> None:
    """Runtime placeholder; real checking is done by static analyzers."""


if TYPE_CHECKING:
    # Decorating a class preserves its type.
    assert_type(BoundProxy, type[BoundProxy])  # pyright: ignore[reportUnusedCallResult]
    assert_type(RawProxy, type[RawProxy])  # pyright: ignore[reportUnusedCallResult]
