"""Pre-cached mixed property descriptors.

``pre_*`` descriptors are mixed properties that **only cache when accessed on
a class**.  When accessed on an instance, the value is computed every time
and is *not* stored in the instance cache.

This is useful for "pre-processing" or configuration-like properties that
should be memoized at the class level (because they are expensive to compute
and identical for all instances) but still callable on instances when needed.
"""

# ruff: noqa: N801

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from typing import Any, TypeVar, cast, override

from zx.core import Is
from zx.prop.cached.klass import class_cached_property
from zx.prop.cached.mixed import (
    mixed_cached_property,
    mixed_parent_cached_property,
)
from zx.prop.primitives import AttributeExceptionError, parent_call

__all__ = ("pre_cached_property", "pre_parent_cached_property")

T_co = TypeVar("T_co", covariant=True)
R = TypeVar("R")


class pre_parent_cached_property[T_co](
    mixed_parent_cached_property[T_co],
):
    """Mixed parent-cached descriptor that skips instance caching.

    Overrides ``__set__`` so that when ``node`` is an instance, the value
    is returned immediately without being written to the cache dict.  When
    ``node`` is a class, the normal parent-aware caching logic is used.
    """

    @override
    def call(self, node: Any, *args: Any, **kw: Any) -> T_co:
        pivot = self.get_node(node)

        if not Is.Class(pivot):
            try:
                return self.function(node)
            except AttributeError as e:
                raise AttributeExceptionError(e) from e

        with suppress(KeyError):
            stored = self.get_cache(pivot)[self.name]
            if not self.is_actual:
                return stored
            value, stamp = stored
            if self.is_actual(self, pivot, stamp) is True:
                return value

        try:
            value = self.function(node)
        except AttributeError as e:
            raise AttributeExceptionError(e) from e
        return self.__set__(pivot, value)

    @override
    def __set__(self, node: Any, value: Any) -> Any:
        self.get_node(node)
        if not Is.Class(node):
            return value
        return super().__set__(node, value)


class pre_cached_property[T_co](
    mixed_cached_property[T_co],
):
    """Mixed cached descriptor that skips instance caching.

    Same semantics as ``pre_parent_cached_property`` but caches directly on
    the accessed class rather than the owning parent class.
    """

    @override
    def call(self, node: Any, *args: Any, **kw: Any) -> T_co:
        pivot = self.get_node(node)

        if not Is.Class(pivot):
            try:
                return self.function(node)
            except AttributeError as e:
                raise AttributeExceptionError(e) from e

        with suppress(KeyError):
            stored = self.get_cache(pivot)[self.name]
            if not self.is_actual:
                return stored
            value, stamp = stored
            if self.is_actual(self, pivot, stamp) is True:
                return value

        try:
            value = self.function(node)
        except AttributeError as e:
            raise AttributeExceptionError(e) from e
        return self.__set__(pivot, value)

    @override
    def __set__(self, node: Any, value: Any) -> Any:
        self.get_node(node)
        if not Is.Class(node):
            return value
        return super().__set__(node, value)

    @class_cached_property
    @override
    def here(
        cls,  # noqa: N805
    ) -> type[pre_parent_cached_property[Any]]:
        return pre_parent_cached_property


def _pre_parent_cached_property_with_parent[R](
    function: Callable[..., R],
) -> pre_parent_cached_property[R]:
    return pre_parent_cached_property(
        cast("Callable[[Any], R]", parent_call(function)),
    )


def _pre_cached_property_with_parent[R](
    function: Callable[..., R],
) -> pre_cached_property[R]:
    return pre_cached_property(
        cast("Callable[[Any], R]", parent_call(function)),
    )


pre_parent_cached_property.with_parent = staticmethod(  # type: ignore[method-assign]
    _pre_parent_cached_property_with_parent,
)
pre_cached_property.with_parent = staticmethod(  # type: ignore[method-assign]
    _pre_cached_property_with_parent,
)
