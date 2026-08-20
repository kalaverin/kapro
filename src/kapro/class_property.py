"""Class-level and mixed-level property descriptors.

The descriptors here extend :class:`BaseProperty` so that the wrapped function
receives the *class* itself (for ``class_property``) or either the instance or
the class (for ``mixed_property``) as its first positional argument.
"""

# ruff: noqa: ANN401, N801

from __future__ import annotations

from collections.abc import Callable
from functools import cached_property
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

from kain import Is, Who
from kain.internals import get_owner

from kapro.primitives import (
    AttributeExceptionError,
    BaseProperty,
    ContextFaultError,
    parent_call,
)

__all__ = ("class_property", "mixed_property")

T_co = TypeVar("T_co", covariant=True)
R = TypeVar("R")


class class_property[T_co](BaseProperty[T_co]):
    """Descriptor that calls ``function(klass)``.

    When the attribute is accessed as ``MyClass.attr`` *or*
    ``MyClass().attr``, the underlying function is invoked with ``MyClass``
    (the class object) as the first argument.  This is analogous to a
    ``classmethod``, but for properties.

    The descriptor also resolves the *owning* class via
    :func:`kapro.internals.get_owner`.  If the property is inherited, the
    ``node`` passed to ``get_owner`` ensures the MRO lookup starts from the
    concrete subclass, so mix-ins and subclassing behave correctly.
    """

    # ``klass`` is used by error-formatting utilities to indicate that this
    # descriptor expects a class-like ``node``.
    klass: ClassVar[bool | NoneType] = True

    def __init__(self, function: Callable[[Any], T_co]) -> None:
        super().__init__(function)

    @cached_property
    @override
    def title(self) -> str:
        return f"class descriptor {Who.Addr(self)}".strip()

    @override
    def header_with_context(self, node: Any) -> str:
        return self.footer(node)

    def get_node(self, node: Any) -> Any:
        if node is None or not Is.Class(node):
            msg = f"{self.header_with_context(node)}, node={node!r}"
            raise ContextFaultError(msg)
        result = get_owner(node, self.name)
        return result if result is not None else node

    @override
    def call(self, node: Any, *args: Any, **kw: Any) -> T_co:
        self.get_node(node)
        try:
            return self.function(node)
        except AttributeError as e:
            raise AttributeExceptionError(e) from e

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

    def __get__(
        self,
        instance: object | None,
        klass: type[Any] | None = None,
    ) -> T_co:
        return self.call(klass)

    if TYPE_CHECKING:

        @staticmethod
        @override
        def with_parent(  # pyright: ignore[reportIncompatibleMethodOverride]
            function: Callable[..., R],
        ) -> class_property[R]: ...


class mixed_property[T_co](BaseProperty[T_co]):
    """Descriptor that calls ``function(instance_or_klass)``.

    A *mixed* property works on both instances and classes:

    * ``obj.attr``   → ``function(obj)``
    * ``Cls.attr``   → ``function(Cls)``

    Unlike ``class_property``, the instance itself (not the class) is passed
    when accessed on an instance.  Like ``class_property``, ``get_owner`` is
    used to resolve the defining class when ``node`` is a class.
    """

    klass: ClassVar[bool | NoneType] = None

    def __init__(self, function: Callable[[Any], T_co]) -> None:
        super().__init__(function)

    @cached_property
    @override
    def title(self) -> str:
        return f"mixed descriptor {Who.Addr(self)}".strip()

    @override
    def header_with_context(self, node: Any) -> str:
        return self.footer(node, "mixed")

    def get_node(self, node: Any) -> Any:
        if node is None:
            msg = f"{self.header_with_context(node)}, node={node!r}"
            raise ContextFaultError(msg)
        return get_owner(node, self.name) if Is.Class(node) else node

    @override
    def call(self, node: Any, *args: Any, **kw: Any) -> T_co:
        self.get_node(node)
        try:
            return self.function(node)
        except AttributeError as e:
            raise AttributeExceptionError(e) from e

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

    def __get__(
        self,
        instance: object | None,
        klass: type[Any] | None = None,
    ) -> T_co:
        if instance is None:
            return self.call(klass)
        return self.call(instance)

    if TYPE_CHECKING:

        @staticmethod
        @override
        def with_parent(  # pyright: ignore[reportIncompatibleMethodOverride]
            function: Callable[..., R],
        ) -> mixed_property[R]: ...


def _class_property_with_parent[R](
    function: Callable[..., R],
) -> class_property[R]:
    return class_property(cast("Callable[[Any], R]", parent_call(function)))


def _mixed_property_with_parent[R](
    function: Callable[..., R],
) -> mixed_property[R]:
    return mixed_property(cast("Callable[[Any], R]", parent_call(function)))


class_property.with_parent = staticmethod(  # type: ignore[method-assign]
    _class_property_with_parent,
)
mixed_property.with_parent = staticmethod(  # type: ignore[method-assign]
    _mixed_property_with_parent,
)
