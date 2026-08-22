"""Unit tests for pre_parent_cached_property and pre_cached_property.

Arrange-Act-Assert pattern, BDD docstrings.
"""

from __future__ import annotations

import pytest
from faker import Faker

from kapro.cached.mixed import (
    mixed_cached_property,
    mixed_parent_cached_property,
)
from kapro.cached.pre import (
    pre_cached_property,
    pre_parent_cached_property,
)
from kapro.primitives import BaseProperty

# ------------------------------------------------------------------
# pre_parent_cached_property
# ------------------------------------------------------------------


class TestPreParentCachedProperty:
    """GIVEN a pre_parent_cached_property descriptor
    WHEN accessed on a class or instance
    THEN it caches only on classes, skipping instance caching.
    """

    def test_instance_access_skips_cache(self, fake: Faker) -> None:
        """GIVEN an instance access
        WHEN the descriptor is accessed repeatedly
        THEN the function is called every time (no instance cache).
        """
        counter = 0

        class Sample:
            attr = pre_parent_cached_property(lambda _node: counter + 1)

        instance = Sample()
        prop = Sample.__dict__["attr"]
        first = instance.attr
        counter += 1
        second = instance.attr

        assert first != second
        assert (
            instance.__dict__.get("__instance_memoized__", {}).get(
                prop.name,
            )
            is None
        )

    def test_class_access_caches_on_owner(self, fake: Faker) -> None:
        """GIVEN a class access on a subclass
        WHEN the descriptor is accessed repeatedly
        THEN the value is cached on the owning class.
        """
        expected = fake.pyint()

        class Base:
            @pre_parent_cached_property
            def attr(cls) -> int:
                return expected

        class Child(Base):
            pass

        first = Child.attr
        second = Child.attr

        assert first == second
        assert "__class_memoized__" in Base.__dict__

    def test_set_on_instance_returns_value_without_storing(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN __set__ called with an instance node
        WHEN invoked
        THEN the value is returned but not stored in the cache.
        """
        expected = fake.pyint()

        class Sample:
            attr = pre_parent_cached_property(lambda _node: 1)

        prop = Sample.__dict__["attr"]
        instance = Sample()
        result = prop.__set__(instance, expected)

        assert result == expected
        assert "__instance_memoized__" not in instance.__dict__

    def test_set_on_class_stores_in_cache(self, fake: Faker) -> None:
        """GIVEN __set__ called with a class node
        WHEN invoked
        THEN the value is stored in the class cache.
        """
        expected = fake.pyint()

        class Sample:
            attr = pre_parent_cached_property(lambda _node: 1)

        prop = Sample.__dict__["attr"]
        prop.__set__(Sample, expected)

        assert Sample.__dict__["__class_memoized__"][prop.name] == expected

    def test_is_subclass_of_mixed_parent_cached(self) -> None:
        """GIVEN pre_parent_cached_property
        WHEN checked via issubclass
        THEN it is a subclass of mixed_parent_cached_property.
        """
        assert issubclass(
            pre_parent_cached_property,
            mixed_parent_cached_property,
        )

    def test_is_subclass_of_base_property(self) -> None:
        """GIVEN pre_parent_cached_property
        WHEN checked via issubclass
        THEN it is a subclass of BaseProperty.
        """
        assert issubclass(pre_parent_cached_property, BaseProperty)

    def test_with_parent_injects_parent_result(self, fake: Faker) -> None:
        """GIVEN a parent and child with with_parent
        WHEN accessed on the class
        THEN the child receives the parent's computed value.
        """
        base_value = fake.pyint(min_value=1, max_value=100)
        increment = fake.pyint(min_value=1, max_value=10)

        class Parent:
            @pre_parent_cached_property
            def value(cls) -> int:
                return base_value

        class Child(Parent):
            @pre_parent_cached_property.with_parent
            def value(cls, parent_result: int) -> int:
                return parent_result + increment

        assert Child.value == base_value + increment


# ------------------------------------------------------------------
# pre_cached_property
# ------------------------------------------------------------------


class TestPreCachedProperty:
    """GIVEN a pre_cached_property descriptor
    WHEN accessed on a class or instance
    THEN it caches only on classes, skipping instance caching.
    """

    def test_instance_access_skips_cache(self, fake: Faker) -> None:
        """GIVEN an instance access
        WHEN the descriptor is accessed repeatedly
        THEN the function is called every time (no instance cache).
        """
        counter = 0

        class Sample:
            attr = pre_cached_property(lambda _node: counter + 1)

        instance = Sample()
        prop = Sample.__dict__["attr"]
        first = instance.attr
        counter += 1
        second = instance.attr

        assert first != second
        assert (
            instance.__dict__.get("__instance_memoized__", {}).get(
                prop.name,
            )
            is None
        )

    def test_class_access_caches_on_class(self, fake: Faker) -> None:
        """GIVEN a class access on a subclass
        WHEN the descriptor is accessed repeatedly
        THEN the value is cached on the accessed class.
        """
        expected = fake.pyint()
        counter = 0

        class Base:
            attr = pre_cached_property(lambda _node: expected + counter)

        class Child(Base):
            pass

        first = Child.attr
        counter += 1
        second = Child.attr

        assert first == second
        assert "__class_memoized__" in Child.__dict__

    def test_here_property_returns_parent_class(self) -> None:
        """GIVEN pre_cached_property
        WHEN accessing .here on the descriptor class
        THEN it returns pre_parent_cached_property.
        """

        class Sample:
            attr = pre_cached_property(lambda _node: 1)

        prop = Sample.__dict__["attr"]
        assert prop.here is pre_parent_cached_property

    def test_is_subclass_of_mixed_cached(self) -> None:
        """GIVEN pre_cached_property
        WHEN checked via issubclass
        THEN it is a subclass of mixed_cached_property.
        """
        assert issubclass(pre_cached_property, mixed_cached_property)

    def test_with_parent_injects_parent_result(self, fake: Faker) -> None:
        """GIVEN a parent and child with with_parent
        WHEN accessed on an instance
        THEN the child receives the parent's computed value.
        """
        base_value = fake.pyint(min_value=1, max_value=100)
        increment = fake.pyint(min_value=1, max_value=10)

        class Parent:
            @pre_cached_property
            def value(self) -> int:
                return base_value

        class Child(Parent):
            @pre_cached_property.with_parent
            def value(self, parent_result: int) -> int:
                return parent_result + increment

        instance = Child()
        assert instance.value == base_value + increment


class TestWithParent:
    """GIVEN pre_* descriptors with with_parent
    WHEN the decorator is used
    THEN it returns the correct descriptor type and preserves semantics.
    """

    def test_pre_parent_with_parent_returns_pre_parent_type(
        self,
        fake: Faker,
    ) -> None:
        """pre_parent_cached_property.with_parent returns its own type."""

        class Parent:
            @pre_parent_cached_property
            def value(cls) -> int:
                return fake.pyint()

        class Child(Parent):
            @pre_parent_cached_property.with_parent
            def value(cls, parent_result: int) -> int:
                return parent_result

        prop = Child.__dict__["value"]
        assert isinstance(prop, pre_parent_cached_property)
        assert not isinstance(prop, mixed_cached_property)

    def test_pre_cached_with_parent_returns_pre_cached_type(
        self,
        fake: Faker,
    ) -> None:
        """pre_cached_property.with_parent returns its own type
        and still skips instance caching.
        """
        counter = 0

        class Parent:
            @pre_cached_property
            def value(self) -> int:
                return 1

        class Child(Parent):
            @pre_cached_property.with_parent
            def value(self, parent_result: int) -> int:
                nonlocal counter
                counter += 1
                return parent_result + counter

        instance = Child()
        first = instance.value
        second = instance.value

        assert first != second
        assert counter == 2
        prop = Child.__dict__["value"]
        assert isinstance(prop, pre_cached_property)


# ------------------------------------------------------------------
# Annotation inference
# ------------------------------------------------------------------


class TestAnnotationInference:
    """GIVEN pre-cached descriptors with type annotations
    WHEN instantiated or inspected
    THEN generic parameters and function names are preserved.
    """

    def test_pre_cached_property_preserves_function_name(self) -> None:
        """GIVEN an annotated function
        WHEN wrapped in pre_cached_property
        THEN .name matches the original function.
        """

        def compute(_node: object) -> int:
            return 42

        prop = pre_cached_property(compute)
        assert prop.name == "compute"

    def test_pre_parent_cached_property_preserves_function_name(
        self,
    ) -> None:
        """GIVEN an annotated function
        WHEN wrapped in pre_parent_cached_property
        THEN .name matches the original function.
        """

        def compute(_node: object) -> int:
            return 42

        prop = pre_parent_cached_property(compute)
        assert prop.name == "compute"

    def test_pre_cached_property_is_generic_subclass(self) -> None:
        """GIVEN pre_cached_property
        WHEN inspected
        THEN it is a generic class.
        """
        assert hasattr(pre_cached_property, "__class_getitem__")

    def test_pre_parent_cached_property_is_generic_subclass(
        self,
    ) -> None:
        """GIVEN pre_parent_cached_property
        WHEN inspected
        THEN it is a generic class.
        """
        assert hasattr(pre_parent_cached_property, "__class_getitem__")


# ------------------------------------------------------------------
# Inheritance contract
# ------------------------------------------------------------------


class TestInheritanceContract:
    """GIVEN the pre-cached descriptor hierarchy
    WHEN inspecting inherited methods and attributes
    THEN the full interface is available.
    """

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(pre_parent_cached_property, id="parent"),
            pytest.param(pre_cached_property, id="plain"),
        ),
    )
    def test_inherits_name_from_base_property(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any pre-cached descriptor
        WHEN wrapping a function
        THEN .name is inherited from BaseProperty.
        """

        def sample(_node: object) -> int:
            return 1

        prop = descriptor_type(sample)
        assert prop.name == "sample"

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(pre_parent_cached_property, id="parent"),
            pytest.param(pre_cached_property, id="plain"),
        ),
    )
    def test_inherits_is_data_from_base_property(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any pre-cached descriptor
        WHEN accessing .is_data
        THEN it reflects __set__ / __delete__ presence.
        """

        def sample(_node: object) -> int:
            return 1

        prop = descriptor_type(sample)
        assert isinstance(prop.is_data, bool)

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(pre_parent_cached_property, id="parent"),
            pytest.param(pre_cached_property, id="plain"),
        ),
    )
    def test_inherits_str_and_repr(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any pre-cached descriptor
        WHEN calling str() and repr()
        THEN they contain expected introspection info.
        """

        def sample(_node: object) -> int:
            return 1

        prop = descriptor_type(sample)
        assert "<" in str(prop)
        assert ">" in repr(prop)

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(pre_parent_cached_property, id="parent"),
            pytest.param(pre_cached_property, id="plain"),
        ),
    )
    def test_inherits_get_node(self, descriptor_type: type) -> None:
        """GIVEN any pre-cached descriptor
        WHEN calling .get_node
        THEN the inherited logic works.
        """

        class Sample:
            attr = descriptor_type(lambda _node: 1)

        prop = Sample.__dict__["attr"]
        instance = Sample()
        assert prop.get_node(instance) is instance

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(pre_parent_cached_property, id="parent"),
            pytest.param(pre_cached_property, id="plain"),
        ),
    )
    def test_inherits_custom_callback_mixin(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any pre-cached descriptor
        WHEN checking mixin methods
        THEN .by and .ttl are available.
        """
        assert hasattr(descriptor_type, "by")
        assert hasattr(descriptor_type, "ttl")


class TestEdgeCases:
    """Paranoid edge-case coverage for pre cached descriptors."""

    def test_instance_access_never_caches_value(self) -> None:
        """
        Given: pre_parent_cached_property
        WHEN: accessed repeatedly on instance
        THEN: value is recomputed each time (no caching).
        """

        call_count = 0

        def compute(_node: object) -> int:
            nonlocal call_count
            call_count += 1
            return 1

        class Base:
            attr = pre_parent_cached_property(compute)

        instance = Base()
        _ = instance.attr
        _ = instance.attr
        expected_calls = 2
        assert call_count == expected_calls

    def test_class_access_caches_on_owner(self) -> None:
        """
        Given: pre_parent_cached_property
        WHEN: accessed on class
        THEN: cache lives in __class_memoized__ on owner.
        """

        def compute(_node: object) -> int:
            return 1

        class Base:
            attr = pre_parent_cached_property(compute)

        _ = Base.attr
        assert "__class_memoized__" in Base.__dict__
