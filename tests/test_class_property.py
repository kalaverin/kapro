"""Granular unit tests for kapro.class_property module."""

from __future__ import annotations

from typing import Any

import pytest

from kapro.class_property import (
    class_property,
    mixed_property,
)
from kapro.primitives import ContextFaultError


class TestClassProperty:
    """Granular tests for class_property descriptor."""

    def test_instance_access_passes_class(self) -> None:
        class Foo:
            @class_property
            def prop(cls) -> str:
                return cls.__name__

        assert Foo().prop == "Foo"

    def test_class_access_passes_class(self) -> None:
        class Foo:
            @class_property
            def prop(cls) -> str:
                return cls.__name__

        assert Foo.prop == "Foo"

    def test_inheritance_passes_child_class(self) -> None:
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

    def test_title_contains_address(self) -> None:
        desc = class_property(lambda cls: 1)
        assert "class descriptor" in desc.title

    def test_header_with_context_uses_footer(self) -> None:
        class Foo:
            @class_property
            def prop(cls) -> int:
                return 42

        desc = Foo.__dict__["prop"]
        ctx = desc.header_with_context(Foo)
        assert "called with" in ctx

    def test_get_node_returns_owner(self) -> None:
        class Foo:
            @class_property
            def prop(cls) -> int:
                return 42

        desc = Foo.__dict__["prop"]
        assert desc.get_node(Foo) is Foo

    def test_get_node_raises_on_none(self) -> None:
        class Foo:
            @class_property
            def prop(cls) -> int:
                return 42

        desc = Foo.__dict__["prop"]
        with pytest.raises(ContextFaultError):
            desc.get_node(None)

    def test_get_node_raises_on_instance(self) -> None:
        class Foo:
            @class_property
            def prop(cls) -> int:
                return 42

        desc = Foo.__dict__["prop"]
        with pytest.raises(ContextFaultError):
            desc.get_node(Foo())

    def test_call_invokes_function(self) -> None:
        class Foo:
            counter = 0

            @class_property
            def prop(cls) -> int:
                Foo.counter += 1
                return Foo.counter

        desc = Foo.__dict__["prop"]
        assert desc.call(Foo) == 1
        assert desc.call(Foo) == 2

    def test_call_raises_attribute_exception(self) -> None:
        class Foo:
            @class_property
            def prop(cls) -> str:
                return cls.nonexistent.attr  # type: ignore[assignment][attr-defined]

        desc = Foo.__dict__["prop"]
        with pytest.raises(Exception, match=r".") as exc_info:
            desc.call(Foo)
        # AttributeExceptionError wraps AttributeError
        assert type(exc_info.value).__name__ in (
            "AttributeExceptionError",
            "AttributeError",
        )

    def test_direct_get_instance_and_class(self) -> None:
        class Foo:
            @class_property
            def prop(cls) -> str:
                return cls.__name__

        desc = Foo.__dict__["prop"]
        assert desc.__get__(Foo(), Foo) == "Foo"
        assert desc.__get__(None, Foo) == "Foo"

    def test_is_data_false(self) -> None:
        class Foo:
            @class_property
            def prop(cls) -> int:
                return 42

        assert Foo.__dict__["prop"].is_data is False

    def test_with_parent(self) -> None:
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
        # class_property is not cached, so each access re-evaluates parent_call
        assert Parent.counter == 2

    def test_mixin_get_node_resolves_owner(self) -> None:
        class Mixin:
            @class_property
            def prop(cls) -> str:
                return "mixin"

        class Concrete(Mixin):
            pass

        desc = Mixin.__dict__["prop"]
        # get_node should resolve owner; since prop is not in
        # Concrete.__dict__, get_owner returns Mixin
        assert desc.get_node(Concrete) is Mixin


class TestMixedProperty:
    """Granular tests for mixed_property descriptor."""

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

    def test_inheritance_passes_child(self) -> None:
        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                if isinstance(self_or_cls, type):
                    return self_or_cls.__name__
                return self_or_cls.__class__.__name__

        class Bar(Foo):
            pass

        assert Bar.prop == "Bar"
        assert Bar().prop == "Bar"

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

    def test_falsy_instance_gets_itself(self) -> None:
        """A falsy instance must still be passed to the mixed_property,
        not routed to the class because of `instance or klass`.
        """

        class Falsy:
            def __bool__(self) -> bool:
                return False

            @mixed_property
            def prop(self_or_cls: Any) -> Any:
                return self_or_cls

        obj = Falsy()
        assert obj.prop is obj

    def test_title_contains_address(self) -> None:
        desc = mixed_property(lambda x: 1)
        assert "mixed descriptor" in desc.title

    def test_header_with_context_uses_footer(self) -> None:
        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> int:
                return 42

        desc = Foo.__dict__["prop"]
        ctx = desc.header_with_context(Foo())
        assert "called with" in ctx
        assert "mixed" in ctx

    def test_get_node_returns_instance_for_instance(self) -> None:
        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> int:
                return 42

        obj = Foo()
        desc = Foo.__dict__["prop"]
        assert desc.get_node(obj) is obj

    def test_get_node_returns_owner_for_class(self) -> None:
        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> int:
                return 42

        desc = Foo.__dict__["prop"]
        assert desc.get_node(Foo) is Foo

    def test_get_node_raises_on_none(self) -> None:
        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> int:
                return 42

        desc = Foo.__dict__["prop"]
        with pytest.raises(ContextFaultError):
            desc.get_node(None)

    def test_call_invokes_function_with_instance(self) -> None:
        class Foo:
            counter = 0

            @mixed_property
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return Foo.counter

        desc = Foo.__dict__["prop"]
        obj = Foo()
        assert desc.call(obj) == 1
        assert desc.call(obj) == 2

    def test_call_invokes_function_with_class(self) -> None:
        class Foo:
            counter = 0

            @mixed_property
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return Foo.counter

        desc = Foo.__dict__["prop"]
        assert desc.call(Foo) == 1
        assert desc.call(Foo) == 2

    def test_call_raises_attribute_exception(self) -> None:
        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                return self_or_cls.nonexistent.attr  # type: ignore[assignment][attr-defined,union-attr]

        desc = Foo.__dict__["prop"]
        with pytest.raises(Exception, match=r".") as exc_info:
            desc.call(Foo())
        assert type(exc_info.value).__name__ in (
            "AttributeExceptionError",
            "AttributeError",
        )

    def test_direct_get_instance(self) -> None:
        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                return "instance"

        desc = Foo.__dict__["prop"]
        assert desc.__get__(Foo(), Foo) == "instance"

    def test_direct_get_class(self) -> None:
        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                return "class"

        desc = Foo.__dict__["prop"]
        assert desc.__get__(None, Foo) == "class"

    def test_is_data_false(self) -> None:
        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> int:
                return 42

        assert Foo.__dict__["prop"].is_data is False

    def test_with_parent(self) -> None:
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

    def test_mixin_get_node_resolves_owner_for_class(self) -> None:
        class Mixin:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                return "mixin"

        class Concrete(Mixin):
            pass

        desc = Mixin.__dict__["prop"]
        assert desc.get_node(Concrete) is Mixin

    def test_mixin_get_node_returns_instance_for_instance(self) -> None:
        class Mixin:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                return "mixin"

        class Concrete(Mixin):
            pass

        obj = Concrete()
        desc = Mixin.__dict__["prop"]
        assert desc.get_node(obj) is obj
