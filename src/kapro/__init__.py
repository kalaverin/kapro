from __future__ import annotations

from typing import Any, TypeVar, final, overload, override

from kapro import special
from kapro.cached import (
    cached_property,
    class_cached_property,
    mixed_cached_property,
    post_cached_property,
    pre_cached_property,
)
from kapro.class_property import class_property, mixed_property
from kapro.primitives import Nothing, bound_property

T_co = TypeVar("T_co", covariant=True)


@final
class pin[T_co](bound_property[T_co]):  # noqa: N801
    native = cached_property
    cls = class_cached_property
    any = mixed_cached_property
    pre = pre_cached_property
    post = post_cached_property

    @overload
    def __get__(
        self,
        node: None,
        klass: Any = ...,  # noqa: ANN401
    ) -> pin[T_co]: ...

    @overload
    def __get__(
        self,
        node: object,
        klass: Any = ...,  # noqa: ANN401
    ) -> T_co: ...

    @override
    def __get__(
        self,
        node: object | None,
        klass: Any = Nothing,
    ) -> pin[T_co] | T_co:
        return super().__get__(node, klass)


__all__ = (
    "class_property",
    "mixed_property",
    "pin",
    "special",
)
