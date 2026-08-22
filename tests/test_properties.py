"""Tests for kapro.properties module."""

from __future__ import annotations

import time
from typing import Any

import pytest

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

    def test_instance_caches_value(self) -> None:
        class Foo:
            counter = 0

            @pin
            def prop(self) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.counter == 1
        assert "prop" in obj.__dict__
        assert obj.__dict__["prop"] == 42

    def test_class_access_raises(self) -> None:
        class Foo:
            @pin
            def prop(self) -> int:
                return 42

        with pytest.raises(ContextFaultError):
            Foo.prop

    def test_delete_raises(self) -> None:
        class Foo:
            @pin
            def prop(self) -> int:
                return 42

        obj = Foo()
        assert obj.prop == 42
        with pytest.raises(ReadOnlyError):
            del obj.prop

    def test_rejects_async(self) -> None:
        with pytest.raises(TypeError):

            class Foo:
                @pin
                async def prop(self) -> int:
                    return 42

    def test_instances_have_separate_cache(self) -> None:
        class Foo:
            counter = 0

            @pin
            def prop(self) -> int:
                Foo.counter += 1
                return Foo.counter

        a = Foo()
        b = Foo()
        assert a.prop == 1
        assert b.prop == 2
        assert a.prop == 1
        assert b.prop == 2


class TestPinNative:
    """Tests for @pin.native (cached_property)."""

    def test_instance_caches_value(self) -> None:
        class Foo:
            counter = 0

            @pin.native
            def prop(self) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_manual_set_and_delete(self) -> None:
        class Foo:
            @pin.native
            def prop(self) -> int:
                return 42

        obj = Foo()
        assert obj.prop == 42
        obj.prop = 100
        assert obj.prop == 100
        del obj.prop
        assert obj.prop == 42

    def test_ttl_expiration(self) -> None:
        class Foo:
            counter = 0

            @pin.native.ttl(0.01)
            def prop(self) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.counter == 1
        time.sleep(0.02)
        assert obj.prop == 42
        assert Foo.counter == 2

    def test_instances_have_separate_cache(self) -> None:
        class Foo:
            counter = 0

            @pin.native
            def prop(self) -> int:
                Foo.counter += 1
                return Foo.counter

        a = Foo()
        b = Foo()
        assert a.prop == 1
        assert b.prop == 2
        assert a.prop == 1
        assert b.prop == 2


class TestPinCls:
    """Tests for @pin.cls (child-aware class cached property)."""

    def test_class_access_caches(self) -> None:
        class Foo:
            counter = 0

            @pin.cls
            def prop(cls) -> str:
                Foo.counter += 1
                return cls.__name__

        assert Foo.prop == "Foo"
        assert Foo.prop == "Foo"
        assert Foo.counter == 1
        assert "__class_memoized__" in Foo.__dict__

    def test_instance_access_uses_class(self) -> None:
        class Foo:
            counter = 0

            @pin.cls
            def prop(cls) -> str:
                Foo.counter += 1
                return cls.__name__

        obj = Foo()
        assert obj.prop == "Foo"
        assert obj.prop == "Foo"
        assert Foo.counter == 1

    def test_inheritance_passes_child_class(self) -> None:
        class Foo:
            counter = 0

            @pin.cls
            def prop(cls) -> str:
                Foo.counter += 1
                return cls.__name__

        class Bar(Foo):
            pass

        assert Bar.prop == "Bar"
        assert Bar().prop == "Bar"
        assert Foo.counter == 1
        assert Bar.prop == "Bar"
        assert Bar().prop == "Bar"
        assert Foo.counter == 1

    def test_inheritance_separate_cache_per_class(self) -> None:
        class Foo:
            @pin.cls
            def prop(cls) -> str:
                return cls.__name__

        class Bar(Foo):
            pass

        assert Foo.prop == "Foo"
        assert Bar.prop == "Bar"
        assert Foo.prop == "Foo"


class TestPinAny:
    """Tests for @pin.any (mixed cached property)."""

    def test_instance_caches(self) -> None:
        class Foo:
            counter = 0

            @pin.any
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_class_caches(self) -> None:
        class Foo:
            counter = 0

            @pin.any
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return 42

        assert Foo.prop == 42
        assert Foo.prop == 42
        assert Foo.counter == 1
        assert "__class_memoized__" in Foo.__dict__

    def test_instance_and_class_caches_are_separate(self) -> None:
        class Foo:
            counter_i = 0
            counter_c = 0

            @pin.any
            def prop(self_or_cls: Any) -> int:
                if isinstance(self_or_cls, type):
                    Foo.counter_c += 1
                else:
                    Foo.counter_i += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert Foo.prop == 42
        assert obj.prop == 42
        assert Foo.prop == 42
        assert Foo.counter_i == 1
        assert Foo.counter_c == 1

    def test_inheritance_passes_child(self) -> None:
        class Foo:
            @pin.any
            def prop(self_or_cls: Any) -> str:
                if isinstance(self_or_cls, type):
                    return self_or_cls.__name__
                return self_or_cls.__class__.__name__

        class Bar(Foo):
            pass

        assert Bar.prop == "Bar"
        assert Bar().prop == "Bar"


class TestPinPre:
    """Tests for @pin.pre (mixed, caches only on class access)."""

    def test_class_access_caches(self) -> None:
        class Foo:
            counter = 0

            @pin.pre
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return 42

        assert Foo.prop == 42
        assert Foo.prop == 42
        assert Foo.counter == 1
        assert "__class_memoized__" in Foo.__dict__

    def test_instance_access_does_not_cache(self) -> None:
        class Foo:
            counter = 0

            @pin.pre
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.counter == 2
        assert "__instance_memoized__" not in obj.__dict__

    def test_class_and_instance_are_independent(self) -> None:
        class Foo:
            counter_c = 0
            counter_i = 0

            @pin.pre
            def prop(self_or_cls: Any) -> int:
                if isinstance(self_or_cls, type):
                    Foo.counter_c += 1
                else:
                    Foo.counter_i += 1
                return 42

        obj = Foo()
        assert Foo.prop == 42
        assert Foo.prop == 42
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.counter_c == 1
        assert Foo.counter_i == 2


class TestPinPost:
    """Tests for @pin.post (mixed, caches only on instance access)."""

    def test_instance_access_caches(self) -> None:
        class Foo:
            counter = 0

            @pin.post
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_class_access_does_not_cache(self) -> None:
        class Foo:
            counter = 0

            @pin.post
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return 42

        assert Foo.prop == 42
        assert Foo.prop == 42
        assert Foo.counter == 2
        cache = Foo.__dict__["__class_memoized__"]
        assert "prop" not in cache

    def test_class_and_instance_are_independent(self) -> None:
        class Foo:
            counter_c = 0
            counter_i = 0

            @pin.post
            def prop(self_or_cls: Any) -> int:
                if isinstance(self_or_cls, type):
                    Foo.counter_c += 1
                else:
                    Foo.counter_i += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.prop == 42
        assert Foo.prop == 42
        assert Foo.counter_i == 1
        assert Foo.counter_c == 2


class TestClassProperty:
    """Tests for @class_property."""

    def test_instance_access_passes_class(self) -> None:
        class Foo:
            @class_property
            def prop(cls) -> str:
                return cls.__name__

        assert Foo().prop == "Foo"

    def test_class_access_passes_actual_class(self) -> None:
        class Foo:
            @class_property
            def prop(cls) -> str:
                return cls.__name__

        class Bar(Foo):
            pass

        assert Bar.prop == "Bar"
        assert Bar().prop == "Bar"

    def test_no_caching(self) -> None:
        class Foo:
            counter = 0

            @class_property
            def prop(cls) -> int:
                Foo.counter += 1
                return Foo.counter

        assert Foo.prop == 1
        assert Foo.prop == 2
        assert Foo().prop == 3


class TestMixedProperty:
    """Tests for @mixed_property."""

    def test_instance_access_passes_instance(self) -> None:
        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                return (
                    "instance"
                    if not isinstance(self_or_cls, type)
                    else "class"
                )

        assert Foo().prop == "instance"

    def test_class_access_passes_class(self) -> None:
        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                return (
                    "instance"
                    if not isinstance(self_or_cls, type)
                    else "class"
                )

        assert Foo.prop == "class"

    def test_falsy_instance_gets_itself(self) -> None:
        """A falsy instance must still receive itself in the getter."""

        class Falsy:
            def __bool__(self) -> bool:
                return False

            @mixed_property
            def prop(self_or_cls: Any) -> Any:
                return self_or_cls

        obj = Falsy()
        assert obj.prop is obj

    def test_no_caching(self) -> None:
        class Foo:
            counter = 0

            @mixed_property
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return Foo.counter

        assert Foo().prop == 1
        assert Foo().prop == 2
        assert Foo.prop == 3
        assert Foo.prop == 4


class TestWithParent:
    """Tests for BaseProperty.with_parent() method."""

    def test_pin_with_parent(self) -> None:
        class Parent:
            counter = 0

            @pin
            def prop(self) -> int:
                Parent.counter += 1
                return 42

        class Child(Parent):
            @pin.with_parent
            def prop(self, parent_value: int) -> int:
                return parent_value + 10

        obj = Child()
        assert obj.prop == 52
        assert obj.prop == 52
        assert Parent.counter == 1

    def test_pin_native_with_parent(self) -> None:
        class Parent:
            counter = 0

            @pin.native
            def prop(self) -> int:
                Parent.counter += 1
                return 42

        class Child(Parent):
            @pin.native.with_parent
            def prop(self, parent_value: int) -> int:
                return parent_value + 10

        obj = Child()
        assert obj.prop == 52
        assert obj.prop == 52
        assert Parent.counter == 1

    def test_pin_cls_with_parent(self) -> None:
        class Parent:
            counter = 0

            @pin.cls
            def prop(cls) -> str:
                Parent.counter += 1
                return f"parent_{cls.__name__}"

        class Child(Parent):
            @pin.cls.with_parent
            def prop(cls, parent_value: str) -> str:
                return f"child_{parent_value}"

        assert Child.prop == "child_parent_Child"
        assert Child.prop == "child_parent_Child"
        assert Parent.counter == 1

    def test_pin_any_with_parent(self) -> None:
        class Parent:
            counter = 0

            @pin.any
            def prop(self_or_cls: Any) -> int:
                Parent.counter += 1
                return 42

        class Child(Parent):
            @pin.any.with_parent
            def prop(self_or_cls: Any, parent_value: int) -> int:
                return parent_value + 10

        obj = Child()
        assert obj.prop == 52
        assert Child.prop == 52
        assert Parent.counter == 2  # instance and class are separate

    def test_pin_pre_with_parent(self) -> None:
        class Parent:
            @pin.pre
            def prop(self_or_cls: Any) -> int:
                return 42

        class Child(Parent):
            @pin.pre.with_parent
            def prop(self_or_cls: Any, parent_value: int) -> int:
                return parent_value + 10

        assert Child.prop == 52
        assert Child().prop == 52

    def test_pin_post_with_parent(self) -> None:
        class Parent:
            @pin.post
            def prop(self_or_cls: Any) -> int:
                return 42

        class Child(Parent):
            @pin.post.with_parent
            def prop(self_or_cls: Any, parent_value: int) -> int:
                return parent_value + 10

        assert Child.prop == 52
        assert Child().prop == 52

    def test_class_property_with_parent(self) -> None:
        class Parent:
            counter = 0

            @class_property
            def prop(cls) -> str:
                Parent.counter += 1
                return f"parent_{cls.__name__}"

        class Child(Parent):
            @class_property.with_parent
            def prop(cls, parent_value: str) -> str:
                return f"child_{parent_value}"

        assert Child.prop == "child_parent_Child"
        assert Child().prop == "child_parent_Child"

    def test_mixed_property_with_parent(self) -> None:
        class Parent:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                return "parent"

        class Child(Parent):
            @mixed_property.with_parent
            def prop(self_or_cls: Any, parent_value: str) -> str:
                return f"child_of_{parent_value}"

        assert Child.prop == "child_of_parent"
        assert Child().prop == "child_of_parent"

    def test_with_parent_without_parent_descriptor(self) -> None:
        class Foo:
            @pin.with_parent
            def prop(self, parent_value: int) -> int:
                return parent_value + 10

        obj = Foo()
        with pytest.raises(NotImplementedError):
            obj.prop


class TestCustomCallbackBy:
    """Tests for .by() and .by() custom cache invalidation."""

    def test_pin_native_by_custom_callback(self) -> None:
        should_invalidate = False

        def is_actual(
            self: Any,
            node: Any,
            timestamp: float | None = None,
        ) -> bool | float:
            if timestamp is None:
                return time.time()
            return not should_invalidate

        class Foo:
            counter = 0

            @pin.native.by(is_actual)
            def prop(self) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.counter == 1

        should_invalidate = True
        assert obj.prop == 42
        assert Foo.counter == 2

    def test_pin_native_expired_by_alias(self) -> None:
        expired = False

        def is_still_valid(
            self: Any,
            node: Any,
            timestamp: float | None = None,
        ) -> bool | float:
            if timestamp is None:
                return time.time()
            return not expired

        class Foo:
            counter = 0

            @pin.native.by(is_still_valid)
            def prop(self) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert Foo.counter == 1

        expired = True
        assert obj.prop == 42
        assert Foo.counter == 2

    def test_pin_cls_by_custom_callback(self) -> None:
        expired = False

        def is_still_valid(
            self: Any,
            node: Any,
            timestamp: float | None = None,
        ) -> bool | float:
            if timestamp is None:
                return time.time()
            return not expired

        class Foo:
            counter = 0

            @pin.cls.by(is_still_valid)
            def prop(cls) -> int:
                Foo.counter += 1
                return 42

        assert Foo.prop == 42
        assert Foo.counter == 1

        expired = True
        assert Foo.prop == 42
        assert Foo.counter == 2

    def test_pin_any_by_custom_callback(self) -> None:
        expired = False

        def is_still_valid(
            self: Any,
            node: Any,
            timestamp: float | None = None,
        ) -> bool | float:
            if timestamp is None:
                return time.time()
            return not expired

        class Foo:
            counter = 0

            @pin.any.by(is_still_valid)
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert Foo.prop == 42
        assert Foo.counter == 2

        expired = True
        assert obj.prop == 42
        assert Foo.counter == 3

    def test_ttl_on_pin_cls(self) -> None:
        class Foo:
            counter = 0

            @pin.cls.ttl(0.01)
            def prop(cls) -> int:
                Foo.counter += 1
                return 42

        assert Foo.prop == 42
        assert Foo.counter == 1
        time.sleep(0.02)
        assert Foo.prop == 42
        assert Foo.counter == 2

    def test_ttl_on_pin_any(self) -> None:
        class Foo:
            counter = 0

            @pin.any.ttl(0.01)
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert Foo.counter == 1
        time.sleep(0.02)
        assert obj.prop == 42
        assert Foo.counter == 2

    def test_ttl_rejects_non_number(self) -> None:
        with pytest.raises(TypeError, match="expire must be float or int"):
            pin.native.ttl("invalid")

    def test_ttl_rejects_zero(self) -> None:
        with pytest.raises(
            ValueError,
            match="expire must be a positive number",
        ):
            pin.native.ttl(0)

    def test_ttl_rejects_negative(self) -> None:
        with pytest.raises(
            ValueError,
            match="expire must be a positive number",
        ):
            pin.native.ttl(-1)


class TestExceptions:
    """Tests for descriptor exceptions."""

    def test_property_error_inheritance(self) -> None:
        assert issubclass(ContextFaultError, PropertyError)
        assert issubclass(ReadOnlyError, PropertyError)
        assert issubclass(AttributeExceptionError, PropertyError)

    def test_context_fault_error_catchable(self) -> None:
        class Foo:
            @pin
            def prop(self) -> int:
                return 42

        with pytest.raises(ContextFaultError):
            Foo.prop

    def test_read_only_error_on_delete(self) -> None:
        class Foo:
            @pin
            def prop(self) -> int:
                return 42

        obj = Foo()
        assert obj.prop == 42
        with pytest.raises(ReadOnlyError):
            del obj.prop

    def test_attribute_exception_wraps_error(self) -> None:
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

    def test_descriptor_string_repr(self) -> None:
        class Foo:
            @pin
            def prop(self) -> int:
                return 42

        descriptor = Foo.__dict__["prop"]
        str_repr = str(descriptor)
        repr_str = repr(descriptor)
        assert "descriptor" in str_repr.lower() or "pin" in str_repr.lower()
        assert "descriptor" in repr_str.lower() or "pin" in repr_str.lower()

    def test_multiple_inheritance_with_pin_native(self) -> None:
        class Mixin:
            counter = 0

            @pin.native
            def prop(self) -> int:
                Mixin.counter += 1
                return 42

        class Base:
            pass

        class Child(Mixin, Base):
            pass

        obj = Child()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Mixin.counter == 1

    def test_pin_native_delete_then_reaccess(self) -> None:
        class Foo:
            counter = 0

            @pin.native
            def prop(self) -> int:
                Foo.counter += 1
                return Foo.counter

        obj = Foo()
        assert obj.prop == 1
        del obj.prop
        assert obj.prop == 2
        assert obj.prop == 2

    def test_class_property_no_cache(self) -> None:
        class Foo:
            counter = 0

            @class_property
            def prop(cls) -> int:
                Foo.counter += 1
                return Foo.counter

        assert Foo.prop == 1
        assert Foo.prop == 2
        assert Foo().prop == 3
        assert Foo().prop == 4

    def test_mixed_property_no_cache(self) -> None:
        class Foo:
            counter = 0

            @mixed_property
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return Foo.counter

        assert Foo.prop == 1
        assert Foo.prop == 2
        assert Foo().prop == 3
        assert Foo().prop == 4


class TestDescriptorInternals:
    """Tests for internal descriptor behavior and attributes."""

    def test_pin_name_property(self) -> None:
        class Foo:
            @pin
            def my_property(self) -> int:
                return 42

        descriptor = Foo.__dict__["my_property"]
        assert descriptor.name == "my_property"

    def test_pin_native_name_property(self) -> None:
        class Foo:
            @pin.native
            def my_property(self) -> int:
                return 42

        descriptor = Foo.__dict__["my_property"]
        assert descriptor.name == "my_property"

    def test_is_data_property(self) -> None:
        class Foo:
            @pin.native
            def cached_prop(self) -> int:
                return 42

        cached_desc = Foo.__dict__["cached_prop"]
        assert cached_desc.is_data is True

    def test_class_property_is_not_data(self) -> None:
        class Foo:
            @class_property
            def prop(cls) -> int:
                return 42

        descriptor = Foo.__dict__["prop"]
        assert descriptor.is_data is False

    def test_mixed_property_is_not_data(self) -> None:
        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> int:
                return 42

        descriptor = Foo.__dict__["prop"]
        assert descriptor.is_data is False


class TestCachedSetOperations:
    """Tests for __set__ behavior on cached properties."""

    def test_manual_override_pin_native(self) -> None:
        class Foo:
            @pin.native
            def prop(self) -> int:
                return 42

        obj = Foo()
        assert obj.prop == 42
        obj.prop = 100
        assert obj.prop == 100

    def test_manual_override_pin_cls(self) -> None:
        class Foo:
            @pin.cls
            def prop(cls) -> int:
                return 42

        Foo.prop = 100  # type: ignore[assignment]
        assert Foo.prop == 100  # type: ignore[assignment]

    def test_manual_override_pin_any_instance(self) -> None:
        class Foo:
            @pin.any
            def prop(self_or_cls: Any) -> int:
                return 42

        obj = Foo()
        assert obj.prop == 42
        obj.prop = 100
        assert obj.prop == 100
        assert Foo.prop == 42

    def test_manual_override_pin_pre_class_only(self) -> None:
        class Foo:
            counter = 0

            @pin.pre
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return Foo.counter

        obj = Foo()
        assert obj.prop == 1
        assert obj.prop == 2
        obj.prop = 100
        val = obj.prop
        assert val == 3

    def test_manual_set_on_class_pin_pre(self) -> None:
        class Foo:
            counter = 0

            @pin.pre
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return Foo.counter

        assert Foo.prop == 1
        assert Foo.prop == 1
        Foo.prop = 100  # type: ignore[assignment]
        assert Foo.prop == 100

    def test_manual_override_pin_post_instance_only(self) -> None:
        class Foo:
            counter = 0

            @pin.post
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return Foo.counter

        obj = Foo()
        assert obj.prop == 1
        obj.prop = 100
        assert obj.prop == 100


class TestInheritanceScenarios:
    """Complex inheritance scenarios."""

    def test_diamond_inheritance_with_pin_native(self) -> None:
        class A:
            counter = 0

            @pin.native
            def prop(self) -> int:
                A.counter += 1
                return 42

        class B(A):
            pass

        class C(A):
            pass

        class D(B, C):
            pass

        obj = D()
        assert obj.prop == 42
        assert obj.prop == 42
        assert A.counter == 1

    def test_override_with_different_descriptor_type(self) -> None:
        class Parent:
            @pin
            def prop(self) -> int:
                return 42

        class Child(Parent):
            @pin.native
            def prop(self) -> int:
                return 100

        obj = Child()
        assert obj.prop == 100
        obj.prop = 200
        assert obj.prop == 200


class TestBasePropertyInterface:
    """Tests for BaseProperty interface compliance."""

    def test_base_property_requires_title(self) -> None:
        class ConcreteProperty(BaseProperty):
            pass

        with pytest.raises(NotImplementedError):
            _ = ConcreteProperty(lambda: 42).title

    def test_base_property_requires_header_with_context(self) -> None:
        class ConcreteProperty(BaseProperty):
            @property
            def title(self) -> str:
                return "test"

        prop = ConcreteProperty(lambda: 42)
        with pytest.raises(NotImplementedError):
            prop.header_with_context(None)


class TestPinSubclassing:
    """Tests for subclassing pin and its variants."""

    def test_pin_subclass_creation(self) -> None:
        class MyPin(pin):
            def custom_method(self) -> str:
                return "custom"

        class Foo:
            @MyPin
            def prop(self) -> int:
                return 42

        obj = Foo()
        assert obj.prop == 42
        descriptor = Foo.__dict__["prop"]
        assert descriptor.custom_method() == "custom"
