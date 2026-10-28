"""Unit tests for class_parent_cached_property and class_cached_property.

Arrange-Act-Assert pattern, BDD docstrings.
"""

from __future__ import annotations

import pytest
import time_machine
from faker import Faker

from zx.core.classes import Nothing
from zx.prop.cached.klass import (
    CustomCallbackMixin,
    class_cached_property,
    class_parent_cached_property,
)
from zx.prop.primitives import (
    AttributeExceptionError,
    BaseProperty,
    ContextFaultError,
)

# ------------------------------------------------------------------
# class_parent_cached_property
# ------------------------------------------------------------------


class TestClassParentCachedProperty:
    """GIVEN a class_parent_cached_property descriptor
    WHEN accessed on a class
    THEN it computes, caches on the owning class, and guards appropriately.
    """

    def test_computes_on_first_access(self, fake: Faker) -> None:
        """GIVEN a fresh class
        WHEN the descriptor is accessed
        THEN the function is called and the result is returned.
        """
        expected = fake.pyint()

        class Sample:
            attr = class_parent_cached_property(lambda _cls: expected)

        assert Sample.attr == expected

    def test_caches_in_class_memoized(self, fake: Faker) -> None:
        """GIVEN a descriptor that has been accessed
        WHEN inspecting the class __dict__
        THEN __class_memoized__ contains the cached value.
        """
        expected = fake.pyint()

        class Sample:
            attr = class_parent_cached_property(lambda _cls: expected)

        prop = Sample.__dict__["attr"]
        _ = Sample.attr

        assert "__class_memoized__" in Sample.__dict__
        assert Sample.__dict__["__class_memoized__"][prop.name] == expected

    def test_subclass_shares_parent_cache(self, fake: Faker) -> None:
        """GIVEN a parent class with the descriptor
        WHEN a subclass accesses the attribute
        THEN the cache lives on the owning (parent) class.
        """
        expected = fake.pyint()

        class Base:
            @class_parent_cached_property
            def attr(cls) -> int:
                return expected

        class Child(Base):
            pass

        assert Child.attr == expected
        assert "__class_memoized__" in Base.__dict__

    def test_get_node_raises_on_none(self) -> None:
        """GIVEN node is None
        WHEN get_node is called
        THEN ContextFaultError is raised.
        """
        prop = class_parent_cached_property(lambda _cls: 1)

        with pytest.raises(ContextFaultError):
            prop.get_node(None)

    def test_get_node_raises_on_non_class(self) -> None:
        """GIVEN node is not a class
        WHEN get_node is called
        THEN ContextFaultError is raised.
        """
        prop = class_parent_cached_property(lambda _cls: 1)

        with pytest.raises(ContextFaultError):
            prop.get_node(object())

    def test_get_node_returns_owner_for_subclass(self) -> None:
        """GIVEN a subclass node
        WHEN get_node is called
        THEN the owning parent class is returned.
        """

        class Base:
            @class_parent_cached_property
            def attr(cls) -> int:
                return 1

        class Child(Base):
            pass

        prop = Base.__dict__["attr"]
        assert prop.get_node(Child) is Base

    def test_get_node_returns_node_when_no_owner(self) -> None:
        """GIVEN the defining class itself
        WHEN get_node is called
        THEN the class is returned.
        """

        class Sample:
            attr = class_parent_cached_property(lambda _cls: 1)

        prop = Sample.__dict__["attr"]
        assert prop.get_node(Sample) is Sample

    def test_title_contains_class_data_descriptor(self) -> None:
        """GIVEN a class_parent_cached_property instance
        WHEN .title is accessed
        THEN it contains 'class data-descriptor'.
        """
        prop = class_parent_cached_property(lambda _cls: 1)

        assert "class data-descriptor" in prop.title

    def test_header_with_context_returns_footer(self) -> None:
        """GIVEN a class_parent_cached_property instance
        WHEN .header_with_context is called
        THEN it equals .footer(node).
        """
        prop = class_parent_cached_property(lambda _cls: 1)
        node = type("X", (), {})

        assert prop.header_with_context(node) == prop.footer(node)

    def test_is_subclass_of_base_property(self) -> None:
        """GIVEN class_parent_cached_property
        WHEN checked via issubclass
        THEN it is a subclass of BaseProperty.
        """
        assert issubclass(class_parent_cached_property, BaseProperty)

    def test_is_subclass_of_custom_callback_mixin(self) -> None:
        """GIVEN class_parent_cached_property
        WHEN checked via issubclass
        THEN it is a subclass of CustomCallbackMixin.
        """
        assert issubclass(
            class_parent_cached_property,
            CustomCallbackMixin,
        )

    def test_with_parent_injects_parent_result(self, fake: Faker) -> None:
        """GIVEN a parent descriptor and child with_parent
        WHEN the child is accessed
        THEN the child receives the parent's computed value.
        """
        base_value = fake.pyint(min_value=1, max_value=100)
        increment = fake.pyint(min_value=1, max_value=10)

        class Parent:
            @class_parent_cached_property
            def value(cls) -> int:
                return base_value

        class Child(Parent):
            @class_parent_cached_property.with_parent
            def value(cls, parent_result: int) -> int:
                return parent_result + increment

        assert Child.value == base_value + increment

    def test_delete_removes_cache_entry(self, fake: Faker) -> None:
        """GIVEN a cached value
        WHEN __delete__ is called
        THEN the entry is removed from the cache.
        """
        expected = fake.pyint()

        class Sample:
            attr = class_parent_cached_property(lambda _cls: expected)

        prop = Sample.__dict__["attr"]
        _ = Sample.attr
        prop.__delete__(Sample)

        assert "attr" not in Sample.__dict__.get("__class_memoized__", {})

    def test_set_stores_value_without_is_actual(self, fake: Faker) -> None:
        """GIVEN a descriptor without is_actual
        WHEN __set__ is called
        THEN the raw value is stored in the cache.
        """
        expected = fake.pyint()

        class Sample:
            attr = class_parent_cached_property(lambda _cls: 1)

        prop = Sample.__dict__["attr"]
        prop.__set__(Sample, expected)

        assert Sample.__dict__["__class_memoized__"][prop.name] == expected


# ------------------------------------------------------------------
# class_cached_property
# ------------------------------------------------------------------


class TestClassCachedProperty:
    """GIVEN a class_cached_property descriptor
    WHEN accessed on a class or subclass
    THEN it caches directly on the accessed node.
    """

    def test_caches_on_accessed_class(self, fake: Faker) -> None:
        """GIVEN a class with class_cached_property
        WHEN accessed
        THEN the cache lives on that class, not a parent.
        """
        expected = fake.pyint()

        class Base:
            attr = class_cached_property(lambda _cls: expected)

        class Child(Base):
            pass

        _ = Child.attr
        assert "__class_memoized__" in Child.__dict__

    def test_subclass_has_independent_cache(self, fake: Faker) -> None:
        """GIVEN a parent and child class
        WHEN each accesses the descriptor
        THEN each maintains its own cached value.
        """

        class Base:
            attr = class_cached_property(lambda _cls: 1)

        class Child(Base):
            pass

        base_value = Base.attr
        child_value = Child.attr

        assert base_value == child_value == 1
        assert "__class_memoized__" in Base.__dict__
        assert "__class_memoized__" in Child.__dict__

    def test_get_node_returns_node_directly(self) -> None:
        """GIVEN a class node
        WHEN get_node is called
        THEN the node itself is returned without owner resolution.
        """

        class Base:
            attr = class_cached_property(lambda _cls: 1)

        class Child(Base):
            pass

        prop = Base.__dict__["attr"]
        assert prop.get_node(Child) is Child

    def test_here_property_returns_parent_class(self) -> None:
        """GIVEN class_cached_property
        WHEN accessing .here on the class
        THEN it returns class_parent_cached_property.
        """

        class Sample:
            attr = class_cached_property(lambda _cls: 1)

        prop = Sample.__dict__["attr"]
        assert prop.here is class_parent_cached_property

    def test_is_subclass_of_class_parent_cached(self) -> None:
        """GIVEN class_cached_property
        WHEN checked via issubclass
        THEN it is a subclass of class_parent_cached_property.
        """
        assert issubclass(
            class_cached_property,
            class_parent_cached_property,
        )

    def test_with_parent_injects_parent_result(self, fake: Faker) -> None:
        """GIVEN a parent and child with with_parent
        WHEN the child is accessed
        THEN the child receives the parent's computed value.
        """
        base_value = fake.pyint(min_value=1, max_value=100)
        increment = fake.pyint(min_value=1, max_value=10)

        class Parent:
            @class_cached_property
            def value(cls) -> int:
                return base_value

        class Child(Parent):
            @class_cached_property.with_parent
            def value(cls, parent_result: int) -> int:
                return parent_result + increment

        assert Child.value == base_value + increment


# ------------------------------------------------------------------
# CustomCallbackMixin
# ------------------------------------------------------------------


class TestCustomCallbackMixin:
    """GIVEN CustomCallbackMixin factories
    WHEN configured with custom callbacks or TTL
    THEN cache invalidation behaves correctly.
    """

    def test_by_returns_partial_with_is_actual(self) -> None:
        """GIVEN a custom callback
        WHEN .by is called
        THEN the returned callable produces a descriptor with is_actual set.
        """

        def always_actual(
            _self: object,
            _node: object,
            _value: object = Nothing,
        ) -> bool:
            return True

        factory = class_parent_cached_property.by(always_actual)
        prop = factory(lambda _cls: 1)

        assert prop.is_actual is always_actual

    def test_ttl_returns_callable(self) -> None:
        """GIVEN a positive TTL
        WHEN .ttl is called
        THEN a callable factory is returned.
        """
        factory = class_parent_cached_property.ttl(60.0)
        assert callable(factory)

    def test_ttl_validates_numeric_type(self) -> None:
        """GIVEN a non-numeric TTL
        WHEN .ttl is called
        THEN TypeError is raised.
        """
        with pytest.raises(TypeError, match="float or int"):
            class_parent_cached_property.ttl("not-a-number")

    def test_ttl_validates_positive_value(self) -> None:
        """GIVEN a non-positive TTL
        WHEN .ttl is called
        THEN ValueError is raised.
        """
        with pytest.raises(ValueError, match="positive number"):
            class_parent_cached_property.ttl(0)

    def test_ttl_expires_after_duration(self, fake: Faker) -> None:
        """GIVEN a TTL-configured descriptor
        WHEN time advances beyond the TTL
        THEN the value is recomputed.
        """
        first_value = fake.pyint(min_value=1, max_value=100)
        second_value = fake.pyint(min_value=1000, max_value=9999)
        call_count = 0

        def compute(_cls: type[object]) -> int:
            nonlocal call_count
            call_count += 1
            return first_value if call_count == 1 else second_value

        class Sample:
            attr = class_parent_cached_property.ttl(1.0)(compute)

        with time_machine.travel("2024-01-15 12:00:00+00:00"):
            assert Sample.attr == first_value

        with time_machine.travel("2024-01-15 12:00:02+00:00"):
            assert Sample.attr == second_value

    def test_custom_callback_false_invalidates(self, fake: Faker) -> None:
        """GIVEN a custom is_actual returning False
        WHEN the descriptor is accessed
        THEN the value is recomputed every time.
        """
        counter = 0

        def compute(_cls: type[object]) -> int:
            nonlocal counter
            counter += 1
            return counter

        def never_actual(
            _self: object,
            _node: object,
            _value: object = Nothing,
        ) -> bool:
            return False

        class Sample:
            attr = class_parent_cached_property.by(never_actual)(compute)

        first = Sample.attr
        second = Sample.attr

        assert first != second

    def test_custom_callback_true_preserves_cache(self, fake: Faker) -> None:
        """GIVEN a custom is_actual returning True
        WHEN the descriptor is accessed repeatedly
        THEN the cached value is returned.
        """
        expected = fake.pyint()
        counter = 0

        def compute(_cls: type[object]) -> int:
            nonlocal counter
            counter += 1
            return expected

        def always_actual(
            _self: object,
            _node: object,
            _value: object = Nothing,
        ) -> bool:
            return True

        class Sample:
            attr = class_parent_cached_property.by(always_actual)(compute)

        _ = Sample.attr
        _ = Sample.attr

        assert counter == 1


# ------------------------------------------------------------------
# Annotation inference
# ------------------------------------------------------------------


class TestAnnotationInference:
    """GIVEN class cached descriptors with type annotations
    WHEN instantiated or inspected
    THEN generic parameters and function names are preserved.
    """

    def test_class_cached_property_preserves_function_name(self) -> None:
        """GIVEN an annotated function
        WHEN wrapped in class_cached_property
        THEN .name matches the original function.
        """

        def compute(_cls: type[object]) -> int:
            return 42

        prop = class_cached_property(compute)
        assert prop.name == "compute"

    def test_class_parent_cached_property_preserves_function_name(
        self,
    ) -> None:
        """GIVEN an annotated function
        WHEN wrapped in class_parent_cached_property
        THEN .name matches the original function.
        """

        def compute(_cls: type[object]) -> int:
            return 42

        prop = class_parent_cached_property(compute)
        assert prop.name == "compute"

    def test_class_cached_property_is_generic_subclass(self) -> None:
        """GIVEN class_cached_property
        WHEN inspected
        THEN it is a generic class.
        """
        assert hasattr(class_cached_property, "__class_getitem__")

    def test_class_parent_cached_property_is_generic_subclass(
        self,
    ) -> None:
        """GIVEN class_parent_cached_property
        WHEN inspected
        THEN it is a generic class.
        """
        assert hasattr(class_parent_cached_property, "__class_getitem__")


# ------------------------------------------------------------------
# Inheritance contract
# ------------------------------------------------------------------


class TestInheritanceContract:
    """GIVEN the class cached descriptor hierarchy
    WHEN inspecting inherited methods and attributes
    THEN the full interface is available.
    """

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(class_parent_cached_property, id="parent"),
            pytest.param(class_cached_property, id="plain"),
        ),
    )
    def test_inherits_name_from_base_property(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any class cached descriptor
        WHEN wrapping a function
        THEN .name is inherited from BaseProperty.
        """

        def sample(_cls: type[object]) -> int:
            return 1

        prop = descriptor_type(sample)
        assert prop.name == "sample"

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(class_parent_cached_property, id="parent"),
            pytest.param(class_cached_property, id="plain"),
        ),
    )
    def test_inherits_is_data_from_base_property(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any class cached descriptor
        WHEN accessing .is_data
        THEN it reflects __set__ / __delete__ presence.
        """

        def sample(_cls: type[object]) -> int:
            return 1

        prop = descriptor_type(sample)
        assert isinstance(prop.is_data, bool)

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(class_parent_cached_property, id="parent"),
            pytest.param(class_cached_property, id="plain"),
        ),
    )
    def test_inherits_str_and_repr(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any class cached descriptor
        WHEN calling str() and repr()
        THEN they contain expected introspection info.
        """

        def sample(_cls: type[object]) -> int:
            return 1

        prop = descriptor_type(sample)
        assert "<" in str(prop)
        assert ">" in repr(prop)

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(class_parent_cached_property, id="parent"),
            pytest.param(class_cached_property, id="plain"),
        ),
    )
    def test_inherits_call_logic(self, descriptor_type: type) -> None:
        """GIVEN any class cached descriptor
        WHEN calling .call
        THEN the inherited caching logic works.
        """
        expected = 42

        class Sample:
            attr = descriptor_type(lambda _cls: expected)

        prop = Sample.__dict__["attr"]
        assert prop.call(Sample) == expected

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(class_parent_cached_property, id="parent"),
            pytest.param(class_cached_property, id="plain"),
        ),
    )
    def test_inherits_get_cache(self, descriptor_type: type) -> None:
        """GIVEN any class cached descriptor
        WHEN calling .get_cache
        THEN it returns the class-level cache dict.
        """

        class Sample:
            attr = descriptor_type(lambda _cls: 1)

        prop = Sample.__dict__["attr"]
        cache = prop.get_cache(Sample)

        assert isinstance(cache, dict)

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(class_parent_cached_property, id="parent"),
            pytest.param(class_cached_property, id="plain"),
        ),
    )
    def test_inherits_set_and_delete(self, descriptor_type: type) -> None:
        """GIVEN any class cached descriptor
        WHEN using __set__ and __delete__
        THEN they manipulate the cache correctly.
        """

        class Sample:
            attr = descriptor_type(lambda _cls: 1)

        prop = Sample.__dict__["attr"]
        new_value = 99
        prop.__set__(Sample, new_value)
        assert Sample.__dict__["__class_memoized__"][prop.name] == new_value

        prop.__delete__(Sample)
        assert prop.name not in Sample.__dict__.get("__class_memoized__", {})

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(class_parent_cached_property, id="parent"),
            pytest.param(class_cached_property, id="plain"),
        ),
    )
    def test_inherits_custom_callback_mixin(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any class cached descriptor
        WHEN checking mixin methods
        THEN .by and .ttl are available.
        """
        assert hasattr(descriptor_type, "by")
        assert hasattr(descriptor_type, "ttl")


class TestEdgeCases:
    """Paranoid edge-case coverage for cached klass descriptors."""

    def test_is_actual_method_conflict_raises_type_error(self) -> None:
        """
        Given: a subclass with is_actual method AND is_actual keyword
        WHEN: instantiating class_parent_cached_property
        THEN: TypeError is raised.
        """

        class Descriptor(class_parent_cached_property):
            def is_actual(self, node: object, stamp: float) -> bool:
                return True

        with pytest.raises(TypeError, match="can't be overridden"):
            Descriptor(lambda _cls: 1, is_actual=lambda _s, _n, _t: False)

    def test_call_wraps_attribute_error(self) -> None:
        """
        Given: a function that raises AttributeError
        WHEN: class_parent_cached_property.call() runs
        THEN: AttributeExceptionError is raised.
        """

        class Base:
            attr = class_parent_cached_property(lambda _cls: _cls.missing)

        with pytest.raises(AttributeExceptionError):
            _ = Base.attr

    def test_class_cached_property_get_node_rejects_none(self) -> None:
        """
        Given: class_cached_property
        WHEN: get_node(None) is called
        THEN: ContextFaultError is raised.
        """

        class Base:
            attr = class_cached_property(lambda _cls: 1)

        descriptor = Base.__dict__["attr"]
        with pytest.raises(ContextFaultError):
            descriptor.get_node(None)

    def test_get_cache_early_return_from_dict(self) -> None:
        """
        Given: a class with pre-existing __class_memoized__
        WHEN: get_cache is called
        THEN: the existing dict is returned without recreation.
        """

        def compute(_cls: type[object]) -> int:
            return 1

        class Base:
            attr = class_parent_cached_property(compute)

        # Populate cache via first access
        _ = Base.attr
        descriptor = Base.__dict__["attr"]
        cache_first = descriptor.get_cache(Base)
        cache_second = descriptor.get_cache(Base)
        assert cache_first is cache_second

    def test_ttl_zero_raises_value_error(self) -> None:
        """
        Given: ttl with zero duration
        WHEN: decorating a function
        THEN: ValueError is raised.
        """

        with pytest.raises(ValueError, match="positive"):
            class_parent_cached_property.ttl(0.0)(lambda _cls: 1)

    def test_ttl_negative_raises_value_error(self) -> None:
        """
        Given: ttl with negative duration
        WHEN: decorating a function
        THEN: ValueError is raised.
        """

        with pytest.raises(ValueError, match="positive"):
            class_parent_cached_property.ttl(-1.0)(lambda _cls: 1)
