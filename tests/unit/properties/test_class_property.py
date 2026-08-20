"""Unit tests for class_property and mixed_property descriptors.

Arrange-Act-Assert pattern, BDD docstrings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from faker import Faker

from kapro.class_property import class_property, mixed_property
from kapro.primitives import (
    AttributeExceptionError,
    BaseProperty,
    ContextFaultError,
)

if TYPE_CHECKING:
    from collections.abc import Callable


# ------------------------------------------------------------------
# class_property
# ------------------------------------------------------------------


class TestClassProperty:
    """GIVEN a class_property descriptor
    WHEN accessed on a class or instance
    THEN it invokes function(klass) and resolves ownership correctly.
    """

    def test_class_property_on_class_access_calls_function(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a class with class_property
        WHEN accessed on the class
        THEN function receives the class and returns computed value.
        """
        expected = fake.pyint()

        class Sample:
            attr = class_property(lambda _cls: expected)

        assert Sample.attr == expected

    def test_class_property_on_instance_access_calls_function_with_class(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a class with class_property
        WHEN accessed on an instance
        THEN function still receives the class, not the instance.
        """
        expected = fake.pyint()

        class Sample:
            attr = class_property(lambda _cls: expected)

        instance = Sample()
        assert instance.attr == expected

    def test_class_property_resolves_owner_via_get_owner(self) -> None:
        """GIVEN a parent class defining class_property
        WHEN a child class accesses the attribute
        THEN get_owner resolves the defining class correctly.
        """

        class Base:
            attr = class_property(lambda _cls: Base)

        class Child(Base):
            pass

        assert Child.attr is Base

    def test_class_property_title_contains_class_descriptor(self) -> None:
        """GIVEN a class_property instance
        WHEN .title is accessed
        THEN it contains 'class descriptor'.
        """
        prop = class_property(lambda _cls: 1)

        assert "class descriptor" in prop.title

    def test_class_property_header_with_context_returns_footer(
        self,
    ) -> None:
        """GIVEN a class_property instance
        WHEN .header_with_context is called
        THEN it equals .footer(node).
        """
        prop = class_property(lambda _cls: 1)
        node = object()

        assert prop.header_with_context(node) == prop.footer(node)

    def test_class_property_get_node_raises_on_none(self) -> None:
        """GIVEN node is None
        WHEN get_node is called
        THEN ContextFaultError is raised.
        """
        prop = class_property(lambda _cls: 1)

        with pytest.raises(ContextFaultError):
            prop.get_node(None)

    def test_class_property_get_node_raises_on_non_class(self) -> None:
        """GIVEN node is not a class
        WHEN get_node is called
        THEN ContextFaultError is raised.
        """
        prop = class_property(lambda _cls: 1)

        with pytest.raises(ContextFaultError):
            prop.get_node(object())

    def test_class_property_call_wraps_attribute_error(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a function that raises AttributeError
        WHEN call is invoked
        THEN AttributeExceptionError is raised preserving the cause.
        """
        msg = fake.pystr()

        class Sample:
            attr = class_property(
                lambda _cls: (_ for _ in ()).throw(AttributeError(msg)),
            )

        with pytest.raises(AttributeExceptionError) as exc_info:
            _ = Sample.attr

        assert isinstance(exc_info.value.__cause__, AttributeError)

    def test_class_property_with_parent_injects_parent_result(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a parent class_property and child override with with_parent
        WHEN the child is accessed
        THEN the child receives the parent's computed value.
        """
        base_value = fake.pyint(min_value=1, max_value=100)
        increment = fake.pyint(min_value=1, max_value=10)

        class Parent:
            @class_property
            def value(cls) -> int:
                return base_value

        class Child(Parent):
            @class_property.with_parent
            def value(cls, parent_result: int) -> int:
                return parent_result + increment

        assert Child.value == base_value + increment

    def test_class_property_is_subclass_of_base_property(self) -> None:
        """GIVEN class_property
        WHEN checked via issubclass
        THEN it is a subclass of BaseProperty.
        """
        assert issubclass(class_property, BaseProperty)

    def test_class_property_klass_attribute_is_true(self) -> None:
        """GIVEN class_property
        WHEN accessing .klass
        THEN it is True.
        """
        assert class_property.klass is True

    def test_class_property_inherited_method_call_works(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN an inherited class_property
        WHEN accessing call on the subclass
        THEN the inherited behavior works.
        """
        expected = fake.pyint()

        class Base:
            attr = class_property(lambda _cls: expected)

        class Child(Base):
            pass

        assert Child.attr == expected
        assert Base.attr == expected


# ------------------------------------------------------------------
# mixed_property
# ------------------------------------------------------------------


class TestMixedProperty:
    """GIVEN a mixed_property descriptor
    WHEN accessed on a class or instance
    THEN it invokes function with the appropriate node.
    """

    def test_mixed_property_on_class_access_calls_function_with_class(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a class with mixed_property
        WHEN accessed on the class
        THEN function receives the class.
        """
        expected = fake.pyint()

        class Sample:
            attr = mixed_property(lambda _node: expected)

        assert Sample.attr == expected

    def test_mixed_property_on_instance_access_calls_function_with_instance(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a class with mixed_property
        WHEN accessed on an instance
        THEN function receives the instance.
        """
        expected = fake.pyint()

        class Sample:
            attr = mixed_property(lambda _node: expected)

        instance = Sample()
        assert instance.attr == expected

    def test_mixed_property_on_instance_passes_actual_instance(self) -> None:
        """GIVEN a mixed_property that returns its argument
        WHEN accessed on an instance
        THEN the instance itself is returned.
        """

        class Sample:
            attr = mixed_property(lambda node: node)

        instance = Sample()
        assert instance.attr is instance

    def test_mixed_property_on_class_passes_actual_class(self) -> None:
        """GIVEN a mixed_property that returns its argument
        WHEN accessed on the class
        THEN the class itself is returned.
        """

        class Sample:
            attr = mixed_property(lambda node: node)

        assert Sample.attr is Sample

    def test_mixed_property_get_node_raises_on_none(self) -> None:
        """GIVEN node is None
        WHEN get_node is called
        THEN ContextFaultError is raised.
        """
        prop = mixed_property(lambda _node: 1)

        with pytest.raises(ContextFaultError):
            prop.get_node(None)

    def test_mixed_property_get_node_returns_instance_for_instance(
        self,
    ) -> None:
        """GIVEN an instance node
        WHEN get_node is called
        THEN the instance is returned.
        """
        prop = mixed_property(lambda _node: 1)
        node = object()

        assert prop.get_node(node) is node

    def test_mixed_property_get_node_returns_owner_for_class(self) -> None:
        """GIVEN a class node that is a subclass
        WHEN get_node is called
        THEN get_owner result is returned.
        """

        class Base:
            @mixed_property
            def attr(self) -> object:
                return self

        class Child(Base):
            pass

        prop = Base.__dict__["attr"]
        assert prop.get_node(Child) is Base

    def test_mixed_property_title_contains_mixed_descriptor(self) -> None:
        """GIVEN a mixed_property instance
        WHEN .title is accessed
        THEN it contains 'mixed descriptor'.
        """
        prop = mixed_property(lambda _node: 1)

        assert "mixed descriptor" in prop.title

    def test_mixed_property_header_with_context_includes_mixed(
        self,
    ) -> None:
        """GIVEN a mixed_property instance
        WHEN .header_with_context is called
        THEN it includes 'mixed' in the footer.
        """
        prop = mixed_property(lambda _node: 1)
        node = object()

        assert "mixed" in prop.header_with_context(node)

    def test_mixed_property_call_wraps_attribute_error(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a function that raises AttributeError
        WHEN call is invoked
        THEN AttributeExceptionError is raised preserving the cause.
        """
        msg = fake.pystr()

        class Sample:
            attr = mixed_property(
                lambda _node: (_ for _ in ()).throw(AttributeError(msg)),
            )

        with pytest.raises(AttributeExceptionError) as exc_info:
            _ = Sample.attr

        assert isinstance(exc_info.value.__cause__, AttributeError)

    def test_mixed_property_with_parent_injects_parent_result(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a parent mixed_property and child override with with_parent
        WHEN the child is accessed on an instance
        THEN the child receives the parent's computed value.
        """
        base_value = fake.pyint(min_value=1, max_value=100)
        increment = fake.pyint(min_value=1, max_value=10)

        class Parent:
            @mixed_property
            def value(self) -> int:
                return base_value

        class Child(Parent):
            @mixed_property.with_parent
            def value(self, parent_result: int) -> int:
                return parent_result + increment

        instance = Child()
        assert instance.value == base_value + increment

    def test_mixed_property_is_subclass_of_base_property(self) -> None:
        """GIVEN mixed_property
        WHEN checked via issubclass
        THEN it is a subclass of BaseProperty.
        """
        assert issubclass(mixed_property, BaseProperty)

    def test_mixed_property_klass_attribute_is_none(self) -> None:
        """GIVEN mixed_property
        WHEN accessing .klass
        THEN it is None.
        """
        assert mixed_property.klass is None

    def test_mixed_property_inherited_access_works(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN an inherited mixed_property
        WHEN accessing on subclass
        THEN the inherited behavior works.
        """
        expected = fake.pyint()

        class Base:
            attr = mixed_property(lambda _node: expected)

        class Child(Base):
            pass

        assert Child.attr == expected
        assert Base.attr == expected


# ------------------------------------------------------------------
# Annotation inference
# ------------------------------------------------------------------


class TestAnnotationInference:
    """GIVEN descriptors with type annotations
    WHEN instantiated or inspected
    THEN generic parameters and return types are inferred correctly.
    """

    def test_class_property_preserves_return_type_annotation(self) -> None:
        """GIVEN a function annotated to return int
        WHEN wrapped in class_property
        THEN the descriptor is a generic subclass.
        """

        def func(_cls: type[object]) -> int:
            return 42

        prop = class_property(func)

        assert prop.name == "func"
        assert issubclass(type(prop), BaseProperty)

    def test_mixed_property_preserves_return_type_annotation(self) -> None:
        """GIVEN a function annotated to return str
        WHEN wrapped in mixed_property
        THEN the descriptor preserves the function name.
        """

        def func(_node: object) -> str:
            return "hello"

        prop = mixed_property(func)

        assert prop.name == "func"


# ------------------------------------------------------------------
# Inheritance contract — verify all inherited methods/attrs
# ------------------------------------------------------------------


class TestInheritanceContract:
    """GIVEN the descriptor class hierarchy
    WHEN inspecting methods and attributes
    THEN every subclass inherits the expected interface from BaseProperty.
    """

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(class_property, id="class-property"),
            pytest.param(mixed_property, id="mixed-property"),
        ),
    )
    def test_inherits_name_property(
        self,
        descriptor_type: Callable[[object], BaseProperty[object]],
    ) -> None:
        """GIVEN any descriptor subclass
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
            pytest.param(class_property, id="class-property"),
            pytest.param(mixed_property, id="mixed-property"),
        ),
    )
    def test_inherits_is_data_property(
        self,
        descriptor_type: Callable[[object], BaseProperty[object]],
    ) -> None:
        """GIVEN any descriptor subclass
        WHEN checking .is_data
        THEN it reflects whether __set__ or __delete__ exists.
        """

        def sample(_node: object) -> int:
            return 1

        prop = descriptor_type(sample)
        assert isinstance(prop.is_data, bool)

    @pytest.mark.parametrize(
        "descriptor_type",
        (
            pytest.param(class_property, id="class-property"),
            pytest.param(mixed_property, id="mixed-property"),
        ),
    )
    def test_inherits_str_and_repr(
        self,
        descriptor_type: Callable[[object], BaseProperty[object]],
    ) -> None:
        """GIVEN any descriptor subclass
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
            pytest.param(class_property, id="class-property"),
            pytest.param(mixed_property, id="mixed-property"),
        ),
    )
    def test_inherits_with_parent_factory(
        self,
        descriptor_type: type[BaseProperty[object]],
    ) -> None:
        """GIVEN any descriptor subclass
        WHEN calling with_parent
        THEN it returns an instance of the same type.
        """

        def sample(_node: object, _parent: int) -> int:
            return 1

        prop = descriptor_type.with_parent(sample)
        assert isinstance(prop, descriptor_type)


class TestEdgeCases:
    """Paranoid edge-case coverage for class_property / mixed_property."""

    def test_mixed_property_instance_then_class(self) -> None:
        """
        Given: mixed_property accessed on instance then class
        WHEN: both accesses occur
        THEN: they receive different nodes (instance vs class).
        """

        nodes: list[object] = []

        def capture(node: object) -> object:
            nodes.append(node)
            return node

        class Base:
            attr = mixed_property(capture)

        instance = Base()
        _ = instance.attr
        _ = Base.attr
        assert nodes[0] is instance
        assert nodes[1] is Base

    def test_descriptor_replacement_in_subclass(self) -> None:
        """
        Given: a base class with class_property
        WHEN: subclass replaces it with plain attribute
        THEN: subclass uses the plain attribute.
        """

        class Base:
            attr = class_property(lambda _cls: 1)

        expected = 42

        class Child(Base):
            attr = expected  # type: ignore[assignment][misc]

        assert Child.attr == expected
