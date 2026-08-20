"""Class-level cached property descriptors.

This module implements the ``class_cached_property`` family.  Both variants
store their cache in a dictionary named ``__class_memoized__`` attached to
the class object (either the concrete class or the owning parent class,
depending on the variant).

In addition, :class:`CustomCallbackMixin` provides a pluggable cache
invalidation mechanism via the ``is_actual`` callback.
"""

# ruff: noqa: ANN401, N801

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from functools import cached_property, partial
from time import time
from typing import TYPE_CHECKING, Any, TypeVar, cast, override

from kain import Is, Who
from kain.internals import get_owner

from kapro.primitives import (
    AttributeExceptionError,
    BaseProperty,
    ContextFaultError,
    Nothing,
    parent_call,
)

__all__ = ("class_cached_property", "class_parent_cached_property")

T_co = TypeVar("T_co", covariant=True)
R = TypeVar("R")


class CustomCallbackMixin:
    """Mixin that adds TTL and custom callback support to cached descriptors.

    The mixin is designed to be combined with a descriptor class (e.g.
    ``class_parent_cached_property``).  It exposes two factory classmethods:

    * :meth:`by` / :meth:`expired_by` - supply your own ``is_actual``
      predicate.
    * :meth:`ttl` - supply a numeric lifetime in seconds.

    ``is_actual`` signature
    -----------------------
    ``is_actual(self, node, stamp) -> bool | float``

    * When called **without** ``stamp`` (during ``__set__``), it should
      return the *new* stamp to store alongside the cached value.
    * When called **with** ``stamp`` (during ``call`` / cache lookup), it
      should return ``True`` if the cached value is still valid.

    If ``is_actual`` is ``Nothing`` (the default), the cache never expires.
    """

    @classmethod
    def by(cls, callback: Callable[..., Any]) -> Callable[..., Any]:
        return partial(cls, is_actual=callback)  # type: ignore[call-arg]

    @classmethod
    def ttl(cls, expire: float) -> Callable[..., Any]:
        if not isinstance(expire, float | int):  # type: ignore[redundant-expr]
            msg = f"expire must be float or int, not {Who.Cast(expire)}"
            raise TypeError(msg)
        if expire <= 0:
            msg = f"expire must be a positive number, not {Who.Cast(expire)}"
            raise ValueError(msg)

        def is_actual(_self: Any, _node: Any, value: Any = Nothing) -> Any:
            if isinstance(value, float):
                return value + expire > time()
            return time()

        return cls.by(is_actual)


class class_parent_cached_property[T_co](
    BaseProperty[T_co],
    CustomCallbackMixin,
):
    """Class-level cached descriptor that stores cache on the *owning* class.

    The *owning* class is determined by :func:`kapro.internals.get_owner`,
    which walks the MRO to find the class that actually defines this
    descriptor.  This means that if ``Base`` defines the property and
    ``Child(Base)`` is accessed, the cache lives on ``Base`` — so all
    subclasses share the same cached value.

    Cache structure
    ---------------
    The cache dict is stored in the class ``__dict__`` under the key
    ``__class_memoized__``.  Each entry is keyed by the property ``name``.

    * Without ``is_actual`` → ``cache[name] = value``
    * With ``is_actual``    → ``cache[name] = (value, stamp)``
    """

    def __init__(
        self,
        function: Callable[[Any], T_co],
        is_actual: Any = Nothing,
    ) -> None:
        super().__init__(function)
        if method := getattr(Is.classOf(self), "is_actual", None):
            if is_actual:
                msg = (
                    f"{Who.Is(self)}.is_actual method ({Who.Cast(method)}) "
                    "can't be overridden by the is_actual keyword argument"
                )
                raise TypeError(msg)
            is_actual = method
        self.is_actual: Any = is_actual

    @cached_property
    @override
    def title(self) -> str:
        return f"class data-descriptor {Who.Addr(self)}".strip()

    @override
    def header_with_context(self, node: Any) -> str:
        return self.footer(node)

    def get_node(self, node: Any) -> Any:
        if node is None or not Is.Class(node):
            msg = f"{self.header_with_context(node)}, node={node!r}"
            raise ContextFaultError(msg)
        result = get_owner(node, self.name)
        return result if result is not None else node

    def get_cache(self, node: Any) -> dict[str, Any]:
        self.get_node(node)
        name = "__class_memoized__"
        if hasattr(node, "__dict__"):
            with suppress(KeyError):
                return cast("dict[str, Any]", node.__dict__[name])
        cache: dict[str, Any] = {}
        setattr(node, name, cache)
        return cache

    @override
    def call(self, node: Any, *args: Any, **kw: Any) -> T_co:
        pivot = self.get_node(node)
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

    def __get__(self, instance: Any, klass: Any = None) -> T_co:
        return self.call(klass)

    def __set__(self, node: Any, value: Any) -> Any:
        cache = self.get_cache(node)
        if not self.is_actual:
            cache[self.name] = value
        else:
            cache[self.name] = (value, self.is_actual(self, node))
        return value

    def __delete__(self, node: Any) -> None:
        cache = self.get_cache(node)
        with suppress(KeyError):
            del cache[self.name]

    if TYPE_CHECKING:

        @staticmethod
        @override
        def with_parent(  # pyright: ignore[reportIncompatibleMethodOverride]
            function: Callable[..., R],
        ) -> class_parent_cached_property[R]: ...


def _class_parent_cached_property_with_parent[R](
    function: Callable[..., R],
) -> class_parent_cached_property[R]:
    return class_parent_cached_property(
        cast("Callable[[Any], R]", parent_call(function)),
    )


class_parent_cached_property.with_parent = staticmethod(  # type: ignore[method-assign]
    _class_parent_cached_property_with_parent,
)


class class_cached_property[T_co](
    class_parent_cached_property[T_co],
):
    """Class-level cached descriptor that stores cache on the accessed class.

    This is the "plain" variant of ``class_parent_cached_property``.  Rather
    than resolving the *owning* parent via ``get_owner``, it caches directly
    on ``node`` (the class that was passed to ``__get__``).  Consequently,
    each subclass maintains its own independent cache.
    """

    @override
    def get_node(self, node: Any) -> Any:
        if node is None or not Is.Class(node):
            msg = f"{self.header_with_context(node)}, node={node!r}"
            raise ContextFaultError(msg)
        return node

    @class_parent_cached_property
    def here(cls) -> type[class_parent_cached_property[Any]]:  # noqa: N805
        return class_parent_cached_property

    if TYPE_CHECKING:

        @staticmethod
        @override
        def with_parent(
            function: Callable[..., R],
        ) -> class_cached_property[R]: ...


def _class_cached_property_with_parent[R](
    function: Callable[..., R],
) -> class_cached_property[R]:
    return class_cached_property(
        cast("Callable[[Any], R]", parent_call(function)),
    )


class_cached_property.with_parent = staticmethod(  # type: ignore[method-assign]
    _class_cached_property_with_parent,
)
