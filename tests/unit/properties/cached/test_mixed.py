"""Unit tests for mixed_parent_cached_property and mixed_cached_property.

Arrange-Act-Assert pattern, BDD docstrings.
"""

from __future__ import annotations

import pytest
from faker import Faker

from kapro.cached.klass import class_parent_cached_property
from kapro.cached.mixed import (
    mixed_cached_property,
    mixed_parent_cached_property,
)
from kapro.primitives import BaseProperty, ContextFaultError

# ------------------------------------------------------------------
# mixed_parent_cached_property
# ------------------------------------------------------------------


class TestMixedParentCachedProperty:
    """GIVEN a mixed_parent_cached_property descriptor
    WHEN accessed on a class or instance
    THEN it caches on the appropriate node with owner resolution.
    """

    def test_instance_access_caches_on_instance(self, fake: Faker) -> None:
        """GIVEN an instance access
        WHEN the descriptor is accessed
        THEN the cache lives on the instance.
        """
        expected = fake.pyint()

        class Sample:
            attr = mixed_parent_cached_property(lambda _node: expected)

        instance = Sample()
        assert instance.attr == expected
        assert "__instance_memoized__" in instance.__dict__

    def test_class_access_caches_on_owner(self, fake: Faker) -> None:
        """GIVEN a class access on a subclass
        WHEN the descriptor is accessed
        THEN the cache lives on the owning parent class.
        """
        expected = fake.pyint()

        class Base:
            @mixed_parent_cached_property
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
        prop = mixed_parent_cached_property(lambda _node: 1)

        with pytest.raises(ContextFaultError):
            prop.get_node(None)

    def test_get_node_returns_instance_for_instance(self) -> None:
        """GIVEN an instance node
        WHEN get_node is called
        THEN the instance is returned.
        """

        class Sample:
            attr = mixed_parent_cached_property(lambda _node: 1)

        prop = Sample.__dict__["attr"]
        instance = Sample()
        assert prop.get_node(instance) is instance

    def test_get_node_returns_owner_for_class(self) -> None:
        """GIVEN a subclass node
        WHEN get_node is called
        THEN the owning parent class is returned.
        """

        class Base:
            @mixed_parent_cached_property
            def attr(cls) -> int:
                return 1

        class Child(Base):
            pass

        prop = Base.__dict__["attr"]
        assert prop.get_node(Child) is Base

    def test_title_contains_mixed_data_descriptor(self) -> None:
        """GIVEN a mixed_parent_cached_property instance
        WHEN .title is accessed
        THEN it contains 'mixed data-descriptor'.
        """
        prop = mixed_parent_cached_property(lambda _node: 1)

        assert "mixed data-descriptor" in prop.title

    def test_header_with_context_includes_mixed(self) -> None:
        """GIVEN a mixed_parent_cached_property instance
        WHEN .header_with_context is called
        THEN it includes 'mixed'.
        """
        prop = mixed_parent_cached_property(lambda _node: 1)

        assert "mixed" in prop.header_with_context(object())

    def test_is_subclass_of_class_parent_cached(self) -> None:
        """GIVEN mixed_parent_cached_property
        WHEN checked via issubclass
        THEN it is a subclass of class_parent_cached_property.
        """
        assert issubclass(
            mixed_parent_cached_property,
            class_parent_cached_property,
        )

    def test_is_subclass_of_base_property(self) -> None:
        """GIVEN mixed_parent_cached_property
        WHEN checked via issubclass
        THEN it is a subclass of BaseProperty.
        """
        assert issubclass(mixed_parent_cached_property, BaseProperty)

    def test_with_parent_injects_parent_result_on_instance(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a parent and child with with_parent
        WHEN accessed on an instance
        THEN the child receives the parent's computed value.
        """
        base_value = fake.pyint(min_value=1, max_value=100)
        increment = fake.pyint(min_value=1, max_value=10)

        class Parent:
            @mixed_parent_cached_property
            def value(self) -> int:
                return base_value

        class Child(Parent):
            @mixed_parent_cached_property.with_parent
            def value(self, parent_result: int) -> int:
                return parent_result + increment

        instance = Child()
        assert instance.value == base_value + increment

    def test_with_parent_injects_parent_result_on_class(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a parent and child with with_parent
        WHEN accessed on the class
        THEN the child receives the parent's computed value.
        """
        base_value = fake.pyint(min_value=1, max_value=100)
        increment = fake.pyint(min_value=1, max_value=10)

        class Parent:
            @mixed_parent_cached_property
            def value(cls) -> int:
                return base_value

        class Child(Parent):
            @mixed_parent_cached_property.with_parent
            def value(cls, parent_result: int) -> int:
                return parent_result + increment

        assert Child.value == base_value + increment


# ------------------------------------------------------------------
# mixed_cached_property
# ------------------------------------------------------------------


class TestMixedCachedProperty:
    """GIVEN a mixed_cached_property descriptor
    WHEN accessed on a class or instance
    THEN it caches directly on the accessed node.
    """

    def test_instance_access_caches_on_instance(self, fake: Faker) -> None:
        """GIVEN an instance access
        WHEN the descriptor is accessed
        THEN the cache lives on the instance.
        """
        expected = fake.pyint()

        class Sample:
            attr = mixed_cached_property(lambda _node: expected)

        instance = Sample()
        assert instance.attr == expected
        assert "__instance_memoized__" in instance.__dict__

    def test_class_access_caches_on_class(self, fake: Faker) -> None:
        """GIVEN a class access on a subclass
        WHEN the descriptor is accessed
        THEN the cache lives on the accessed class.
        """
        expected = fake.pyint()

        class Base:
            attr = mixed_cached_property(lambda _node: expected)

        class Child(Base):
            pass

        assert Child.attr == expected
        assert "__class_memoized__" in Child.__dict__

    def test_get_node_returns_node_directly(self) -> None:
        """GIVEN any non-None node
        WHEN get_node is called
        THEN the node itself is returned.
        """

        class Base:
            attr = mixed_cached_property(lambda _node: 1)

        class Child(Base):
            pass

        prop = Base.__dict__["attr"]
        assert prop.get_node(Child) is Child

    def test_get_node_raises_on_none(self) -> None:
        """GIVEN node is None
        WHEN get_node is called
        THEN ContextFaultError is raised.
        """
        prop = mixed_cached_property(lambda _node: 1)

        with pytest.raises(ContextFaultError):
            prop.get_node(None)

    def test_here_property_returns_parent_class(self) -> None:
        """GIVEN mixed_cached_property
        WHEN accessing .here on the descriptor class
        THEN it returns mixed_parent_cached_property.
        """

        class Sample:
            attr = mixed_cached_property(lambda _node: 1)

        prop = Sample.__dict__["attr"]
        assert prop.here is mixed_parent_cached_property

    def test_is_subclass_of_mixed_parent_cached(self) -> None:
        """GIVEN mixed_cached_property
        WHEN checked via issubclass
        THEN it is a subclass of mixed_parent_cached_property.
        """
        assert issubclass(
            mixed_cached_property,
            mixed_parent_cached_property,
        )

    def test_with_parent_injects_parent_result(self, fake: Faker) -> None:
        """GIVEN a parent and child with with_parent
        WHEN accessed on an instance
        THEN the child receives the parent's computed value.
        """
        base_value = fake.pyint(min_value=1, max_value=100)
        increment = fake.pyint(min_value=1, max_value=10)

        class Parent:
            @mixed_cached_property
            def value(self) -> int:
                return base_value

        class Child(Parent):
            @mixed_cached_property.with_parent
            def value(self, parent_result: int) -> int:
                return parent_result + increment

        instance = Child()
        assert instance.value == base_value + increment


# ------------------------------------------------------------------
# Annotation inference
# ------------------------------------------------------------------


class TestAnnotationInference:
    """GIVEN mixed cached descriptors with type annotations
    WHEN instantiated or inspected
    THEN generic parameters and function names are preserved.
    """

    def test_mixed_cached_property_preserves_function_name(self) -> None:
        """GIVEN an annotated function
        WHEN wrapped in mixed_cached_property
        THEN .name matches the original function.
        """

        def compute(_node: object) -> int:
            return 42

        prop = mixed_cached_property(compute)
        assert prop.name == "compute"

    def test_mixed_parent_cached_property_preserves_function_name(
        self,
    ) -> None:
        """GIVEN an annotated function
        WHEN wrapped in mixed_parent_cached_property
        THEN .name matches the original function.
        """

        def compute(_node: object) -> int:
            return 42

        prop = mixed_parent_cached_property(compute)
        assert prop.name == "compute"

    def test_mixed_cached_property_is_generic_subclass(self) -> None:
        """GIVEN mixed_cached_property
        WHEN inspected
        THEN it is a generic class.
        """
        assert hasattr(mixed_cached_property, "__class_getitem__")

    def test_mixed_parent_cached_property_is_generic_subclass(
        self,
    ) -> None:
        """GIVEN mixed_parent_cached_property
        WHEN inspected
        THEN it is a generic class.
        """
        assert hasattr(mixed_parent_cached_property, "__class_getitem__")


# ------------------------------------------------------------------
# Inheritance contract
# ------------------------------------------------------------------


class TestInheritanceContract:
    """GIVEN the mixed cached descriptor hierarchy
    WHEN inspecting inherited methods and attributes
    THEN the full interface is available.
    """

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(mixed_parent_cached_property, id="parent"),
            pytest.param(mixed_cached_property, id="plain"),
        ),
    )
    def test_inherits_name_from_base_property(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any mixed cached descriptor
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
            pytest.param(mixed_parent_cached_property, id="parent"),
            pytest.param(mixed_cached_property, id="plain"),
        ),
    )
    def test_inherits_is_data_from_base_property(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any mixed cached descriptor
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
            pytest.param(mixed_parent_cached_property, id="parent"),
            pytest.param(mixed_cached_property, id="plain"),
        ),
    )
    def test_inherits_str_and_repr(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any mixed cached descriptor
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
            pytest.param(mixed_parent_cached_property, id="parent"),
            pytest.param(mixed_cached_property, id="plain"),
        ),
    )
    def test_inherits_call_logic(self, descriptor_type: type) -> None:
        """GIVEN any mixed cached descriptor
        WHEN calling .call
        THEN the inherited caching logic works.
        """
        expected = 42

        class Sample:
            attr = descriptor_type(lambda _node: expected)

        prop = Sample.__dict__["attr"]
        instance = Sample()
        assert prop.call(instance) == expected

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(mixed_parent_cached_property, id="parent"),
            pytest.param(mixed_cached_property, id="plain"),
        ),
    )
    def test_inherits_get_cache(self, descriptor_type: type) -> None:
        """GIVEN any mixed cached descriptor
        WHEN calling .get_cache
        THEN it returns the appropriate cache dict.
        """

        class Sample:
            attr = descriptor_type(lambda _node: 1)

        prop = Sample.__dict__["attr"]
        instance = Sample()
        cache = prop.get_cache(instance)

        assert isinstance(cache, dict)

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(mixed_parent_cached_property, id="parent"),
            pytest.param(mixed_cached_property, id="plain"),
        ),
    )
    def test_inherits_set_and_delete(self, descriptor_type: type) -> None:
        """GIVEN any mixed cached descriptor
        WHEN using __set__ and __delete__
        THEN they manipulate the cache correctly.
        """

        class Sample:
            attr = descriptor_type(lambda _node: 1)

        prop = Sample.__dict__["attr"]
        instance = Sample()
        new_value = 99
        prop.__set__(instance, new_value)
        assert (
            instance.__dict__["__instance_memoized__"][prop.name] == new_value
        )

        prop.__delete__(instance)
        assert prop.name not in instance.__dict__.get(
            "__instance_memoized__",
            {},
        )

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(mixed_parent_cached_property, id="parent"),
            pytest.param(mixed_cached_property, id="plain"),
        ),
    )
    def test_inherits_custom_callback_mixin(
        self,
        descriptor_type: type,
    ) -> None:
        """GIVEN any mixed cached descriptor
        WHEN checking mixin methods
        THEN .by and .ttl are available.
        """
        assert hasattr(descriptor_type, "by")
        assert hasattr(descriptor_type, "ttl")


class TestEdgeCases:
    """Paranoid edge-case coverage for mixed cached descriptors."""

    def test_mixed_parent_instance_and_class_caches_are_isolated(
        self,
    ) -> None:
        """
        Given: mixed_parent_cached_property
        WHEN: accessed on instance and class
        THEN: caches are stored in separate dicts.
        """

        def compute(_node: object) -> int:
            return 1

        class Base:
            attr = mixed_parent_cached_property(compute)

        instance = Base()
        _ = instance.attr
        _ = Base.attr
        assert "__instance_memoized__" in instance.__dict__
        assert "__class_memoized__" in Base.__dict__

    def test_subclass_replacement_with_different_descriptor(self) -> None:
        """
        Given: a base class with mixed_cached_property
        WHEN: subclass replaces it with plain attribute
        THEN: subclass uses the plain attribute.
        """

        def compute(_node: object) -> int:
            return 1

        class Base:
            attr = mixed_cached_property(compute)

        expected = 42

        class Child(Base):
            attr = expected  # type: ignore[assignment][misc]

        assert Child.attr == expected
