"""Parameterized edge-case coverage for all kapro descriptors.

Matrix: descriptor kind x class kind (normal, frozen dataclass, slots,
single inheritance, diamond, mixin).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass
from typing import Any

import pytest
from faker import Faker

from kapro import pin
from kapro.cached import (
    cached_property,
    class_cached_property,
    mixed_cached_property,
    post_cached_property,
    pre_cached_property,
)
from kapro.class_property import class_property, mixed_property
from kapro.primitives import ContextFaultError, bound_property

# ------------------------------------------------------------------
# Expectation profiles
# ------------------------------------------------------------------


class _Profile:
    """Expected behavior for a descriptor kind."""

    def __init__(
        self,
        *,
        instance_works: bool,
        class_works: bool,
        instance_needs_dict: bool,
        caches_instance: bool,
        caches_class: bool,
    ) -> None:
        self.instance_works = instance_works
        self.class_works = class_works
        self.instance_needs_dict = instance_needs_dict
        self.caches_instance = caches_instance
        self.caches_class = caches_class


_PROFILES: dict[Any, _Profile] = {
    bound_property: _Profile(
        instance_works=True,
        class_works=False,
        instance_needs_dict=True,
        caches_instance=True,
        caches_class=False,
    ),
    pin: _Profile(
        instance_works=True,
        class_works=False,
        instance_needs_dict=True,
        caches_instance=True,
        caches_class=False,
    ),
    cached_property: _Profile(
        instance_works=True,
        class_works=False,
        instance_needs_dict=True,
        caches_instance=True,
        caches_class=False,
    ),
    class_cached_property: _Profile(
        instance_works=True,
        class_works=True,
        instance_needs_dict=False,
        caches_instance=False,
        caches_class=True,
    ),
    mixed_cached_property: _Profile(
        instance_works=True,
        class_works=True,
        instance_needs_dict=True,
        caches_instance=True,
        caches_class=True,
    ),
    pre_cached_property: _Profile(
        instance_works=True,
        class_works=True,
        instance_needs_dict=False,
        caches_instance=False,
        caches_class=True,
    ),
    post_cached_property: _Profile(
        instance_works=True,
        class_works=True,
        instance_needs_dict=True,
        caches_instance=True,
        caches_class=False,
    ),
    class_property: _Profile(
        instance_works=True,
        class_works=True,
        instance_needs_dict=False,
        caches_instance=False,
        caches_class=False,
    ),
    mixed_property: _Profile(
        instance_works=True,
        class_works=True,
        instance_needs_dict=False,
        caches_instance=False,
        caches_class=False,
    ),
}


_INSTANCE_EXCEPTIONS: dict[tuple[Any, str], type[BaseException]] = {
    (bound_property, "slots"): TypeError,
    (pin, "slots"): TypeError,
    (pin.native, "frozen_dataclass"): FrozenInstanceError,
    (pin.any, "frozen_dataclass"): FrozenInstanceError,
    (pin.any, "slots"): AttributeError,
    (pin.pre, "frozen_dataclass"): FrozenInstanceError,
    (pin.pre, "slots"): AttributeError,
    (pin.post, "frozen_dataclass"): FrozenInstanceError,
    (pin.post, "slots"): AttributeError,
}


_RESTRICTED_CLASS_KINDS = {"frozen_dataclass", "slots"}


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture(
    params=[
        pytest.param(bound_property, id="bound-property"),
        pytest.param(pin, id="pin"),
        pytest.param(pin.native, id="pin-native"),
        pytest.param(pin.cls, id="pin-cls"),
        pytest.param(pin.any, id="pin-any"),
        pytest.param(pin.pre, id="pin-pre"),
        pytest.param(pin.post, id="pin-post"),
        pytest.param(class_property, id="class-property"),
        pytest.param(mixed_property, id="mixed-property"),
    ],
)
def descriptor_kind(request: pytest.FixtureRequest) -> Any:
    """Parameterized descriptor factory."""
    return request.param


@pytest.fixture(
    params=[
        pytest.param("normal", id="normal"),
        pytest.param("frozen_dataclass", id="frozen-dataclass"),
        pytest.param("slots", id="slots"),
        pytest.param("single_inheritance", id="single-inheritance"),
        pytest.param("diamond", id="diamond"),
        pytest.param("mixin", id="mixin"),
    ],
)
def class_kind(request: pytest.FixtureRequest) -> str:
    """Parameterized class shape."""
    return request.param


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_class(descriptor: Any, kind: str, value: int) -> type:
    """Build a class (or subclass) carrying *descriptor* under ``attr``."""

    def compute(_node: object) -> int:
        return value

    if kind == "normal":

        class Sample:
            attr = descriptor(compute)

        return Sample

    if kind == "frozen_dataclass":

        @dataclass(frozen=True)
        class FrozenSample:
            attr = descriptor(compute)

        return FrozenSample

    if kind == "slots":

        class SlottedSample:
            __slots__ = ()
            attr = descriptor(compute)

        return SlottedSample

    if kind == "single_inheritance":

        class Base:
            attr = descriptor(compute)

        class Child(Base):
            pass

        return Child

    if kind == "diamond":

        class Base:
            attr = descriptor(compute)

        class A(Base):
            pass

        class B(Base):
            pass

        class Diamond(A, B):
            pass

        return Diamond

    if kind == "mixin":

        class Mixin:
            attr = descriptor(compute)

        class Base:
            pass

        class Mixed(Base, Mixin):
            pass

        return Mixed

    msg = f"unknown class kind: {kind}"
    raise ValueError(msg)


def _get_descriptor(cls: type, name: str) -> Any:
    """Walk the MRO and return the descriptor named *name*."""
    for base in cls.__mro__:
        if name in base.__dict__:
            return base.__dict__[name]
    msg = f"{name!r} not found on {cls!r}"
    raise AttributeError(msg)


def _has_instance_cache(instance: object, descriptor: Any) -> bool:
    """Check whether *descriptor* has cached *instance* in the right place."""
    name = descriptor.name
    if name in getattr(instance, "__dict__", {}):
        return True
    instance_memo = getattr(instance, "__dict__", {}).get(
        "__instance_memoized__",
    )
    return isinstance(instance_memo, dict) and name in instance_memo


def _has_class_cache(cls: type, descriptor: Any) -> bool:
    """Check whether *descriptor* has cached *cls* in the right place."""
    name = descriptor.name
    class_memo = cls.__dict__.get("__class_memoized__")
    return isinstance(class_memo, dict) and name in class_memo


# ------------------------------------------------------------------
# Matrix
# ------------------------------------------------------------------


class TestDescriptorEdgeCases:
    """GIVEN every descriptor kind on every class shape
    WHEN accessed on an instance or on the class
    THEN the expected behavior (works/raises/caches) is observed.
    """

    def test_descriptor_instance_access(
        self,
        fake: Faker,
        descriptor_kind: Any,
        class_kind: str,
    ) -> None:
        """GIVEN a descriptor on a class
        WHEN accessed on an instance
        THEN it works or raises as expected for that shape.
        """
        expected = fake.pyint()
        cls = _make_class(descriptor_kind, class_kind, expected)
        profile = _PROFILES[descriptor_kind]

        expected_exception = _INSTANCE_EXCEPTIONS.get(
            (descriptor_kind, class_kind),
        )

        if expected_exception is not None:
            instance = cls()
            with pytest.raises(expected_exception):
                _ = instance.attr
        elif not profile.instance_works:
            instance = cls()
            with pytest.raises(ContextFaultError):
                _ = instance.attr
        else:
            instance = cls()
            assert instance.attr == expected

            if profile.caches_instance and hasattr(instance, "__dict__"):
                descriptor = _get_descriptor(cls, "attr")
                assert _has_instance_cache(instance, descriptor)

    def test_descriptor_class_access(
        self,
        fake: Faker,
        descriptor_kind: Any,
        class_kind: str,
    ) -> None:
        """GIVEN a descriptor on a class
        WHEN accessed on the class itself
        THEN it works or raises as expected.
        """
        expected = fake.pyint()
        cls = _make_class(descriptor_kind, class_kind, expected)
        profile = _PROFILES[descriptor_kind]

        if profile.class_works:
            assert cls.attr == expected

            if profile.caches_class:
                descriptor = _get_descriptor(cls, "attr")
                assert _has_class_cache(cls, descriptor)
        else:
            with pytest.raises(ContextFaultError):
                _ = cls.attr

    def test_descriptor_function_receives_expected_node(
        self,
        fake: Faker,
        descriptor_kind: Any,
    ) -> None:
        """GIVEN a descriptor that captures its node
        WHEN accessed on instance then class
        THEN class-level descriptors receive the class on both accesses
        and mixed descriptors receive the appropriate node.
        """
        nodes: list[object] = []

        def capture(node: object) -> int:
            nodes.append(node)
            return fake.pyint()

        class Sample:
            attr = descriptor_kind(capture)

        profile = _PROFILES[descriptor_kind]
        instance = Sample()

        expected_exception = _INSTANCE_EXCEPTIONS.get(
            (descriptor_kind, "normal"),
        )

        if profile.instance_works and expected_exception is None:
            _ = instance.attr
            if descriptor_kind in {class_property, class_cached_property}:
                assert nodes[-1] is Sample
            else:
                assert nodes[-1] is instance

        if profile.class_works:
            _ = Sample.attr
            assert nodes[-1] is Sample
