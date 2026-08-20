"""Unit tests for post_parent_cached_property and post_cached_property.

Arrange-Act-Assert pattern, BDD docstrings.
"""

from __future__ import annotations

import pytest
from faker import Faker

from kapro.cached.mixed import (
    mixed_cached_property,
    mixed_parent_cached_property,
)
from kapro.cached.post import (
    post_cached_property,
    post_parent_cached_property,
)
from kapro.primitives import BaseProperty

# ------------------------------------------------------------------
# post_parent_cached_property
# ------------------------------------------------------------------


class TestPostParentCachedProperty:
    """GIVEN a post_parent_cached_property descriptor
    WHEN accessed on a class or instance
    THEN it caches only on instances, skipping class caching.
    """

    def test_class_access_skips_cache(self, fake: Faker) -> None:
        """GIVEN a class access
        WHEN the descriptor is accessed repeatedly
        THEN the function is called every time (no class cache).
        """
        counter = 0

        class Sample:
            attr = post_parent_cached_property(lambda _node: counter + 1)

        prop = Sample.__dict__["attr"]
        first = Sample.attr
        counter += 1
        second = Sample.attr

        assert first != second
        assert (
            Sample.__dict__.get("__class_memoized__", {}).get(
                prop.name,
            )
            is None
        )

    def test_instance_access_caches_on_instance(self, fake: Faker) -> None:
        """GIVEN an instance access
        WHEN the descriptor is accessed repeatedly
        THEN the value is cached on the instance.
        """
        expected = fake.pyint()
        counter = 0

        class Sample:
            attr = post_parent_cached_property(
                lambda _node: expected + counter,
            )

        instance = Sample()
        first = instance.attr
        counter += 1
        second = instance.attr

        assert first == second
        assert "__instance_memoized__" in instance.__dict__

    def test_set_on_class_returns_value_without_storing(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN __set__ called with a class node
        WHEN invoked
        THEN the value is returned but not stored in the cache.
        """
        expected = fake.pyint()

        class Sample:
            attr = post_parent_cached_property(lambda _node: 1)

        prop = Sample.__dict__["attr"]
        result = prop.__set__(Sample, expected)

        assert result == expected
        assert "__class_memoized__" not in Sample.__dict__

    def test_set_on_instance_stores_in_cache(self, fake: Faker) -> None:
        """GIVEN __set__ called with an instance node
        WHEN invoked
        THEN the value is stored in the instance cache.
        """
        expected = fake.pyint()

        class Sample:
            attr = post_parent_cached_property(lambda _node: 1)

        prop = Sample.__dict__["attr"]
        instance = Sample()
        prop.__set__(instance, expected)

        assert (
            instance.__dict__["__instance_memoized__"][prop.name] == expected
        )

    def test_is_subclass_of_mixed_parent_cached(self) -> None:
        """GIVEN post_parent_cached_property
        WHEN checked via issubclass
        THEN it is a subclass of mixed_parent_cached_property.
        """
        assert issubclass(
            post_parent_cached_property,
            mixed_parent_cached_property,
        )

    def test_is_subclass_of_base_property(self) -> None:
        """GIVEN post_parent_cached_property
        WHEN checked via issubclass
        THEN it is a subclass of BaseProperty.
        """
        assert issubclass(post_parent_cached_property, BaseProperty)

    def test_with_parent_injects_parent_result(self, fake: Faker) -> None:
        """GIVEN a parent and child with with_parent
        WHEN accessed on an instance
        THEN the child receives the parent's computed value.
        """
        base_value = fake.pyint(min_value=1, max_value=100)
        increment = fake.pyint(min_value=1, max_value=10)

        class Parent:
            @post_parent_cached_property
            def value(self) -> int:
                return base_value

        class Child(Parent):
            @post_parent_cached_property.with_parent
            def value(self, parent_result: int) -> int:
                return parent_result + increment

        instance = Child()
        assert instance.value == base_value + increment


# ------------------------------------------------------------------
# post_cached_property
# ------------------------------------------------------------------


class TestPostCachedProperty:
    """GIVEN a post_cached_property descriptor
    WHEN accessed on a class or instance
    THEN it caches only on instances, skipping class caching.
    """

    def test_class_access_skips_cache(self, fake: Faker) -> None:
        """GIVEN a class access
        WHEN the descriptor is accessed repeatedly
        THEN the function is called every time (no class cache).
        """
        counter = 0

        class Sample:
            attr = post_cached_property(lambda _node: counter + 1)

        prop = Sample.__dict__["attr"]
        first = Sample.attr
        counter += 1
        second = Sample.attr

        assert first != second
        assert (
            Sample.__dict__.get("__class_memoized__", {}).get(
                prop.name,
            )
            is None
        )

    def test_instance_access_caches_on_instance(self, fake: Faker) -> None:
        """GIVEN an instance access
        WHEN the descriptor is accessed repeatedly
        THEN the value is cached on the instance.
        """
        expected = fake.pyint()
        counter = 0

        class Sample:
            attr = post_cached_property(lambda _node: expected + counter)

        instance = Sample()
        first = instance.attr
        counter += 1
        second = instance.attr

        assert first == second
        assert "__instance_memoized__" in instance.__dict__

    def test_here_property_returns_parent_class(self) -> None:
        """GIVEN post_cached_property
        WHEN accessing .here on the descriptor class
        THEN it returns post_parent_cached_property.
        """

        class Sample:
            attr = post_cached_property(lambda _node: 1)

        prop = Sample.__dict__["attr"]
        assert prop.here is post_parent_cached_property

    def test_is_subclass_of_mixed_cached(self) -> None:
        """GIVEN post_cached_property
        WHEN checked via issubclass
        THEN it is a subclass of mixed_cached_property.
        """
        assert issubclass(post_cached_property, mixed_cached_property)

    def test_with_parent_injects_parent_result(self, fake: Faker) -> None:
        """GIVEN a parent and child with with_parent
        WHEN accessed on an instance
        THEN the child receives the parent's computed value.
        """
        base_value = fake.pyint(min_value=1, max_value=100)
        increment = fake.pyint(min_value=1, max_value=10)

        class Parent:
            @post_cached_property
            def value(self) -> int:
                return base_value

        class Child(Parent):
            @post_cached_property.with_parent
            def value(self, parent_result: int) -> int:
                return parent_result + increment

        instance = Child()
        assert instance.value == base_value + increment


# ------------------------------------------------------------------
# Annotation inference
# ------------------------------------------------------------------


class TestAnnotationInference:
    """GIVEN post-cached descriptors with type annotations
    WHEN instantiated or inspected
    THEN generic parameters and function names are preserved.
    """

    def test_post_cached_property_preserves_function_name(self) -> None:
        """GIVEN an annotated function
        WHEN wrapped in post_cached_property
        THEN .name matches the original function.
        """

        def compute(_node: object) -> int:
            return 42

        prop = post_cached_property(compute)
        assert prop.name == "compute"

    def test_post_parent_cached_property_preserves_function_name(
        self,
    ) -> None:
        """GIVEN an annotated function
        WHEN wrapped in post_parent_cached_property
        THEN .name matches the original function.
        """

        def compute(_node: object) -> int:
            return 42

        prop = post_parent_cached_property(compute)
        assert prop.name == "compute"

    def test_post_cached_property_is_generic_subclass(self) -> None:
        """GIVEN post_cached_property
        WHEN inspected
        THEN it is a generic class.
        """
        assert hasattr(post_cached_property, "__class_getitem__")

    def test_post_parent_cached_property_is_generic_subclass(
        self,
    ) -> None:
        """GIVEN post_parent_cached_property
        WHEN inspected
        THEN it is a generic class.
        """
        assert hasattr(post_parent_cached_property, "__class_getitem__")


# ------------------------------------------------------------------
# Inheritance contract
# ------------------------------------------------------------------


class TestInheritanceContract:
    """GIVEN the post-cached descriptor hierarchy
    WHEN inspecting inherited methods and attributes
    THEN the full interface is available.
    """

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(post_parent_cached_property, id="parent"),
            pytest.param(post_cached_property, id="plain"),
        ),
    )
    def test_inherits_name_from_base_property(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any post-cached descriptor
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
            pytest.param(post_parent_cached_property, id="parent"),
            pytest.param(post_cached_property, id="plain"),
        ),
    )
    def test_inherits_is_data_from_base_property(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any post-cached descriptor
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
            pytest.param(post_parent_cached_property, id="parent"),
            pytest.param(post_cached_property, id="plain"),
        ),
    )
    def test_inherits_str_and_repr(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any post-cached descriptor
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
            pytest.param(post_parent_cached_property, id="parent"),
            pytest.param(post_cached_property, id="plain"),
        ),
    )
    def test_inherits_get_node(self, descriptor_type: type) -> None:
        """GIVEN any post-cached descriptor
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
            pytest.param(post_parent_cached_property, id="parent"),
            pytest.param(post_cached_property, id="plain"),
        ),
    )
    def test_inherits_custom_callback_mixin(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any post-cached descriptor
        WHEN checking mixin methods
        THEN .by and .ttl are available.
        """
        assert hasattr(descriptor_type, "by")
        assert hasattr(descriptor_type, "ttl")


class TestEdgeCases:
    """Paranoid edge-case coverage for post cached descriptors."""

    def test_class_access_never_caches_value(self) -> None:
        """
        Given: post_parent_cached_property
        WHEN: accessed repeatedly on class
        THEN: value is recomputed each time (no caching).
        """

        call_count = 0

        def compute(_node: object) -> int:
            nonlocal call_count
            call_count += 1
            return 1

        class Base:
            attr = post_parent_cached_property(compute)

        _ = Base.attr
        _ = Base.attr
        expected_calls = 2
        assert call_count == expected_calls

    def test_instance_access_caches_on_instance(self) -> None:
        """
        Given: post_parent_cached_property
        WHEN: accessed on instance
        THEN: cache lives in __instance_memoized__.
        """

        def compute(_node: object) -> int:
            return 1

        class Base:
            attr = post_parent_cached_property(compute)

        instance = Base()
        _ = instance.attr
        assert "__instance_memoized__" in instance.__dict__
