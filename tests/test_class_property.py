"""Granular unit tests for kapro.class_property module."""

from __future__ import annotations

from typing import Any

import pytest
from faker import Faker

from kapro.class_property import (
    class_property,
    mixed_property,
)
from kapro.primitives import (
    AttributeExceptionError,
    ContextFaultError,
)


class TestClassProperty:
    """Granular tests for class_property descriptor."""

    def test_instance_access_passes_class(self, fake: Faker) -> None:
        """GIVEN a class_property
        WHEN accessed on an instance repeatedly
        THEN the function receives the class and recomputes each time.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries)]

        class Foo:
            counter = 0

            @class_property
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        for i in range(tries):
            assert obj.prop == values[i]

        assert Foo.counter == tries

    def test_class_access_passes_class(self, fake: Faker) -> None:
        """GIVEN a class_property
        WHEN accessed on the class repeatedly
        THEN the function receives the class and recomputes each time.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries)]

        class Foo:
            counter = 0

            @class_property
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        for i in range(tries):
            assert Foo.prop == values[i]

        assert Foo.counter == tries

    def test_inheritance_passes_child_class(self, fake: Faker) -> None:
        """GIVEN an inherited class_property
        WHEN accessed on a child class and its instance repeatedly
        THEN the function receives the child class and recomputes.
        """
        values = [fake.pyint(), fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @class_property
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        class Bar(Foo):
            pass

        assert Bar.prop == values[0]
        assert Bar().prop == values[1]
        assert Bar.prop == values[2]

    def test_no_caching(self, fake: Faker) -> None:
        """GIVEN a class_property
        WHEN accessed repeatedly
        THEN it recomputes every time.
        """
        tries = fake.pyint(min_value=3, max_value=6)
        values = [fake.pyint() for _ in range(tries)]

        class Foo:
            counter = 0

            @class_property
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        for i in range(tries):
            assert Foo.prop == values[i]

    def test_title_contains_address(self, fake: Faker) -> None:
        """GIVEN a class_property descriptor
        WHEN its title is read
        THEN it contains the expected descriptor kind.
        """

        def func(cls: Any) -> int:
            return fake.pyint()

        desc = class_property(func)
        assert "class descriptor" in desc.title

    def test_header_with_context_uses_footer(self, fake: Faker) -> None:
        """GIVEN a class_property
        WHEN header_with_context is called
        THEN it includes the footer text.
        """

        class Foo:
            @class_property
            def prop(cls) -> int:
                return fake.pyint()

        desc = Foo.__dict__["prop"]
        ctx = desc.header_with_context(Foo)
        assert "called with" in ctx

    def test_get_node_returns_owner(self, fake: Faker) -> None:
        """GIVEN a class_property
        WHEN get_node is called with the class
        THEN the class itself is returned.
        """

        class Foo:
            @class_property
            def prop(cls) -> int:
                return fake.pyint()

        desc = Foo.__dict__["prop"]
        assert desc.get_node(Foo) is Foo

    def test_get_node_raises_on_none(self, fake: Faker) -> None:
        """GIVEN a class_property
        WHEN get_node is called with None
        THEN ContextFaultError is raised.
        """

        class Foo:
            @class_property
            def prop(cls) -> int:
                return fake.pyint()

        desc = Foo.__dict__["prop"]
        with pytest.raises(ContextFaultError):
            desc.get_node(None)

    def test_get_node_raises_on_instance(self, fake: Faker) -> None:
        """GIVEN a class_property
        WHEN get_node is called with an instance
        THEN ContextFaultError is raised.
        """

        class Foo:
            @class_property
            def prop(cls) -> int:
                return fake.pyint()

        desc = Foo.__dict__["prop"]
        with pytest.raises(ContextFaultError):
            desc.get_node(Foo())

    def test_call_invokes_function(self, fake: Faker) -> None:
        """GIVEN a class_property
        WHEN call is invoked repeatedly
        THEN the function runs each time.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @class_property
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        desc = Foo.__dict__["prop"]
        assert desc.call(Foo) == values[0]
        assert desc.call(Foo) == values[1]

    def test_call_raises_attribute_exception(self, fake: Faker) -> None:
        """GIVEN a class_property that triggers AttributeError
        WHEN call is invoked
        THEN AttributeExceptionError is raised.
        """

        class Foo:
            @class_property
            def prop(cls) -> str:
                return cls.nonexistent.attr  # type: ignore[attr-defined]

        desc = Foo.__dict__["prop"]
        with pytest.raises(AttributeExceptionError):
            desc.call(Foo)

    def test_direct_get_instance_and_class(self, fake: Faker) -> None:
        """GIVEN a class_property
        WHEN __get__ is called directly with instance or class
        THEN the function receives the class and recomputes.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @class_property
            def prop(cls) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        desc = Foo.__dict__["prop"]
        assert desc.__get__(Foo(), Foo) == values[0]
        assert desc.__get__(None, Foo) == values[1]

    def test_is_data_false(self, fake: Faker) -> None:
        """GIVEN a class_property
        WHEN inspected via is_data
        THEN it reports False.
        """

        class Foo:
            @class_property
            def prop(cls) -> int:
                return fake.pyint()

        assert Foo.__dict__["prop"].is_data is False

    def test_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent class_property
        WHEN a child overrides via with_parent
        THEN the parent value is injected on every access.
        """
        parent_prefix = fake.word()
        child_prefix = fake.word()

        class Parent:
            counter = 0

            @class_property
            def prop(cls) -> str:
                Parent.counter += 1
                return f"{parent_prefix}_{cls.__name__}"

        class Child(Parent):
            @class_property.with_parent
            def prop(cls, parent_value: str) -> str:
                return f"{child_prefix}_{parent_value}"

        expected = f"{child_prefix}_{parent_prefix}_{Child.__name__}"
        assert Child.prop == expected
        assert Child().prop == expected
        # class_property is not cached, so each access re-evaluates.
        assert Parent.counter == 2

    def test_mixin_get_node_resolves_owner(self, fake: Faker) -> None:
        """GIVEN a class_property defined in a mixin
        WHEN get_node is called on a concrete subclass
        THEN the mixin (owner) is returned.
        """
        label = fake.pystr()

        class Mixin:
            @class_property
            def prop(cls) -> str:
                return label

        class Concrete(Mixin):
            pass

        desc = Mixin.__dict__["prop"]
        assert desc.get_node(Concrete) is Mixin


class TestMixedProperty:
    """Granular tests for mixed_property descriptor."""

    def test_instance_access_passes_instance(self, fake: Faker) -> None:
        """GIVEN a mixed_property
        WHEN accessed on an instance repeatedly
        THEN the function receives the instance and recomputes.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries)]

        class Foo:
            counter = 0

            @mixed_property
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        obj = Foo()
        for i in range(tries):
            assert obj.prop == values[i]

        assert Foo.counter == tries

    def test_class_access_passes_class(self, fake: Faker) -> None:
        """GIVEN a mixed_property
        WHEN accessed on the class repeatedly
        THEN the function receives the class and recomputes.
        """
        tries = fake.pyint(min_value=2, max_value=5)
        values = [fake.pyint() for _ in range(tries)]

        class Foo:
            counter = 0

            @mixed_property
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        for i in range(tries):
            assert Foo.prop == values[i]

        assert Foo.counter == tries

    def test_inheritance_passes_child(self, fake: Faker) -> None:
        """GIVEN an inherited mixed_property
        WHEN accessed on a child class and instance
        THEN the function receives the child node.
        """
        values = [fake.pyint(), fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @mixed_property
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        class Bar(Foo):
            pass

        assert Bar.prop == values[0]
        assert Bar().prop == values[1]
        assert Bar.prop == values[2]

    def test_no_caching(self, fake: Faker) -> None:
        """GIVEN a mixed_property
        WHEN accessed repeatedly
        THEN it recomputes every time.
        """
        tries = fake.pyint(min_value=4, max_value=7)
        values = [fake.pyint() for _ in range(tries)]

        class Foo:
            counter = 0

            @mixed_property
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        for i in range(tries):
            assert Foo().prop == values[i]

    def test_falsy_instance_gets_itself(self) -> None:
        """GIVEN a falsy instance with a mixed_property
        WHEN the property is accessed
        THEN the function receives the instance, not the class.
        """

        class Falsy:
            def __bool__(self) -> bool:
                return False

            @mixed_property
            def prop(self_or_cls: Any) -> Any:
                return self_or_cls

        obj = Falsy()
        assert obj.prop is obj

    def test_title_contains_address(self, fake: Faker) -> None:
        """GIVEN a mixed_property descriptor
        WHEN its title is read
        THEN it contains the expected descriptor kind.
        """

        def func(self_or_cls: Any) -> int:
            return fake.pyint()

        desc = mixed_property(func)
        assert "mixed descriptor" in desc.title

    def test_header_with_context_uses_footer(self, fake: Faker) -> None:
        """GIVEN a mixed_property
        WHEN header_with_context is called
        THEN it includes the footer text and descriptor kind.
        """

        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> int:
                return fake.pyint()

        desc = Foo.__dict__["prop"]
        ctx = desc.header_with_context(Foo())
        assert "called with" in ctx
        assert "mixed" in ctx

    def test_get_node_returns_instance_for_instance(self, fake: Faker) -> None:
        """GIVEN a mixed_property
        WHEN get_node is called with an instance
        THEN the same instance is returned.
        """

        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> int:
                return fake.pyint()

        obj = Foo()
        desc = Foo.__dict__["prop"]
        assert desc.get_node(obj) is obj

    def test_get_node_returns_owner_for_class(self, fake: Faker) -> None:
        """GIVEN a mixed_property
        WHEN get_node is called with the class
        THEN the class itself is returned.
        """

        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> int:
                return fake.pyint()

        desc = Foo.__dict__["prop"]
        assert desc.get_node(Foo) is Foo

    def test_get_node_raises_on_none(self, fake: Faker) -> None:
        """GIVEN a mixed_property
        WHEN get_node is called with None
        THEN ContextFaultError is raised.
        """

        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> int:
                return fake.pyint()

        desc = Foo.__dict__["prop"]
        with pytest.raises(ContextFaultError):
            desc.get_node(None)

    def test_call_invokes_function_with_instance(self, fake: Faker) -> None:
        """GIVEN a mixed_property
        WHEN call is invoked with an instance repeatedly
        THEN the function runs each time.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @mixed_property
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        desc = Foo.__dict__["prop"]
        obj = Foo()
        assert desc.call(obj) == values[0]
        assert desc.call(obj) == values[1]

    def test_call_invokes_function_with_class(self, fake: Faker) -> None:
        """GIVEN a mixed_property
        WHEN call is invoked with a class repeatedly
        THEN the function runs each time.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @mixed_property
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        desc = Foo.__dict__["prop"]
        assert desc.call(Foo) == values[0]
        assert desc.call(Foo) == values[1]

    def test_call_raises_attribute_exception(self, fake: Faker) -> None:
        """GIVEN a mixed_property that triggers AttributeError
        WHEN call is invoked on an instance
        THEN AttributeExceptionError is raised.
        """

        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                return self_or_cls.nonexistent.attr  # type: ignore[attr-defined,union-attr]

        desc = Foo.__dict__["prop"]
        with pytest.raises(AttributeExceptionError):
            desc.call(Foo())

    def test_direct_get_instance(self, fake: Faker) -> None:
        """GIVEN a mixed_property
        WHEN __get__ is called with an instance repeatedly
        THEN the function receives the instance and recomputes.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @mixed_property
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        desc = Foo.__dict__["prop"]
        assert desc.__get__(Foo(), Foo) == values[0]
        assert desc.__get__(Foo(), Foo) == values[1]

    def test_direct_get_class(self, fake: Faker) -> None:
        """GIVEN a mixed_property
        WHEN __get__ is called with None/class repeatedly
        THEN the function receives the class and recomputes.
        """
        values = [fake.pyint(), fake.pyint()]

        class Foo:
            counter = 0

            @mixed_property
            def prop(self_or_cls: Any) -> int:
                value = values[Foo.counter]
                Foo.counter += 1
                return value

        desc = Foo.__dict__["prop"]
        assert desc.__get__(None, Foo) == values[0]
        assert desc.__get__(None, Foo) == values[1]

    def test_is_data_false(self, fake: Faker) -> None:
        """GIVEN a mixed_property
        WHEN inspected via is_data
        THEN it reports False.
        """

        class Foo:
            @mixed_property
            def prop(self_or_cls: Any) -> int:
                return fake.pyint()

        assert Foo.__dict__["prop"].is_data is False

    def test_with_parent(self, fake: Faker) -> None:
        """GIVEN a parent mixed_property
        WHEN a child overrides via with_parent
        THEN the parent value is injected on every access.
        """
        parent_label = fake.word()
        child_prefix = fake.word()

        class Parent:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                return parent_label

        class Child(Parent):
            @mixed_property.with_parent
            def prop(self_or_cls: Any, parent_value: str) -> str:
                return f"{child_prefix}_{parent_value}"

        expected = f"{child_prefix}_{parent_label}"
        assert Child.prop == expected
        assert Child().prop == expected

    def test_mixin_get_node_resolves_owner(self, fake: Faker) -> None:
        """GIVEN a mixed_property defined in a mixin
        WHEN get_node is called on a concrete subclass
        THEN the mixin (owner) is returned.
        """
        label = fake.pystr()

        class Mixin:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                return label

        class Concrete(Mixin):
            pass

        desc = Mixin.__dict__["prop"]
        assert desc.get_node(Concrete) is Mixin

    def test_mixin_get_node_returns_instance_for_instance(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a mixed_property defined in a mixin
        WHEN get_node is called with an instance of a subclass
        THEN the instance itself is returned.
        """
        label = fake.pystr()

        class Mixin:
            @mixed_property
            def prop(self_or_cls: Any) -> str:
                return label

        class Concrete(Mixin):
            pass

        obj = Concrete()
        desc = Mixin.__dict__["prop"]
        assert desc.get_node(obj) is obj
