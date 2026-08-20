"""Granular unit tests for kapro.primitives."""

from __future__ import annotations

from functools import cached_property as stdlib_cached_property

import pytest

from kapro.primitives import (
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


class TestExceptions:
    """Granular tests for the exception hierarchy."""

    def test_property_error_is_base_exception(self) -> None:
        assert issubclass(PropertyError, Exception)

    def test_context_fault_error_inheritance(self) -> None:
        assert issubclass(ContextFaultError, PropertyError)
        assert issubclass(ContextFaultError, Exception)

    def test_read_only_error_inheritance(self) -> None:
        assert issubclass(ReadOnlyError, PropertyError)
        assert issubclass(ReadOnlyError, Exception)

    def test_attribute_exception_inheritance(self) -> None:
        assert issubclass(AttributeExceptionError, PropertyError)
        assert issubclass(AttributeExceptionError, Exception)

    def test_attribute_exception_stores_origin(self) -> None:
        origin = AttributeError("foo")
        exc = AttributeExceptionError(origin)
        assert exc.exception is origin

    def test_attribute_exception_message_from_colon(self) -> None:
        origin = AttributeError("module: something went wrong")
        exc = AttributeExceptionError(origin)
        assert exc.message == " something went wrong"

    def test_attribute_exception_message_without_colon(self) -> None:
        origin = AttributeError("no colon here")
        exc = AttributeExceptionError(origin)
        assert exc.message == "no colon here"

    def test_attribute_exception_message_accesses_cached_property(
        self,
    ) -> None:
        origin = AttributeError("test")
        exc = AttributeExceptionError(origin)
        # message is a cached_property; first access computes it
        assert exc.message == "test"
        # second access returns cached value
        assert exc.message == "test"

    def test_attribute_exception_str_is_message(self) -> None:
        origin = AttributeError("split: here")
        exc = AttributeExceptionError(origin)
        assert str(exc) == " here"


class TestNothing:
    """Tests for the module-level sentinel."""

    def test_nothing_is_missing_instance(self) -> None:
        from kain.classes import Missing

        assert isinstance(Nothing, Missing)

    def test_nothing_is_falsy(self) -> None:
        assert bool(Nothing) is False

    def test_nothing_never_equals_itself(self) -> None:
        assert Nothing is Nothing  # identity yes
        assert (Nothing == Nothing) is False  # equality no


class TestExtractWrapped:
    """Granular tests for extract_wrapped()."""

    def test_from_bound_property(self) -> None:
        class Foo:
            @bound_property
            def prop(self) -> int:
                return 42

        # Access descriptor from __dict__ to avoid triggering __get__
        wrapped = extract_wrapped(Foo.__dict__["prop"])
        # __get__ is a bound method; equality check is sufficient
        assert wrapped == Foo.__dict__["prop"].__get__

    def test_from_base_property_subclass_with_call(self) -> None:
        class DummyProp(BaseProperty):
            def call(self, node: object) -> str:
                return "dummy"

        desc = DummyProp(lambda: 42)
        wrapped = extract_wrapped(desc)
        assert wrapped == desc.call
        assert wrapped(None) == "dummy"

    def test_from_builtin_property(self) -> None:
        class Foo:
            @property
            def prop(self) -> int:
                return 42

        wrapped = extract_wrapped(Foo.prop)
        assert wrapped is Foo.prop.fget

    def test_from_cached_property(self) -> None:
        class Foo:
            @stdlib_cached_property
            def prop(self) -> int:
                return 42

        wrapped = extract_wrapped(Foo.prop)
        assert wrapped is Foo.prop.func

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(NotImplementedError) as exc_info:
            extract_wrapped("not a descriptor")
        assert "couldn't extract wrapped function" in str(exc_info.value)

    def test_error_message_contains_descriptor_type(self) -> None:
        with pytest.raises(NotImplementedError) as exc_info:
            extract_wrapped(12345)
        msg = str(exc_info.value)
        assert "couldn't extract wrapped function" in msg
        assert "@property" in msg
        assert "@cached_property" in msg
        assert "bound_property" in msg
        assert "BaseProperty" in msg


class TestParentCall:
    """Granular tests for parent_call() and with_parent()."""

    def test_basic_override_index_zero(self) -> None:
        """Child overrides the property; index=0 finds immediate parent."""

        class Parent:
            counter = 0

            @bound_property
            def prop(self) -> int:
                Parent.counter += 1
                return 10

        def override(self, parent: int, *a: object, **k: object) -> int:
            return parent + 5

        override.__name__ = "prop"
        wrapped = parent_call(override)

        class Child(Parent):
            prop = bound_property(wrapped)

        obj = Child()
        assert obj.prop == 15
        assert Parent.counter == 1

    def test_inherited_without_override_index_one(self) -> None:
        """Child inherits without override; index=1 skips inherited copy."""

        class GrandParent:
            counter = 0

            @bound_property
            def prop(self) -> int:
                GrandParent.counter += 1
                return 100

        class Parent(GrandParent):
            pass

        def override(self, parent: int, *a: object, **k: object) -> int:
            return parent + 1

        override.__name__ = "prop"
        wrapped = parent_call(override)

        class Child(Parent):
            prop = bound_property(wrapped)

        obj = Child()
        assert obj.prop == 101
        assert GrandParent.counter == 1

    def test_args_and_kwargs_forwarding(self) -> None:
        # Use a BaseProperty subclass for the parent so that ``call``
        # accepts *args, **kw (extract_wrapped returns ``call`` for
        # BaseProperty subclasses, whereas bound_property returns ``__get__``
        # which does not accept extra arguments).
        class ParentProp(BaseProperty):
            @property
            def title(self) -> str:
                return "parent_prop"

            def header_with_context(self, node: object) -> str:
                return "ctx"

            def call(self, node: object, *args: object, **kw: object) -> str:
                extra = kw.pop("extra", "")
                return f"parent{extra}"

        class Parent:
            prop = ParentProp(lambda: None)

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
        # Test parent_call in isolation — it forwards *args, **kw to
        # the parent descriptor's ``call`` method.
        result = wrapped(obj, "_child", prefix=">")
        assert result == ">parent_child"

    def test_no_parent_descriptor_raises_not_implemented(self) -> None:
        def override(self: object, parent: object) -> object:
            return parent

        override.__name__ = "prop"
        wrapped = parent_call(override)

        class Orphan:
            prop = bound_property(wrapped)

        obj = Orphan()
        with pytest.raises(NotImplementedError):
            obj.prop

    def test_with_parent_returns_instance(self) -> None:
        class MyProp(BaseProperty):
            @property
            def title(self) -> str:
                return "my"

            def header_with_context(self, node: object) -> str:
                return "ctx"

        desc = MyProp.with_parent(lambda self, parent: parent + 1)
        assert isinstance(desc, MyProp)

    def test_with_parent_wraps_function(self) -> None:
        class Parent:
            @bound_property
            def prop(self) -> int:
                return 7

        def override(self: object, parent: int) -> int:
            return parent * 2

        override.__name__ = "prop"

        class Child(Parent):
            prop = bound_property.with_parent(override)

        obj = Child()
        assert obj.prop == 14

    def test_parent_call_preserves_function_name(self) -> None:
        def override(self, parent: int) -> int:
            return parent

        wrapped = parent_call(override)
        assert wrapped.__name__ == "override"


class TestBaseProperty:
    """Granular tests for BaseProperty introspection and formatting."""

    def test_name_from_function(self) -> None:
        def my_func() -> int:
            return 42

        class Dummy(BaseProperty):
            @property
            def title(self) -> str:
                return "dummy"

            def header_with_context(self, node: object) -> str:
                return "ctx"

        desc = Dummy(my_func)
        assert desc.name == "my_func"

    def test_is_data_true_when_set_defined(self) -> None:
        class DataDesc(BaseProperty):
            @property
            def title(self) -> str:
                return "data"

            def header_with_context(self, node: object) -> str:
                return "ctx"

            def __set__(self, node: object, value: object) -> None:
                pass

        desc = DataDesc(lambda: 1)
        assert desc.is_data is True

    def test_is_data_true_when_delete_defined(self) -> None:
        class DataDesc(BaseProperty):
            @property
            def title(self) -> str:
                return "data"

            def header_with_context(self, node: object) -> str:
                return "ctx"

            def __delete__(self, node: object) -> None:
                pass

        desc = DataDesc(lambda: 1)
        assert desc.is_data is True

    def test_is_data_false_without_set_or_delete(self) -> None:
        class NonData(BaseProperty):
            @property
            def title(self) -> str:
                return "nondata"

            def header_with_context(self, node: object) -> str:
                return "ctx"

        desc = NonData(lambda: 1)
        assert desc.is_data is False

    def test_title_abstract_raises(self) -> None:
        desc = BaseProperty(lambda: 1)
        with pytest.raises(NotImplementedError):
            _ = desc.title

    def test_header_with_context_abstract_raises(self) -> None:
        desc = BaseProperty(lambda: 1)
        with pytest.raises(NotImplementedError):
            desc.header_with_context(None)

    def test_header_uses_quoted_repr(self) -> None:
        class Dummy(BaseProperty):
            @property
            def title(self) -> str:
                return "dummy"

            def header_with_context(self, node: object) -> str:
                return "ctx"

        def fn() -> int:
            return 42

        desc = Dummy(fn)
        assert "dummy(" in desc.header
        assert "fn" in desc.header

    def test_header_fallback_on_repr_error(self) -> None:
        class BadFunc:
            def __repr__(self) -> str:
                raise RuntimeError("boom")

        class Dummy(BaseProperty):
            @property
            def title(self) -> str:
                return "dummy"

            def header_with_context(self, node: object) -> str:
                return "ctx"

        desc = Dummy(BadFunc())
        # Who.Is produces a fully-qualified name
        assert "BadFunc" in desc.header
        assert "dummy(" in desc.header

    def test_footer_auto_detects_instance(self) -> None:
        class Dummy(BaseProperty):
            @property
            def title(self) -> str:
                return "dummy"

            def header_with_context(self, node: object) -> str:
                return "ctx"

        obj = object()
        desc = Dummy(lambda: 1)
        footer = desc.footer(obj)
        assert "instance context" in footer

    def test_footer_auto_detects_class(self) -> None:
        class Dummy(BaseProperty):
            @property
            def title(self) -> str:
                return "dummy"

            def header_with_context(self, node: object) -> str:
                return "ctx"

        desc = Dummy(lambda: 1)
        footer = desc.footer(int)
        assert "class context" in footer

    def test_footer_preserves_custom_mode(self) -> None:
        class Dummy(BaseProperty):
            @property
            def title(self) -> str:
                return "dummy"

            def header_with_context(self, node: object) -> str:
                return "ctx"

        desc = Dummy(lambda: 1)
        footer = desc.footer(None, mode="custom")
        assert "custom context" in footer

    def test_str_contains_header(self) -> None:
        class Dummy(BaseProperty):
            @property
            def title(self) -> str:
                return "dummy"

            def header_with_context(self, node: object) -> str:
                return "ctx"

        desc = Dummy(lambda: 1)
        assert desc.header in str(desc)

    def test_repr_contains_title(self) -> None:
        class Dummy(BaseProperty):
            @property
            def title(self) -> str:
                return "dummy"

            def header_with_context(self, node: object) -> str:
                return "ctx"

        desc = Dummy(lambda: 1)
        assert "dummy" in repr(desc)


class TestBoundProperty:
    """Granular tests for bound_property descriptor protocol."""

    def test_rejects_coroutine_function(self) -> None:
        async def async_fn(self) -> int:
            return 42

        with pytest.raises(TypeError, match="coroutine function"):
            bound_property(async_fn)

    def test_get_computes_and_caches(self) -> None:
        counter = 0

        class Foo:
            @bound_property
            def prop(self) -> int:
                nonlocal counter
                counter += 1
                return 99

        obj = Foo()
        assert obj.prop == 99
        assert obj.prop == 99
        assert counter == 1
        assert obj.__dict__["prop"] == 99

    def test_get_raises_on_class_access(self) -> None:
        class Foo:
            @bound_property
            def prop(self) -> int:
                return 42

        with pytest.raises(ContextFaultError):
            _ = Foo.prop

    def test_delete_raises_read_only_error(self) -> None:
        class Foo:
            @bound_property
            def prop(self) -> int:
                return 42

        obj = Foo()
        assert obj.prop == 42
        with pytest.raises(ReadOnlyError):
            del obj.prop

    def test_title_contains_address(self) -> None:
        desc = bound_property(lambda self: 1)
        assert "instance just-replace descriptor" in desc.title

    def test_header_with_context_uses_footer(self) -> None:
        class Foo:
            @bound_property
            def prop(self) -> int:
                return 42

        desc = Foo.__dict__["prop"]
        ctx = desc.header_with_context(None)
        assert "called with" in ctx

    def test_caches_falsy_values(self) -> None:
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

    def test_instances_have_separate_caches(self) -> None:
        class Foo:
            counter = 0

            @bound_property
            def prop(self) -> int:
                Foo.counter += 1
                return Foo.counter

        a = Foo()
        b = Foo()
        assert a.prop == 1
        assert b.prop == 2
        assert a.prop == 1
        assert b.prop == 2

    def test_direct_get_with_none_node_raises(self) -> None:
        class Foo:
            @bound_property
            def prop(self) -> int:
                return 42

        with pytest.raises(ContextFaultError):
            Foo.prop.__get__(None, Foo)

    def test_direct_get_computes_value(self) -> None:
        class Foo:
            @bound_property
            def prop(self) -> int:
                return 42

        obj = Foo()
        desc = Foo.__dict__["prop"]
        assert desc.__get__(obj, Foo) == 42

    def test_name_matches_function_name(self) -> None:
        class Foo:
            @bound_property
            def my_prop(self) -> int:
                return 1

        assert Foo().my_prop
        assert Foo.__dict__["my_prop"].name == "my_prop"
