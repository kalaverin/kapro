from __future__ import annotations

from typing import Any, override

from kapro.cached.klass import class_cached_property
from kapro.cached.mixed import (
    mixed_cached_property,
    mixed_parent_cached_property,
)

__all__ = ("pre_cached_property", "pre_parent_cached_property")
T_co: Any

class pre_parent_cached_property[T_co](
    mixed_parent_cached_property[T_co],
):
    @override
    def __set__(self, node: Any, value: Any) -> Any: ...

class pre_cached_property[T_co](
    mixed_cached_property[T_co],
):
    @override
    def __set__(self, node: Any, value: Any) -> Any: ...
    @class_cached_property
    @override
    def here(
        cls,
    ) -> type[pre_parent_cached_property[Any]]: ...
