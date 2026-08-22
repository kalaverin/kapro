"""Known descriptor inconsistencies captured as expected failures."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass

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


def test_bound_property_on_frozen_dataclass_raises() -> None:
    """Frozen instances should be immutable for all instance descriptors."""

    class Owner:
        attr = bound_property(lambda node: node.value * 2)

    descriptor = Owner.__dict__["attr"]
    frozen = _Frozen(7)
    with pytest.raises(FrozenInstanceError):
        descriptor.__get__(frozen, Owner)


def test_frozen_dataclass_cached_and_bound_property_agree() -> None:
    """Both cached and bound instance properties raise FrozenInstanceError."""

    class Owner:
        bp = bound_property(lambda node: node.value * 2)
        cp = cached_property(lambda node: node.value * 2)

    descriptor_bp = Owner.__dict__["bp"]
    descriptor_cp = Owner.__dict__["cp"]
    frozen = _Frozen(7)
    with pytest.raises(FrozenInstanceError):
        descriptor_bp.__get__(frozen, Owner)
    with pytest.raises(FrozenInstanceError):
        descriptor_cp.__get__(frozen, Owner)


def test_pre_cached_property_on_slots_works() -> None:
    """pre_cached_property skips instance caching, so slots should be fine."""

    class Slotted:
        __slots__ = ()
        attr = pre_cached_property(lambda _: 42)

    assert Slotted().attr == 42


def test_mixed_cached_property_on_slots_raises() -> None:
    """mixed_cached_property needs instance __dict__; slots raise TypeError."""

    class Slotted:
        __slots__ = ()
        attr = mixed_cached_property(lambda _: 42)

    with pytest.raises(TypeError):
        Slotted().attr
