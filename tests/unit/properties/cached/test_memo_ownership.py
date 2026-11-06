"""Unit tests for instance memo ownership across copies.

Arrange-Act-Assert pattern, BDD docstrings.

Covers the copy-on-write detach of ``__instance_memoized__``: a shallow
copy shares the memo dict by reference, and the first descriptor access
through the clone must give it its own memo instead of clobbering the
original's entries (regression for the shared-memo ping-pong bug).
"""

from __future__ import annotations

import gc
from copy import copy, deepcopy
from typing import Any

from faker import Faker

from zx.prop import detach_memo, pin
from zx.prop.cached.instance import cached_property
from zx.prop.cached.memo import INSTANCE_MEMOIZED, _InstanceMemo
from zx.prop.primitives import Nothing


def _flow_actual(
    _self: Any,
    node: Any,
    stamp: Any = Nothing,
) -> Any:
    """Staleness predicate: valid while `node.flow` is the same object."""
    if stamp is Nothing:
        return node.flow
    return stamp is node.flow


def _counting(returns: list[str]) -> Any:
    """Build a compute function that records one call per invocation."""
    counter = 0

    def compute(_self: Any) -> str:
        nonlocal counter
        value = returns[min(counter, len(returns) - 1)]
        counter += 1
        return value

    return compute


# ------------------------------------------------------------------
# copy-on-write detach
# ------------------------------------------------------------------


class TestShallowCopyDetach:
    """GIVEN an instance with a populated memo
    WHEN a shallow copy accesses a cached property
    THEN the clone gets its own memo and the original keeps its entries.
    """

    def test_clone_recomputes_instead_of_reusing_cached_value(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a cached property with a call counter
        WHEN the original is accessed, then a shallow copy is accessed
        THEN the function runs once per instance.
        """
        calls: list[str] = []

        class Sample:
            attr = cached_property(
                lambda _self: calls.append("hit") or len(calls),
            )

        instance = Sample()
        assert instance.attr == 1

        clone = copy(instance)
        assert clone.attr == 2

    def test_clone_gets_own_memo_dict(self, fake: Faker) -> None:
        """GIVEN an original with a populated memo
        WHEN a shallow copy accesses the property
        THEN the two instances hold distinct memo dicts.
        """
        expected = fake.pyint()

        class Sample:
            attr = cached_property(lambda _self: expected)

        instance = Sample()
        _ = instance.attr
        clone = copy(instance)
        _ = clone.attr

        memo = instance.__dict__[INSTANCE_MEMOIZED]
        clone_memo = clone.__dict__[INSTANCE_MEMOIZED]
        assert isinstance(memo, _InstanceMemo)
        assert memo is not clone_memo

    def test_original_entry_survives_clone_access(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN an original with a cached value
        WHEN a shallow copy computes a different value
        THEN the original's memo entry is untouched.
        """
        first = fake.pyint()
        second = fake.pyint()

        class Sample:
            attr = cached_property(
                lambda self: second if self.__dict__.get("_seen") else first,
            )

        instance = Sample()
        assert instance.attr == first

        clone = copy(instance)
        clone.__dict__["_seen"] = True
        assert clone.attr == second

        prop = Sample.__dict__["attr"]
        assert instance.__dict__[INSTANCE_MEMOIZED][prop.name] == first


class TestIsActualNoClobber:
    """GIVEN an is_actual staleness predicate pinned on instance state
    WHEN original and shallow copy diverge
    THEN entries never clobber each other and no recompute ping-pong starts.
    """

    def test_divergent_stamps_do_not_clobber(self) -> None:
        """GIVEN original and clone with different `flow` objects
        WHEN both access the pinned property repeatedly
        THEN each keeps its own value and the function runs once per instance.
        """

        class Flow:
            def __init__(self, name: str) -> None:
                self.name = name

        calls: list[str] = []

        class Sample:
            def __init__(self, flow: Flow) -> None:
                self.flow = flow

            @cached_property.by(_flow_actual)
            def codec(self) -> str:
                calls.append(self.flow.name)
                return self.flow.name

        original = Sample(Flow("a"))
        assert original.codec == "a"

        clone = copy(original)
        clone.flow = Flow("b")

        for _ in range(3):
            assert clone.codec == "b"
            assert original.codec == "a"

        assert calls == ["a", "b"]


# ------------------------------------------------------------------
# mixed descriptors
# ------------------------------------------------------------------


class TestMixedDescriptorDetach:
    """GIVEN a mixed cached property (pin.any)
    WHEN a shallow copy accesses it on the instance side
    THEN the instance memo detaches exactly like cached_property.
    """

    def test_mixed_instance_side_detaches_on_copy(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN pin.any accessed on an instance
        WHEN the instance is shallow-copied and accessed again
        THEN the clone owns a separate memo dict.
        """
        calls: list[str] = []

        class Sample:
            attr = pin.any(
                lambda _self: calls.append("hit") or len(calls),
            )

        instance = Sample()
        assert instance.attr == 1

        clone = copy(instance)
        assert clone.attr == 2
        assert (
            instance.__dict__[INSTANCE_MEMOIZED]
            is not clone.__dict__[INSTANCE_MEMOIZED]
        )


# ------------------------------------------------------------------
# deepcopy and dead owners
# ------------------------------------------------------------------


class TestDeepcopyAndDeadOwner:
    """GIVEN exotic copy/lifetime paths
    WHEN the memo owner tag no longer matches
    THEN the memo is replaced, not reused.
    """

    def test_deepcopy_detaches_on_first_access(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a deep-copied instance
        WHEN the property is accessed on the copy
        THEN the copy recomputes with its own memo.
        """
        calls: list[str] = []

        class Sample:
            attr = cached_property(
                lambda _self: calls.append("hit") or len(calls),
            )

        instance = Sample()
        assert instance.attr == 1

        clone = deepcopy(instance)
        assert clone.attr == 2
        assert (
            instance.__dict__[INSTANCE_MEMOIZED]
            is not clone.__dict__[INSTANCE_MEMOIZED]
        )

    def test_dead_owner_memo_is_replaced(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN the original instance is garbage-collected
        WHEN the clone accesses the property
        THEN the dead-owned memo is replaced without error.
        """
        expected = fake.pyint()

        class Sample:
            attr = cached_property(lambda _self: expected)

        instance = Sample()
        _ = instance.attr

        clone = copy(instance)
        del instance
        gc.collect()

        assert clone.attr == expected
        memo = clone.__dict__[INSTANCE_MEMOIZED]
        assert memo.is_owned_by(clone)

    def test_owner_without_weakref_support(self) -> None:
        """GIVEN a class with __dict__ but no __weakref__ slot
        WHEN copied and accessed
        THEN the strong-reference fallback still detaches.
        """

        class Sample:
            __slots__ = ("__dict__",)

            attr = cached_property(lambda _self: "value")

        instance = Sample()
        assert instance.attr == "value"

        clone = copy(instance)
        assert clone.attr == "value"
        memo = clone.__dict__[INSTANCE_MEMOIZED]
        assert memo.is_owned_by(clone)
        assert not memo.is_owned_by(instance)


# ------------------------------------------------------------------
# detach_memo
# ------------------------------------------------------------------


class TestDetachMemo:
    """GIVEN a node holding a shared or owned memo
    WHEN detach_memo is called
    THEN foreign memos are replaced eagerly, owned/absent ones untouched.
    """

    def test_eager_detach_after_copy(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a populated memo shared into a clone
        WHEN detach_memo(clone) runs before any access
        THEN the clone holds its own empty memo.
        """
        expected = fake.pyint()

        class Sample:
            attr = cached_property(lambda _self: expected)

        instance = Sample()
        _ = instance.attr
        clone = copy(instance)

        detach_memo(clone)

        assert (
            instance.__dict__[INSTANCE_MEMOIZED]
            is not clone.__dict__[INSTANCE_MEMOIZED]
        )
        assert clone.__dict__[INSTANCE_MEMOIZED] == {}
        assert clone.attr == expected

    def test_idempotent_on_already_owned_memo(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a node that already owns its memo
        WHEN detach_memo runs
        THEN the same dict object is kept.
        """
        expected = fake.pyint()

        class Sample:
            attr = cached_property(lambda _self: expected)

        instance = Sample()
        _ = instance.attr
        memo = instance.__dict__[INSTANCE_MEMOIZED]

        detach_memo(instance)

        assert instance.__dict__[INSTANCE_MEMOIZED] is memo

    def test_noop_when_memo_absent(self) -> None:
        """GIVEN a node whose memo was never created
        WHEN detach_memo runs
        THEN no memo appears.
        """

        class Sample:
            attr = cached_property(lambda _self: "value")

        instance = Sample()
        detach_memo(instance)

        assert INSTANCE_MEMOIZED not in instance.__dict__

    def test_noop_without_dict(self) -> None:
        """GIVEN a node without __dict__
        WHEN detach_memo runs
        THEN it returns silently.
        """
        detach_memo(object())
