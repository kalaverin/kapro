from __future__ import annotations

from typing import Any

__all__ = ("detach_memo",)

INSTANCE_MEMOIZED: str

class _InstanceMemo(dict[str, Any]):
    def __init__(self, owner: Any) -> None: ...
    def is_owned_by(self, pivot: Any) -> bool: ...

def own_memo(pivot: Any) -> dict[str, Any]: ...
def detach_memo(node: Any) -> None: ...
