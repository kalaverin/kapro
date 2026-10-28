"""Mixed-level cached property descriptors.

A *mixed* property works on both instances and classes.  The cache is stored
in a dictionary whose name depends on the access context:

* Instance access → ``__instance_memoized__``
* Class access    → ``__class_memoized__``

Like the other cached families, there are two variants:

* ``mixed_cached_property`` - caches directly on the accessed node.
* ``mixed_parent_cached_property`` - resolves the owning class via
  :func:`zx.prop.internals.get_owner` when accessed on a class.
"""

# ruff: noqa: N801

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import FrozenInstanceError
from functools import cached_property
from typing import TYPE_CHECKING, Any, TypeVar, cast, override

from zx.core import Is, Who
from zx.core.internals import get_owner

from zx.prop.cached.klass import (
    class_cached_property,
    class_parent_cached_property,
)
from zx.prop.primitives import ContextFaultError, is_frozen, parent_call

__all__ = ("mixed_cached_property", "mixed_parent_cached_property")

T_co = TypeVar("T_co", covariant=True)
R = TypeVar("R")


class mixed_parent_cached_property[T_co](
    class_parent_cached_property[T_co],
):
    """Mixed cached descriptor with parent-aware class caching.

    When accessed on a class, the cache is stored on the *owning* class
    (found via ``get_owner``).  When accessed on an instance, the cache is
    stored on the instance itself (``__instance_memoized__``).
    """

    @cached_property
    @override
    def title(self) -> str:
        return f"mixed data-descriptor {Who.Addr(self)}".strip()

    @override
    def header_with_context(self, node: Any) -> str:
        return self.footer(node, "mixed")

    @override
    def get_node(self, node: Any) -> Any:
        if node is None:
            msg = f"{self.header_with_context(node)}, node={node!r}"
            raise ContextFaultError(msg)
        result = get_owner(node, self.name)
        return result if result is not None and Is.Class(node) else node

    @override
    def get_cache(self, node: Any) -> dict[str, Any]:
        pivot = self.get_node(node)

        name = f"__{('instance', 'class')[Is.Class(pivot)]}_memoized__"
        if Is.Class(pivot):
            if hasattr(pivot, "__dict__"):
                with suppress(KeyError):
                    return cast("dict[str, Any]", pivot.__dict__[name])
            cache: dict[str, Any] = {}
            setattr(pivot, name, cache)
            return cache

        if is_frozen(pivot):
            msg = (
                f"{self.header_with_context(pivot)} is frozen "
                "and cannot be cached"
            )
            raise FrozenInstanceError(msg)

        instance_cache = getattr(pivot, "__dict__", None)
        if instance_cache is None:
            msg = f"{self.header_with_context(pivot)} has no __dict__"
            raise TypeError(msg)

        with suppress(KeyError):
            return instance_cache[name]

        new_cache: dict[str, Any] = {}
        instance_cache[name] = new_cache
        return new_cache

    @override
    def __get__(self, instance: Any, klass: Any = None) -> T_co:
        if instance is None:
            return self.call(klass)
        return self.call(instance)

    if TYPE_CHECKING:

        @staticmethod
        @override
        def with_parent(
            function: Callable[..., R],
        ) -> mixed_parent_cached_property[R]: ...


def _mixed_parent_cached_property_with_parent[R](
    function: Callable[..., R],
) -> mixed_parent_cached_property[R]:
    return mixed_parent_cached_property(
        cast("Callable[[Any], R]", parent_call(function)),
    )


mixed_parent_cached_property.with_parent = staticmethod(  # type: ignore[method-assign]
    _mixed_parent_cached_property_with_parent,
)


class mixed_cached_property[T_co](
    mixed_parent_cached_property[T_co],
):
    """Mixed cached descriptor that caches directly on the accessed node.

    This is the plain variant: no ``get_owner`` lookup is performed.
    The cache lives either on the instance or on the concrete class that
    was used to access the attribute.
    """

    @override
    def get_node(self, node: Any) -> Any:
        if node is None:
            msg = f"{self.header_with_context(node)}, node={node!r}"
            raise ContextFaultError(msg)
        return node

    @class_cached_property
    def here(cls) -> type[mixed_parent_cached_property[Any]]:  # noqa: N805
        return mixed_parent_cached_property

    if TYPE_CHECKING:

        @staticmethod
        @override
        def with_parent(
            function: Callable[..., R],
        ) -> mixed_cached_property[R]: ...


def _mixed_cached_property_with_parent[R](
    function: Callable[..., R],
) -> mixed_cached_property[R]:
    return mixed_cached_property(
        cast("Callable[[Any], R]", parent_call(function)),
    )


mixed_cached_property.with_parent = staticmethod(  # type: ignore[method-assign]
    _mixed_cached_property_with_parent,
)
