"""Comprehensive tests for the `.here` attribute on cached descriptors."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import time_machine
from faker import Faker

from zx.prop.cached.klass import (
    class_cached_property,
    class_parent_cached_property,
)
from zx.prop.cached.mixed import (
    mixed_cached_property,
    mixed_parent_cached_property,
)
from zx.prop.cached.post import (
    post_cached_property,
    post_parent_cached_property,
)
from zx.prop.cached.pre import (
    pre_cached_property,
    pre_parent_cached_property,
)


class TestClassCachedPropertyHere:
    """Tests for ``class_cached_property.here``."""

    def test_here_returns_parent_class(self) -> None:
        """GIVEN class_cached_property
        WHEN .here is accessed
        THEN it returns class_parent_cached_property.
        """
        assert class_cached_property.here is class_parent_cached_property

    def test_here_child_access_first_caches_child_value_on_owner(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a class_cached_property.here on a base class
        WHEN the child class accesses it first
        THEN the cache lives on the owner class.
        """
        values = [fake.pyint(), fake.pyint()]

        class Base:
            counter = 0

            @class_cached_property.here
            def prop(cls) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            pass

        assert Child.prop == values[0]
        assert Base.prop == values[0]
        assert Base.counter == 1
        assert "__class_memoized__" in Base.__dict__
        assert "__class_memoized__" not in Child.__dict__

    def test_here_base_access_first_caches_value(self, fake: Faker) -> None:
        """GIVEN a class_cached_property.here on a base class
        WHEN the base class accesses it first
        THEN the child hits the same owner cache.
        """
        values = [fake.pyint(), fake.pyint()]

        class Base:
            counter = 0

            @class_cached_property.here
            def prop(cls) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            pass

        assert Base.prop == values[0]
        assert Child.prop == values[0]
        assert Base.counter == 1

    def test_plain_vs_here_cache_location(self, fake: Faker) -> None:
        """GIVEN a plain class_cached_property and a .here variant
        WHEN accessed through a child class
        THEN plain caches on the accessed class while here caches on owner.
        """
        values = [fake.pyint() for _ in range(3)]

        class Base:
            counter = 0

            @class_cached_property
            def plain(cls) -> str:
                value = f"{cls.__name__}_{values[Base.counter]}"
                Base.counter += 1
                return value

            @class_cached_property.here
            def here_prop(cls) -> str:
                value = f"{cls.__name__}_{values[Base.counter]}"
                Base.counter += 1
                return value

        class Child(Base):
            pass

        assert Base.plain == f"Base_{values[0]}"
        assert Child.plain == f"Child_{values[1]}"
        assert Base.counter == 2

        Base.counter = 0
        assert Child.here_prop == f"Child_{values[0]}"
        assert Base.here_prop == f"Child_{values[0]}"
        assert Base.counter == 1

    def test_here_ttl(self, fake: Faker) -> None:
        """GIVEN a class_cached_property.here with TTL
        WHEN time advances past the TTL
        THEN the value is recomputed on the owner class.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Base:
            counter = 0

            @class_cached_property.here.ttl(ttl_seconds)
            def prop(cls) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            pass

        with time_machine.travel(0, tick=False) as traveller:
            assert Child.prop == values[0]
            assert Base.counter == 1
            traveller.shift(timedelta(seconds=ttl_seconds * 2))
            assert Base.prop == values[1]
            assert Base.counter == 2

    def test_here_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent class_cached_property.here
        WHEN a child overrides via with_parent
        THEN the parent value is injected and cached on the owner.
        """
        parent_prefix = fake.word()
        child_prefix = fake.word()

        class Parent:
            counter = 0

            @class_cached_property.here
            def prop(cls) -> str:
                Parent.counter += 1
                return f"{parent_prefix}_{cls.__name__}"

        class Child(Parent):
            @class_cached_property.here.with_parent
            def prop(cls, parent_value: str) -> str:
                return f"{child_prefix}_{parent_value}"

        expected = f"{child_prefix}_{parent_prefix}_Child"
        for _ in range(fake.pyint(min_value=2, max_value=5)):
            assert Child.prop == expected

        assert Parent.counter == 1

    def test_here_manual_set_on_owner(self, fake: Faker) -> None:
        """GIVEN a cached value on a class_cached_property.here
        WHEN the owner cache is set and deleted manually
        THEN both owner and child see the override and reset.
        """
        original = fake.pystr()
        override = fake.pystr()

        class Base:
            @class_cached_property.here
            def prop(cls) -> str:
                return original

        class Child(Base):
            pass

        desc = Base.__dict__["prop"]
        desc.__set__(Base, override)
        assert Base.prop == override
        assert Child.prop == override
        desc.__delete__(Base)
        assert Base.prop == original


class TestMixedCachedPropertyHere:
    """Tests for ``mixed_cached_property.here``."""

    def test_here_returns_parent_class(self) -> None:
        """GIVEN mixed_cached_property
        WHEN .here is accessed
        THEN it returns mixed_parent_cached_property.
        """
        assert mixed_cached_property.here is mixed_parent_cached_property

    def test_here_instance_caches_on_instance(self, fake: Faker) -> None:
        """GIVEN a mixed_cached_property.here
        WHEN accessed on an instance twice
        THEN the value is cached on the instance.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Base:
            counter = 0

            @mixed_cached_property.here
            def prop(self_or_cls: Any) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            pass

        obj = Child()
        for _ in range(tries):
            assert obj.prop == values[0]

        assert Base.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_here_class_caches_on_owner(self, fake: Faker) -> None:
        """GIVEN a mixed_cached_property.here on a base class
        WHEN accessed on a child class twice
        THEN the value is cached on the owner class.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Base:
            counter = 0

            @mixed_cached_property.here
            def prop(self_or_cls: Any) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            pass

        for _ in range(tries):
            assert Child.prop == values[0]

        assert Base.counter == 1
        assert "__class_memoized__" in Base.__dict__
        assert "__class_memoized__" not in Child.__dict__

    def test_here_ttl(self, fake: Faker) -> None:
        """GIVEN a mixed_cached_property.here with TTL
        WHEN time advances past the TTL on an instance
        THEN the value is recomputed.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Base:
            counter = 0

            @mixed_cached_property.here.ttl(ttl_seconds)
            def prop(self_or_cls: Any) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        obj = Base()
        with time_machine.travel(0, tick=False) as traveller:
            assert obj.prop == values[0]
            assert Base.counter == 1
            traveller.shift(timedelta(seconds=ttl_seconds * 2))
            assert obj.prop == values[1]
            assert Base.counter == 2

    def test_here_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent mixed_cached_property.here
        WHEN a child overrides via with_parent
        THEN the parent value is injected for both class and instance access.
        """
        values = [fake.pyint(), fake.pyint()]

        class Parent:
            counter = 0

            @mixed_cached_property.here
            def prop(self_or_cls: Any) -> int:
                Parent.counter += 1
                return values[0]

        class Child(Parent):
            @mixed_cached_property.here.with_parent
            def prop(self_or_cls: Any, parent_value: int) -> int:
                return parent_value + values[1]

        obj = Child()
        expected = values[0] + values[1]
        for _ in range(fake.pyint(min_value=2, max_value=5)):
            assert Child.prop == expected
            assert obj.prop == expected

        assert Parent.counter == 2


class TestPreCachedPropertyHere:
    """Tests for ``pre_cached_property.here``."""

    def test_here_returns_parent_class(self) -> None:
        """GIVEN pre_cached_property
        WHEN .here is accessed
        THEN it returns pre_parent_cached_property.
        """
        assert pre_cached_property.here is pre_parent_cached_property

    def test_here_class_caches_on_owner(self, fake: Faker) -> None:
        """GIVEN a pre_cached_property.here on a base class
        WHEN accessed on a child class twice
        THEN the value is cached on the owner class.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Base:
            counter = 0

            @pre_cached_property.here
            def prop(self_or_cls: Any) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            pass

        for _ in range(tries):
            assert Child.prop == values[0]

        assert Base.counter == 1
        assert "__class_memoized__" in Base.__dict__

    def test_here_instance_does_not_cache(self, fake: Faker) -> None:
        """GIVEN a pre_cached_property.here
        WHEN accessed on an instance twice
        THEN it recomputes each time.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries)]

        class Base:
            counter = 0

            @pre_cached_property.here
            def prop(self_or_cls: Any) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        obj = Base()
        for i in range(tries):
            assert obj.prop == values[i]

        assert Base.counter == tries
        assert "__instance_memoized__" not in obj.__dict__

    def test_here_ttl(self, fake: Faker) -> None:
        """GIVEN a pre_cached_property.here with TTL
        WHEN time advances past the TTL on a class
        THEN the value is recomputed on the owner class.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Base:
            counter = 0

            @pre_cached_property.here.ttl(ttl_seconds)
            def prop(self_or_cls: Any) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        with time_machine.travel(0, tick=False) as traveller:
            assert Base.prop == values[0]
            assert Base.counter == 1
            traveller.shift(timedelta(seconds=ttl_seconds * 2))
            assert Base.prop == values[1]
            assert Base.counter == 2


class TestPostCachedPropertyHere:
    """Tests for ``post_cached_property.here``."""

    def test_here_returns_parent_class(self) -> None:
        """GIVEN post_cached_property
        WHEN .here is accessed
        THEN it returns post_parent_cached_property.
        """
        assert post_cached_property.here is post_parent_cached_property

    def test_here_instance_caches_on_instance(self, fake: Faker) -> None:
        """GIVEN a post_cached_property.here
        WHEN accessed on an instance twice
        THEN the value is cached on the instance.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Base:
            counter = 0

            @post_cached_property.here
            def prop(self_or_cls: Any) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            pass

        obj = Child()
        for _ in range(tries):
            assert obj.prop == values[0]

        assert Base.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_here_class_does_not_cache(self, fake: Faker) -> None:
        """GIVEN a post_cached_property.here
        WHEN accessed on a class twice
        THEN it recomputes each time.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries)]

        class Base:
            counter = 0

            @post_cached_property.here
            def prop(self_or_cls: Any) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        for i in range(tries):
            assert Base.prop == values[i]

        assert Base.counter == tries
        cache = Base.__dict__["__class_memoized__"]
        assert "prop" not in cache

    def test_here_ttl_instance(self, fake: Faker) -> None:
        """GIVEN a post_cached_property.here with TTL
        WHEN time advances past the TTL on an instance
        THEN the value is recomputed.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Base:
            counter = 0

            @post_cached_property.here.ttl(ttl_seconds)
            def prop(self_or_cls: Any) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        obj = Base()
        with time_machine.travel(0, tick=False) as traveller:
            assert obj.prop == values[0]
            assert Base.counter == 1
            traveller.shift(timedelta(seconds=ttl_seconds * 2))
            assert obj.prop == values[1]
            assert Base.counter == 2


class TestHereDiamondInheritance:
    """Diamond inheritance with ``.here`` should share one owner cache."""

    def test_diamond_class_cached_property_here(self, fake: Faker) -> None:
        """GIVEN a diamond hierarchy with class_cached_property.here
        WHEN each class accesses the property
        THEN only one computation happens and the cache lives on the owner.
        """
        values = [fake.pyint(), fake.pyint()]

        class A:
            counter = 0

            @class_cached_property.here
            def prop(cls) -> int:
                value = values[A.counter]
                A.counter += 1
                return value

        class B(A):
            pass

        class C(A):
            pass

        class D(B, C):
            pass

        assert A.prop == values[0]
        assert B.prop == values[0]
        assert C.prop == values[0]
        assert D.prop == values[0]
        assert A.counter == 1
        assert "__class_memoized__" in A.__dict__

    def test_diamond_mixed_cached_property_here(self, fake: Faker) -> None:
        """GIVEN a diamond hierarchy with mixed_cached_property.here
        WHEN classes access the property
        THEN only one computation happens on the owner class.
        """
        values = [fake.pyint(), fake.pyint()]

        class A:
            counter = 0

            @mixed_cached_property.here
            def prop(self_or_cls: Any) -> int:
                value = values[A.counter]
                A.counter += 1
                return value

        class B(A):
            pass

        class C(A):
            pass

        class D(B, C):
            pass

        assert B.prop == values[0]
        assert C.prop == values[0]
        assert D.prop == values[0]
        assert A.counter == 1

    def test_diamond_pre_cached_property_here(self, fake: Faker) -> None:
        """GIVEN a diamond hierarchy with pre_cached_property.here
        WHEN classes access the property
        THEN only one computation happens on the owner class.
        """
        values = [fake.pyint(), fake.pyint()]

        class A:
            counter = 0

            @pre_cached_property.here
            def prop(self_or_cls: Any) -> int:
                value = values[A.counter]
                A.counter += 1
                return value

        class B(A):
            pass

        class C(A):
            pass

        class D(B, C):
            pass

        assert B.prop == values[0]
        assert C.prop == values[0]
        assert D.prop == values[0]
        assert A.counter == 1

    def test_diamond_post_cached_property_here(self, fake: Faker) -> None:
        """GIVEN a diamond hierarchy with post_cached_property.here
        WHEN an instance accesses the property
        THEN it is cached on the instance.
        """
        values = [fake.pyint(), fake.pyint()]

        class A:
            counter = 0

            @post_cached_property.here
            def prop(self_or_cls: Any) -> int:
                value = values[A.counter]
                A.counter += 1
                return value

        class B(A):
            pass

        class C(A):
            pass

        class D(B, C):
            pass

        obj = D()
        for _ in range(fake.pyint(min_value=2, max_value=5)):
            assert obj.prop == values[0]

        assert A.counter == 1
        assert "__instance_memoized__" in obj.__dict__
