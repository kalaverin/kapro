from __future__ import annotations

from typing import Any, override

from kapro.cached.klass import class_cached_property
from kapro.cached.mixed import (
    mixed_cached_property,
    mixed_parent_cached_property,
)

__all__ = ("post_cached_property", "post_parent_cached_property")
T_co: Any

class post_parent_cached_property[T_co](
    mixed_parent_cached_property[T_co],
):
    @override
    def __set__(self, node: Any, value: Any) -> Any: ...

class post_cached_property[T_co](
    mixed_cached_property[T_co],
):
    @override
    def __set__(self, node: Any, value: Any) -> Any: ...
    @class_cached_property
    @override
    def here(
        cls,
    ) -> type[post_parent_cached_property[Any]]: ...
