from __future__ import annotations

from collections.abc import Callable
from functools import cached_property as base_cached_property
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    overload,
    override,
)

from kapro.cached.klass import class_parent_cached_property

__all__ = ("cached_property",)
T_co: Any
R = TypeVar("R")

class cached_property[T_co](class_parent_cached_property[T_co]):
    @base_cached_property
    @override
    def title(self) -> str: ...
    @override
    def get_node(self, node: Any) -> Any: ...
    @override
    def get_cache(self, node: Any) -> dict[str, Any]: ...
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
    @override  # type: ignore[misc]
    def __get__(
        self,
        instance: object | None,
        klass: Any = None,
    ) -> cached_property[T_co] | T_co: ...

    if TYPE_CHECKING:
        @staticmethod
        @override
        def with_parent(function: Callable[..., R]) -> cached_property[R]: ...

def _cached_property_with_parent[R](
    function: Callable[..., R],
) -> cached_property[R]: ...
