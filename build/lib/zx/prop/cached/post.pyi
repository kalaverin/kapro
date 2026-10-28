from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, override

from zx.prop.cached.klass import class_cached_property
from zx.prop.cached.mixed import (
    mixed_cached_property,
    mixed_parent_cached_property,
)

__all__ = ("post_cached_property", "post_parent_cached_property")
T_co: Any
T = TypeVar("T")
R = TypeVar("R")

class _PostParentCachedPropertyFactory(Protocol):
    def __call__(
        self,
        function: Callable[[Any], T],
    ) -> post_parent_cached_property[T]: ...

class post_parent_cached_property[T_co](
    mixed_parent_cached_property[T_co],
):
    @override
    def __set__(self, node: Any, value: Any) -> Any: ...

    if TYPE_CHECKING:
        @staticmethod
        @override
        def with_parent(
            function: Callable[..., R],
        ) -> post_parent_cached_property[R]: ...

class post_cached_property[T_co](
    mixed_cached_property[T_co],
):
    @override
    def __set__(self, node: Any, value: Any) -> Any: ...
    @class_cached_property
    @override
    def here(
        cls,
    ) -> _PostParentCachedPropertyFactory: ...

    if TYPE_CHECKING:
        @staticmethod
        @override
        def with_parent(
            function: Callable[..., R],
        ) -> post_cached_property[R]: ...
