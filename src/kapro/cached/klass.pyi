from __future__ import annotations

from collections.abc import Callable
from functools import cached_property
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, override

from kapro.primitives import (
    BaseProperty,
    Nothing,
)

__all__ = ("class_cached_property", "class_parent_cached_property")
T_co: Any
R = TypeVar("R")
T = TypeVar("T")

class _ClassParentCachedPropertyFactory(Protocol):
    def __call__(
        self,
        function: Callable[[Any], T],
    ) -> class_parent_cached_property[T]: ...

class CustomCallbackMixin:
    @classmethod
    def by(cls, callback: Callable[..., Any]) -> Callable[..., Any]: ...
    @classmethod
    def ttl(cls, expire: float) -> Callable[..., Any]: ...

class class_parent_cached_property[T_co](
    BaseProperty[T_co],
    CustomCallbackMixin,
):
    is_actual: Any
    def __init__(
        self: Any,
        function: Callable[[Any], T_co],
        is_actual: Any = Nothing,
    ) -> None: ...
    @cached_property
    @override
    def title(self) -> str: ...
    @override
    def header_with_context(self, node: Any) -> str: ...
    def get_node(self, node: Any) -> Any: ...
    def get_cache(self, node: Any) -> dict[str, Any]: ...
    @override
    def call(self, node: Any, *args: Any, **kw: Any) -> T_co: ...
    def __get__(self, instance: Any, klass: Any = None) -> T_co: ...
    def __set__(self, node: Any, value: Any) -> Any: ...
    def __delete__(self, node: Any) -> None: ...

    if TYPE_CHECKING:
        @staticmethod
        @override
        def with_parent(  # pyright: ignore[reportIncompatibleMethodOverride]
            function: Callable[..., R],
        ) -> class_parent_cached_property[R]: ...

def _class_parent_cached_property_with_parent[R](
    function: Callable[..., R],
) -> class_parent_cached_property[R]: ...

class class_cached_property[T_co](
    class_parent_cached_property[T_co],
):
    @override
    def get_node(self, node: Any) -> Any: ...
    @class_parent_cached_property
    def here(cls) -> _ClassParentCachedPropertyFactory: ...

    if TYPE_CHECKING:
        @staticmethod
        @override
        def with_parent(
            function: Callable[..., R],
        ) -> class_cached_property[R]: ...

def _class_cached_property_with_parent[R](
    function: Callable[..., R],
) -> class_cached_property[R]: ...
