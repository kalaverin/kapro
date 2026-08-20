"""Primitive building blocks for the ``kapro.properties`` descriptor system.

This module defines the exception hierarchy, helper utilities, and the two
foundational descriptor classes (:class:`BaseProperty` and
:class:`bound_property`) that the rest of the package builds upon.

Key concepts
------------

* **``BaseProperty``** - Abstract-ish base for all descriptors.  It provides
  introspective attributes (``name``, ``title``, ``header``) and the
  ``with_parent`` classmethod that enables *parent-calling* properties.
* **``bound_property``** - The simplest concrete descriptor.  It replaces an
  instance method, stores the computed value in the instance ``__dict__``, and
  raises on class-level access or deletion.
* **``parent_call``** - A function wrapper used by ``with_parent``.  It walks
  the MRO to find the *parent* descriptor with the same name, extracts its
  wrapped function, evaluates it, and then passes that result as the *second*
  positional argument to the user-defined override.
* **``extract_wrapped``** - Central registry of "how to get the original user
  function back out of a descriptor".  Needed by ``parent_call`` so that it
  can invoke the parent implementation with the same ``(node, *args, **kw)``
  signature.
"""

# ruff: noqa: ANN401, N801

from __future__ import annotations

from collections.abc import Callable
from functools import cached_property, wraps
from inspect import iscoroutinefunction
from typing import Any, Self, TypeVar, cast, overload, override

from kain import Is, Who
from kain.classes import Missing
from kain.internals import get_attr

__all__ = ("bound_property", "parent_call")
Nothing = Missing()

T_co = TypeVar("T_co", covariant=True)


def get_name(func: object) -> str:
    return cast("str", getattr(func, "__name__", "Unknown"))


class PropertyError(Exception): ...


class ContextFaultError(PropertyError):
    """Raised when a descriptor is accessed in an unsupported context.

    Example: accessing an instance-only property on the class, or a
    class-only property on an instance, or with ``node is None``.
    """


class ReadOnlyError(PropertyError):
    """Raised when an attempt is made to delete a read-only descriptor."""


class AttributeExceptionError(PropertyError):
    """Wraps an ``AttributeError`` raised inside a property getter.

    The builtin ``property`` swallows the original traceback context in some
    situations; this wrapper preserves the cause while producing a clean
    message derived from the original exception text.

    .. note::
        The class name intentionally ends in ``Exception`` rather than
        ``Error`` (hence the ``N818`` noqa).
    """

    def __init__(self, origin: BaseException) -> None:
        self.exception: BaseException = origin
        super().__init__(self.message)

    @cached_property
    def message(self) -> str:
        return str(self.exception).rsplit(":", 1)[-1]


def extract_wrapped(obj: Any) -> Callable[..., Any]:
    """Extract the original user function from a descriptor object.
    This is the inverse operation of wrapping a function inside a descriptor.
    It is used by :func:`parent_call` so that it can invoke the parent
    implementation with the same signature the user originally wrote.

    Supported descriptor types (in order of checking):

    1. :class:`bound_property` → returns ``obj.__get__``
    2. Subclasses of :class:`BaseProperty` → returns ``obj.call``
    3. Built-in :class:`property` → returns ``obj.fget``
    4. :class:`functools.cached_property` → returns ``obj.func``

    Args:
        obj: The descriptor object to unwrap.

    Returns:
        The original user function wrapped by ``obj``.

    Raises:
        NotImplementedError: If ``obj`` is not one of the supported
            descriptor types.
    """

    if Is.subclass(obj, bound_property):
        return obj.__get__

    if Is.subclass(obj, BaseProperty):
        return obj.call

    if Is.subclass(obj, property):
        return obj.fget

    if Is.subclass(obj, cached_property):
        return obj.func

    msg = (
        f"couldn't extract wrapped function from {Who.Is(obj)}: "
        "replace it with @property, @cached_property, "
        f"@{Who.Is(bound_property)}, or other descriptor derived "
        f"from {Who.Is(BaseProperty)}"
    )
    raise NotImplementedError(msg)


def parent_call(func: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap ``func`` so that it receives the parent descriptor's value first.

    This is the engine behind ``BaseProperty.with_parent``.  When a property
    is created ``with_parent``, the user function is wrapped with this
    decorator.  At runtime it does the following:

    1. Walk the MRO of ``node``'s class to find the *parent* descriptor with
       the same ``__name__`` as ``func``.
    2. Use :func:`extract_wrapped` to pull out the parent's implementation.
    3. Call that parent implementation, passing ``node`` plus any extra
       ``*args, **kw``.
    4. Call the user's ``func``, injecting the parent result as the *second*
       positional argument (right after ``node``).

    The ``index`` parameter to :func:`kapro.internals.get_attr` is computed
    with the expression ``func.__name__ not in Is.classOf(node).__dict__``.
    Because ``bool`` is a subclass of ``int`` in Python, this yields:

    * ``False`` (i.e. ``0``) when the current class *overrides* the property —
      we want the first match in the MRO **excluding** the current class,
      which is the immediate parent implementation.
    * ``True`` (i.e. ``1``) when the current class *inherits* the property
      without overriding — we skip the first match (the inherited parent)
      and take the next one up the chain.

    Args:
        func: The user-defined override function.

    Returns:
        A wrapper that supplies ``func(node, parent_value, *args, **kw)``.

    Raises:
        RecursionError: When the wrapper detects infinite recursion.
    """

    @wraps(func)
    def parent_caller(node: Any, *args: Any, **kw: Any) -> Any:
        try:
            desc = get_attr(
                Is.classOf(node),
                get_name(func),
                exclude_self=True,
                index=get_name(func) not in Is.classOf(node).__dict__,
            )
            return func(
                node,
                extract_wrapped(desc)(node, *args, **kw),
                *args,
                **kw,
            )

        except RecursionError as e:
            msg = (
                f"{Who.Is(node)}.{get_name(func)} call real {Who.Is(func)}, "
                f"couldn't reach parent descriptor; maybe {Who.Is(func)} "
                f"it's mixin of {Who.Is(node)}?"
            )
            raise RecursionError(msg) from e

    return parent_caller


class BaseProperty[T_co]:
    """Abstract base class shared by all ``kapro`` descriptors.

    ``BaseProperty`` does not implement ``__get__`` itself; subclasses decide
    whether the descriptor is instance-only, class-only, or mixed.  What this
    class *does* provide is:

    * Introspection helpers: ``name``, ``title``, ``header``
    * A printable ``__str__`` / ``__repr__``
    * The :meth:`with_parent` classmethod, which enables parent-aware
      properties via :func:`parent_call`.
    """

    @classmethod
    def with_parent(cls, function: Callable[..., Any]) -> Self:
        return cls(parent_call(function))

    def __init__(self, function: Callable[..., Any]) -> None:
        self.function: Callable[..., Any] = function

    @cached_property
    def name(self) -> str:
        return get_name(self.function)

    @cached_property
    def is_data(self) -> bool:
        return hasattr(type(self), "__set__") or hasattr(
            type(self),
            "__delete__",
        )

    @cached_property
    def title(self) -> str:
        raise NotImplementedError

    @cached_property
    def header(self) -> str:
        try:
            return f"{self.title}({self.function!a})"
        except Exception:  # noqa: BLE001
            return f"{self.title}({Who.Is(self.function)})"

    def header_with_context(self, node: Any) -> str:
        raise NotImplementedError

    def footer(self, node: Any, mode: str = "undefined") -> str:
        if node is not None:
            mode = ("instance", "class")[Is.Class(node)]
        return f"{self.header} called with {mode} context ({Who.Addr(node)})"

    def call(self, node: Any, *args: Any, **kw: Any) -> T_co:
        raise NotImplementedError

    @override
    def __str__(self) -> str:
        return f"<{self.header}>"

    @override
    def __repr__(self) -> str:
        return f"<{self.title}>"


class bound_property[T_co](BaseProperty[T_co]):
    """Simple instance-bound descriptor (non-caching, read-only).
    ``bound_property`` is the moral equivalent of a write-once instance
    attribute.  When accessed on an instance, it calls ``function(instance)``,
    stores the result in the instance ``__dict__`` under the property's
    ``name``, and returns it.  Subsequent accesses bypass the descriptor
    entirely because Python finds the value in ``__dict__`` first.

    Accessing the property on the class (``instance is None``) raises
    :exc:`ContextFaultError`.  Deleting the property raises
    :exc:`ReadOnlyError`.

    Coroutine functions are rejected at decoration time; async properties
    must use ``@pin.native`` (i.e. :class:`cached_property`) instead.
    """

    def __init__(self, function: Callable[[Any], T_co]) -> None:
        if iscoroutinefunction(function):
            msg = (
                f"{Who.Is(function)} is coroutine function, "
                "you must use @pin.native instead of just @pin"
            )
            raise TypeError(msg)
        super().__init__(function)

    @cached_property
    @override
    def title(self) -> str:
        return f"instance just-replace descriptor {Who.Addr(self)}"

    @override
    def header_with_context(self, node: Any) -> str:
        return self.footer(node)

    @overload
    def __get__(
        self,
        node: None,
        klass: Any = ...,
    ) -> bound_property[T_co]: ...

    @overload
    def __get__(
        self,
        node: object,
        klass: Any = ...,
    ) -> T_co: ...

    def __get__(
        self,
        node: object | None,
        klass: Any = Nothing,
    ) -> bound_property[T_co] | T_co:
        if node is None:
            raise ContextFaultError(self.header_with_context(klass))

        cache = getattr(node, "__dict__", None)
        if cache is None:
            raise TypeError(
                f"{self.header_with_context(node)} has no __dict__",
            )

        try:
            return cache[self.name]

        except KeyError:
            value = self.function(node)
            cache[self.name] = value
            return value

    def __set__(self, node: object, value: Any) -> None:
        msg = f"{self.header_with_context(node)}: setter called"
        raise ReadOnlyError(msg)

    def __delete__(self, node: object) -> None:
        msg = f"{self.header_with_context(node)}: deleter called"
        raise ReadOnlyError(msg)
