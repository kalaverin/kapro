"""Unit tests for the ``proxy_to`` class decorator.

Arrange-Act-Assert pattern, BDD docstrings, heavy parameterization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

import pytest
from faker import Faker

from kapro import pin
from kapro.cached import (
    cached_property,
    class_cached_property,
    mixed_cached_property,
    post_cached_property,
    pre_cached_property,
)
from kapro.class_property import class_property, mixed_property
from kapro.primitives import bound_property
from kapro.special.proxy_to import proxy_to

if TYPE_CHECKING:
    from collections.abc import Callable


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _dict_getter(name: str) -> Callable[[dict[str, Any]], Any]:
    """Return a getter that indexes a dict by *name*."""
    return lambda entity: entity[name]


class _SimpleTarget:
    """Simple target object for object-pivot tests."""

    def __init__(self, value: int, label: str) -> None:
        self.value = value
        self.label = label

    def get_value(self) -> int:
        return self.value

    def get_label(self) -> str:
        return self.label

    def _private(self) -> int:
        return self.value


class _CallableTarget:
    """Target whose proxied attribute is a callable taking args."""

    def __init__(self, multiplier: int) -> None:
        self.multiplier = multiplier

    def scale(self, value: int) -> int:
        return value * self.multiplier


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


class TestProxyToValidation:
    """GIVEN invalid decorator arguments
    WHEN proxy_to is applied
    THEN it raises the expected exception immediately.
    """

    def test_proxy_to_on_non_class_raises_type_error(self) -> None:
        """GIVEN a non-class object
        WHEN proxy_to is applied
        THEN TypeError is raised.
        """
        decorator = proxy_to("pivot", "method")

        with pytest.raises(TypeError, match="isn't a class"):
            decorator(object())

    def test_proxy_to_with_empty_names_raises_value_error(self) -> None:
        """GIVEN an empty sequence of names
        WHEN proxy_to is applied to a class
        THEN ValueError is raised.
        """

        with pytest.raises(ValueError, match="at least one method name"):

            @proxy_to("pivot", [])
            class Proxy:
                pivot = None


# ------------------------------------------------------------------
# Pivot types
# ------------------------------------------------------------------


class TestProxyToPivotTypes:
    """GIVEN different pivot kinds
    WHEN a proxied attribute is accessed
    THEN the call is forwarded correctly.
    """

    def test_string_pivot_forwards_to_instance_attribute(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a string pivot naming an instance attribute
        WHEN the proxied method is accessed on an instance
        THEN the target method is invoked.
        """
        expected = fake.pyint()

        @proxy_to("target", "get_value")
        class Proxy:
            target = _SimpleTarget(expected, fake.pystr())

        instance = Proxy()

        assert instance.get_value() == expected

    def test_object_pivot_forwards_to_external_object(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN an object pivot passed directly
        WHEN the proxied method is accessed on an instance
        THEN the external object's method is returned.
        """
        expected = fake.pystr()
        target = _SimpleTarget(fake.pyint(), expected)

        @proxy_to(target, "get_label")
        class Proxy:
            pass

        instance = Proxy()

        assert instance.get_label() == expected

    def test_none_pivot_with_default_returns_default(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a string pivot that resolves to None
        WHEN a default is configured
        THEN the default value is returned.
        """
        default_value = fake.pyint()

        @proxy_to("target", "missing", default=default_value)
        class Proxy:
            target = None

        instance = Proxy()

        assert instance.missing == default_value

    def test_none_pivot_without_default_raises_attribute_error(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a string pivot that resolves to None
        WHEN no default is configured
        THEN AttributeError is raised with pivot context.
        """

        @proxy_to("target", "missing")
        class Proxy:
            target = None

        instance = Proxy()

        with pytest.raises(AttributeError, match=r"target.*does not exist"):
            _ = instance.missing


# ------------------------------------------------------------------
# Bind modes
# ------------------------------------------------------------------


class TestProxyToBindModes:
    """GIVEN the optional binder argument
    WHEN a proxied attribute is accessed
    THEN the chosen descriptor is used.
    """

    @pytest.mark.parametrize(
        "binder, descriptor_type",
        (
            pytest.param(
                bound_property,
                bound_property,
                id="bound-property",
            ),
            pytest.param(pin, pin, id="pin"),
            pytest.param(
                pin.native,
                cached_property,
                id="pin-native",
            ),
            pytest.param(
                pin.cls,
                class_cached_property,
                id="pin-cls",
            ),
            pytest.param(
                pin.any,
                mixed_cached_property,
                id="pin-any",
            ),
            pytest.param(
                pin.pre,
                pre_cached_property,
                id="pin-pre",
            ),
            pytest.param(
                pin.post,
                post_cached_property,
                id="pin-post",
            ),
            pytest.param(
                class_property,
                class_property,
                id="class-property",
            ),
            pytest.param(
                mixed_property,
                mixed_property,
                id="mixed-property",
            ),
        ),
    )
    def test_explicit_binder_produces_expected_descriptor_type(
        self,
        fake: Faker,
        binder: Callable[[Callable[..., Any]], Any],
        descriptor_type: type,
    ) -> None:
        """GIVEN an explicit binder
        WHEN the class is decorated
        THEN the class attribute is wrapped by that descriptor.
        """
        expected = fake.pyint()

        @proxy_to("target", "get_value", binder=binder)
        class Proxy:
            target = _SimpleTarget(expected, fake.pystr())

        descriptor = Proxy.__dict__["get_value"]
        assert isinstance(descriptor, descriptor_type)

    def test_omitted_binder_defaults_to_bound_property(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN no binder argument and a string last positional
        WHEN the class is decorated
        THEN bound_property is used by default.
        """
        expected = fake.pyint()

        @proxy_to("target", "get_value")
        class Proxy:
            target = _SimpleTarget(expected, fake.pystr())

        descriptor = Proxy.__dict__["get_value"]
        assert isinstance(descriptor, bound_property)

    def test_none_binder_attaches_raw_method(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN None as the binder
        WHEN the class is decorated
        THEN the raw target method is resolved at access time.
        """
        expected = fake.pyint()
        target_obj = _SimpleTarget(expected, fake.pystr())

        @proxy_to("target", "get_value", binder=None)
        class Proxy:
            target = target_obj

        descriptor = Proxy.__dict__["get_value"]
        assert descriptor.__class__.__name__ == "RawProxy"
        assert Proxy().get_value() == expected


# ------------------------------------------------------------------
# Forwarding
# ------------------------------------------------------------------


class TestProxyToForwarding:
    """GIVEN one or more proxied method names
    WHEN the decorator is applied
    THEN __proxy_fields__ tracks and sorts them.
    """

    def test_single_method_name_populates_proxy_fields(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a single method name
        WHEN the class is decorated
        THEN __proxy_fields__ contains that name.
        """

        @proxy_to("target", "get_value")
        class Proxy:
            target = _SimpleTarget(fake.pyint(), fake.pystr())

        assert Proxy.__proxy_fields__ == ["get_value"]

    def test_multiple_method_names_are_sorted(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN multiple method names out of order
        WHEN the class is decorated
        THEN __proxy_fields__ is sorted.
        """

        @proxy_to("target", ["get_value", "get_label"])
        class Proxy:
            target = _SimpleTarget(fake.pyint(), fake.pystr())

        assert Proxy.__proxy_fields__ == ["get_label", "get_value"]

    def test_multiple_decorators_append_and_sort(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN multiple stacked proxy_to decorators
        WHEN the class is decorated
        THEN __proxy_fields__ merges and sorts all names.
        """

        @proxy_to("target", "get_label")
        @proxy_to("target", "get_value")
        class Proxy:
            target = _SimpleTarget(fake.pyint(), fake.pystr())

        assert Proxy.__proxy_fields__ == ["get_label", "get_value"]

    def test_proxy_forwards_callable_arguments(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a proxied method that accepts arguments
        WHEN called with arguments
        THEN they are forwarded to the target method.
        """
        multiplier = fake.pyint(min_value=2, max_value=10)
        value = fake.pyint()

        @proxy_to("target", "scale")
        class Proxy:
            target = _CallableTarget(multiplier)

        instance = Proxy()

        assert instance.scale(value) == value * multiplier


# ------------------------------------------------------------------
# Safety
# ------------------------------------------------------------------


class TestProxyToSafety:
    """GIVEN the ``safe`` flag
    WHEN proxy_to would overwrite an existing attribute
    THEN the behavior depends on the flag and name privacy.
    """

    def test_safe_true_blocks_overwriting_public_attribute(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN safe=True and an existing public method
        WHEN proxy_to targets that name
        THEN TypeError is raised.
        """
        with pytest.raises(TypeError, match="already exists"):

            @proxy_to("target", "existing")
            class Proxy:
                target = _SimpleTarget(fake.pyint(), fake.pystr())

                @staticmethod
                def existing() -> str:
                    return fake.pystr()

    def test_safe_false_allows_overwriting_public_attribute(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN safe=False and an existing public method
        WHEN proxy_to targets that name
        THEN the method is overwritten.
        """
        expected = fake.pyint()

        @proxy_to("target", "get_value", safe=False)
        class Proxy:
            target = _SimpleTarget(expected, fake.pystr())

            @staticmethod
            def get_value() -> int:
                return fake.pyint()

        instance = Proxy()
        assert instance.get_value() == expected

    def test_safe_true_blocks_private_attribute(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN safe=True and an existing private method
        WHEN proxy_to targets that name
        THEN TypeError is raised.
        """
        with pytest.raises(TypeError, match="already exists"):

            @proxy_to("target", "_private")
            class Proxy:
                target = _SimpleTarget(fake.pyint(), fake.pystr())

                @staticmethod
                def _private() -> int:
                    return fake.pyint()

    def test_safe_false_allows_overwriting_private_attribute(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN safe=False and an existing private method
        WHEN proxy_to targets that name
        THEN the private method is overwritten.
        """
        expected = fake.pyint()

        @proxy_to("target", "_private", safe=False)
        class Proxy:
            target = _SimpleTarget(expected, fake.pystr())

            @staticmethod
            def _private() -> int:
                return fake.pyint()

        instance = Proxy()
        assert instance._private() == expected


# ------------------------------------------------------------------
# Defaults
# ------------------------------------------------------------------


class TestProxyToDefaults:
    """GIVEN a default fallback
    WHEN the pivot or attribute is missing
    THEN the default is returned or AttributeError is raised.
    """

    def test_default_used_when_pivot_attribute_missing(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a missing method on the pivot
        WHEN default is provided
        THEN the default is returned.
        """
        default_value = fake.pystr()

        @proxy_to("target", "missing", default=default_value)
        class Proxy:
            target = _SimpleTarget(fake.pyint(), fake.pystr())

        instance = Proxy()

        assert instance.missing == default_value

    def test_attribute_error_without_default_mentions_missing_attr(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a missing method on the pivot
        WHEN no default is provided
        THEN AttributeError mentions the missing attribute.
        """

        @proxy_to("target", "missing")
        class Proxy:
            target = _SimpleTarget(fake.pyint(), fake.pystr())

        instance = Proxy()

        with pytest.raises(
            AttributeError,
            match=r"missing.*does not exist",
        ):
            _ = instance.missing

    def test_default_warning_is_logged(
        self,
        fake: Faker,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """GIVEN a default fallback
        WHEN the pivot is None
        THEN a warning is logged.
        """
        default_value = fake.pyint()

        @proxy_to("target", "missing", default=default_value)
        class Proxy:
            target = None

        instance = Proxy()

        with caplog.at_level("WARNING"):
            _ = instance.missing

        assert any("return" in rec.message for rec in caplog.records)


# ------------------------------------------------------------------
# Custom getter
# ------------------------------------------------------------------


class TestProxyToCustomGetter:
    """GIVEN a custom getter
    WHEN the proxied attribute is accessed
    THEN the getter is used to extract the value.
    """

    def test_dict_getter_indexes_pivot_dict(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a dict pivot and a key-indexing getter
        WHEN the proxied key is accessed
        THEN the dict value is returned.
        """
        key = fake.word()
        expected = fake.pyint()

        @proxy_to("data", key, getter=_dict_getter)
        class Proxy:
            data: ClassVar[dict[str, int]] = {key: expected}

        instance = Proxy()

        assert getattr(instance, key) == expected

    def test_dict_getter_missing_key_uses_default(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a missing dict key
        WHEN a default is provided
        THEN the default is returned.
        """
        default_value = fake.pystr()

        @proxy_to(
            "data",
            "missing",
            getter=_dict_getter,
            default=default_value,
        )
        class Proxy:
            data: ClassVar[dict[str, int]] = {}

        instance = Proxy()

        assert instance.missing == default_value


# ------------------------------------------------------------------
# Pre processor
# ------------------------------------------------------------------


class TestProxyToPostProcessor:
    """GIVEN a post processor
    WHEN the proxied attribute is accessed
    THEN the value is transformed eagerly.
    """

    def test_post_applies_eagerly_to_value(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a post processor
        WHEN the proxied attribute is accessed
        THEN the processed value is returned directly.
        """
        expected = fake.pyint()

        @proxy_to("target", "value", post=lambda value: value * 2)
        class Proxy:
            target = _SimpleTarget(expected, fake.pystr())

        instance = Proxy()

        assert instance.value == expected * 2


# ------------------------------------------------------------------
# Error messages
# ------------------------------------------------------------------


class TestProxyToErrorMessages:
    """GIVEN a failure path
    WHEN an exception is raised
    THEN the message names the proxied attribute and pivot.
    """

    def test_missing_string_pivot_mentions_pivot_path(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a string pivot that does not exist on the instance
        WHEN the proxied method is accessed
        THEN AttributeError mentions the pivot path.
        """

        @proxy_to("missing_pivot", "method")
        class Proxy:
            pass

        instance = Proxy()

        with pytest.raises(AttributeError, match="missing_pivot"):
            _ = instance.method

    def test_missing_object_pivot_method_mentions_target(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN an object pivot without the requested method
        WHEN the proxied method is accessed
        THEN AttributeError mentions the proxied name.
        """
        target = _SimpleTarget(fake.pyint(), fake.pystr())

        @proxy_to(target, "nonexistent")
        class Proxy:
            pass

        instance = Proxy()

        with pytest.raises(AttributeError, match="nonexistent"):
            _ = instance.nonexistent


# ------------------------------------------------------------------
# Inheritance
# ------------------------------------------------------------------


class TestProxyToInheritance:
    """GIVEN a decorated base class
    WHEN subclassing or overriding
    THEN proxy fields and forwarding behave correctly.
    """

    def test_subclass_inherits_proxy_fields(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a decorated base class
        WHEN a subclass is created
        THEN it inherits __proxy_fields__.
        """

        @proxy_to("target", "get_value")
        class Base:
            target = _SimpleTarget(fake.pyint(), fake.pystr())

        class Child(Base):
            pass

        assert Child.__proxy_fields__ == ["get_value"]

    def test_subclass_override_with_safe_false_works(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a subclass with an overriding proxy_to
        WHEN safe=False is used
        THEN the new proxy replaces the inherited one.
        """
        first = fake.pyint()
        second = fake.pyint()

        @proxy_to("first_target", "get_value")
        class Base:
            first_target = _SimpleTarget(first, fake.pystr())
            second_target = _SimpleTarget(second, fake.pystr())

        @proxy_to("second_target", "get_value", safe=False)
        class Child(Base):
            pass

        instance = Child()
        assert instance.get_value() == second


# ------------------------------------------------------------------
# Frozen dataclasses
# ------------------------------------------------------------------


class TestProxyToFrozenDataclass:
    """GIVEN a frozen dataclass decorated with proxy_to
    WHEN accessing the proxy
    THEN descriptor-based binders fail and None binder works.
    """

    def test_bound_property_works_on_frozen_dataclass(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a frozen dataclass with bound_property binder
        WHEN the proxy is accessed on an instance
        THEN it returns the target value.
        """

        @proxy_to("target", "get_value")
        @dataclass(frozen=True)
        class Proxy:
            target: _SimpleTarget = field(
                default_factory=lambda: _SimpleTarget(
                    fake.pyint(),
                    fake.pystr(),
                ),
            )

        instance = Proxy()

        assert instance.get_value() == instance.target.get_value()

    def test_none_binder_works_on_frozen_dataclass(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a frozen dataclass with None binder
        WHEN the proxy is accessed
        THEN the raw method is returned.
        """
        expected = fake.pyint()
        target_obj = _SimpleTarget(expected, fake.pystr())

        @proxy_to("target", "get_value", binder=None)
        @dataclass(frozen=True)
        class Proxy:
            target: _SimpleTarget = target_obj

        instance = Proxy()

        assert instance.get_value() == expected


# ------------------------------------------------------------------
# Slots
# ------------------------------------------------------------------


class TestProxyToSlots:
    """GIVEN a class with __slots__ decorated with proxy_to
    WHEN accessing the proxy
    THEN descriptor-based instance binders fail appropriately.
    """

    def test_bound_property_raises_on_slots_instance(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a slotted class with bound_property binder
        WHEN the proxy is accessed on an instance
        THEN TypeError is raised.
        """

        @proxy_to("target", "get_value")
        class Proxy:
            __slots__ = ("target",)

            def __init__(self) -> None:
                self.target = _SimpleTarget(fake.pyint(), fake.pystr())

        instance = Proxy()

        with pytest.raises(TypeError, match="has no __dict__"):
            _ = instance.get_value

    def test_none_binder_works_on_slots(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a slotted class with None binder
        WHEN the proxy is accessed
        THEN the raw method is returned.
        """
        expected = fake.pyint()
        target_obj = _SimpleTarget(expected, fake.pystr())

        @proxy_to("target", "get_value", binder=None)
        class Proxy:
            __slots__ = ()
            target = target_obj

        instance = Proxy()

        assert instance.get_value() == expected

    def test_class_level_binder_works_on_slots_instance(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a slotted class with class_property binder
        WHEN the proxy is accessed on an instance
        THEN forwarding works via the class cache.
        """
        expected = fake.pyint()

        @proxy_to("target", "get_value", binder=class_cached_property)
        class Proxy:
            __slots__ = ()
            target = _SimpleTarget(expected, fake.pystr())

        instance = Proxy()

        assert instance.get_value() == expected


# ------------------------------------------------------------------
# Complex inheritance
# ------------------------------------------------------------------


class TestProxyToComplexInheritance:
    """GIVEN diamond or mixin inheritance
    WHEN proxy_to is applied on a base or mixin
    THEN subclasses resolve forwarding correctly.
    """

    def test_diamond_inheritance_resolves_proxy(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a diamond hierarchy with proxy_to on the top class
        WHEN the proxy is accessed on the diamond subclass
        THEN forwarding resolves correctly.
        """
        expected = fake.pyint()

        @proxy_to("target", "get_value")
        class Top:
            target = _SimpleTarget(expected, fake.pystr())

        class Left(Top):
            pass

        class Right(Top):
            pass

        class Bottom(Left, Right):
            pass

        instance = Bottom()
        assert instance.get_value() == expected

    def test_mixin_inheritance_resolves_proxy(
        self,
        fake: Faker,
    ) -> None:
        """GIVEN a mixin with proxy_to
        WHEN a class inherits from it alongside a base
        THEN forwarding resolves correctly.
        """
        expected = fake.pyint()

        @proxy_to("target", "get_value")
        class Mixin:
            target = _SimpleTarget(expected, fake.pystr())

        class Base:
            pass

        class Child(Base, Mixin):
            pass

        instance = Child()
        assert instance.get_value() == expected


# ------------------------------------------------------------------
# Fixed bugs (formerly XFAIL)
# ------------------------------------------------------------------


class _ObjectTarget:
    """Target with a plain data attribute for object-pivot tests."""

    def __init__(self, value: int) -> None:
        self.value = value


class _Engine:
    """Target with a method for object-pivot tests."""

    def __init__(self, power_value: int) -> None:
        self.power_value = power_value

    def power(self) -> int:
        return self.power_value


class TestProxyToFixedBugs:
    """GIVEN previously failing edge cases
    WHEN the new implementation is used
    THEN they work as expected.
    """

    def test_object_pivot_uses_custom_getter(
        self,
        fake: Faker,
    ) -> None:
        """Object pivot should respect the getter argument."""
        power = fake.pyint()
        engine = _Engine(power)

        @proxy_to(
            engine,
            "power",
            getter=lambda name: lambda obj: getattr(obj, name)() * 2,
        )
        class Proxy:
            pass

        assert Proxy().power == power * 2

    def test_object_pivot_uses_default_for_missing_attr(
        self,
        fake: Faker,
    ) -> None:
        """Object pivot should fall back to default."""
        default_value = fake.pyint()

        @proxy_to(
            _Engine(fake.pyint()),
            "missing",
            default=default_value,
        )
        class Proxy:
            pass

        assert Proxy().missing == default_value

    def test_object_pivot_uses_post_processor(
        self,
        fake: Faker,
    ) -> None:
        """Object pivot should apply post processor eagerly."""
        value = fake.pyint()

        @proxy_to(_ObjectTarget(value), "value", post=lambda v: v * 2)
        class Proxy:
            pass

        assert Proxy().value == value * 2

    def test_object_pivot_with_none_binder_works(
        self,
        fake: Faker,
    ) -> None:
        """Object pivot with binder=None should resolve the raw attribute."""
        power = fake.pyint()

        @proxy_to(_Engine(power), "power", binder=None)
        class Proxy:
            pass

        assert Proxy().power() == power

    def test_none_binder_respects_per_instance_pivot(
        self,
        fake: Faker,
    ) -> None:
        """None binder should use the instance-level pivot at access time."""
        first = fake.pyint()
        second = fake.pyint()

        @proxy_to("target", "get_value", binder=None)
        class Proxy:
            target = _SimpleTarget(first, fake.pystr())

        instance = Proxy()
        instance.target = _SimpleTarget(second, fake.pystr())

        assert instance.get_value() == second

    def test_none_binder_resolves_descriptor_pivot(
        self,
        fake: Faker,
    ) -> None:
        """None binder should dereference a pivot that is a descriptor."""
        power = fake.pyint()

        class EngineDescriptor:
            def __get__(
                self,
                instance: object | None,
                owner: type,
            ) -> _Engine:
                return _Engine(power)

        @proxy_to("engine", "power", binder=None)
        class Proxy:
            engine = EngineDescriptor()

        assert Proxy().power() == power

    def test_proxy_fields_is_not_mutated_in_base_class(
        self,
        fake: Faker,
    ) -> None:
        """Subclass decoration must not mutate the base class list."""
        name_a = f"field_{fake.pyint()}"
        name_b = f"field_{fake.pyint()}"

        @proxy_to("target", name_a)
        class Base:
            target = _SimpleTarget(fake.pyint(), fake.pystr())

        @proxy_to("target", name_b)
        class Child(Base):
            target = _SimpleTarget(fake.pyint(), fake.pystr())

        assert Base.__proxy_fields__ == [name_a]
        assert Child.__proxy_fields__ == sorted([name_a, name_b])

    def test_names_accept_tuple(
        self,
        fake: Faker,
    ) -> None:
        """Names may be passed as a tuple, not only a list or string."""

        @proxy_to("target", ("get_value", "get_label"))
        class Proxy:
            target = _SimpleTarget(fake.pyint(), fake.pystr())

        assert Proxy.__proxy_fields__ == ["get_label", "get_value"]
