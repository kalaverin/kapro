from collections.abc import Callable, Sequence
from typing import Any, TypeVar

__all__ = ("Binder", "RawBinder", "proxy_to")

C = TypeVar("C")
T = TypeVar("T")

type Binder[T] = Callable[[Callable[[Any], T]], Any]

class RawBinder:
    def __call__(self, fn: Callable[[Any], T]) -> Any: ...

def proxy_to(
    pivot: str | object,
    names: str | Sequence[str],
    *,
    binder: Binder[Any] | None = ...,
    getter: Callable[[str], Callable[[Any], Any]] = ...,
    default: Any = ...,
    post: Callable[[Any], Any] | None = ...,
    safe: bool = ...,
) -> Callable[[type[C]], type[C]]: ...
