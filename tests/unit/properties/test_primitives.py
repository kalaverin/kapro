"""Unit tests for properties primitive building blocks.

Arrange-Act-Assert pattern, BDD docstrings.
"""

import functools
from functools import cached_property
from typing import Any, override

import pytest
from faker import Faker
from kain import Who

from kapro.class_property import class_property
from kapro.primitives import (
    AttributeExceptionError,
    BaseProperty,
    ContextFaultError,
    PropertyError,
    ReadOnlyError,
    bound_property,
    extract_wrapped,
    parent_call,
)

# ------------------------------------------------------------------
# Exception hierarchy
# ------------------------------------------------------------------


class TestExceptionHierarchy:
    """GIVEN the properties exception hierarchy
    WHEN subclasses are instantiated or inspected
    THEN inheritance and message extraction behave correctly.
    """

    def test_context_fault_error_is_property_error_subclass(self) -> None:
        """GIVEN ContextFaultError
        WHEN checked via issubclass
        THEN it is a subclass of PropertyError.
        """
        assert issubclass(ContextFaultError, PropertyError)

    def test_read_only_error_is_property_error_subclass(self) -> None:
        """GIVEN ReadOnlyError
        WHEN checked via issubclass
        THEN it is a subclass of PropertyError.
        """
        assert issubclass(ReadOnlyError, PropertyError)

    def test_attribute_exception_error_is_property_error_subclass(
        self,
    ) -> None:
        """GIVEN AttributeExceptionError
        WHEN checked via issubclass
        THEN it is a subclass of PropertyError.
        """
        assert issubclass(AttributeExceptionError, PropertyError)

    def test_attribute_exception_error_message_extracts_last_colon_part(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN an origin exception with a colon-separated message
        WHEN AttributeExceptionError.message is accessed
        THEN the substring after the last colon is returned.
        """
        suffix = fake.pystr()
        origin = AttributeError(f"obj.attr: {suffix}")
        exc = AttributeExceptionError(origin)

        assert exc.message == f" {suffix}"

    def test_attribute_exception_error_stores_origin_exception(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN an origin exception
        WHEN AttributeExceptionError is constructed
        THEN .exception refers to the original instance.
        """
        origin = RuntimeError(fake.pystr())
        exc = AttributeExceptionError(origin)

        assert exc.exception is origin


# ------------------------------------------------------------------
# extract_wrapped
# ------------------------------------------------------------------


class TestExtractWrapped:
    """GIVEN a descriptor object
    WHEN extract_wrapped is called
    THEN the original user function is returned.
    """

    def test_extract_wrapped_from_bound_property_returns_get(
        self,
    ) -> None:
        """GIVEN a bound_property descriptor
        WHEN extract_wrapped is called
        THEN the descriptor's __get__ is returned.
        """

        def func(_self: object) -> int:
            return 42

        desc = bound_property(func)

        assert extract_wrapped(desc).__func__ is desc.__get__.__func__

    def test_extract_wrapped_from_base_property_subclass_returns_call(
        self,
    ) -> None:
        """GIVEN a BaseProperty subclass (e.g., class_property)
        WHEN extract_wrapped is called
        THEN the descriptor's .call is returned.
        """

        def func(_self: type[object]) -> int:
            return 42

        desc = class_property(func)

        assert extract_wrapped(desc).__func__ is desc.call.__func__

    def test_extract_wrapped_from_builtin_property_returns_fget(
        self,
    ) -> None:
        """GIVEN a built-in property
        WHEN extract_wrapped is called
        THEN property.fget is returned.
        """

        def func(_self: object) -> int:
            return 42

        desc = property(func)

        assert extract_wrapped(desc) is desc.fget

    def test_extract_wrapped_from_cached_property_returns_func(
        self,
    ) -> None:
        """GIVEN a functools.cached_property
        WHEN extract_wrapped is called
        THEN cached_property.func is returned.
        """

        def func(_self: object) -> int:
            return 42

        desc = functools.cached_property(func)

        assert extract_wrapped(desc) is desc.func

    def test_extract_wrapped_raises_not_implemented_for_unsupported(
        self,
    ) -> None:
        """GIVEN an unsupported object
        WHEN extract_wrapped is called
        THEN NotImplementedError is raised with guidance.
        """
        with pytest.raises(NotImplementedError, match="couldn't extract"):
            extract_wrapped(42)


# ------------------------------------------------------------------
# parent_call
# ------------------------------------------------------------------


class TestParentCall:
    """GIVEN a descriptor hierarchy
    WHEN a child property uses with_parent
    THEN the parent result is injected as the second positional arg.
    """

    def test_parent_call_injects_parent_result_as_second_argument(
        self,
    ) -> None:
        """GIVEN a parent descriptor and a child override with with_parent
        WHEN the child is accessed on an instance
        THEN the child receives the parent's computed value.
        """

        class Parent:
            @bound_property
            def value(self) -> int:
                return 10

        class Child(Parent):
            @bound_property.with_parent
            def value(self, parent_result: int) -> int:
                return parent_result + 5

        instance = Child()

        assert instance.value == 10 + 5

    def test_parent_call_raises_recursion_error_on_infinite_loop(
        self,
    ) -> None:
        """GIVEN a parent and child both using with_parent on the same name
        WHEN the child is accessed
        THEN RecursionError is raised with a diagnostic message.
        """

        class Parent:
            @bound_property.with_parent
            def value(self, _parent: int) -> int:
                return 1

        class Child(Parent):
            @bound_property.with_parent
            def value(self, _parent: int) -> int:
                return 2

        instance = Child()

        with pytest.raises(RecursionError, match="couldn't reach parent"):
            _ = instance.value


# ------------------------------------------------------------------
# BaseProperty introspection
# ------------------------------------------------------------------


class TestBasePropertyIntrospection:
    """GIVEN a BaseProperty instance
    WHEN introspective attributes are accessed
    THEN they reflect the wrapped function and type.
    """

    def test_base_property_name_derives_from_function_name(self) -> None:
        """GIVEN a function with a known __name__
        WHEN a BaseProperty subclass is constructed
        THEN .name matches that __name__.
        """

        def compute(_self: object) -> int:
            return 42

        prop = bound_property(compute)

        assert prop.name == "compute"

    def test_base_property_is_data_true_when_set_or_delete_exists(
        self,
    ) -> None:
        """GIVEN a subclass that defines __set__
        WHEN .is_data is accessed
        THEN it is True.
        """

        class DataProp(BaseProperty[Any]):
            def __set__(self, _node: object, _value: object) -> None:
                pass

        prop = DataProp(lambda _self: 1)

        assert prop.is_data is True

    def test_base_property_title_raises_not_implemented(self) -> None:
        """GIVEN a direct BaseProperty instance
        WHEN .title is accessed
        THEN NotImplementedError is raised.
        """
        prop = BaseProperty(lambda _self: 1)

        with pytest.raises(NotImplementedError):
            _ = prop.title

    def test_base_property_header_uses_title_and_function(
        self,
    ) -> None:
        """GIVEN a BaseProperty subclass with a title
        WHEN .header is accessed
        THEN it contains the title and function repr.
        """

        def compute(_self: object) -> int:
            return 42

        prop = bound_property(compute)

        assert prop.title in prop.header
        assert "compute" in prop.header

    def test_base_property_header_fallback_on_exception(self) -> None:
        """GIVEN a function whose __repr__ raises during header formatting
        WHEN .header is accessed
        THEN the fallback format using Who.Is is returned.
        """

        class BadRepr:
            def __call__(self, _self: object) -> int:
                return 1

            def __repr__(self) -> str:
                raise RuntimeError("bad repr")

        prop = bound_property(BadRepr())
        header = prop.header

        # Fallback path uses Who.Is(self.function), not ascii repr.
        assert "RuntimeError" not in header
        assert Who.Is(prop.function) in header

    def test_base_property_str_contains_header(self) -> None:
        """GIVEN a BaseProperty subclass
        WHEN str() is called
        THEN it contains the header within angle brackets.
        """
        prop = bound_property(lambda _self: 1)

        assert prop.header in str(prop)
        assert str(prop).startswith("<")
        assert str(prop).endswith(">")

    def test_base_property_repr_contains_title(self) -> None:
        """GIVEN a BaseProperty subclass
        WHEN repr() is called
        THEN it contains the title within angle brackets.
        """
        prop = bound_property(lambda _self: 1)

        assert prop.title in repr(prop)

    def test_base_property_footer_formats_node_context(self) -> None:
        """GIVEN an instance node
        WHEN footer() is called
        THEN it contains 'instance' and the node's address.
        """
        prop = bound_property(lambda _self: 1)
        node = object()

        footer = prop.footer(node)

        assert "instance" in footer
        assert f"#{id(node):x}" in footer


# ------------------------------------------------------------------
# bound_property behavior
# ------------------------------------------------------------------


class TestBoundProperty:
    """GIVEN a bound_property attached to a class
    WHEN accessed on instances or the class
    THEN it computes, caches, and guards appropriately.
    """

    def test_bound_property_computes_value_on_first_access(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a fresh instance
        WHEN the descriptor is accessed
        THEN the function is called and the result is returned.
        """
        expected = fake.pyint()

        class Sample:
            attr = bound_property(lambda _self: expected)

        instance = Sample()

        assert instance.attr == expected

    def test_bound_property_uses_dict_cache_on_subsequent_access(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a descriptor that has already been accessed
        WHEN accessed again
        THEN the cached value from __dict__ is returned.
        """
        counter = 0

        def compute(_self: object) -> int:
            return counter + 1

        class Sample:
            attr = bound_property(compute)

        instance = Sample()
        first = instance.attr
        second = instance.attr

        assert first == second
        assert compute.__name__ in instance.__dict__

    def test_bound_property_on_class_access_raises_context_fault(
        self,
    ) -> None:
        """GIVEN class-level access (node is None)
        WHEN the descriptor is accessed on the class
        THEN ContextFaultError is raised.
        """

        class Sample:
            attr = bound_property(lambda _self: 1)

        with pytest.raises(ContextFaultError):
            _ = Sample.attr

    def test_bound_property_delete_raises_read_only_error(self) -> None:
        """GIVEN an instance with a cached value
        WHEN del is used on the descriptor
        THEN ReadOnlyError is raised.
        """

        class Sample:
            attr = bound_property(lambda _self: 1)

        instance = Sample()
        _ = instance.attr  # populate cache

        with pytest.raises(ReadOnlyError):
            del instance.attr

    def test_bound_property_rejects_coroutine_function(self) -> None:
        """GIVEN an async function
        WHEN it is passed to bound_property
        THEN TypeError is raised with a message about coroutine functions.
        """

        async def coro(_self: object) -> int:
            return 1

        with pytest.raises(TypeError, match="coroutine function"):
            bound_property(coro)

    def test_bound_property_on_object_without_dict_raises_type_error(
        self,
    ) -> None:
        """GIVEN an object lacking __dict__
        WHEN the descriptor's __get__ is invoked with that object
        THEN TypeError is raised.
        """

        class Sample:
            attr = bound_property(lambda _self: 1)

        descriptor = Sample.__dict__["attr"]

        with pytest.raises(TypeError, match="has no __dict__"):
            descriptor.__get__(object(), Sample)

    def test_bound_property_header_with_context_contains_mode(
        self,
    ) -> None:
        """GIVEN an error triggered by class access
        WHEN ContextFaultError is raised
        THEN the message contains the 'class' context mode.
        """

        class Sample:
            attr = bound_property(lambda _self: 1)

        with pytest.raises(ContextFaultError, match="class"):
            _ = Sample.attr


class TestAnnotationInference:
    """Verify type-parameter preservation on primitive descriptors."""

    def test_bound_property_is_generic(self) -> None:
        """
        Given: a bound_property wrapping a function
        When: inspecting its type origin
        Then: it is a subclass of Generic.
        """

        def sample(_self: object) -> int:
            return 1

        prop = bound_property(sample)
        assert hasattr(type(prop), "__orig_bases__")

    def test_base_property_subclass_preserves_return_annotation(
        self,
    ) -> None:
        """
        Given: a custom subclass of BaseProperty
        When: wrapping an annotated function
        Then: the function annotation is preserved.
        """

        class CustomProp(BaseProperty):
            def title(self) -> str:  # type: ignore[assignment][override]
                return "custom"

            def header_with_context(self, node: object) -> str:
                return "ctx"

        def sample(_node: object) -> int:
            return 1

        prop = CustomProp(sample)
        assert prop.function is sample

    def test_extract_wrapped_return_type_is_callable(self) -> None:
        """
        Given: a bound_property descriptor
        When: extract_wrapped is called
        Then: result is callable.
        """

        def sample(_self: object) -> int:
            return 1

        prop = bound_property(sample)
        unwrapped = extract_wrapped(prop)
        assert callable(unwrapped)

    def test_parent_call_returns_callable(self) -> None:
        """
        Given: any function
        When: wrapped with parent_call
        Then: result is callable.
        """

        def sample(_node: object, _parent: int) -> int:
            return 1

        wrapped = parent_call(sample)
        assert callable(wrapped)


class TestInheritanceContract:
    """Verify bound_property inherits BaseProperty surface completely."""

    def test_inherits_name_property(self) -> None:
        """
        Given: a bound_property instance
        WHEN: accessing .name
        THEN: it derives from BaseProperty.
        """

        def sample(_node: object) -> int:
            return 1

        prop = bound_property(sample)
        assert prop.name == "sample"

    def test_inherits_is_data_property(self) -> None:
        """
        Given: a bound_property instance
        WHEN: accessing .is_data
        THEN: it is True because __delete__ is defined.
        """

        def sample(_node: object) -> int:
            return 1

        prop = bound_property(sample)
        assert prop.is_data is True

    def test_inherits_str_and_repr(self) -> None:
        """
        Given: a bound_property instance
        WHEN: converting to str/repr
        THEN: they contain expected fragments.
        """

        def sample(_node: object) -> int:
            return 1

        prop = bound_property(sample)
        assert "sample" in str(prop)
        assert "bound_property" in repr(prop).lower()

    def test_inherits_header_with_context(self) -> None:
        """
        Given: a bound_property instance
        WHEN: calling header_with_context with an instance
        THEN: footer-derived string is returned.
        """

        def sample(_node: object) -> int:
            return 1

        prop = bound_property(sample)
        ctx = prop.header_with_context(object())
        assert "instance" in ctx

    def test_inherits_footer_with_none_node(self) -> None:
        """
        Given: a bound_property instance
        WHEN: calling footer with None
        THEN: mode stays "undefined".
        """

        def sample(_node: object) -> int:
            return 1

        prop = bound_property(sample)
        foot = prop.footer(None)
        assert "undefined" in foot

    def test_inherits_call_raises_not_implemented_on_base(self) -> None:
        """
        Given: a raw BaseProperty instance
        WHEN: calling .call directly
        THEN: NotImplementedError is raised.
        """

        class Raw(BaseProperty):
            def title(self) -> str:  # type: ignore[assignment][override]
                return "raw"

            def header_with_context(self, node: object) -> str:
                return "ctx"

        prop = Raw(lambda: 1)
        with pytest.raises(NotImplementedError):
            prop.call(object())

    def test_bound_property_with_parent_factory(self) -> None:
        """
        Given: bound_property.with_parent
        WHEN: applied to a function
        THEN: a bound_property instance is returned.
        """

        def sample(_node: object, _parent: int) -> int:
            return 1

        prop = bound_property.with_parent(sample)
        assert isinstance(prop, bound_property)


class TestEdgeCases:
    """Paranoid edge-case coverage for primitives."""

    def test_attribute_exception_error_with_empty_message(self) -> None:
        """
        Given: an AttributeError with empty message
        WHEN: wrapped in AttributeExceptionError
        THEN: .message is empty string.
        """

        origin = AttributeError("")
        exc = AttributeExceptionError(origin)
        assert exc.message == ""

    def test_extract_wrapped_prefers_bound_property_over_baseproperty(
        self,
    ) -> None:
        """
        Given: a bound_property (subclass of BaseProperty)
        WHEN: extract_wrapped is called
        THEN: __get__ is returned (first match), not .call.
        """

        def sample(_self: object) -> int:
            return 1

        prop = bound_property(sample)
        unwrapped = extract_wrapped(prop)
        assert unwrapped.__func__ is prop.__get__.__func__

    def test_parent_call_with_missing_parent_raises_not_implemented(
        self,
    ) -> None:
        """
        Given: a class hierarchy with no parent descriptor
        WHEN: parent_call wrapper runs
        THEN: NotImplementedError is raised (extract_wrapped(None)).
        """

        def override(_node: object, _parent: int) -> int:
            return 1

        class Orphan:
            attr = bound_property(parent_call(override))

        instance = Orphan()
        with pytest.raises(NotImplementedError):
            _ = instance.attr

    def test_base_property_footer_with_class_node(self) -> None:
        """
        Given: a BaseProperty subclass
        WHEN: footer is called with a class node
        THEN: mode is "class".
        """

        class Sample(BaseProperty):
            @cached_property
            def title(self) -> str:
                return "sample"

            def header_with_context(self, node: object) -> str:
                return "ctx"

            @override
            def __repr__(self) -> str:
                return "<Sample>"

        prop = Sample(lambda: 1)
        foot = prop.footer(type)
        assert "class" in foot
