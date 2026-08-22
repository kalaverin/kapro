"""Tests for kapro.properties module."""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Any

import pytest
import time_machine
from faker import Faker

from kapro import (
    class_property,
    mixed_property,
    pin,
)
from kapro.primitives import (
    AttributeExceptionError,
    BaseProperty,
    ContextFaultError,
    PropertyError,
    ReadOnlyError,
)


class TestPin:
    """Tests for @pin (bound_property)."""

    def test_instance_caches_value(self, fake: Faker) -> None:
        """GIVEN a @pin property
        WHEN accessed twice on an instance
        THEN the value is computed once and cached in __dict__.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin
            def prop(self) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        assert obj.prop == values[0]
        assert obj.prop == values[0]
        assert Foo.counter == 1
        assert "prop" in obj.__dict__
        assert obj.__dict__["prop"] == values[0]

    def test_class_access_raises(self, fake: Faker) -> None:
        """GIVEN a @pin property
        WHEN accessed on the class
        THEN ContextFaultError is raised.
        """

        class Foo:
            @pin
            def prop(self) -> int:
                return fake.pyint()

        with pytest.raises(ContextFaultError):
            Foo.prop

    def test_delete_raises(self, fake: Faker) -> None:
        """GIVEN a cached @pin property
        WHEN deleted from the instance
        THEN ReadOnlyError is raised.
        """
        values = [fake.pyint()]

        class Foo:
            @pin
            def prop(self) -> int:
                return values[0]

        obj = Foo()
        assert obj.prop == values[0]
        with pytest.raises(ReadOnlyError):
            del obj.prop

    def test_rejects_async(self, fake: Faker) -> None:
        """GIVEN an async method decorated with @pin
        WHEN the class is defined
        THEN TypeError is raised.
        """
        with pytest.raises(TypeError):

            class Foo:
                @pin
                async def prop(self) -> int:
                    return fake.pyint()

    def test_instances_have_separate_cache(self, fake: Faker) -> None:
        """GIVEN two instances with @pin properties
        WHEN each accesses the property
        THEN they cache independent values.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin
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


class TestPinNative:
    """Tests for @pin.native (cached_property)."""

    def test_instance_caches_value(self, fake: Faker) -> None:
        """GIVEN a @pin.native property
        WHEN accessed twice on an instance
        THEN the value is computed once and cached.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.native
            def prop(self) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        assert obj.prop == values[0]
        assert obj.prop == values[0]
        assert Foo.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_manual_set_and_delete(self, fake: Faker) -> None:
        """GIVEN a @pin.native cached value
        WHEN overridden and then deleted
        THEN the manual value is used until the cache is cleared.
        """
        initial = fake.pyint()
        override = fake.pyint()

        class Foo:
            @pin.native
            def prop(self) -> int:
                return initial

        obj = Foo()
        assert obj.prop == initial
        obj.prop = override
        assert obj.prop == override
        del obj.prop
        assert obj.prop == initial

    def test_ttl_expiration(self, fake: Faker) -> None:
        """GIVEN a @pin.native property with a TTL
        WHEN time advances past the TTL
        THEN the value is recomputed.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.native.ttl(ttl_seconds)
            def prop(self) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        with time_machine.travel(0, tick=False) as traveller:
            obj = Foo()
            assert obj.prop == values[0]
            assert obj.prop == values[0]
            assert Foo.counter == 1
            traveller.shift(timedelta(seconds=ttl_seconds * 2))
            assert obj.prop == values[1]
            assert Foo.counter == 2

    def test_instances_have_separate_cache(self, fake: Faker) -> None:
        """GIVEN two instances with @pin.native properties
        WHEN each accesses the property
        THEN they have separate caches.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.native
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


class TestPinCls:
    """Tests for @pin.cls (child-aware class cached property)."""

    def test_class_access_caches(self, fake: Faker) -> None:
        """GIVEN a @pin.cls property
        WHEN accessed repeatedly on the class
        THEN the value is computed once and cached on the class.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.cls
            def prop(cls) -> int:
                Foo.counter += 1
                return values[0]

        assert Foo.prop == values[0]
        assert Foo.prop == values[0]
        assert Foo.counter == 1
        assert "__class_memoized__" in Foo.__dict__

    def test_instance_access_uses_class(self, fake: Faker) -> None:
        """GIVEN a @pin.cls property
        WHEN accessed on an instance
        THEN it uses the class cache.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.cls
            def prop(cls) -> int:
                Foo.counter += 1
                return values[0]

        obj = Foo()
        assert obj.prop == values[0]
        assert obj.prop == values[0]
        assert Foo.counter == 1

    def test_inheritance_passes_child_class(self, fake: Faker) -> None:
        """GIVEN a @pin.cls property on a base class
        WHEN accessed on a child class and its instance
        THEN the child class is passed to the getter.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.cls
            def prop(cls) -> str:
                Foo.counter += 1
                return f"{cls.__name__}_{values[0]}"

        class Bar(Foo):
            pass

        expected = f"{Bar.__name__}_{values[0]}"
        assert Bar.prop == expected
        assert Bar().prop == expected
        assert Foo.counter == 1
        assert Bar.prop == expected
        assert Bar().prop == expected
        assert Foo.counter == 1

    def test_inheritance_separate_cache_per_class(self, fake: Faker) -> None:
        """GIVEN @pin.cls on a base and child class
        WHEN each class accesses the property
        THEN they cache independent values.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.cls
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        class Bar(Foo):
            pass

        assert Foo.prop == values[0]
        assert Bar.prop == values[1]
        assert Foo.prop == values[0]
        assert Bar.prop == values[1]


class TestPinAny:
    """Tests for @pin.any (mixed cached property)."""

    def test_instance_caches(self, fake: Faker) -> None:
        """GIVEN a @pin.any property
        WHEN accessed twice on an instance
        THEN the value is cached on the instance.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.any
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        assert obj.prop == values[0]
        assert obj.prop == values[0]
        assert Foo.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_class_caches(self, fake: Faker) -> None:
        """GIVEN a @pin.any property
        WHEN accessed twice on the class
        THEN the value is cached on the class.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.any
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        assert Foo.prop == values[0]
        assert Foo.prop == values[0]
        assert Foo.counter == 1
        assert "__class_memoized__" in Foo.__dict__

    def test_instance_and_class_caches_are_separate(self, fake: Faker) -> None:
        """GIVEN a @pin.any property
        WHEN accessed on both instance and class
        THEN the two caches are independent.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values_i = [fake.pyint() for _ in range(tries)]
        values_c = [fake.pyint() for _ in range(tries)]

        class Foo:
            counter_i = 0
            counter_c = 0

            @pin.any
            def prop(self_or_cls: Any) -> int:
                if isinstance(self_or_cls, type):
                    value = values_c[Foo.counter_c]
                    Foo.counter_c += 1
                else:
                    value = values_i[Foo.counter_i]
                    Foo.counter_i += 1
                return value

        obj = Foo()
        assert obj.prop == values_i[0]
        assert Foo.prop == values_c[0]
        assert obj.prop == values_i[0]
        assert Foo.prop == values_c[0]
        assert Foo.counter_i == 1
        assert Foo.counter_c == 1

    def test_inheritance_passes_child(self, fake: Faker) -> None:
        """GIVEN a @pin.any property on a base class
        WHEN accessed on a child class and its instance
        THEN the child identity is passed to the getter.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            @pin.any
            def prop(self_or_cls: Any) -> str:
                if isinstance(self_or_cls, type):
                    name = self_or_cls.__name__
                else:
                    name = self_or_cls.__class__.__name__
                return f"{name}_{values[0]}"

        class Bar(Foo):
            pass

        expected = f"{Bar.__name__}_{values[0]}"
        assert Bar.prop == expected
        assert Bar().prop == expected


class TestPinPre:
    """Tests for @pin.pre (mixed, caches only on class access)."""

    def test_class_access_caches(self, fake: Faker) -> None:
        """GIVEN a @pin.pre property
        WHEN accessed repeatedly on the class
        THEN the value is cached on the class.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.pre
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        assert Foo.prop == values[0]
        assert Foo.prop == values[0]
        assert Foo.counter == 1
        assert "__class_memoized__" in Foo.__dict__

    def test_instance_access_does_not_cache(self, fake: Faker) -> None:
        """GIVEN a @pin.pre property
        WHEN accessed repeatedly on an instance
        THEN it recomputes every time.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries)]

        class Foo:
            counter = 0

            @pin.pre
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        for i in range(tries):
            assert obj.prop == values[i]

        assert Foo.counter == tries
        assert "__instance_memoized__" not in obj.__dict__

    def test_class_and_instance_are_independent(self, fake: Faker) -> None:
        """GIVEN a @pin.pre property
        WHEN accessed on class and instance
        THEN class is cached while instance recomputes.
        """
        values_c = [fake.pyint(), fake.pyint()]
        values_i = [fake.pyint(), fake.pyint()]

        class Foo:
            counter_c = 0
            counter_i = 0

            @pin.pre
            def prop(self_or_cls: Any) -> int:
                if isinstance(self_or_cls, type):
                    value = values_c[Foo.counter_c]
                    Foo.counter_c += 1
                else:
                    value = values_i[Foo.counter_i]
                    Foo.counter_i += 1
                return value

        obj = Foo()
        assert Foo.prop == values_c[0]
        assert Foo.prop == values_c[0]
        assert obj.prop == values_i[0]
        assert obj.prop == values_i[1]
        assert Foo.counter_c == 1
        assert Foo.counter_i == 2

class TestPinPost:
    """Tests for @pin.post (mixed, caches only on instance access)."""

    def test_instance_access_caches(self, fake: Faker) -> None:
        """GIVEN a @pin.post property
        WHEN accessed twice on an instance
        THEN the value is cached on the instance.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.post
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        assert obj.prop == values[0]
        assert obj.prop == values[0]
        assert Foo.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_class_access_does_not_cache(self, fake: Faker) -> None:
        """GIVEN a @pin.post property
        WHEN accessed repeatedly on the class
        THEN it recomputes and does not use the class cache.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries)]

        class Foo:
            counter = 0

            @pin.post
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        for i in range(tries):
            assert Foo.prop == values[i]

        assert Foo.counter == tries
        cache = Foo.__dict__["__class_memoized__"]
        assert "prop" not in cache

    def test_class_and_instance_are_independent(self, fake: Faker) -> None:
        """GIVEN a @pin.post property
        WHEN accessed on instance and class
        THEN instance is cached while class recomputes.
        """
        values_i = [fake.pyint(), fake.pyint()]
        values_c = [fake.pyint(), fake.pyint()]

        class Foo:
            counter_i = 0
            counter_c = 0

            @pin.post
            def prop(self_or_cls: Any) -> int:
                if isinstance(self_or_cls, type):
                    value = values_c[Foo.counter_c]
                    Foo.counter_c += 1
                else:
                    value = values_i[Foo.counter_i]
                    Foo.counter_i += 1
                return value

        obj = Foo()
        assert obj.prop == values_i[0]
        assert obj.prop == values_i[0]
        assert Foo.prop == values_c[0]
        assert Foo.prop == values_c[1]
        assert Foo.counter_i == 1
        assert Foo.counter_c == 2


class TestClassProperty:
    """Tests for @class_property."""

    def test_instance_access_passes_class(self) -> None:
        """GIVEN a @class_property
        WHEN accessed on an instance
        THEN the class is passed to the getter.
        """

        class Foo:
            @class_property
            def prop(cls) -> str:
                return cls.__name__

        assert Foo().prop == Foo.__name__

    def test_class_access_passes_actual_class(self) -> None:
        """GIVEN a @class_property in an inheritance chain
        WHEN accessed on a child class and its instance
        THEN the actual class is passed to the getter.
        """

        class Foo:
            @class_property
            def prop(cls) -> str:
                return cls.__name__

        class Bar(Foo):
            pass

        assert Bar.prop == Bar.__name__
        assert Bar().prop == Bar.__name__

    def test_no_caching(self, fake: Faker) -> None:
        """GIVEN a @class_property
        WHEN accessed repeatedly
        THEN it never caches and always recomputes.
        """
        values = [fake.pyint() for _ in range(4)]

        class Foo:
            counter = 0

            @class_property
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        assert Foo.prop == values[0]
        assert Foo.prop == values[1]
        assert Foo().prop == values[2]
        assert Foo().prop == values[3]


class TestMixedProperty:
    """Tests for @mixed_property."""

    def test_instance_access_passes_instance(self, fake: Faker) -> None:
        """GIVEN a @mixed_property
        WHEN accessed on an instance
        THEN the instance is passed to the getter.
        """
        instance_label = fake.word()
        class_label = fake.word()

        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                return (
                    instance_label
                    if not isinstance(self_or_cls, type)
                    else class_label
                )

        assert Foo().prop == instance_label

    def test_class_access_passes_class(self, fake: Faker) -> None:
        """GIVEN a @mixed_property
        WHEN accessed on the class
        THEN the class is passed to the getter.
        """
        instance_label = fake.word()
        class_label = fake.word()

        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                return (
                    instance_label
                    if not isinstance(self_or_cls, type)
                    else class_label
                )

        assert Foo.prop == class_label

    def test_falsy_instance_gets_itself(self) -> None:
        """GIVEN a falsy instance with a @mixed_property
        WHEN the property is accessed
        THEN the instance itself is passed to the getter.
        """

        class Falsy:
            def __bool__(self) -> bool:
                return False

            @mixed_property
            def prop(self_or_cls: Any) -> Any:
                return self_or_cls

        obj = Falsy()
        assert obj.prop is obj

    def test_no_caching(self, fake: Faker) -> None:
        """GIVEN a @mixed_property
        WHEN accessed repeatedly
        THEN it never caches and always recomputes.
        """
        values = [fake.pyint() for _ in range(4)]

        class Foo:
            counter = 0

            @mixed_property
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        assert Foo().prop == values[0]
        assert Foo().prop == values[1]
        assert Foo.prop == values[2]
        assert Foo.prop == values[3]


class TestWithParent:
    """Tests for BaseProperty.with_parent() method."""

    def test_pin_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent @pin property
        WHEN a child overrides via with_parent
        THEN the parent value is injected and cached.
        """
        values = [fake.pyint(), fake.pyint()]

        class Parent:
            counter = 0

            @pin
            def prop(self) -> int:
                Parent.counter += 1
                return values[0]

        class Child(Parent):
            @pin.with_parent
            def prop(self, parent_value: int) -> int:
                return parent_value + values[1]

        obj = Child()
        expected = values[0] + values[1]
        assert obj.prop == expected
        assert obj.prop == expected
        assert Parent.counter == 1

    def test_pin_native_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent @pin.native property
        WHEN a child overrides via with_parent
        THEN the parent value is injected and cached.
        """
        values = [fake.pyint(), fake.pyint()]

        class Parent:
            counter = 0

            @pin.native
            def prop(self) -> int:
                Parent.counter += 1
                return values[0]

        class Child(Parent):
            @pin.native.with_parent
            def prop(self, parent_value: int) -> int:
                return parent_value + values[1]

        obj = Child()
        expected = values[0] + values[1]
        assert obj.prop == expected
        assert obj.prop == expected
        assert Parent.counter == 1

    def test_pin_cls_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent @pin.cls property
        WHEN a child overrides via with_parent
        THEN the parent value is injected into the class getter.
        """
        parent_prefix = fake.word()
        child_prefix = fake.word()

        class Parent:
            counter = 0

            @pin.cls
            def prop(cls) -> str:
                Parent.counter += 1
                return f"{parent_prefix}_{cls.__name__}"

        class Child(Parent):
            @pin.cls.with_parent
            def prop(cls, parent_value: str) -> str:
                return f"{child_prefix}_{parent_value}"

        expected = f"{child_prefix}_{parent_prefix}_{Child.__name__}"
        assert Child.prop == expected
        assert Child.prop == expected
        assert Parent.counter == 1

    def test_pin_any_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent @pin.any property
        WHEN a child overrides via with_parent
        THEN the parent value is injected for both instance and class access.
        """
        values = [fake.pyint(), fake.pyint()]

        class Parent:
            counter = 0

            @pin.any
            def prop(self_or_cls: Any) -> int:
                Parent.counter += 1
                return values[0]

        class Child(Parent):
            @pin.any.with_parent
            def prop(self_or_cls: Any, parent_value: int) -> int:
                return parent_value + values[1]

        obj = Child()
        expected = values[0] + values[1]
        assert obj.prop == expected
        assert Child.prop == expected
        assert Parent.counter == 2  # instance and class are separate

    def test_pin_pre_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent @pin.pre property
        WHEN a child overrides via with_parent
        THEN the parent value is injected for class-cached access.
        """
        values = [fake.pyint(), fake.pyint()]

        class Parent:
            @pin.pre
            def prop(self_or_cls: Any) -> int:
                return values[0]

        class Child(Parent):
            @pin.pre.with_parent
            def prop(self_or_cls: Any, parent_value: int) -> int:
                return parent_value + values[1]

        expected = values[0] + values[1]
        assert Child.prop == expected
        assert Child().prop == expected

    def test_pin_post_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent @pin.post property
        WHEN a child overrides via with_parent
        THEN the parent value is injected for instance-cached access.
        """
        values = [fake.pyint(), fake.pyint()]

        class Parent:
            @pin.post
            def prop(self_or_cls: Any) -> int:
                return values[0]

        class Child(Parent):
            @pin.post.with_parent
            def prop(self_or_cls: Any, parent_value: int) -> int:
                return parent_value + values[1]

        expected = values[0] + values[1]
        assert Child.prop == expected
        assert Child().prop == expected

    def test_class_property_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent @class_property
        WHEN a child overrides via with_parent
        THEN the parent value is injected into the class getter.
        """
        parent_prefix = fake.word()
        child_prefix = fake.word()

        class Parent:
            counter = 0

            @class_property
            def prop(cls) -> str:
                Parent.counter += 1
                return f"{parent_prefix}_{cls.__name__}"

        class Child(Parent):
            @class_property.with_parent
            def prop(cls, parent_value: str) -> str:
                return f"{child_prefix}_{parent_value}"

        expected = f"{child_prefix}_{parent_prefix}_{Child.__name__}"
        assert Child.prop == expected
        assert Child().prop == expected

    def test_mixed_property_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent @mixed_property
        WHEN a child overrides via with_parent
        THEN the parent value is injected into the mixed getter.
        """
        parent_word = fake.word()
        child_word = fake.word()

        class Parent:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                return parent_word

        class Child(Parent):
            @mixed_property.with_parent
            def prop(self_or_cls: Any, parent_value: str) -> str:
                return f"{child_word}_{parent_value}"

        expected = f"{child_word}_{parent_word}"
        assert Child.prop == expected
        assert Child().prop == expected

    def test_with_parent_without_parent_descriptor(self, fake: Faker) -> None:
        """GIVEN a class using @pin.with_parent without a parent descriptor
        WHEN the property is accessed
        THEN NotImplementedError is raised.
        """
        offset = fake.pyint()

        class Foo:
            @pin.with_parent
            def prop(self, parent_value: int) -> int:
                return parent_value + offset

        obj = Foo()
        with pytest.raises(NotImplementedError):
            obj.prop

class TestCustomCallbackBy:
    """Tests for .by() and .ttl() custom cache invalidation."""

    def test_pin_native_by_custom_callback(self, fake: Faker) -> None:
        """GIVEN a custom is_actual callback on @pin.native
        WHEN the callback reports stale
        THEN the value is recomputed.
        """
        expired = False
        values = [fake.pyint(), fake.pyint()]

        def is_actual(
            _self: Any,
            _node: Any,
            timestamp: float | None = None,
        ) -> bool | float:
            if timestamp is None:
                return time.time()
            return not expired

        class Foo:
            counter = 0

            @pin.native.by(is_actual)
            def prop(self) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        assert obj.prop == values[0]
        assert obj.prop == values[0]
        assert Foo.counter == 1

        expired = True
        assert obj.prop == values[1]
        assert Foo.counter == 2

    def test_pin_native_expired_by_alias(self, fake: Faker) -> None:
        """GIVEN a custom is_still_valid callback on @pin.native
        WHEN it flips to invalid
        THEN the value is recomputed.
        """
        expired = False
        values = [fake.pyint(), fake.pyint()]

        def is_still_valid(
            _self: Any,
            _node: Any,
            timestamp: float | None = None,
        ) -> bool | float:
            if timestamp is None:
                return time.time()
            return not expired

        class Foo:
            counter = 0

            @pin.native.by(is_still_valid)
            def prop(self) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        assert obj.prop == values[0]
        assert Foo.counter == 1

        expired = True
        assert obj.prop == values[1]
        assert Foo.counter == 2

    def test_pin_cls_by_custom_callback(self, fake: Faker) -> None:
        """GIVEN a custom callback on @pin.cls
        WHEN it reports stale
        THEN the class value is recomputed.
        """
        expired = False
        values = [fake.pyint(), fake.pyint()]

        def is_still_valid(
            _self: Any,
            _node: Any,
            timestamp: float | None = None,
        ) -> bool | float:
            if timestamp is None:
                return time.time()
            return not expired

        class Foo:
            counter = 0

            @pin.cls.by(is_still_valid)
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        assert Foo.prop == values[0]
        assert Foo.counter == 1

        expired = True
        assert Foo.prop == values[1]
        assert Foo.counter == 2

    def test_pin_any_by_custom_callback(self, fake: Faker) -> None:
        """GIVEN a custom callback on @pin.any
        WHEN it reports stale
        THEN the cached value is recomputed.
        """
        expired = False
        values = [fake.pyint(), fake.pyint(), fake.pyint()]

        def is_still_valid(
            _self: Any,
            _node: Any,
            timestamp: float | None = None,
        ) -> bool | float:
            if timestamp is None:
                return time.time()
            return not expired

        class Foo:
            counter = 0

            @pin.any.by(is_still_valid)
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        assert obj.prop == values[0]
        assert Foo.prop == values[1]
        assert Foo.counter == 2

        expired = True
        assert obj.prop == values[2]
        assert Foo.counter == 3

    def test_ttl_on_pin_native(self, fake: Faker) -> None:
        """GIVEN a TTL on @pin.native
        WHEN time advances past the TTL
        THEN the value is recomputed.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.native.ttl(ttl_seconds)
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

    def test_ttl_on_pin_cls(self, fake: Faker) -> None:
        """GIVEN a TTL on @pin.cls
        WHEN time advances past the TTL
        THEN the class value is recomputed.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.cls.ttl(ttl_seconds)
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        with time_machine.travel(0, tick=False) as traveller:
            assert Foo.prop == values[0]
            assert Foo.counter == 1
            traveller.shift(timedelta(seconds=ttl_seconds * 2))
            assert Foo.prop == values[1]
            assert Foo.counter == 2

    def test_ttl_on_pin_any(self, fake: Faker) -> None:
        """GIVEN a TTL on @pin.any
        WHEN time advances past the TTL
        THEN the value is recomputed.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.any.ttl(ttl_seconds)
            def prop(self_or_cls: Any) -> int:
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

    def test_ttl_on_pin_pre(self, fake: Faker) -> None:
        """GIVEN a TTL on @pin.pre
        WHEN time advances past the TTL
        THEN the class value is recomputed.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.pre.ttl(ttl_seconds)
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        with time_machine.travel(0, tick=False) as traveller:
            assert Foo.prop == values[0]
            assert Foo.counter == 1
            traveller.shift(timedelta(seconds=ttl_seconds * 2))
            assert Foo.prop == values[1]
            assert Foo.counter == 2

    def test_ttl_on_pin_post(self, fake: Faker) -> None:
        """GIVEN a TTL on @pin.post
        WHEN time advances past the TTL
        THEN the instance value is recomputed.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.post.ttl(ttl_seconds)
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

    def test_ttl_rejects_non_number(self, fake: Faker) -> None:
        """GIVEN a non-numeric TTL
        WHEN applied to @pin.native.ttl
        THEN TypeError is raised.
        """
        with pytest.raises(TypeError, match="expire must be float or int"):
            pin.native.ttl(fake.word())

    def test_ttl_rejects_zero(self, fake: Faker) -> None:
        """GIVEN a zero TTL
        WHEN applied to @pin.native.ttl
        THEN ValueError is raised.
        """
        zero_ttl = fake.pyint(min_value=0, max_value=0)
        with pytest.raises(
            ValueError,
            match="expire must be a positive number",
        ):
            pin.native.ttl(zero_ttl)

    def test_ttl_rejects_negative(self, fake: Faker) -> None:
        """GIVEN a negative TTL
        WHEN applied to @pin.native.ttl
        THEN ValueError is raised.
        """
        negative_ttl = fake.pyint(min_value=-10, max_value=-1)
        with pytest.raises(
            ValueError,
            match="expire must be a positive number",
        ):
            pin.native.ttl(negative_ttl)

    def test_pin_pre_by_custom_callback(self, fake: Faker) -> None:
        """GIVEN a custom callback on @pin.pre
        WHEN it reports stale
        THEN the class value is recomputed.
        """
        expired = False
        values = [fake.pyint(), fake.pyint()]

        def is_still_valid(
            _self: Any,
            _node: Any,
            timestamp: float | None = None,
        ) -> bool | float:
            if timestamp is None:
                return time.time()
            return not expired

        class Foo:
            counter = 0

            @pin.pre.by(is_still_valid)
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        assert Foo.prop == values[0]
        assert Foo.counter == 1

        expired = True
        assert Foo.prop == values[1]
        assert Foo.counter == 2

    def test_pin_pre_ttl_expiration(self, fake: Faker) -> None:
        """GIVEN a TTL on @pin.pre
        WHEN time advances past the TTL
        THEN the class value is recomputed.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.pre.ttl(ttl_seconds)
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        with time_machine.travel(0, tick=False) as traveller:
            assert Foo.prop == values[0]
            assert Foo.counter == 1
            traveller.shift(timedelta(seconds=ttl_seconds * 2))
            assert Foo.prop == values[1]
            assert Foo.counter == 2

    def test_pin_post_by_custom_callback(self, fake: Faker) -> None:
        """GIVEN a custom callback on @pin.post
        WHEN it reports stale
        THEN the instance value is recomputed.
        """
        expired = False
        values = [fake.pyint(), fake.pyint()]

        def is_still_valid(
            _self: Any,
            _node: Any,
            timestamp: float | None = None,
        ) -> bool | float:
            if timestamp is None:
                return time.time()
            return not expired

        class Foo:
            counter = 0

            @pin.post.by(is_still_valid)
            def prop(self) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        assert obj.prop == values[0]
        assert Foo.counter == 1

        expired = True
        assert obj.prop == values[1]
        assert Foo.counter == 2

    def test_pin_post_ttl_expiration(self, fake: Faker) -> None:
        """GIVEN a TTL on @pin.post
        WHEN time advances past the TTL
        THEN the instance value is recomputed.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.post.ttl(ttl_seconds)
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

    def test_pin_cls_here_by_custom_callback(self, fake: Faker) -> None:
        """GIVEN a custom callback on @pin.cls.here
        WHEN it reports stale
        THEN the owner class value is recomputed and shared.
        """
        expired = False
        values = [fake.pyint(), fake.pyint()]

        def is_still_valid(
            _self: Any,
            _node: Any,
            timestamp: float | None = None,
        ) -> bool | float:
            if timestamp is None:
                return time.time()
            return not expired

        class Base:
            counter = 0

            @pin.cls.here.by(is_still_valid)
            def prop(cls) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            pass

        assert Base.prop == values[0]
        assert Base.counter == 1
        assert Child.prop == values[0]
        assert Base.counter == 1      # shared owner cache

        expired = True
        assert Child.prop == values[1]
        assert Base.counter == 2

    def test_pin_cls_here_ttl_expiration(self, fake: Faker) -> None:
        """GIVEN a TTL on @pin.cls.here
        WHEN time advances past the TTL
        THEN the owner class value is recomputed and shared.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Base:
            counter = 0

            @pin.cls.here.ttl(ttl_seconds)
            def prop(cls) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            pass

        with time_machine.travel(0, tick=False) as traveller:
            assert Base.prop == values[0]
            assert Base.counter == 1
            assert Child.prop == values[0]
            assert Base.counter == 1      # shared owner cache

            traveller.shift(timedelta(seconds=ttl_seconds * 2))
            assert Child.prop == values[1]
            assert Base.counter == 2

    def test_pin_any_here_by_custom_callback(self, fake: Faker) -> None:
        """GIVEN a custom callback on @pin.any.here
        WHEN it reports stale
        THEN instance and class caches are recomputed independently.
        """
        expired = False
        values = [fake.pyint(), fake.pyint(), fake.pyint()]

        def is_still_valid(
            _self: Any,
            _node: Any,
            timestamp: float | None = None,
        ) -> bool | float:
            if timestamp is None:
                return time.time()
            return not expired

        class Base:
            counter = 0

            @pin.any.here.by(is_still_valid)
            def prop(self_or_cls: Any) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            pass

        obj = Child()
        assert obj.prop == values[0]
        assert Base.counter == 1
        assert obj.prop == values[0]
        assert Base.counter == 1      # instance cache

        expired = True
        assert obj.prop == values[1]
        assert Base.counter == 2

        assert Base.prop == values[2]
        assert Base.counter == 3      # class access recomputes

    def test_pin_any_here_ttl_expiration(self, fake: Faker) -> None:
        """GIVEN a TTL on @pin.any.here
        WHEN time advances past the TTL
        THEN the instance value is recomputed.
        """
        ttl_seconds = fake.pyint(min_value=1, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        class Base:
            counter = 0

            @pin.any.here.ttl(ttl_seconds)
            def prop(self_or_cls: Any) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            pass

        with time_machine.travel(0, tick=False) as traveller:
            obj = Child()
            assert obj.prop == values[0]
            assert Base.counter == 1
            traveller.shift(timedelta(seconds=ttl_seconds * 2))
            assert obj.prop == values[1]
            assert Base.counter == 2

    def test_pin_native_by_custom_stamp_handler(self, fake: Faker) -> None:
        """GIVEN a stamp-based callback on @pin.native
        WHEN the age crosses the threshold
        THEN the value is recomputed.
        """
        now = 0
        max_age = fake.pyint(min_value=2, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        def is_actual(
            _self: Any,
            _node: Any,
            stamp: float | None = None,
        ) -> bool | float:
            if stamp is None:
                return now
            return now - stamp < max_age

        class Foo:
            counter = 0

            @pin.native.by(is_actual)
            def prop(self) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        assert obj.prop == values[0]
        assert Foo.counter == 1

        now = max_age - 1
        assert obj.prop == values[0]
        assert Foo.counter == 1      # still within max_age

        now = max_age
        assert obj.prop == values[1]
        assert Foo.counter == 2      # exactly max_age, recompute

    def test_pin_cls_by_custom_stamp_handler(self, fake: Faker) -> None:
        """GIVEN a stamp-based callback on @pin.cls
        WHEN the age crosses the threshold
        THEN the class value is recomputed.
        """
        now = 0
        max_age = fake.pyint(min_value=2, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        def is_actual(
            _self: Any,
            _node: Any,
            stamp: float | None = None,
        ) -> bool | float:
            if stamp is None:
                return now
            return now - stamp < max_age

        class Foo:
            counter = 0

            @pin.cls.by(is_actual)
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        assert Foo.prop == values[0]
        assert Foo.counter == 1

        now = max_age - 1
        assert Foo.prop == values[0]
        assert Foo.counter == 1

        now = max_age
        assert Foo.prop == values[1]
        assert Foo.counter == 2

    def test_pin_pre_by_custom_stamp_handler(self, fake: Faker) -> None:
        """GIVEN a stamp-based callback on @pin.pre
        WHEN class access ages out
        THEN the class value is recomputed; instance access always recomputes.
        """
        now = 0
        max_age = fake.pyint(min_value=2, max_value=10)
        values = [fake.pyint(), fake.pyint(), fake.pyint()]

        def is_actual(
            _self: Any,
            _node: Any,
            stamp: float | None = None,
        ) -> bool | float:
            if stamp is None:
                return now
            return now - stamp < max_age

        class Foo:
            counter = 0

            @pin.pre.by(is_actual)
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        assert Foo.prop == values[0]
        assert Foo.counter == 1

        now = max_age - 1
        assert Foo.prop == values[0]
        assert Foo.counter == 1
        assert Foo().prop == values[1]       # instance access recomputes
        assert Foo.counter == 2

        now = max_age
        assert Foo.prop == values[2]
        assert Foo.counter == 3

    def test_pin_post_by_custom_stamp_handler(self, fake: Faker) -> None:
        """GIVEN a stamp-based callback on @pin.post
        WHEN instance access ages out
        THEN the instance value is recomputed; class access always recomputes.
        """
        now = 0
        max_age = fake.pyint(min_value=2, max_value=10)
        values = [fake.pyint(), fake.pyint(), fake.pyint()]

        def is_actual(
            _self: Any,
            _node: Any,
            stamp: float | None = None,
        ) -> bool | float:
            if stamp is None:
                return now
            return now - stamp < max_age

        class Foo:
            counter = 0

            @pin.post.by(is_actual)
            def prop(self) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        assert obj.prop == values[0]
        assert Foo.counter == 1

        now = max_age - 1
        assert obj.prop == values[0]
        assert Foo.counter == 1
        assert Foo.prop == values[1]         # class access recomputes
        assert Foo.counter == 2

        now = max_age
        assert obj.prop == values[2]
        assert Foo.counter == 3

    def test_pin_cls_here_by_custom_stamp_handler(self, fake: Faker) -> None:
        """GIVEN a stamp-based callback on @pin.cls.here
        WHEN the age crosses the threshold
        THEN the owner class value is recomputed and shared.
        """
        now = 0
        max_age = fake.pyint(min_value=2, max_value=10)
        values = [fake.pyint(), fake.pyint()]

        def is_actual(
            _self: Any,
            _node: Any,
            stamp: float | None = None,
        ) -> bool | float:
            if stamp is None:
                return now
            return now - stamp < max_age

        class Base:
            counter = 0

            @pin.cls.here.by(is_actual)
            def prop(cls) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            pass

        assert Base.prop == values[0]
        assert Base.counter == 1
        assert Child.prop == values[0]       # shared owner cache
        assert Base.counter == 1

        now = max_age - 1
        assert Child.prop == values[0]
        assert Base.counter == 1

        now = max_age
        assert Child.prop == values[1]
        assert Base.counter == 2

    def test_pin_any_here_by_custom_stamp_handler(self, fake: Faker) -> None:
        """GIVEN a stamp-based callback on @pin.any.here
        WHEN the instance ages out
        THEN the instance value is recomputed; class access is separate.
        """
        now = 0
        max_age = fake.pyint(min_value=2, max_value=10)
        values = [fake.pyint(), fake.pyint(), fake.pyint()]

        def is_actual(
            _self: Any,
            _node: Any,
            stamp: float | None = None,
        ) -> bool | float:
            if stamp is None:
                return now
            return now - stamp < max_age

        class Base:
            counter = 0

            @pin.any.here.by(is_actual)
            def prop(self_or_cls: Any) -> int:
                value = values[Base.counter]
                Base.counter += 1
                return value

        class Child(Base):
            pass

        obj = Child()
        assert obj.prop == values[0]
        assert Base.counter == 1

        now = max_age - 1
        assert obj.prop == values[0]
        assert Base.counter == 1      # instance cache still valid

        now = max_age
        assert obj.prop == values[1]
        assert Base.counter == 2

        assert Base.prop == values[2]
        assert Base.counter == 3      # class access recomputes


class TestExceptions:
    """Tests for descriptor exceptions."""

    def test_property_error_inheritance(self) -> None:
        """GIVEN the property exception hierarchy
        WHEN checking subclass relationships
        THEN all specific errors inherit from PropertyError.
        """
        assert issubclass(ContextFaultError, PropertyError)
        assert issubclass(ReadOnlyError, PropertyError)
        assert issubclass(AttributeExceptionError, PropertyError)

    def test_context_fault_error_catchable(self, fake: Faker) -> None:
        """GIVEN a @pin property accessed on the class
        WHEN ContextFaultError is raised
        THEN it is catchable via pytest.raises.
        """

        class Foo:
            @pin
            def prop(self) -> int:
                return fake.pyint()

        with pytest.raises(ContextFaultError):
            Foo.prop

    def test_read_only_error_on_delete(self, fake: Faker) -> None:
        """GIVEN a cached @pin property
        WHEN deletion is attempted
        THEN ReadOnlyError is raised.
        """
        values = [fake.pyint()]

        class Foo:
            @pin
            def prop(self) -> int:
                return values[0]

        obj = Foo()
        assert obj.prop == values[0]
        with pytest.raises(ReadOnlyError):
            del obj.prop

    def test_attribute_exception_wraps_error(self) -> None:
        """GIVEN a @pin.native getter that raises AttributeError
        WHEN the property is accessed
        THEN it is wrapped as AttributeExceptionError.
        """

        class Foo:
            @pin.native
            def prop(self) -> int:
                return self.nonexistent.attr

        obj = Foo()
        with pytest.raises(AttributeExceptionError) as exc_info:
            obj.prop
        assert hasattr(exc_info.value, "exception")
        assert isinstance(exc_info.value.exception, AttributeError)

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_pin_with_none_return(self) -> None:
        """GIVEN a @pin property returning None
        WHEN accessed twice
        THEN the None value is cached.
        """

        class Foo:
            counter = 0

            @pin
            def prop(self) -> None:
                Foo.counter += 1

        obj = Foo()
        assert obj.prop is None
        assert obj.prop is None
        assert Foo.counter == 1
        assert obj.__dict__["prop"] is None

    def test_pin_native_none_caching(self) -> None:
        """GIVEN a @pin.native property returning None
        WHEN accessed twice
        THEN the None value is cached.
        """

        class Foo:
            counter = 0

            @pin.native
            def prop(self) -> None:
                Foo.counter += 1

        obj = Foo()
        assert obj.prop is None
        assert obj.prop is None
        assert Foo.counter == 1

    def test_falsy_values_cached_correctly(self) -> None:
        """GIVEN a @pin.native property returning falsy values
        WHEN accessed repeatedly
        THEN each falsy value is cached independently.
        """

        class Foo:
            counter = 0

            @pin.native
            def zero(self) -> int:
                Foo.counter += 1
                return 0

            @pin.native
            def empty_str(self) -> str:
                Foo.counter += 1
                return ""

            @pin.native
            def empty_list(self) -> list:
                Foo.counter += 1
                return []

            @pin.native
            def false(self) -> bool:
                Foo.counter += 1
                return False

        obj = Foo()
        assert obj.zero == 0
        assert obj.zero == 0
        assert obj.empty_str == ""
        assert obj.empty_str == ""
        assert obj.empty_list == []
        assert obj.empty_list == []
        assert obj.false is False
        assert obj.false is False
        assert Foo.counter == 4

    def test_descriptor_string_repr(self, fake: Faker) -> None:
        """GIVEN a descriptor
        WHEN converted to string or repr
        THEN it mentions the descriptor or pin.
        """

        class Foo:
            @pin
            def prop(self) -> int:
                return fake.pyint()

        descriptor = Foo.__dict__["prop"]
        str_repr = str(descriptor)
        repr_str = repr(descriptor)
        assert "descriptor" in str_repr.lower() or "pin" in str_repr.lower()
        assert "descriptor" in repr_str.lower() or "pin" in repr_str.lower()

    def test_multiple_inheritance_with_pin_native(self, fake: Faker) -> None:
        """GIVEN a mixin with @pin.native
        WHEN inherited alongside another base
        THEN the property is still cached once.
        """
        values = [fake.pyint(), fake.pyint()]

        class Mixin:
            counter = 0

            @pin.native
            def prop(self) -> int:
                Mixin.counter += 1
                return values[0]

        class Base:
            pass

        class Child(Mixin, Base):
            pass

        obj = Child()
        assert obj.prop == values[0]
        assert obj.prop == values[0]
        assert Mixin.counter == 1

    def test_pin_native_delete_then_reaccess(self, fake: Faker) -> None:
        """GIVEN a @pin.native property
        WHEN the cache is deleted and accessed again
        THEN the value is recomputed.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.native
            def prop(self) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        assert obj.prop == values[0]
        del obj.prop
        assert obj.prop == values[1]
        assert obj.prop == values[1]

    def test_class_property_no_cache(self, fake: Faker) -> None:
        """GIVEN a @class_property
        WHEN accessed repeatedly
        THEN it never caches.
        """
        values = [fake.pyint() for _ in range(4)]

        class Foo:
            counter = 0

            @class_property
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        assert Foo.prop == values[0]
        assert Foo.prop == values[1]
        assert Foo().prop == values[2]
        assert Foo().prop == values[3]

    def test_mixed_property_no_cache(self, fake: Faker) -> None:
        """GIVEN a @mixed_property
        WHEN accessed repeatedly
        THEN it never caches.
        """
        values = [fake.pyint() for _ in range(4)]

        class Foo:
            counter = 0

            @mixed_property
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        assert Foo().prop == values[0]
        assert Foo().prop == values[1]
        assert Foo.prop == values[2]
        assert Foo.prop == values[3]


class TestDescriptorInternals:
    """Tests for internal descriptor behavior and attributes."""

    def test_pin_name_property(self, fake: Faker) -> None:
        """GIVEN a @pin descriptor
        WHEN its name attribute is read
        THEN it matches the defined method name.
        """

        class Foo:
            @pin
            def my_property(self) -> int:
                return fake.pyint()

        descriptor = Foo.__dict__["my_property"]
        assert descriptor.name == "my_property"

    def test_pin_native_name_property(self, fake: Faker) -> None:
        """GIVEN a @pin.native descriptor
        WHEN its name attribute is read
        THEN it matches the defined method name.
        """

        class Foo:
            @pin.native
            def my_property(self) -> int:
                return fake.pyint()

        descriptor = Foo.__dict__["my_property"]
        assert descriptor.name == "my_property"

    def test_is_data_property(self, fake: Faker) -> None:
        """GIVEN a cached descriptor
        WHEN checked for is_data
        THEN it reports True.
        """

        class Foo:
            @pin.native
            def cached_prop(self) -> int:
                return fake.pyint()

        cached_desc = Foo.__dict__["cached_prop"]
        assert cached_desc.is_data is True

    def test_class_property_is_not_data(self, fake: Faker) -> None:
        """GIVEN a @class_property descriptor
        WHEN checked for is_data
        THEN it reports False.
        """

        class Foo:
            @class_property
            def prop(cls) -> int:
                return fake.pyint()

        descriptor = Foo.__dict__["prop"]
        assert descriptor.is_data is False

    def test_mixed_property_is_not_data(self, fake: Faker) -> None:
        """GIVEN a @mixed_property descriptor
        WHEN checked for is_data
        THEN it reports False.
        """

        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> int:
                return fake.pyint()

        descriptor = Foo.__dict__["prop"]
        assert descriptor.is_data is False


class TestCachedSetOperations:
    """Tests for __set__ behavior on cached properties."""

    def test_manual_override_pin_native(self, fake: Faker) -> None:
        """GIVEN a @pin.native cached value
        WHEN manually overridden on the instance
        THEN the override is returned.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            @pin.native
            def prop(self) -> int:
                return values[0]

        obj = Foo()
        assert obj.prop == values[0]
        obj.prop = values[1]
        assert obj.prop == values[1]

    def test_manual_override_pin_cls(self, fake: Faker) -> None:
        """GIVEN a @pin.cls cached value
        WHEN manually overridden on the class
        THEN the override is returned.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            @pin.cls
            def prop(cls) -> int:
                return values[0]

        Foo.prop = values[1]  # type: ignore[assignment]
        assert Foo.prop == values[1]  # type: ignore[assignment]

    def test_manual_override_pin_any_instance(self, fake: Faker) -> None:
        """GIVEN a @pin.any property
        WHEN manually overridden on an instance
        THEN only the instance cache is affected.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            @pin.any
            def prop(self_or_cls: Any) -> int:
                return values[0]

        obj = Foo()
        assert obj.prop == values[0]
        obj.prop = values[1]
        assert obj.prop == values[1]
        assert Foo.prop == values[0]

    def test_manual_override_pin_pre_class_only(self, fake: Faker) -> None:
        """GIVEN a @pin.pre property
        WHEN manually set on an instance
        THEN the instance cache is ignored and recomputation continues.
        """
        values = [fake.pyint() for _ in range(3)]
        _override = fake.pyint()

        class Foo:
            counter = 0

            @pin.pre
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        assert obj.prop == values[0]
        assert obj.prop == values[1]
        obj.prop = _override
        val = obj.prop
        assert val == values[2]

    def test_manual_set_on_class_pin_pre(self, fake: Faker) -> None:
        """GIVEN a @pin.pre property
        WHEN manually set on the class
        THEN the class cache stores the override.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.pre
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        assert Foo.prop == values[0]
        assert Foo.prop == values[0]
        Foo.prop = values[1]  # type: ignore[assignment]
        assert Foo.prop == values[1]

    def test_manual_override_pin_post_instance_only(self, fake: Faker) -> None:
        """GIVEN a @pin.post property
        WHEN manually set on an instance
        THEN the instance cache stores the override.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @pin.post
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        assert obj.prop == values[0]
        obj.prop = values[1]
        assert obj.prop == values[1]


class TestInheritanceScenarios:
    """Complex inheritance scenarios."""

    def test_diamond_inheritance_with_pin_native(self, fake: Faker) -> None:
        """GIVEN a diamond inheritance with @pin.native
        WHEN the property is accessed
        THEN it is computed once and cached.
        """
        values = [fake.pyint(), fake.pyint()]

        class A:
            counter = 0

            @pin.native
            def prop(self) -> int:
                A.counter += 1
                return values[0]

        class B(A):
            pass

        class C(A):
            pass

        class D(B, C):
            pass

        obj = D()
        assert obj.prop == values[0]
        assert obj.prop == values[0]
        assert A.counter == 1

    def test_override_descriptor_type(self, fake: Faker) -> None:
        """GIVEN a parent @pin and child @pin.native
        WHEN the child property is accessed and manually set
        THEN the native override behavior applies.
        """
        values = [fake.pyint(), fake.pyint(), fake.pyint()]

        class Parent:
            @pin
            def prop(self) -> int:
                return values[0]

        class Child(Parent):
            @pin.native
            def prop(self) -> int:
                return values[1]

        obj = Child()
        assert obj.prop == values[1]
        obj.prop = values[2]
        assert obj.prop == values[2]


class TestBasePropertyInterface:
    """Tests for BaseProperty interface compliance."""

    def test_base_property_requires_title(self, fake: Faker) -> None:
        """GIVEN a concrete BaseProperty without title
        WHEN its title is read
        THEN NotImplementedError is raised.
        """

        class ConcreteProperty(BaseProperty):
            pass

        def func() -> int:
            return fake.pyint()

        with pytest.raises(NotImplementedError):
            _ = ConcreteProperty(func).title

    def test_base_property_requires_header_context(self, fake: Faker) -> None:
        """GIVEN a concrete BaseProperty with title
        WHEN header_with_context is called
        THEN NotImplementedError is raised.
        """

        class ConcreteProperty(BaseProperty):
            @property
            def title(self) -> str:
                return fake.pystr()

        def func() -> int:
            return fake.pyint()

        prop = ConcreteProperty(func)
        with pytest.raises(NotImplementedError):
            prop.header_with_context(None)


class TestPinSubclassing:
    """Tests for subclassing pin and its variants."""

    def test_pin_subclass_creation(self, fake: Faker) -> None:
        """GIVEN a custom subclass of pin
        WHEN used as a decorator
        THEN it behaves as a descriptor and exposes custom methods.
        """
        value = fake.pyint()
        custom_word = fake.word()

        class MyPin(pin):
            def custom_method(self) -> str:
                return custom_word

        class Foo:
            @MyPin
            def prop(self) -> int:
                return value

        obj = Foo()
        assert obj.prop == value
        descriptor = Foo.__dict__["prop"]
        assert descriptor.custom_method() == custom_word
