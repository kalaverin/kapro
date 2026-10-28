from __future__ import annotations

from collections.abc import Callable
from functools import cached_property
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    overload,
    override,
)

from zx.prop.primitives import (
    BaseProperty,
)

__all__ = ("class_property", "mixed_property")
T_co: Any
R = TypeVar("R")

class class_property[T_co](BaseProperty[T_co]):
    def __init__(self, function: Callable[[Any], T_co]) -> None: ...
    @cached_property
    @override
    def title(self) -> str: ...
    @override
    def header_with_context(self, node: Any) -> str: ...
    def get_node(self, node: Any) -> Any: ...
    @override
    def call(self, node: Any, *args: Any, **kw: Any) -> T_co: ...
    @overload
    def __get__(
        self,
        instance: None,
        klass: type[Any] | None = ...,
    ) -> T_co: ...
    @overload
    def __get__(
        self,
        instance: object,
        klass: type[Any] | None = ...,
    ) -> T_co: ...
    def __get__(  # type: ignore[misc]
        self,
        instance: object | None,
        klass: type[Any] | None = None,
    ) -> T_co: ...

    if TYPE_CHECKING:
        @staticmethod
        @override
        def with_parent(  # pyright: ignore[reportIncompatibleMethodOverride]
            function: Callable[..., R],
        ) -> class_property[R]: ...

class mixed_property[T_co](BaseProperty[T_co]):
    def __init__(self, function: Callable[[Any], T_co]) -> None: ...
    @cached_property
    @override
    def title(self) -> str: ...
    @override
    def header_with_context(self, node: Any) -> str: ...
    def get_node(self, node: Any) -> Any: ...
    @override
    def call(self, node: Any, *args: Any, **kw: Any) -> T_co: ...
    @overload
    def __get__(
        self,
        instance: None,
        klass: type[Any] | None = ...,
    ) -> T_co: ...
    @overload
    def __get__(
        self,
        instance: object,
        klass: type[Any] | None = ...,
    ) -> T_co: ...
    def __get__(  # type: ignore[misc]
        self,
        instance: object | None,
        klass: type[Any] | None = None,
    ) -> T_co: ...

    if TYPE_CHECKING:
        @staticmethod
        @override
        def with_parent(  # pyright: ignore[reportIncompatibleMethodOverride]
            function: Callable[..., R],
        ) -> mixed_property[R]: ...

def _class_property_with_parent[R](
    function: Callable[..., R],
) -> class_property[R]: ...
def _mixed_property_with_parent[R](
    function: Callable[..., R],
) -> mixed_property[R]: ...
