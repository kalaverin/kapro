"""Class decorator that forwards attribute access to a pivot.

``proxy_to`` creates proxy descriptors on a class so that accessing
``instance.name`` delegates to ``instance.pivot.name`` (or to an external
object).  It is used by the descriptor system to wire attribute forwarding
without explicit boilerplate.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from logging import getLogger
from operator import attrgetter
from typing import Any, Never, Protocol, TypeVar, override

from zx.core import Is, Who
from zx.core.classes import Nothing
from zx.core.internals import get_attr

from zx.prop.primitives import bound_property

__all__ = ("Binder", "RawBinder", "proxy_to")

logger = getLogger(__name__)

T = TypeVar("T")


type Binder[T] = Callable[[Callable[[Any], T]], Any]


class RawBinder:
    """Binder used internally when ``binder=None``.

    Returns a :class:`RawProxy` descriptor that resolves the attribute at
    access time, allowing per-instance overrides and descriptor pivots.
    """

    def __call__(self, fn: Callable[[Any], T]) -> RawProxy:
        return RawProxy(fn)


@dataclass(frozen=True)
class ProxyField:
    """Specification for a single proxied attribute."""

    name: str
    resolver: PivotResolver
    getter: Callable[[str], Callable[[Any], Any]]
    default: Any
    post: Callable[[Any], Any] | None


class PivotResolver(Protocol):
    """Resolve a pivot to the object that owns the proxied attribute."""

    def resolve(self, node: Any) -> Any:  # noqa: ANN401
        ...


@dataclass(frozen=True)
class StringPivot(PivotResolver):
    """Resolve a pivot by attribute name."""

    name: str

    @override
    def resolve(self, node: Any) -> Any:
        try:
            return getattr(node, self.name)
        except AttributeError as e:
            msg = f"{Who.Is(node)}.{self.name} does not exist"
            raise AttributeError(msg) from e


@dataclass(frozen=True)
class ObjectPivot(PivotResolver):
    """Resolve a pivot to a fixed object."""

    value: Any

    @override
    def resolve(self, node: Any) -> Any:
        _ = node
        return self.value


class RawProxy:
    """Descriptor that returns the raw proxied attribute on each access."""

    fn: Callable[[Any], Any]

    def __init__(self, fn: Callable[[Any], Any]) -> None:
        self.fn = fn

    def __get__(self, instance: object | None, owner: type) -> Any:  # noqa: ANN401
        node = owner if instance is None else instance
        return self.fn(node)


def normalize_names(names: str | Sequence[str]) -> tuple[str, ...]:
    """Validate and normalize ``names`` to a tuple of strings."""
    if isinstance(names, str):
        return (names,)

    normalized = tuple(names)
    if not normalized:
        raise ValueError("at least one method name is required")

    for name in normalized:
        if not isinstance(name, str):
            msg = f"method name must be a string, got {Who.Is(name)}"
            raise TypeError(msg)

    return normalized


def make_resolver(pivot: str | object) -> PivotResolver:
    """Create a resolver for the given pivot."""
    if isinstance(pivot, str):
        return StringPivot(pivot)
    return ObjectPivot(pivot)


def resolve_value(
    field: ProxyField,
    entity: Any,  # noqa: ANN401
    *,
    call_result: bool = False,
) -> Any:  # noqa: ANN401
    """Resolve the final value for ``field`` from ``entity``.

    When ``call_result`` is ``True`` and the resolved attribute is
    callable, it is called with no arguments before ``post`` is applied.
    This is used by non-raw binders so that ``proxy_to`` feels like a
    property forwarding the *result* of a pivot method.
    """
    if entity is None and field.default is not Nothing:
        return apply_default(field, field.default)

    try:
        result = field.getter(field.name)(entity)
    except (AttributeError, KeyError) as e:
        if field.default is not Nothing:
            return apply_default(field, field.default)
        raise_missing(field, entity, e)

    if call_result and callable(result):
        result = result()

    if field.post is not None:
        result = field.post(result)

    return result


def apply_default(field: ProxyField, value: Any) -> Any:  # noqa: ANN401
    """Return ``value`` after applying ``post`` and logging the fallback."""
    msg = (
        f"{field.name} proxied via {field.resolver}, "
        f"but it does not exist; return {Who.Is(value)}"
    )
    logger.warning(msg)

    if field.post is not None:
        value = field.post(value)

    return value


def raise_missing(
    field: ProxyField,
    entity: Any,  # noqa: ANN401
    exc: BaseException,
) -> Never:
    """Raise an informative error when the proxied attribute is missing."""
    msg = (
        f"{field.name} proxied via {field.resolver}, "
        f"but it does not exist ('{field.name}' not in {Who.Is(entity)})"
    )
    raise Is.classOf(exc)(msg) from exc


def make_wrapper(
    field: ProxyField,
    *,
    call_result: bool = False,
) -> Callable[[Any], Any]:
    """Build the wrapper function passed to the binder."""

    def wrapper(node: Any) -> Any:  # noqa: ANN401
        entity = field.resolver.resolve(node)
        return resolve_value(field, entity, call_result=call_result)

    wrapper.__name__ = field.name
    wrapper.__qualname__ = field.name
    return wrapper


def init_proxy_fields(cls: type) -> list[str]:
    """Return a class-owned ``__proxy_fields__`` list."""
    fields: list[str] = list(getattr(cls, "__proxy_fields__", []))
    cls.__proxy_fields__ = fields
    return fields


def attach_proxy_field(
    cls: type,
    field: ProxyField,
    binder: Binder[Any] | None,
    safe: bool,
) -> None:
    """Attach one proxied attribute to ``cls``."""
    if safe and get_attr(cls, field.name):
        msg = (
            f"{Who.Is(cls)} already exists {field.name!a}: "
            f"{get_attr(cls, field.name)}"
        )
        raise TypeError(msg)

    wrapper = make_wrapper(field, call_result=binder is not None)

    descriptor = RawBinder()(wrapper) if binder is None else binder(wrapper)
    setattr(cls, field.name, descriptor)


def proxy_to(  # noqa: PLR0913
    pivot: str | object,
    names: str | Sequence[str],
    *,
    binder: Binder[Any] | None = bound_property,
    getter: Callable[[str], Callable[[Any], Any]] = attrgetter,
    default: Any = Nothing,  # noqa: ANN401
    post: Callable[[Any], Any] | None = None,
    safe: bool = True,
) -> Callable[[type[T]], type[T]]:
    """Create a class decorator that proxies attributes to a pivot.

    Args:
        pivot: Either a string attribute name on the decorated class, or an
            external object to forward lookups to.
        names: One or more attribute names to proxy from the pivot.
        binder: Callable that turns the proxy wrapper into a descriptor.
            ``None`` attaches a raw runtime lookup descriptor.
        getter: ``(name) -> (obj) -> value`` used to fetch the attribute from
            the pivot object.  Defaults to ``operator.attrgetter``.
        default: Fallback value returned when the pivot or the proxied name
            is missing.  Defaults to ``Nothing`` (raise an exception).
        post: Optional callable ``(value) -> result`` applied to the fetched
            value before returning it.
        safe: If ``True`` (default), raise ``TypeError`` when attempting to
            overwrite an existing attribute on the class.

    Returns:
        A class decorator that mutates the target class in place.
    """
    resolver = make_resolver(pivot)
    normalized = normalize_names(names)

    def class_wrapper(cls: type[T]) -> type[T]:
        if not Is.Class(cls):
            msg = f"{Who.Is(cls)} isn't a class"
            raise TypeError(msg)

        fields = init_proxy_fields(cls)

        for name in normalized:
            field = ProxyField(
                name=name,
                resolver=resolver,
                getter=getter,
                default=default,
                post=post,
            )
            attach_proxy_field(cls, field, binder, safe)
            fields.append(name)
            fields.sort()

        return cls

    return class_wrapper
