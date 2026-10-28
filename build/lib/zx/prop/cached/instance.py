"""Instance-level cached property descriptor.

This module defines :class:`cached_property` — the caching equivalent of
:class:`zx.prop.primitives.bound_property`.  It stores computed
values in a per-instance dictionary named ``__instance_memoized__`` and
supports parent-aware resolution (via inheritance from
:class:`class_parent_cached_property`).
"""

# ruff: noqa: ANN401, N801

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import FrozenInstanceError
from functools import cached_property as base_cached_property
from types import NoneType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    TypeVar,
    cast,
    overload,
    override,
)

from zx.core import Is, Who

from zx.prop.cached.klass import class_parent_cached_property
from zx.prop.primitives import ContextFaultError, is_frozen, parent_call

__all__ = ("cached_property",)

T_co = TypeVar("T_co", covariant=True)
R = TypeVar("R")


class cached_property[T_co](class_parent_cached_property[T_co]):
    klass: ClassVar[bool | NoneType] = False

    @base_cached_property
    @override
    def title(self) -> str:
        return f"instance data-descriptor {Who.Addr(self)}".strip()

    @override
    def get_node(self, node: Any) -> Any:
        if node is None or Is.Class(node):
            msg = f"{self.header_with_context(node)}, node={node!r}"
            if node is None and (not self.klass):
                msg = f"{msg}; looks like a non-instance invocation"
            raise ContextFaultError(msg)
        return node

    @override
    def get_cache(self, node: Any) -> dict[str, Any]:
        pivot = self.get_node(node)

        if is_frozen(pivot):
            msg = (
                f"{self.header_with_context(pivot)} is frozen "
                "and cannot be cached"
            )
            raise FrozenInstanceError(msg)

        cache = getattr(pivot, "__dict__", None)
        if cache is None:
            msg = f"{self.header_with_context(pivot)} has no __dict__"
            raise TypeError(msg)

        name = "__instance_memoized__"
        with suppress(KeyError):
            return cache[name]

        new_cache: dict[str, Any] = {}
        cache[name] = new_cache
        return new_cache

    @overload
    def __get__(
        self,
        instance: None,
        klass: Any = ...,
    ) -> cached_property[T_co]: ...

    @overload
    def __get__(
        self,
        instance: object,
        klass: Any = ...,
    ) -> T_co: ...

    @override
    def __get__(
        self,
        instance: object | None,
        klass: Any = None,
    ) -> cached_property[T_co] | T_co:
        if instance is None:
            raise ContextFaultError(self.header_with_context(klass))
        return self.call(instance)

    if TYPE_CHECKING:

        @staticmethod
        @override
        def with_parent(function: Callable[..., R]) -> cached_property[R]: ...


def _cached_property_with_parent[R](
    function: Callable[..., R],
) -> cached_property[R]:
    return cached_property(cast("Callable[[Any], R]", parent_call(function)))


cached_property.with_parent = staticmethod(  # type: ignore[method-assign]
    _cached_property_with_parent,
)
