"""Known descriptor inconsistencies captured as expected failures."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from kapro.cached import (
    cached_property,
    mixed_cached_property,
    pre_cached_property,
)
from kapro.primitives import bound_property


@dataclass(frozen=True)
class _Frozen:
    value: int = 5


@pytest.mark.xfail(
    reason="bound_property writes to __dict__ directly, bypassing frozen",
)
def test_bound_property_on_frozen_dataclass_raises() -> None:
    """Frozen instances should be immutable for all instance descriptors."""

    class Owner:
        attr = bound_property(lambda node: node.value * 2)

    Owner.attr.__get__(_Frozen(7), Owner)


@pytest.mark.xfail(
    reason="cached_property fails on frozen, bound_property silently works",
)
def test_frozen_dataclass_cached_and_bound_property_agree() -> None:
    """Both cached and bound instance properties should behave the same."""

    class Owner:
        bp = bound_property(lambda node: node.value * 2)
        cp = cached_property(lambda node: node.value * 2)

    frozen = _Frozen(7)
    assert Owner.bp.__get__(frozen, Owner) == 14
    assert Owner.cp.__get__(frozen, Owner) == 14


@pytest.mark.xfail(
    reason="pre_cached_property still tries to create an instance cache",
)
def test_pre_cached_property_on_slots_works() -> None:
    """pre_cached_property skips instance caching, so slots should be fine."""

    class Slotted:
        __slots__ = ()
        attr = pre_cached_property(lambda _: 42)

    assert Slotted().attr == 42


@pytest.mark.xfail(
    reason="mixed_cached_property does not handle missing __dict__",
)
def test_mixed_cached_property_on_slots_works() -> None:
    """cached_property handles slots; mixed_cached_property should too."""

    class Slotted:
        __slots__ = ()
        attr = mixed_cached_property(lambda _: 42)

    assert Slotted().attr == 42
