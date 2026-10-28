from __future__ import annotations

from collections.abc import Callable
from functools import cached_property
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, override

from zx.prop.cached.klass import (
    class_cached_property,
    class_parent_cached_property,
)

__all__ = ("mixed_cached_property", "mixed_parent_cached_property")
T_co: Any
R = TypeVar("R")
T = TypeVar("T")

class _MixedParentCachedPropertyFactory(Protocol):
    def __call__(
        self,
        function: Callable[[Any], T],
    ) -> mixed_parent_cached_property[T]: ...

class mixed_parent_cached_property[T_co](
    class_parent_cached_property[T_co],
):
    @cached_property
    @override
    def title(self) -> str: ...
    @override
    def header_with_context(self, node: Any) -> str: ...
    @override
    def get_node(self, node: Any) -> Any: ...
    @override
    def get_cache(self, node: Any) -> dict[str, Any]: ...
    @override
    def __get__(self, instance: Any, klass: Any = None) -> T_co: ...

    if TYPE_CHECKING:
        @staticmethod
        @override
        def with_parent(
            function: Callable[..., R],
        ) -> mixed_parent_cached_property[R]: ...

def _mixed_parent_cached_property_with_parent[R](
    function: Callable[..., R],
) -> mixed_parent_cached_property[R]: ...

class mixed_cached_property[T_co](
    mixed_parent_cached_property[T_co],
):
    @override
    def get_node(self, node: Any) -> Any: ...
    @class_cached_property
    def here(cls) -> _MixedParentCachedPropertyFactory: ...

    if TYPE_CHECKING:
        @staticmethod
        @override
        def with_parent(
            function: Callable[..., R],
        ) -> mixed_cached_property[R]: ...

def _mixed_cached_property_with_parent[R](
    function: Callable[..., R],
) -> mixed_cached_property[R]: ...
