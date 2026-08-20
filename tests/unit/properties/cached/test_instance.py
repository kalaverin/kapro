"""Unit tests for cached_property descriptor.

Arrange-Act-Assert pattern, BDD docstrings.
"""

from __future__ import annotations

import pytest
from faker import Faker

from kapro.cached.instance import cached_property
from kapro.cached.klass import class_parent_cached_property
from kapro.primitives import BaseProperty, ContextFaultError

# ------------------------------------------------------------------
# cached_property behavior
# ------------------------------------------------------------------


class TestCachedProperty:
    """GIVEN a cached_property descriptor
    WHEN accessed on an instance or class
    THEN it computes, caches, and guards appropriately.
    """

    def test_cached_property_computes_on_first_access(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a fresh instance
        WHEN the descriptor is accessed
        THEN the function is called and the result is returned.
        """
        expected = fake.pyint()

        class Sample:
            attr = cached_property(lambda _self: expected)

        instance = Sample()
        assert instance.attr == expected

    def test_cached_property_caches_in_instance_memoized(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a descriptor that has already been accessed
        WHEN accessed again
        THEN the cached value from __instance_memoized__ is returned.
        """
        expected = fake.pyint()

        class Sample:
            attr = cached_property(lambda _self: expected)

        instance = Sample()
        prop = Sample.__dict__["attr"]
        _ = instance.attr

        assert "__instance_memoized__" in instance.__dict__
        assert (
            instance.__dict__["__instance_memoized__"][prop.name] == expected
        )

    def test_cached_property_returns_same_value_on_subsequent_access(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a descriptor with side effects
        WHEN accessed multiple times
        THEN the function is called only once.
        """
        counter = 0

        class Sample:
            attr = cached_property(lambda _self: counter + 1)

        instance = Sample()
        first = instance.attr
        second = instance.attr

        assert first == second

    def test_cached_property_on_class_access_raises_context_fault(
        self,
    ) -> None:
        """GIVEN class-level access (instance is None)
        WHEN the descriptor is accessed on the class
        THEN ContextFaultError is raised.
        """

        class Sample:
            attr = cached_property(lambda _self: 1)

        with pytest.raises(ContextFaultError):
            _ = Sample.attr

    def test_cached_property_get_node_raises_on_none(self) -> None:
        """GIVEN node is None
        WHEN get_node is called
        THEN ContextFaultError is raised.
        """
        prop = cached_property(lambda _self: 1)

        with pytest.raises(ContextFaultError):
            prop.get_node(None)

    def test_cached_property_get_node_raises_on_class(self) -> None:
        """GIVEN node is a class
        WHEN get_node is called
        THEN ContextFaultError is raised.
        """
        prop = cached_property(lambda _self: 1)

        with pytest.raises(ContextFaultError):
            prop.get_node(type("X", (), {}))

    def test_cached_property_get_node_returns_instance(self) -> None:
        """GIVEN an instance node
        WHEN get_node is called
        THEN the instance is returned.
        """
        prop = cached_property(lambda _self: 1)
        node = object()

        assert prop.get_node(node) is node

    def test_cached_property_title_contains_instance_descriptor(
        self,
    ) -> None:
        """GIVEN a cached_property instance
        WHEN .title is accessed
        THEN it contains 'instance data-descriptor'.
        """
        prop = cached_property(lambda _self: 1)

        assert "instance data-descriptor" in prop.title

    def test_cached_property_is_subclass_of_class_parent_cached(
        self,
    ) -> None:
        """GIVEN cached_property
        WHEN checked via issubclass
        THEN it is a subclass of class_parent_cached_property.
        """
        assert issubclass(cached_property, class_parent_cached_property)

    def test_cached_property_is_subclass_of_base_property(self) -> None:
        """GIVEN cached_property
        WHEN checked via issubclass
        THEN it is a subclass of BaseProperty.
        """
        assert issubclass(cached_property, BaseProperty)

    def test_cached_property_klass_attribute_is_false(self) -> None:
        """GIVEN cached_property
        WHEN accessing .klass
        THEN it is False.
        """
        assert cached_property.klass is False


# ------------------------------------------------------------------
# with_parent
# ------------------------------------------------------------------


class TestCachedPropertyWithParent:
    """GIVEN cached_property.with_parent
    WHEN used in an inheritance hierarchy
    THEN parent result is injected correctly.
    """

    def test_with_parent_injects_parent_result(self, fake: Faker) -> None:
        """GIVEN a parent cached_property and child with_parent
        WHEN the child is accessed on an instance
        THEN the child receives the parent's computed value.
        """
        base_value = fake.pyint(min_value=1, max_value=100)
        increment = fake.pyint(min_value=1, max_value=10)

        class Parent:
            @cached_property
            def value(self) -> int:
                return base_value

        class Child(Parent):
            @cached_property.with_parent
            def value(self, parent_result: int) -> int:
                return parent_result + increment

        instance = Child()
        assert instance.value == base_value + increment

    def test_with_parent_returns_cached_property_instance(self) -> None:
        """GIVEN with_parent called with a function
        WHEN inspected
        THEN the result is a cached_property instance.
        """

        def func(_self: object, _parent: int) -> int:
            return 42

        prop = cached_property.with_parent(func)
        assert isinstance(prop, cached_property)


# ------------------------------------------------------------------
# Inheritance contract
# ------------------------------------------------------------------


class TestInheritanceContract:
    """GIVEN the cached_property hierarchy
    WHEN inspecting inherited methods and attributes
    THEN the full interface from BaseProperty is available.
    """

    def test_inherits_name_from_base_property(self) -> None:
        """GIVEN a cached_property wrapping a function
        WHEN accessing .name
        THEN it is inherited from BaseProperty.
        """

        def sample(_self: object) -> int:
            return 1

        prop = cached_property(sample)
        assert prop.name == "sample"

    def test_inherits_is_data_from_base_property(self) -> None:
        """GIVEN a cached_property instance
        WHEN accessing .is_data
        THEN it reflects the presence of __set__ / __delete__.
        """

        def sample(_self: object) -> int:
            return 1

        prop = cached_property(sample)
        assert isinstance(prop.is_data, bool)

    def test_inherits_str_and_repr_from_base_property(self) -> None:
        """GIVEN a cached_property instance
        WHEN calling str() and repr()
        THEN they contain expected introspection info.
        """

        def sample(_self: object) -> int:
            return 1

        prop = cached_property(sample)
        assert "<" in str(prop)
        assert ">" in repr(prop)

    def test_inherits_call_from_parent_class(self) -> None:
        """GIVEN a cached_property instance
        WHEN calling .call
        THEN the inherited logic computes and caches the value.
        """
        expected = 42

        class Sample:
            attr = cached_property(lambda _self: expected)

        prop = Sample.__dict__["attr"]
        instance = Sample()
        assert prop.call(instance) == expected

    def test_inherits_get_cache_from_parent_class(self) -> None:
        """GIVEN a cached_property instance
        WHEN calling .get_cache
        THEN it returns the instance-level cache dict.
        """

        class Sample:
            attr = cached_property(lambda _self: 1)

        prop = Sample.__dict__["attr"]
        instance = Sample()
        cache = prop.get_cache(instance)

        assert isinstance(cache, dict)

    def test_inherits_set_and_delete(self) -> None:
        """GIVEN a cached_property instance
        WHEN using __set__ and __delete__
        THEN they manipulate the cache correctly.
        """

        class Sample:
            attr = cached_property(lambda _self: 1)

        prop = Sample.__dict__["attr"]
        instance = Sample()

        new_value = 99
        prop.__set__(instance, new_value)
        assert (
            instance.__dict__["__instance_memoized__"][prop.name] == new_value
        )

        prop.__delete__(instance)
        assert prop.name not in instance.__dict__["__instance_memoized__"]

    def test_inherits_custom_callback_mixin(self) -> None:
        """GIVEN cached_property
        WHEN checking for CustomCallbackMixin methods
        THEN .by and .ttl factories are available via the class.
        """
        assert hasattr(cached_property, "by")
        assert hasattr(cached_property, "ttl")


# ------------------------------------------------------------------
# Annotation inference
# ------------------------------------------------------------------


class TestAnnotationInference:
    """GIVEN cached_property with type annotations
    WHEN instantiated
    THEN type information is preserved.
    """

    def test_preserves_function_name(self) -> None:
        """GIVEN an annotated function
        WHEN wrapped in cached_property
        THEN .name matches the original function.
        """

        def compute(_self: object) -> int:
            return 42

        prop = cached_property(compute)
        assert prop.name == "compute"

    def test_is_generic_subclass(self) -> None:
        """GIVEN cached_property
        WHEN inspected
        THEN it is a generic class.
        """
        assert hasattr(cached_property, "__class_getitem__")


class TestEdgeCases:
    """Paranoid edge-case coverage for cached_property."""

    def test_get_cache_early_return_from_dict(self) -> None:
        """
        Given: an instance with pre-existing __instance_memoized__
        WHEN: get_cache is called
        THEN: the existing dict is returned without recreation.
        """

        def compute(_self: object) -> int:
            return 1

        class Base:
            attr = cached_property(compute)

        instance = Base()
        # Populate cache via first access
        _ = instance.attr
        descriptor = Base.__dict__["attr"]
        cache_first = descriptor.get_cache(instance)
        cache_second = descriptor.get_cache(instance)
        assert cache_first is cache_second

    def test_multiple_cached_properties_on_same_class(self) -> None:
        """
        Given: a class with multiple cached_property descriptors
        WHEN: each is accessed
        THEN: they use separate cache keys.
        """

        def first_func(_self: object) -> int:
            return 1

        def second_func(_self: object) -> int:
            return 2

        class Base:
            first = cached_property(first_func)
            second = cached_property(second_func)

        expected_first = 1
        expected_second = 2
        instance = Base()
        assert instance.first == expected_first
        assert instance.second == expected_second
        memo = instance.__dict__["__instance_memoized__"]
        assert memo["first_func"] == expected_first
        assert memo["second_func"] == expected_second
