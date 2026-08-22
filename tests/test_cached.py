"""Granular unit tests for kapro.cached descriptor family."""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Any

import pytest
import time_machine
from faker import Faker

from kapro.cached.instance import cached_property
from kapro.cached.klass import (
    class_cached_property,
    class_parent_cached_property,
)
from kapro.cached.mixed import (
    mixed_cached_property,
    mixed_parent_cached_property,
)
from kapro.cached.post import (
    post_cached_property,
    post_parent_cached_property,
)
from kapro.cached.pre import (
    pre_cached_property,
    pre_parent_cached_property,
)
from kapro.primitives import ContextFaultError


class TestCustomCallbackMixin:
    """Tests for the CustomCallbackMixin helper."""

    def test_by_returns_partial(self) -> None:
        """GIVEN a custom is_actual predicate
        WHEN class_cached_property.by is called
        THEN it returns a callable descriptor factory.
        """

        def cb(_self: object, _node: object, _stamp: float) -> bool:
            return True

        factory = class_cached_property.by(cb)
        assert callable(factory)

    def test_ttl_returns_partial(self, fake: Faker) -> None:
        """GIVEN a positive TTL
        WHEN class_cached_property.ttl is called
        THEN it returns a callable descriptor factory.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=60)

        factory = class_cached_property.ttl(ttl_seconds)
        assert callable(factory)

    def test_ttl_rejects_non_number(self, fake: Faker) -> None:
        """GIVEN a non-numeric TTL
        WHEN class_cached_property.ttl is called
        THEN TypeError is raised.
        """
        with pytest.raises(TypeError, match="expire must be float or int"):
            class_cached_property.ttl(fake.word())

    def test_ttl_rejects_zero(self) -> None:
        """GIVEN a zero TTL
        WHEN class_cached_property.ttl is called
        THEN ValueError is raised.
        """
        with pytest.raises(
            ValueError,
            match="expire must be a positive number",
        ):
            class_cached_property.ttl(0)

    def test_ttl_rejects_negative(self) -> None:
        """GIVEN a negative TTL
        WHEN class_cached_property.ttl is called
        THEN ValueError is raised.
        """
        with pytest.raises(
            ValueError,
            match="expire must be a positive number",
        ):
            class_cached_property.ttl(-1)



class TestClassParentCachedProperty:
    """Tests for class_parent_cached_property."""

    def test_class_access_caches_on_owner(self, fake: Faker) -> None:
        """GIVEN a class_parent_cached_property on a base class
        WHEN accessed on a child class
        THEN the value is cached on the owner class.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Base:
            counter = 0

            @class_parent_cached_property
            def prop(cls) -> int:
                value = values[cls.counter]
                cls.counter += 1
                return value

        for _ in range(tries):
            assert Base.prop == values[0]

        assert Base.counter == 1

        class Child(Base):
            counter = Base.counter

        assert Child.counter == 1

        for _ in range(tries):
            # Still cached to the parent class because already resolved.
            assert Child.prop == values[0]

        assert Child.counter == 1
        assert Base.counter == 1
        assert "__class_memoized__" in Base.__dict__
        assert "__class_memoized__" not in Child.__dict__

    def test_instance_access_delegates_to_class(self, fake: Faker) -> None:
        """GIVEN a class_parent_cached_property
        WHEN accessed on an instance
        THEN it delegates to the class cache.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Foo:
            counter = 0

            @class_parent_cached_property
            def prop(cls) -> int:
                value = values[cls.counter]
                cls.counter += 1
                return value

        obj = Foo()
        for _ in range(tries):
            assert obj.prop == values[0]
            assert Foo.prop == values[0]
            assert Foo().prop == values[0]

        assert Foo.counter == 1

    def test_get_node_returns_owner(self, fake: Faker) -> None:
        """GIVEN an inherited class_parent_cached_property
        WHEN get_node is called with a child class
        THEN the owner class is returned.
        """
        label = fake.pystr()

        class Base:
            @class_parent_cached_property
            def prop(cls) -> str:
                return label

        class Child(Base):
            pass

        desc = Base.__dict__["prop"]
        assert desc.get_node(Child) is Base
        assert desc.get_node(Base) is Base

    def test_get_node_raises_on_none(self, fake: Faker) -> None:
        """GIVEN a class_parent_cached_property
        WHEN get_node is called with None
        THEN ContextFaultError is raised.
        """

        class Foo:
            @class_parent_cached_property
            def prop(cls) -> str:
                return fake.pystr()

        desc = Foo.__dict__["prop"]
        with pytest.raises(ContextFaultError):
            desc.get_node(None)

    def test_get_node_raises_on_instance(self, fake: Faker) -> None:
        """GIVEN a class_parent_cached_property
        WHEN get_node is called with an instance
        THEN ContextFaultError is raised.
        """

        class Foo:
            @class_parent_cached_property
            def prop(cls) -> str:
                return fake.pystr()

        desc = Foo.__dict__["prop"]
        with pytest.raises(ContextFaultError):
            desc.get_node(Foo())

    def test_get_cache_creates_dict(self, fake: Faker) -> None:
        """GIVEN a class_parent_cached_property
        WHEN get_cache is called
        THEN a __class_memoized__ dict is created on the class.
        """

        class Foo:
            @class_parent_cached_property
            def prop(cls) -> str:
                return fake.pystr()

        desc = Foo.__dict__["prop"]
        cache = desc.get_cache(Foo)
        assert isinstance(cache, dict)
        assert Foo.__dict__["__class_memoized__"] is cache

    def test_call_computes_and_caches(self, fake: Faker) -> None:
        """GIVEN a class_parent_cached_property
        WHEN call is invoked twice
        THEN the value is computed once and cached.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @class_parent_cached_property
            def prop(cls) -> int:
                value = values[cls.counter]
                cls.counter += 1
                return value

        desc = Foo.__dict__["prop"]
        assert desc.call(Foo) == values[0]
        assert desc.call(Foo) == values[0]
        assert Foo.counter == 1

    def test_set_and_delete(self, fake: Faker) -> None:
        """GIVEN a class_parent_cached_property with a cached value
        WHEN the cache is set and then deleted
        THEN manual values override and reset correctly.
        """
        original = fake.pyint()
        override = fake.pyint()

        class Foo:
            @class_parent_cached_property
            def prop(cls) -> int:
                return original

        desc = Foo.__dict__["prop"]
        desc.__set__(Foo, override)
        assert desc.call(Foo) == override
        desc.__delete__(Foo)
        assert desc.call(Foo) == original

    def test_ttl_expiration(self, fake: Faker) -> None:
        """GIVEN a class_parent_cached_property with a TTL
        WHEN time advances past the TTL
        THEN the value is recomputed on next access.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @class_parent_cached_property.ttl(ttl_seconds)
            def prop(cls) -> int:
                value = values[cls.counter]
                cls.counter += 1
                return value

        with time_machine.travel(0, tick=False) as traveller:
            assert Foo.prop == values[0]
            assert Foo.counter == 1
            traveller.shift(timedelta(seconds=ttl_seconds * 2))
            assert Foo.prop == values[1]
            assert Foo.counter == 2

    def test_by_custom_callback(self, fake: Faker) -> None:
        """GIVEN a custom is_actual callback
        WHEN it flips to invalid
        THEN the cached value is recomputed.
        """
        expired = False
        values = [fake.pyint(), fake.pyint()]

        def is_actual(
            _self: object,
            _node: object,
            stamp: float | None = None,
        ) -> bool | float:
            if stamp is None:
                return time.time()
            return not expired

        class Foo:
            counter = 0

            @class_parent_cached_property.by(is_actual)
            def prop(cls) -> int:
                value = values[cls.counter]
                cls.counter += 1
                return value

        assert Foo.prop == values[0]
        assert Foo.counter == 1
        expired = True
        assert Foo.prop == values[1]
        assert Foo.counter == 2

    def test_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent class_parent_cached_property
        WHEN a child overrides via with_parent
        THEN the parent value is injected into the child function.
        """
        values = [fake.pyint(), fake.pyint()]

        class Parent:
            counter = 0

            @class_parent_cached_property
            def prop(cls) -> int:
                Parent.counter += 1
                return values[0]

        class Child(Parent):
            @class_parent_cached_property.with_parent
            def prop(cls, parent_result: int) -> int:
                return parent_result + values[1]

        for _ in range(fake.pyint(min_value=2, max_value=5)):
            assert Child.prop == values[0] + values[1]

        assert Parent.counter == 1

    def test_is_data_true(self, fake: Faker) -> None:
        """GIVEN a class_parent_cached_property
        WHEN inspected via is_data
        THEN it reports True.
        """

        class Foo:
            @class_parent_cached_property
            def prop(cls) -> int:
                return fake.pyint()

        assert Foo.__dict__["prop"].is_data is True


class TestClassCachedProperty:
    """Tests for class_cached_property (plain variant)."""

    def test_class_access_caches_on_accessed_class(self, fake: Faker) -> None:
        """GIVEN a class_cached_property on a base class
        WHEN accessed on a child class
        THEN each accessed class has its own cache.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Base:
            counter = 0

            @class_cached_property
            def prop(cls) -> str:
                value = values[cls.counter]
                cls.counter += 1
                return value

        class Child(Base):
            counter = 0

        for _ in range(tries):
            assert Base.prop == values[0]
            assert Child.prop == values[0]

        assert Base.counter == 1
        assert Child.counter == 1
        assert "__class_memoized__" in Base.__dict__
        assert "__class_memoized__" in Child.__dict__

    def test_get_node_returns_class_directly(self, fake: Faker) -> None:
        """GIVEN an inherited class_cached_property
        WHEN get_node is called
        THEN the accessed class itself is returned.
        """
        label = fake.pystr()

        class Base:
            @class_cached_property
            def prop(cls) -> str:
                return label

        class Child(Base):
            pass

        desc = Base.__dict__["prop"]
        assert desc.get_node(Child) is Child
        assert desc.get_node(Base) is Base

    def test_here_returns_parent_class(self) -> None:
        """GIVEN class_cached_property
        WHEN .here is accessed
        THEN it returns class_parent_cached_property.
        """
        desc = class_cached_property.here
        assert desc is class_parent_cached_property

    def test_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent class_cached_property
        WHEN a child overrides via with_parent
        THEN the parent value is injected.
        """
        values = [fake.pyint(), fake.pyint()]

        class Parent:
            counter = 0

            @class_cached_property
            def prop(cls) -> int:
                Parent.counter += 1
                return values[0]

        class Child(Parent):
            @class_cached_property.with_parent
            def prop(cls, parent_result: int) -> int:
                return parent_result + values[1]

        for _ in range(fake.pyint(min_value=2, max_value=5)):
            assert Child.prop == values[0] + values[1]

        assert Parent.counter == 1


class TestCachedProperty:
    """Tests for cached_property (instance-level)."""

    def test_instance_access_caches(self, fake: Faker) -> None:
        """GIVEN a cached_property
        WHEN accessed on an instance twice
        THEN the value is computed once and cached.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Foo:
            counter = 0

            @cached_property
            def prop(self) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        for _ in range(tries):
            assert obj.prop == values[0]

        assert Foo.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_class_access_raises(self, fake: Faker) -> None:
        """GIVEN a cached_property
        WHEN accessed on the class
        THEN ContextFaultError is raised.
        """

        class Foo:
            @cached_property
            def prop(self) -> int:
                return fake.pyint()

        with pytest.raises(ContextFaultError):
            Foo.prop

    def test_instances_have_separate_cache(self, fake: Faker) -> None:
        """GIVEN two instances of the same class
        WHEN each accesses the cached_property
        THEN they have independent caches.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @cached_property
            def prop(self) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        a = Foo()
        b = Foo()
        assert a.prop == values[0]
        assert b.prop == values[1]
        assert a.prop == values[0]
        assert b.prop == values[1]

    def test_get_node_returns_instance(self, fake: Faker) -> None:
        """GIVEN a cached_property
        WHEN get_node is called with an instance
        THEN the same instance is returned.
        """

        class Foo:
            @cached_property
            def prop(self) -> int:
                return fake.pyint()

        obj = Foo()
        desc = Foo.__dict__["prop"]
        assert desc.get_node(obj) is obj

    def test_get_node_raises_on_class(self, fake: Faker) -> None:
        """GIVEN a cached_property
        WHEN get_node is called with the class
        THEN ContextFaultError is raised.
        """

        class Foo:
            @cached_property
            def prop(self) -> int:
                return fake.pyint()

        desc = Foo.__dict__["prop"]
        with pytest.raises(ContextFaultError):
            desc.get_node(Foo)

    def test_get_cache_creates_instance_dict(self, fake: Faker) -> None:
        """GIVEN a cached_property
        WHEN get_cache is called
        THEN a __instance_memoized__ dict is created.
        """

        class Foo:
            @cached_property
            def prop(self) -> int:
                return fake.pyint()

        obj = Foo()
        desc = Foo.__dict__["prop"]
        cache = desc.get_cache(obj)
        assert isinstance(cache, dict)
        assert obj.__dict__["__instance_memoized__"] is cache

    def test_manual_set_and_delete(self, fake: Faker) -> None:
        """GIVEN a cached_property with a cached value
        WHEN the cache is set and deleted manually
        THEN overrides and reset work.
        """
        initial = fake.pyint()
        override = fake.pyint()

        class Foo:
            @cached_property
            def prop(self) -> int:
                return initial

        obj = Foo()
        assert obj.prop == initial
        desc = Foo.__dict__["prop"]
        desc.__set__(obj, override)
        assert obj.prop == override
        desc.__delete__(obj)
        assert obj.prop == initial

    def test_ttl_expiration(self, fake: Faker) -> None:
        """GIVEN a cached_property with a TTL
        WHEN time advances past the TTL
        THEN the value is recomputed.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @cached_property.ttl(ttl_seconds)
            def prop(self) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        with time_machine.travel(0, tick=False) as traveller:
            obj = Foo()
            assert obj.prop == values[0]
            assert Foo.counter == 1
            traveller.shift(timedelta(seconds=ttl_seconds * 2))
            assert obj.prop == values[1]
            assert Foo.counter == 2

    def test_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent cached_property
        WHEN a child overrides via with_parent
        THEN the parent value is injected.
        """
        values = [fake.pyint(), fake.pyint()]

        class Parent:
            counter = 0

            @cached_property
            def prop(self) -> int:
                Parent.counter += 1
                return values[0]

        class Child(Parent):
            @cached_property.with_parent
            def prop(self, parent_result: int) -> int:
                return parent_result + values[1]

        obj = Child()
        for _ in range(fake.pyint(min_value=2, max_value=5)):
            assert obj.prop == values[0] + values[1]

        assert Parent.counter == 1

    def test_is_data_true(self, fake: Faker) -> None:
        """GIVEN a cached_property
        WHEN inspected via is_data
        THEN it reports True.
        """

        class Foo:
            @cached_property
            def prop(self) -> int:
                return fake.pyint()

        assert Foo.__dict__["prop"].is_data is True


class TestMixedParentCachedProperty:
    """Tests for mixed_parent_cached_property."""

    def test_instance_caches_on_instance(self, fake: Faker) -> None:
        """GIVEN a mixed_parent_cached_property
        WHEN accessed on an instance twice
        THEN the value is cached on the instance.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Foo:
            counter = 0

            @mixed_parent_cached_property
            def prop(node: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        for _ in range(tries):
            assert obj.prop == values[0]

        assert Foo.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_falsy_instance_uses_instance_cache(self, fake: Faker) -> None:
        """GIVEN a mixed_parent_cached_property on a falsy instance
        WHEN accessed repeatedly
        THEN it still caches on the instance dict.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Foo:
            counter = 0

            @mixed_parent_cached_property
            def prop(node: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

            def __bool__(self) -> bool:
                return False

        obj = Foo()
        assert not obj
        for _ in range(tries):
            assert obj.prop == values[0]

        assert Foo.counter == 1
        assert "__instance_memoized__" in obj.__dict__
        assert "__class_memoized__" not in Foo.__dict__

    def test_class_caches_on_owner(self, fake: Faker) -> None:
        """GIVEN a mixed_parent_cached_property on a base class
        WHEN accessed on a child class
        THEN the value is cached on the owner class.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Base:
            counter = 0

            @mixed_parent_cached_property
            def prop(node: Any) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            counter = Base.counter

        for _ in range(tries):
            assert Child.prop == values[0]

        assert Base.counter == 1
        assert Child.counter == 0
        assert "__class_memoized__" in Base.__dict__

    def test_instance_and_class_caches_are_separate(self, fake: Faker) -> None:
        """GIVEN a mixed_parent_cached_property
        WHEN accessed on both instance and class
        THEN the two caches are independent.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values_i = [fake.pyint() for _ in range(tries)]
        values_c = [fake.pyint() for _ in range(tries)]

        class Foo:
            counter_i = 0
            counter_c = 0

            @mixed_parent_cached_property
            def prop(node: Any) -> int:
                if isinstance(node, type):
                    value = values_c[Foo.counter_c]
                    Foo.counter_c += 1
                else:
                    value = values_i[Foo.counter_i]
                    Foo.counter_i += 1
                return value

        obj = Foo()
        assert obj.prop == values_i[0]
        assert Foo.prop == values_c[0]

        for _ in range(tries):
            assert obj.prop == values_i[0]
            assert Foo.prop == values_c[0]

        assert Foo.counter_i == 1
        assert Foo.counter_c == 1

    def test_get_node_returns_instance_for_instance(self, fake: Faker) -> None:
        """GIVEN a mixed_parent_cached_property
        WHEN get_node is called with an instance
        THEN the instance is returned.
        """

        class Foo:
            @mixed_parent_cached_property
            def prop(node: Any) -> int:
                return fake.pyint()

        obj = Foo()
        desc = Foo.__dict__["prop"]
        assert desc.get_node(obj) is obj

    def test_get_node_returns_owner_for_class(self, fake: Faker) -> None:
        """GIVEN an inherited mixed_parent_cached_property
        WHEN get_node is called with a child class
        THEN the owner class is returned.
        """

        class Base:
            @mixed_parent_cached_property
            def prop(node: Any) -> int:
                return fake.pyint()

        class Child(Base):
            pass

        desc = Base.__dict__["prop"]
        assert desc.get_node(Child) is Base

    def test_get_node_raises_on_none(self, fake: Faker) -> None:
        """GIVEN a mixed_parent_cached_property
        WHEN get_node is called with None
        THEN ContextFaultError is raised.
        """

        class Foo:
            @mixed_parent_cached_property
            def prop(node: Any) -> int:
                return fake.pyint()

        desc = Foo.__dict__["prop"]
        with pytest.raises(ContextFaultError):
            desc.get_node(None)

    def test_get_cache_uses_instance_dict_for_instance(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a mixed_parent_cached_property
        WHEN get_cache is called with an instance
        THEN the instance dict cache is returned.
        """

        class Foo:
            @mixed_parent_cached_property
            def prop(node: Any) -> int:
                return fake.pyint()

        obj = Foo()
        desc = Foo.__dict__["prop"]
        cache = desc.get_cache(obj)
        assert "__instance_memoized__" in obj.__dict__
        assert obj.__dict__["__instance_memoized__"] is cache

    def test_get_cache_uses_class_dict_for_class(self, fake: Faker) -> None:
        """GIVEN a mixed_parent_cached_property
        WHEN get_cache is called with a class
        THEN the class dict cache is returned.
        """

        class Foo:
            @mixed_parent_cached_property
            def prop(node: Any) -> int:
                return fake.pyint()

        desc = Foo.__dict__["prop"]
        cache = desc.get_cache(Foo)
        assert "__class_memoized__" in Foo.__dict__
        assert Foo.__dict__["__class_memoized__"] is cache

    def test_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent mixed_parent_cached_property
        WHEN a child overrides via with_parent
        THEN the parent value is injected.
        """
        values = [fake.pyint(), fake.pyint()]

        class Parent:
            counter = 0

            @mixed_parent_cached_property
            def prop(node: Any) -> int:
                Parent.counter += 1
                return values[0]

        class Child(Parent):
            @mixed_parent_cached_property.with_parent
            def prop(node: Any, parent_result: int) -> int:
                return parent_result + values[1]

        obj = Child()
        for _ in range(fake.pyint(min_value=2, max_value=5)):
            assert obj.prop == values[0] + values[1]
            assert Child.prop == values[0] + values[1]

        assert Parent.counter == 2

    def test_is_data_true(self, fake: Faker) -> None:
        """GIVEN a mixed_parent_cached_property
        WHEN inspected via is_data
        THEN it reports True.
        """

        class Foo:
            @mixed_parent_cached_property
            def prop(node: Any) -> int:
                return fake.pyint()

        assert Foo.__dict__["prop"].is_data is True


class TestMixedCachedProperty:
    """Tests for mixed_cached_property (plain variant)."""

    def test_instance_caches_on_instance(self, fake: Faker) -> None:
        """GIVEN a mixed_cached_property
        WHEN accessed on an instance twice
        THEN the value is cached on the instance.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Foo:
            counter = 0

            @mixed_cached_property
            def prop(node: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        for _ in range(tries):
            assert obj.prop == values[0]

        assert Foo.counter == 1

    def test_class_caches_on_accessed_class(self, fake: Faker) -> None:
        """GIVEN a mixed_cached_property on a base class
        WHEN accessed on a child class
        THEN the value is cached on the accessed class.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Base:
            counter = 0

            @mixed_cached_property
            def prop(node: Any) -> int:
                value = values[node.counter]
                node.counter += 1
                return value

        class Child(Base):
            counter = 0

        for _ in range(tries):
            assert Child.prop == values[0]

        assert Base.counter == 0
        assert Child.counter == 1
        assert "__class_memoized__" in Child.__dict__

    def test_get_node_returns_node_verbatim(self, fake: Faker) -> None:
        """GIVEN a mixed_cached_property
        WHEN get_node is called
        THEN the supplied node is returned verbatim.
        """

        class Foo:
            @mixed_cached_property
            def prop(node: Any) -> int:
                return fake.pyint()

        obj = Foo()
        desc = Foo.__dict__["prop"]
        assert desc.get_node(obj) is obj
        assert desc.get_node(Foo) is Foo

    def test_here_returns_parent_class(self) -> None:
        """GIVEN mixed_cached_property
        WHEN .here is accessed
        THEN it returns mixed_parent_cached_property.
        """
        desc = mixed_cached_property.here
        assert desc is mixed_parent_cached_property

    def test_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent mixed_cached_property
        WHEN a child overrides via with_parent
        THEN the parent value is injected.
        """
        values = [fake.pyint(), fake.pyint()]

        class Parent:
            counter = 0

            @mixed_cached_property
            def prop(node: Any) -> int:
                Parent.counter += 1
                return values[0]

        class Child(Parent):
            @mixed_cached_property.with_parent
            def prop(node: Any, parent_result: int) -> int:
                return parent_result + values[1]

        obj = Child()
        for _ in range(fake.pyint(min_value=2, max_value=5)):
            assert Child.prop == values[0] + values[1]
            assert obj.prop == values[0] + values[1]

        assert Parent.counter == 2


class TestPreParentCachedProperty:
    """Tests for pre_parent_cached_property."""

    def test_class_access_caches_on_owner(self, fake: Faker) -> None:
        """GIVEN a pre_parent_cached_property on a base class
        WHEN accessed on a child class
        THEN the value is cached on the owner class.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Base:
            counter = 0

            @pre_parent_cached_property
            def prop(node: Any) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            pass

        for _ in range(tries):
            assert Child.prop == values[0]

        assert Base.counter == 1
        assert "__class_memoized__" in Base.__dict__

    def test_instance_access_does_not_cache(self, fake: Faker) -> None:
        """GIVEN a pre_parent_cached_property
        WHEN accessed on an instance twice
        THEN it recomputes each time.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries)]

        class Foo:
            counter = 0

            @pre_parent_cached_property
            def prop(node: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        for i in range(tries):
            assert obj.prop == values[i]

        assert Foo.counter == tries
        assert "__instance_memoized__" not in obj.__dict__

    def test_set_skips_instance_cache(self, fake: Faker) -> None:
        """GIVEN a pre_parent_cached_property
        WHEN __set__ is called on an instance
        THEN the instance cache is not used.
        """
        override = fake.pyint()

        class Foo:
            @pre_parent_cached_property
            def prop(node: Any) -> int:
                return fake.pyint()

        desc = Foo.__dict__["prop"]
        obj = Foo()
        desc.__set__(obj, override)
        cache = obj.__dict__.get("__instance_memoized__", {})
        assert "prop" not in cache

    def test_set_uses_class_cache(self, fake: Faker) -> None:
        """GIVEN a pre_parent_cached_property
        WHEN __set__ is called on a class
        THEN the class cache stores the value.
        """
        override = fake.pyint()

        class Foo:
            @pre_parent_cached_property
            def prop(node: Any) -> int:
                return fake.pyint()

        desc = Foo.__dict__["prop"]
        desc.__set__(Foo, override)
        assert Foo.__dict__["__class_memoized__"]["prop"] == override


class TestPreCachedProperty:
    """Tests for pre_cached_property (plain variant)."""

    def test_class_access_caches_on_accessed_class(self, fake: Faker) -> None:
        """GIVEN a pre_cached_property on a base class
        WHEN accessed on a child class
        THEN the value is cached on the accessed class.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Base:
            counter = 0

            @pre_cached_property
            def prop(node: Any) -> int:
                value = values[node.counter]
                node.counter += 1
                return value

        class Child(Base):
            counter = 0

        for _ in range(tries):
            assert Child.prop == values[0]

        assert Base.counter == 0
        assert Child.counter == 1
        assert "__class_memoized__" in Child.__dict__

    def test_here_returns_parent_class(self) -> None:
        """GIVEN pre_cached_property
        WHEN .here is accessed
        THEN it returns pre_parent_cached_property.
        """
        desc = pre_cached_property.here
        assert desc is pre_parent_cached_property


class TestPostParentCachedProperty:
    """Tests for post_parent_cached_property."""

    def test_instance_access_caches_on_instance(self, fake: Faker) -> None:
        """GIVEN a post_parent_cached_property
        WHEN accessed on an instance twice
        THEN the value is cached on the instance.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Foo:
            counter = 0

            @post_parent_cached_property
            def prop(node: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        for _ in range(tries):
            assert obj.prop == values[0]

        assert Foo.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_class_access_does_not_cache(self, fake: Faker) -> None:
        """GIVEN a post_parent_cached_property
        WHEN accessed on a class twice
        THEN it recomputes each time.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries)]

        class Foo:
            counter = 0

            @post_parent_cached_property
            def prop(node: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        for i in range(tries):
            assert Foo.prop == values[i]

        assert Foo.counter == tries
        cache = Foo.__dict__.get("__class_memoized__", {})
        assert "prop" not in cache

    def test_set_skips_class_cache(self, fake: Faker) -> None:
        """GIVEN a post_parent_cached_property
        WHEN __set__ is called on a class
        THEN the class cache is not used.
        """
        override = fake.pyint()

        class Foo:
            @post_parent_cached_property
            def prop(node: Any) -> int:
                return fake.pyint()

        desc = Foo.__dict__["prop"]
        desc.__set__(Foo, override)
        cache = Foo.__dict__.get("__class_memoized__", {})
        assert "prop" not in cache

    def test_set_uses_instance_cache(self, fake: Faker) -> None:
        """GIVEN a post_parent_cached_property
        WHEN __set__ is called on an instance
        THEN the instance cache stores the value.
        """
        override = fake.pyint()

        class Foo:
            @post_parent_cached_property
            def prop(node: Any) -> int:
                return fake.pyint()

        desc = Foo.__dict__["prop"]
        obj = Foo()
        desc.__set__(obj, override)
        assert obj.__dict__["__instance_memoized__"]["prop"] == override


class TestPostCachedProperty:
    """Tests for post_cached_property (plain variant)."""

    def test_instance_access_caches_on_instance(self, fake: Faker) -> None:
        """GIVEN a post_cached_property
        WHEN accessed on an instance twice
        THEN the value is cached on the instance.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries * 2)]

        class Foo:
            counter = 0

            @post_cached_property
            def prop(node: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        for _ in range(tries):
            assert obj.prop == values[0]

        assert Foo.counter == 1

    def test_class_access_does_not_cache(self, fake: Faker) -> None:
        """GIVEN a post_cached_property on a base class
        WHEN accessed on a child class twice
        THEN it recomputes each time and skips class cache.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries)]

        class Base:
            counter = 0

            @post_cached_property
            def prop(node: Any) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            pass

        for i in range(tries):
            assert Child.prop == values[i]

        assert Base.counter == tries
        cache = Child.__dict__.get("__class_memoized__", {})
        assert "prop" not in cache

    def test_here_returns_parent_class(self) -> None:
        """GIVEN post_cached_property
        WHEN .here is accessed
        THEN it returns post_parent_cached_property.
        """
        desc = post_cached_property.here
        assert desc is post_parent_cached_property
