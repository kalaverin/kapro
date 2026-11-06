"""Instance memo ownership for cached descriptors.

:class:`cached_property` (and its mixed siblings) store per-instance cache
in a side dict at ``node.__dict__[INSTANCE_MEMOIZED]``. A shallow copy
(``copy.copy``) reuses the values of the original ``__dict__``, so the memo
dict ends up shared by reference: two instances silently read and clobber
each other's cache entries. The memo dict therefore tags its owner and
detaches itself copy-on-write when accessed through a different instance,
so the library — not every consumer — owns the invariant "one instance,
one memo".
"""

# ruff: noqa: ANN401

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING, Any
from weakref import ref as weak_ref

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ("detach_memo",)

INSTANCE_MEMOIZED = "__instance_memoized__"


class _InstanceMemo(dict[str, Any]):
    """Memo dict owned by exactly one instance.

    ``copy.copy`` keeps the same memo dict in the clone's ``__dict__``;
    the owner tag lets :func:`own_memo` detect the foreign dict and give
    the clone a fresh one on first access, leaving the original's entries
    intact. The owner is held weakly to avoid a reference cycle
    ``instance -> __dict__ -> memo -> instance``; instances without
    ``__weakref__`` fall back to a strong reference.
    """

    def __init__(self, owner: Any) -> None:
        super().__init__()
        try:
            self._owner_ref: Callable[[], Any] | None = weak_ref(owner)
        except TypeError:
            self._owner_ref = None
            self._owner_strong: Any = owner

    def is_owned_by(self, pivot: Any) -> bool:
        """Return True when ``pivot`` is the instance that created self."""
        if self._owner_ref is not None:
            return self._owner_ref() is pivot
        return getattr(self, "_owner_strong", None) is pivot


def own_memo(pivot: Any) -> dict[str, Any]:
    """Return the instance memo owned by ``pivot``, detaching a foreign one.

    Every read/write path of instance-cached descriptors funnels through
    this function, so a shallow-copied instance gets its own empty memo on
    first access instead of sharing (and clobbering) the original's.
    """
    cache = pivot.__dict__
    with suppress(KeyError):
        memo = cache[INSTANCE_MEMOIZED]
        owned = getattr(memo, "is_owned_by", None)
        if callable(owned) and owned(pivot):
            return memo
    memo = _InstanceMemo(pivot)
    cache[INSTANCE_MEMOIZED] = memo
    return memo


def detach_memo(node: Any) -> None:
    """Give ``node`` its own instance memo, dropping a shared one.

    Eager variant of the copy-on-write detach performed by :func:`own_memo`:
    call right after ``copy.copy`` when the clone should not hold a
    reference to the original's memo at all. No-op when the memo is absent
    or already owned by ``node``.
    """
    cache = getattr(node, "__dict__", None)
    if cache is None:
        return
    try:
        memo = cache[INSTANCE_MEMOIZED]
    except KeyError:
        return
    owned = getattr(memo, "is_owned_by", None)
    if callable(owned) and owned(node):
        return
    cache[INSTANCE_MEMOIZED] = _InstanceMemo(node)
