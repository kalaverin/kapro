"""Post-cached mixed property descriptors.

``post_*`` descriptors are mixed properties that **only cache when accessed on
an instance**.  When accessed on a class, the value is computed every time and
is *not* stored in the class cache.

This is useful for properties that are expensive per-instance but should still
be readable directly from the class (e.g. for introspection or default-value
inspection) without polluting the class-level cache.
"""

# ruff: noqa: N801

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast, override

from zx.core import Is
from zx.prop.cached.klass import class_cached_property
from zx.prop.cached.mixed import (
    mixed_cached_property,
    mixed_parent_cached_property,
)
from zx.prop.primitives import parent_call

__all__ = ("post_cached_property", "post_parent_cached_property")

T_co = TypeVar("T_co", covariant=True)
R = TypeVar("R")


class post_parent_cached_property[T_co](
    mixed_parent_cached_property[T_co],
):
    """Mixed parent-cached descriptor that skips class caching.

    Overrides ``__set__`` so that when ``node`` is a class, the value is
    returned immediately without being written to the cache dict.  When
    ``node`` is an instance, normal instance caching applies.
    """

    @override
    def __set__(self, node: Any, value: Any) -> Any:
        self.get_node(node)
        if Is.Class(node):
            return value
        return super().__set__(node, value)


class post_cached_property[T_co](
    mixed_cached_property[T_co],
):
    """Mixed cached descriptor that skips class caching.

    Same semantics as ``post_parent_cached_property`` but caches directly on
    the accessed instance without owner-resolution for the class side.
    """

    @override
    def __set__(self, node: Any, value: Any) -> Any:
        self.get_node(node)
        if Is.Class(node):
            return value
        return super().__set__(node, value)

    @class_cached_property
    @override
    def here(
        cls,  # noqa: N805
    ) -> type[post_parent_cached_property[Any]]:
        return post_parent_cached_property


def _post_parent_cached_property_with_parent[R](
    function: Callable[..., R],
) -> post_parent_cached_property[R]:
    return post_parent_cached_property(
        cast("Callable[[Any], R]", parent_call(function)),
    )


def _post_cached_property_with_parent[R](
    function: Callable[..., R],
) -> post_cached_property[R]:
    return post_cached_property(
        cast("Callable[[Any], R]", parent_call(function)),
    )


post_parent_cached_property.with_parent = staticmethod(  # type: ignore[method-assign]
    _post_parent_cached_property_with_parent,
)
post_cached_property.with_parent = staticmethod(  # type: ignore[method-assign]
    _post_cached_property_with_parent,
)
