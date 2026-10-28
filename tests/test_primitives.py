"""Granular unit tests for zx.prop.primitives."""

from __future__ import annotations

from functools import cached_property as stdlib_cached_property
from typing import Any

import pytest
from faker import Faker

from zx.prop.primitives import (
    AttributeExceptionError,
    BaseProperty,
    ContextFaultError,
    Nothing,
    PropertyError,
    ReadOnlyError,
    bound_property,
    extract_wrapped,
    parent_call,
)


def _make_dummy(fake: Faker) -> tuple[Any, str, str]:
    """Build a BaseProperty subclass with fake title and context."""
    title = fake.word()
    context = fake.word()

    class Dummy(BaseProperty):
        @property
        def title(self) -> str:
            return title

        def header_with_context(self, node: object) -> str:
            return context

    return Dummy, title, context


def _make_data_desc(fake: Faker) -> tuple[Any, str, str]:
    """Build a data descriptor subclass with fake title and context."""
    title = fake.word()
    context = fake.word()

    class DataDesc(BaseProperty):
        @property
        def title(self) -> str:
            return title

        def header_with_context(self, node: object) -> str:
            return context

        def __set__(self, node: object, value: object) -> None:
            pass

    return DataDesc, title, context


def _make_deletable_desc(fake: Faker) -> tuple[Any, str, str]:
    """Build a data descriptor subclass defining __delete__."""
    title = fake.word()
    context = fake.word()

    class DeletableDesc(BaseProperty):
        @property
        def title(self) -> str:
            return title

        def header_with_context(self, node: object) -> str:
            return context

        def __delete__(self, node: object) -> None:
            pass

    return DeletableDesc, title, context


def _make_non_data(fake: Faker) -> tuple[Any, str, str]:
    """Build a non-data BaseProperty subclass with fake title/context."""
    title = fake.word()
    context = fake.word()

    class NonData(BaseProperty):
        @property
        def title(self) -> str:
            return title

        def header_with_context(self, node: object) -> str:
            return context

    return NonData, title, context


class TestExceptions:
    """Granular tests for the exception hierarchy."""

    def test_property_error_is_base_exception(self) -> None:
        """GIVEN PropertyError
        WHEN checked against Exception
        THEN it is a subclass.
        """
        assert issubclass(PropertyError, Exception)

    def test_context_fault_error_inheritance(self) -> None:
        """GIVEN ContextFaultError
        WHEN checked against the hierarchy
        THEN it inherits from PropertyError and Exception.
        """
        assert issubclass(ContextFaultError, PropertyError)
        assert issubclass(ContextFaultError, Exception)

    def test_read_only_error_inheritance(self) -> None:
        """GIVEN ReadOnlyError
        WHEN checked against the hierarchy
        THEN it inherits from PropertyError and Exception.
        """
        assert issubclass(ReadOnlyError, PropertyError)
        assert issubclass(ReadOnlyError, Exception)

    def test_attribute_exception_inheritance(self) -> None:
        """GIVEN AttributeExceptionError
        WHEN checked against the hierarchy
        THEN it inherits from PropertyError and Exception.
        """
        assert issubclass(AttributeExceptionError, PropertyError)
        assert issubclass(AttributeExceptionError, Exception)

    def test_attribute_exception_stores_origin(self, fake: Faker) -> None:
        """GIVEN an AttributeExceptionError
        WHEN created from an AttributeError
        THEN the original exception is preserved.
        """
        message = fake.pystr()
        origin = AttributeError(message)
        exc = AttributeExceptionError(origin)
        assert exc.exception is origin

    def test_attribute_exception_message_from_colon(self, fake: Faker) -> None:
        """GIVEN an AttributeError with a colon
        WHEN wrapped in AttributeExceptionError
        THEN the message is split after the colon.
        """
        prefix = fake.word()
        suffix = fake.pystr()
        origin = AttributeError(f"{prefix}: {suffix}")
        exc = AttributeExceptionError(origin)
        assert exc.message == f" {suffix}"

    def test_attribute_exception_message_no_colon(self, fake: Faker) -> None:
        """GIVEN an AttributeError without a colon
        WHEN wrapped in AttributeExceptionError
        THEN the message is kept as-is.
        """
        message = fake.pystr()
        origin = AttributeError(message)
        exc = AttributeExceptionError(origin)
        assert exc.message == message

    def test_attribute_exception_message_accesses_cached_property(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN an AttributeExceptionError
        WHEN its message is accessed twice
        THEN the value is computed once and cached.
        """
        message = fake.pystr()
        origin = AttributeError(message)
        exc = AttributeExceptionError(origin)
        assert exc.message == message
        assert exc.message == message

    def test_attribute_exception_str_is_message(self, fake: Faker) -> None:
        """GIVEN an AttributeError with a colon
        WHEN wrapped and stringified
        THEN the suffix is returned.
        """
        prefix = fake.word()
        suffix = fake.pystr()
        origin = AttributeError(f"{prefix}: {suffix}")
        exc = AttributeExceptionError(origin)
        assert str(exc) == f" {suffix}"


class TestNothing:
    """Tests for the module-level sentinel."""

    def test_nothing_is_missing_instance(self) -> None:
        """GIVEN Nothing
        WHEN checked against zx.core.classes.Missing
        THEN it is an instance.
        """
        from zx.core.classes import Missing

        assert isinstance(Nothing, Missing)

    def test_nothing_is_falsy(self) -> None:
        """GIVEN Nothing
        WHEN converted to bool
        THEN it is False.
        """
        assert bool(Nothing) is False

    def test_nothing_never_equals_itself(self) -> None:
        """GIVEN Nothing
        WHEN compared with ==
        THEN it is never equal, even to itself.
        """
        assert Nothing is Nothing  # identity yes
        assert (Nothing == Nothing) is False  # equality no


class TestExtractWrapped:
    """Granular tests for extract_wrapped()."""

    def test_from_bound_property(self, fake: Faker) -> None:
        """GIVEN a bound_property
        WHEN extract_wrapped is called
        THEN the wrapped __get__ is returned.
        """

        class Foo:
            @bound_property
            def prop(self) -> int:
                return fake.pyint()

        wrapped = extract_wrapped(Foo.__dict__["prop"])
        assert wrapped == Foo.__dict__["prop"].__get__

    def test_from_base_property_subclass_with_call(self, fake: Faker) -> None:
        """GIVEN a BaseProperty subclass with call
        WHEN extract_wrapped is called
        THEN the call method is returned and works.
        """
        label = fake.pystr()

        class DummyProp(BaseProperty):
            def call(self, node: object) -> str:
                return label

        def func() -> int:
            return fake.pyint()

        desc = DummyProp(func)
        wrapped = extract_wrapped(desc)
        assert wrapped == desc.call
        assert wrapped(None) == label

    def test_from_builtin_property(self, fake: Faker) -> None:
        """GIVEN a builtin property
        WHEN extract_wrapped is called
        THEN fget is returned.
        """
        value = fake.pyint()

        class Foo:
            @property
            def prop(self) -> int:
                return value

        wrapped = extract_wrapped(Foo.prop)
        assert wrapped is Foo.prop.fget

    def test_from_cached_property(self, fake: Faker) -> None:
        """GIVEN a stdlib cached_property
        WHEN extract_wrapped is called
        THEN the underlying function is returned.
        """
        value = fake.pyint()

        class Foo:
            @stdlib_cached_property
            def prop(self) -> int:
                return value

        wrapped = extract_wrapped(Foo.prop)
        assert wrapped is Foo.prop.func

    def test_unsupported_type_raises(self, fake: Faker) -> None:
        """GIVEN an unsupported descriptor type
        WHEN extract_wrapped is called
        THEN NotImplementedError is raised with a helpful message.
        """
        with pytest.raises(NotImplementedError) as exc_info:
            extract_wrapped(fake.word())
        assert "couldn't extract wrapped function" in str(exc_info.value)

    def test_error_message_contains_descriptor_type(self, fake: Faker) -> None:
        """GIVEN an unsupported descriptor type
        WHEN extract_wrapped raises
        THEN the error message lists supported descriptor types.
        """
        with pytest.raises(NotImplementedError) as exc_info:
            extract_wrapped(fake.pyint())
        msg = str(exc_info.value)
        assert "couldn't extract wrapped function" in msg
        assert "@property" in msg
        assert "@cached_property" in msg
        assert "bound_property" in msg
        assert "BaseProperty" in msg


class TestParentCall:
    """Granular tests for parent_call() and with_parent()."""

    def test_basic_override_index_zero(self, fake: Faker) -> None:
        """GIVEN a child that overrides a bound_property
        WHEN parent_call resolves the immediate parent
        THEN the parent value is injected and computed once.
        """
        parent_value = fake.pyint()
        offset = fake.pyint()

        class Parent:
            counter = 0

            @bound_property
            def prop(self) -> int:
                Parent.counter += 1
                return parent_value

        def override(self: object, parent: int) -> int:
            return parent + offset

        override.__name__ = "prop"
        wrapped = parent_call(override)

        class Child(Parent):
            prop = bound_property(wrapped)

        obj = Child()
        assert obj.prop == parent_value + offset
        assert Parent.counter == 1

    def test_inherited_without_override_index_one(self, fake: Faker) -> None:
        """GIVEN a child that inherits without overriding
        WHEN parent_call resolves the grandparent
        THEN it skips the inherited copy and uses the original.
        """
        parent_value = fake.pyint()
        offset = fake.pyint()

        class GrandParent:
            counter = 0

            @bound_property
            def prop(self) -> int:
                GrandParent.counter += 1
                return parent_value

        class Parent(GrandParent):
            pass

        def override(self: object, parent: int) -> int:
            return parent + offset

        override.__name__ = "prop"
        wrapped = parent_call(override)

        class Child(Parent):
            prop = bound_property(wrapped)

        obj = Child()
        assert obj.prop == parent_value + offset
        assert GrandParent.counter == 1

    def test_args_and_kwargs_forwarding(self, fake: Faker) -> None:
        """GIVEN a parent descriptor accepting extra arguments
        WHEN parent_call forwards *args and **kw
        THEN they reach the parent implementation.
        """
        # Use a BaseProperty subclass for the parent so that ``call``
        # accepts *args, **kw (extract_wrapped returns ``call`` for
        # BaseProperty subclasses, whereas bound_property returns ``__get__``
        # which does not accept extra arguments).
        title = fake.word()
        context = fake.word()
        parent_label = fake.word()
        prefix = fake.word()
        suffix = fake.word()

        class ParentProp(BaseProperty):
            @property
            def title(self) -> str:
                return title

            def header_with_context(self, node: object) -> str:
                return context

            def call(self, node: object, *args: object, **kw: object) -> str:
                return parent_label

        def func() -> None:
            return None

        class Parent:
            prop = ParentProp(func)

        def override(
            self: object,
            parent: str,
            suffix: str,
            prefix: str = "",
        ) -> str:
            return f"{prefix}{parent}{suffix}"

        override.__name__ = "prop"
        wrapped = parent_call(override)

        class Child(Parent):
            prop = bound_property(wrapped)

        obj = Child()
        result = wrapped(obj, f"_{suffix}", prefix=f"{prefix}_")
        assert result == f"{prefix}_{parent_label}_{suffix}"

    def test_no_parent_descriptor_raises_not_implemented(self) -> None:
        """GIVEN an orphan override with no parent descriptor
        WHEN accessed
        THEN NotImplementedError is raised.
        """

        def override(self: object, parent: object) -> object:
            return parent

        override.__name__ = "prop"
        wrapped = parent_call(override)

        class Orphan:
            prop = bound_property(wrapped)

        obj = Orphan()
        with pytest.raises(NotImplementedError):
            obj.prop

    def test_with_parent_returns_instance(self, fake: Faker) -> None:
        """GIVEN BaseProperty.with_parent
        WHEN used as a classmethod factory
        THEN it returns a descriptor instance.
        """
        title = fake.word()
        context = fake.word()

        class MyProp(BaseProperty):
            @property
            def title(self) -> str:
                return title

            def header_with_context(self, node: object) -> str:
                return context

        def override(self: object, parent: int) -> int:
            return parent + 1

        desc = MyProp.with_parent(override)
        assert isinstance(desc, MyProp)

    def test_with_parent_wraps_function(self, fake: Faker) -> None:
        """GIVEN a parent bound_property
        WHEN a child uses bound_property.with_parent
        THEN the parent value is injected.
        """
        parent_value = fake.pyint()

        class Parent:
            @bound_property
            def prop(self) -> int:
                return parent_value

        def override(self: object, parent: int) -> int:
            return parent * 2

        override.__name__ = "prop"

        class Child(Parent):
            prop = bound_property.with_parent(override)

        obj = Child()
        assert obj.prop == parent_value * 2

    def test_parent_call_preserves_function_name(self) -> None:
        """GIVEN a function wrapped by parent_call
        WHEN its __name__ is checked
        THEN the original name is preserved.
        """

        def override(self: object, parent: int) -> int:
            return parent

        wrapped = parent_call(override)
        assert wrapped.__name__ == "override"


class TestBaseProperty:
    """Granular tests for BaseProperty introspection and formatting."""

    def test_name_from_function(self, fake: Faker) -> None:
        """GIVEN a BaseProperty subclass
        WHEN initialized with a function
        THEN its name matches the function name.
        """

        def my_func() -> int:
            return fake.pyint()

        dummy_cls, _title, _context = _make_dummy(fake)
        desc = dummy_cls(my_func)
        assert desc.name == "my_func"

    def test_is_data_true_when_set_defined(self, fake: Faker) -> None:
        """GIVEN a BaseProperty subclass defining __set__
        WHEN is_data is checked
        THEN it reports True.
        """
        data_desc_cls, _title, _context = _make_data_desc(fake)

        def func() -> int:
            return fake.pyint()

        desc = data_desc_cls(func)
        assert desc.is_data is True

    def test_is_data_true_when_delete_defined(self, fake: Faker) -> None:
        """GIVEN a BaseProperty subclass defining __delete__
        WHEN is_data is checked
        THEN it reports True.
        """
        deletable_desc_cls, _title, _context = _make_deletable_desc(fake)

        def func() -> int:
            return fake.pyint()

        desc = deletable_desc_cls(func)
        assert desc.is_data is True

    def test_is_data_false_without_set_or_delete(self, fake: Faker) -> None:
        """GIVEN a BaseProperty subclass without __set__ or __delete__
        WHEN is_data is checked
        THEN it reports False.
        """
        non_data_cls, _title, _context = _make_non_data(fake)

        def func() -> int:
            return fake.pyint()

        desc = non_data_cls(func)
        assert desc.is_data is False

    def test_title_abstract_raises(self, fake: Faker) -> None:
        """GIVEN a raw BaseProperty
        WHEN its title is read
        THEN NotImplementedError is raised.
        """

        def func() -> int:
            return fake.pyint()

        desc = BaseProperty(func)
        with pytest.raises(NotImplementedError):
            _ = desc.title

    def test_header_with_context_abstract_raises(self, fake: Faker) -> None:
        """GIVEN a raw BaseProperty
        WHEN header_with_context is called
        THEN NotImplementedError is raised.
        """

        def func() -> int:
            return fake.pyint()

        desc = BaseProperty(func)
        with pytest.raises(NotImplementedError):
            desc.header_with_context(None)

    def test_header_uses_quoted_repr(self, fake: Faker) -> None:
        """GIVEN a BaseProperty subclass
        WHEN its header is read
        THEN it includes the title and function name.
        """
        dummy_cls, title, _context = _make_dummy(fake)

        def fn() -> int:
            return fake.pyint()

        desc = dummy_cls(fn)
        assert f"{title}(" in desc.header
        assert "fn" in desc.header

    def test_header_fallback_on_repr_error(self, fake: Faker) -> None:
        """GIVEN a function whose __repr__ raises
        WHEN the header is read
        THEN it falls back to Who.Is naming.
        """
        dummy_cls, title, _context = _make_dummy(fake)
        error_message = fake.pystr()

        class BadFunc:
            def __repr__(self) -> str:
                raise RuntimeError(error_message)

        desc = dummy_cls(BadFunc())
        assert "BadFunc" in desc.header
        assert f"{title}(" in desc.header

    def test_footer_auto_detects_instance(self, fake: Faker) -> None:
        """GIVEN a BaseProperty subclass
        WHEN footer is called with an instance
        THEN it reports instance context.
        """
        dummy_cls, _title, _context = _make_dummy(fake)

        def func() -> int:
            return fake.pyint()

        obj = object()
        desc = dummy_cls(func)
        footer = desc.footer(obj)
        assert "instance context" in footer

    def test_footer_auto_detects_class(self, fake: Faker) -> None:
        """GIVEN a BaseProperty subclass
        WHEN footer is called with a class
        THEN it reports class context.
        """
        dummy_cls, _title, _context = _make_dummy(fake)

        def func() -> int:
            return fake.pyint()

        desc = dummy_cls(func)
        footer = desc.footer(int)
        assert "class context" in footer

    def test_footer_preserves_custom_mode(self, fake: Faker) -> None:
        """GIVEN a BaseProperty subclass
        WHEN footer is called with an explicit mode
        THEN that mode is preserved.
        """
        dummy_cls, _title, _context = _make_dummy(fake)

        def func() -> int:
            return fake.pyint()

        desc = dummy_cls(func)
        footer = desc.footer(None, mode="custom")
        assert "custom context" in footer

    def test_str_contains_header(self, fake: Faker) -> None:
        """GIVEN a BaseProperty subclass
        WHEN str() is called
        THEN it contains the header.
        """
        dummy_cls, _title, _context = _make_dummy(fake)

        def func() -> int:
            return fake.pyint()

        desc = dummy_cls(func)
        assert desc.header in str(desc)

    def test_repr_contains_title(self, fake: Faker) -> None:
        """GIVEN a BaseProperty subclass
        WHEN repr() is called
        THEN it contains the title.
        """
        dummy_cls, title, _context = _make_dummy(fake)

        def func() -> int:
            return fake.pyint()

        desc = dummy_cls(func)
        assert title in repr(desc)


class TestBoundProperty:
    """Granular tests for bound_property descriptor protocol."""

    def test_rejects_coroutine_function(self, fake: Faker) -> None:
        """GIVEN an async function
        WHEN used with bound_property
        THEN TypeError is raised.
        """

        async def async_fn(self) -> int:
            return fake.pyint()

        with pytest.raises(TypeError, match="coroutine function"):
            bound_property(async_fn)

    def test_get_computes_and_caches(self, fake: Faker) -> None:
        """GIVEN a bound_property
        WHEN accessed repeatedly
        THEN it computes once and caches in __dict__.
        """
        value = fake.pyint()
        counter = 0

        class Foo:
            @bound_property
            def prop(self) -> int:
                nonlocal counter
                counter += 1
                return value

        obj = Foo()
        assert obj.prop == value
        assert obj.prop == value
        assert counter == 1
        assert obj.__dict__["prop"] == value

    def test_get_raises_on_class_access(self, fake: Faker) -> None:
        """GIVEN a bound_property
        WHEN accessed on the class
        THEN ContextFaultError is raised.
        """

        class Foo:
            @bound_property
            def prop(self) -> int:
                return fake.pyint()

        with pytest.raises(ContextFaultError):
            _ = Foo.prop

    def test_delete_raises_read_only_error(self, fake: Faker) -> None:
        """GIVEN a bound_property with a cached value
        WHEN deleted
        THEN ReadOnlyError is raised.
        """

        class Foo:
            @bound_property
            def prop(self) -> int:
                return fake.pyint()

        obj = Foo()
        assert obj.prop == obj.__dict__["prop"]
        with pytest.raises(ReadOnlyError):
            del obj.prop

    def test_title_contains_address(self, fake: Faker) -> None:
        """GIVEN a bound_property descriptor
        WHEN its title is read
        THEN it contains the expected descriptor kind.
        """

        def func(self: object) -> int:
            return fake.pyint()

        desc = bound_property(func)
        assert "instance just-replace descriptor" in desc.title

    def test_header_with_context_uses_footer(self, fake: Faker) -> None:
        """GIVEN a bound_property
        WHEN header_with_context is called
        THEN it includes the footer text.
        """

        class Foo:
            @bound_property
            def prop(self) -> int:
                return fake.pyint()

        desc = Foo.__dict__["prop"]
        ctx = desc.header_with_context(None)
        assert "called with" in ctx

    def test_caches_falsy_values(self) -> None:
        """GIVEN a bound_property returning falsy values
        WHEN accessed repeatedly
        THEN they are cached correctly.
        """

        class Foo:
            counter = 0

            @bound_property
            def zero(self) -> int:
                Foo.counter += 1
                return 0

            @bound_property
            def empty(self) -> str:
                Foo.counter += 1
                return ""

            @bound_property
            def none_val(self) -> None:
                Foo.counter += 1

        obj = Foo()
        assert obj.zero == 0
        assert obj.zero == 0
        assert obj.empty == ""
        assert obj.empty == ""
        assert obj.none_val is None
        assert obj.none_val is None
        assert Foo.counter == 3

    def test_instances_have_separate_caches(self, fake: Faker) -> None:
        """GIVEN multiple instances with a bound_property
        WHEN each accesses the property
        THEN they have independent caches.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @bound_property
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

    def test_direct_get_with_none_node_raises(self, fake: Faker) -> None:
        """GIVEN a bound_property
        WHEN __get__ is called with None
        THEN ContextFaultError is raised.
        """

        class Foo:
            @bound_property
            def prop(self) -> int:
                return fake.pyint()

        with pytest.raises(ContextFaultError):
            Foo.prop.__get__(None, Foo)

    def test_direct_get_computes_value(self, fake: Faker) -> None:
        """GIVEN a bound_property
        WHEN __get__ is called directly
        THEN the value is computed.
        """
        value = fake.pyint()

        class Foo:
            @bound_property
            def prop(self) -> int:
                return value

        obj = Foo()
        desc = Foo.__dict__["prop"]
        assert desc.__get__(obj, Foo) == value

    def test_name_matches_function_name(self) -> None:
        """GIVEN a bound_property
        WHEN its name is read
        THEN it matches the decorated function name.
        """

        class Foo:
            @bound_property
            def my_prop(self) -> int:
                return 1

        assert Foo().my_prop
        assert Foo.__dict__["my_prop"].name == "my_prop"
