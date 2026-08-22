"""Granular unit tests for kapro.cached descriptor family."""

from __future__ import annotations

import time
from typing import Any

import pytest

from kapro.cached.instance import cached_property
from kapro.cached.klass import (
    class_cached_property,
    class_parent_cached_property,
)
from kapro.cached.mixed import (
    mixed_cached_property,
    mixed_parent_cached_property,
)
from kapro.cached.post import (
    post_cached_property,
    post_parent_cached_property,
)
from kapro.cached.pre import (
    pre_cached_property,
    pre_parent_cached_property,
)
from kapro.primitives import ContextFaultError


class TestCustomCallbackMixin:
    """Tests for the CustomCallbackMixin helper."""

    def test_by_returns_partial(self) -> None:
        def cb(self: object, node: object, stamp: float) -> bool:
            return True

        factory = class_cached_property.by(cb)
        assert callable(factory)

    def test_ttl_returns_partial(self) -> None:
        factory = class_cached_property.ttl(3600)
        assert callable(factory)

    def test_ttl_rejects_non_number(self) -> None:
        with pytest.raises(TypeError, match="expire must be float or int"):
            class_cached_property.ttl("invalid")

    def test_ttl_rejects_zero(self) -> None:
        with pytest.raises(
            ValueError,
            match="expire must be a positive number",
        ):
            class_cached_property.ttl(0)

    def test_ttl_rejects_negative(self) -> None:
        with pytest.raises(
            ValueError,
            match="expire must be a positive number",
        ):
            class_cached_property.ttl(-1)

    def test_expired_by_alias(self) -> None:
        def cb(self: object, node: object, stamp: float) -> bool:
            return True

        # Accessing as class attribute yields bound methods; compare __func__
        assert (
            class_cached_property.by.__func__
            is class_cached_property.by.__func__
        )
        factory = class_cached_property.by(cb)
        assert callable(factory)


class TestClassParentCachedProperty:
    """Tests for class_parent_cached_property."""

    def test_class_access_caches_on_owner(self) -> None:
        class Base:
            counter = 0

            @class_parent_cached_property
            def prop(cls) -> str:
                Base.counter += 1
                return cls.__name__

        class Child(Base):
            pass

        assert Base.prop == "Base"
        assert Child.prop == "Base"
        assert Base.counter == 1
        assert "__class_memoized__" in Base.__dict__
        assert "__class_memoized__" not in Child.__dict__

    def test_instance_access_delegates_to_class(self) -> None:
        class Foo:
            counter = 0

            @class_parent_cached_property
            def prop(cls) -> str:
                Foo.counter += 1
                return cls.__name__

        obj = Foo()
        assert obj.prop == "Foo"
        assert obj.prop == "Foo"
        assert Foo.counter == 1

    def test_get_node_returns_owner(self) -> None:
        class Base:
            @class_parent_cached_property
            def prop(cls) -> str:
                return "base"

        class Child(Base):
            pass

        desc = Base.__dict__["prop"]
        assert desc.get_node(Child) is Base
        assert desc.get_node(Base) is Base

    def test_get_node_raises_on_none(self) -> None:
        class Foo:
            @class_parent_cached_property
            def prop(cls) -> str:
                return "foo"

        desc = Foo.__dict__["prop"]
        with pytest.raises(ContextFaultError):
            desc.get_node(None)

    def test_get_node_raises_on_instance(self) -> None:
        class Foo:
            @class_parent_cached_property
            def prop(cls) -> str:
                return "foo"

        desc = Foo.__dict__["prop"]
        with pytest.raises(ContextFaultError):
            desc.get_node(Foo())

    def test_get_cache_creates_dict(self) -> None:
        class Foo:
            @class_parent_cached_property
            def prop(cls) -> str:
                return "foo"

        desc = Foo.__dict__["prop"]
        cache = desc.get_cache(Foo)
        assert isinstance(cache, dict)
        assert Foo.__dict__["__class_memoized__"] is cache

    def test_call_computes_and_caches(self) -> None:
        class Foo:
            counter = 0

            @class_parent_cached_property
            def prop(cls) -> int:
                Foo.counter += 1
                return Foo.counter

        desc = Foo.__dict__["prop"]
        assert desc.call(Foo) == 1
        assert desc.call(Foo) == 1
        assert Foo.counter == 1

    def test_set_and_delete(self) -> None:
        class Foo:
            @class_parent_cached_property
            def prop(cls) -> str:
                return "original"

        desc = Foo.__dict__["prop"]
        desc.__set__(Foo, "override")
        assert desc.call(Foo) == "override"
        desc.__delete__(Foo)
        assert desc.call(Foo) == "original"

    def test_ttl_expiration(self) -> None:
        class Foo:
            counter = 0

            @class_parent_cached_property.ttl(0.01)
            def prop(cls) -> int:
                Foo.counter += 1
                return 42

        assert Foo.prop == 42
        assert Foo.counter == 1
        time.sleep(0.02)
        assert Foo.prop == 42
        assert Foo.counter == 2

    def test_by_custom_callback(self) -> None:
        expired = False

        def is_actual(
            self: object,
            node: object,
            stamp: float | None = None,
        ) -> bool | float:
            if stamp is None:
                return time.time()
            return not expired

        class Foo:
            counter = 0

            @class_parent_cached_property.by(is_actual)
            def prop(cls) -> int:
                Foo.counter += 1
                return 42

        assert Foo.prop == 42
        assert Foo.counter == 1
        expired = True
        assert Foo.prop == 42
        assert Foo.counter == 2

    def test_with_parent(self) -> None:
        class Parent:
            counter = 0

            @class_parent_cached_property
            def prop(cls) -> str:
                Parent.counter += 1
                return f"parent_{cls.__name__}"

        class Child(Parent):
            @class_parent_cached_property.with_parent
            def prop(cls, parent_value: str) -> str:
                return f"child_{parent_value}"

        assert Child.prop == "child_parent_Child"
        assert Child.prop == "child_parent_Child"
        assert Parent.counter == 1

    def test_is_data_true(self) -> None:
        class Foo:
            @class_parent_cached_property
            def prop(cls) -> int:
                return 42

        assert Foo.__dict__["prop"].is_data is True


class TestClassCachedProperty:
    """Tests for class_cached_property (plain variant)."""

    def test_class_access_caches_on_accessed_class(self) -> None:
        class Base:
            counter = 0

            @class_cached_property
            def prop(cls) -> str:
                Base.counter += 1
                return cls.__name__

        class Child(Base):
            pass

        assert Base.prop == "Base"
        assert Child.prop == "Child"
        assert Base.counter == 2
        assert "__class_memoized__" in Base.__dict__
        assert "__class_memoized__" in Child.__dict__

    def test_get_node_returns_class_directly(self) -> None:
        class Base:
            @class_cached_property
            def prop(cls) -> str:
                return "base"

        class Child(Base):
            pass

        desc = Base.__dict__["prop"]
        assert desc.get_node(Child) is Child
        assert desc.get_node(Base) is Base

    def test_here_returns_parent_class(self) -> None:
        desc = class_cached_property.here
        assert desc is class_parent_cached_property

    def test_with_parent(self) -> None:
        class Parent:
            counter = 0

            @class_cached_property
            def prop(cls) -> str:
                Parent.counter += 1
                return f"parent_{cls.__name__}"

        class Child(Parent):
            @class_cached_property.with_parent
            def prop(cls, parent_value: str) -> str:
                return f"child_{parent_value}"

        assert Child.prop == "child_parent_Child"
        assert Parent.counter == 1


class TestCachedProperty:
    """Tests for cached_property (instance-level)."""

    def test_instance_access_caches(self) -> None:
        class Foo:
            counter = 0

            @cached_property
            def prop(self) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_class_access_raises(self) -> None:
        class Foo:
            @cached_property
            def prop(self) -> int:
                return 42

        with pytest.raises(ContextFaultError):
            Foo.prop

    def test_instances_have_separate_cache(self) -> None:
        class Foo:
            counter = 0

            @cached_property
            def prop(self) -> int:
                Foo.counter += 1
                return Foo.counter

        a = Foo()
        b = Foo()
        assert a.prop == 1
        assert b.prop == 2
        assert a.prop == 1
        assert b.prop == 2

    def test_get_node_returns_instance(self) -> None:
        class Foo:
            @cached_property
            def prop(self) -> int:
                return 42

        obj = Foo()
        desc = Foo.__dict__["prop"]
        assert desc.get_node(obj) is obj

    def test_get_node_raises_on_class(self) -> None:
        class Foo:
            @cached_property
            def prop(self) -> int:
                return 42

        desc = Foo.__dict__["prop"]
        with pytest.raises(ContextFaultError):
            desc.get_node(Foo)

    def test_get_cache_creates_instance_dict(self) -> None:
        class Foo:
            @cached_property
            def prop(self) -> int:
                return 42

        obj = Foo()
        desc = Foo.__dict__["prop"]
        cache = desc.get_cache(obj)
        assert isinstance(cache, dict)
        assert obj.__dict__["__instance_memoized__"] is cache

    def test_manual_set_and_delete(self) -> None:
        class Foo:
            @cached_property
            def prop(self) -> int:
                return 42

        obj = Foo()
        assert obj.prop == 42
        desc = Foo.__dict__["prop"]
        desc.__set__(obj, 100)
        assert obj.prop == 100
        desc.__delete__(obj)
        assert obj.prop == 42

    def test_ttl_expiration(self) -> None:
        class Foo:
            counter = 0

            @cached_property.ttl(0.01)
            def prop(self) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert Foo.counter == 1
        time.sleep(0.02)
        assert obj.prop == 42
        assert Foo.counter == 2

    def test_with_parent(self) -> None:
        class Parent:
            counter = 0

            @cached_property
            def prop(self) -> int:
                Parent.counter += 1
                return 42

        class Child(Parent):
            @cached_property.with_parent
            def prop(self, parent_value: int) -> int:
                return parent_value + 10

        obj = Child()
        assert obj.prop == 52
        assert Parent.counter == 1

    def test_is_data_true(self) -> None:
        class Foo:
            @cached_property
            def prop(self) -> int:
                return 42

        assert Foo.__dict__["prop"].is_data is True


class TestMixedParentCachedProperty:
    """Tests for mixed_parent_cached_property."""

    def test_instance_caches_on_instance(self) -> None:
        class Foo:
            counter = 0

            @mixed_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_falsy_instance_still_uses_instance_cache(self) -> None:
        class Foo:
            counter = 0

            @mixed_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return 42

            def __bool__(self) -> bool:
                return False

        obj = Foo()
        assert not obj
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.counter == 1
        assert "__instance_memoized__" in obj.__dict__
        assert "__class_memoized__" not in Foo.__dict__

    def test_class_caches_on_owner(self) -> None:
        class Base:
            counter = 0

            @mixed_parent_cached_property
            def prop(self_or_cls: Any) -> str:
                Base.counter += 1
                return "base"

        class Child(Base):
            pass

        assert Child.prop == "base"
        assert Child.prop == "base"
        assert Base.counter == 1
        assert "__class_memoized__" in Base.__dict__

    def test_instance_and_class_caches_are_separate(self) -> None:
        class Foo:
            counter_i = 0
            counter_c = 0

            @mixed_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                if isinstance(self_or_cls, type):
                    Foo.counter_c += 1
                else:
                    Foo.counter_i += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert Foo.prop == 42
        assert obj.prop == 42
        assert Foo.prop == 42
        assert Foo.counter_i == 1
        assert Foo.counter_c == 1

    def test_get_node_returns_instance_for_instance(self) -> None:
        class Foo:
            @mixed_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                return 42

        obj = Foo()
        desc = Foo.__dict__["prop"]
        assert desc.get_node(obj) is obj

    def test_get_node_returns_owner_for_class(self) -> None:
        class Base:
            @mixed_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                return 42

        class Child(Base):
            pass

        desc = Base.__dict__["prop"]
        assert desc.get_node(Child) is Base

    def test_get_node_raises_on_none(self) -> None:
        class Foo:
            @mixed_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                return 42

        desc = Foo.__dict__["prop"]
        with pytest.raises(ContextFaultError):
            desc.get_node(None)

    def test_get_cache_uses_instance_dict_for_instance(self) -> None:
        class Foo:
            @mixed_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                return 42

        obj = Foo()
        desc = Foo.__dict__["prop"]
        cache = desc.get_cache(obj)
        assert "__instance_memoized__" in obj.__dict__
        assert obj.__dict__["__instance_memoized__"] is cache

    def test_get_cache_uses_class_dict_for_class(self) -> None:
        class Foo:
            @mixed_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                return 42

        desc = Foo.__dict__["prop"]
        cache = desc.get_cache(Foo)
        assert "__class_memoized__" in Foo.__dict__
        assert Foo.__dict__["__class_memoized__"] is cache

    def test_with_parent(self) -> None:
        class Parent:
            counter = 0

            @mixed_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                Parent.counter += 1
                return 42

        class Child(Parent):
            @mixed_parent_cached_property.with_parent
            def prop(self_or_cls: Any, parent_value: int) -> int:
                return parent_value + 10

        obj = Child()
        assert obj.prop == 52
        assert Child.prop == 52
        assert Parent.counter == 2

    def test_is_data_true(self) -> None:
        class Foo:
            @mixed_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                return 42

        assert Foo.__dict__["prop"].is_data is True


class TestMixedCachedProperty:
    """Tests for mixed_cached_property (plain variant)."""

    def test_instance_caches_on_instance(self) -> None:
        class Foo:
            counter = 0

            @mixed_cached_property
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.counter == 1

    def test_class_caches_on_accessed_class(self) -> None:
        class Base:
            counter = 0

            @mixed_cached_property
            def prop(self_or_cls: Any) -> str:
                Base.counter += 1
                return self_or_cls.__name__

        class Child(Base):
            pass

        assert Child.prop == "Child"
        assert Child.prop == "Child"
        assert Base.counter == 1
        assert "__class_memoized__" in Child.__dict__

    def test_get_node_returns_node_verbatim(self) -> None:
        class Foo:
            @mixed_cached_property
            def prop(self_or_cls: Any) -> int:
                return 42

        obj = Foo()
        desc = Foo.__dict__["prop"]
        assert desc.get_node(obj) is obj
        assert desc.get_node(Foo) is Foo

    def test_here_returns_parent_class(self) -> None:
        desc = mixed_cached_property.here
        assert desc is mixed_parent_cached_property

    def test_with_parent(self) -> None:
        class Parent:
            @mixed_cached_property
            def prop(self_or_cls: Any) -> str:
                return "parent"

        class Child(Parent):
            @mixed_cached_property.with_parent
            def prop(self_or_cls: Any, parent_value: str) -> str:
                return f"child_of_{parent_value}"

        assert Child.prop == "child_of_parent"
        assert Child().prop == "child_of_parent"


class TestPreParentCachedProperty:
    """Tests for pre_parent_cached_property."""

    def test_class_access_caches_on_owner(self) -> None:
        class Base:
            counter = 0

            @pre_parent_cached_property
            def prop(self_or_cls: Any) -> str:
                Base.counter += 1
                return "base"

        class Child(Base):
            pass

        assert Child.prop == "base"
        assert Child.prop == "base"
        assert Base.counter == 1
        assert "__class_memoized__" in Base.__dict__

    def test_instance_access_does_not_cache(self) -> None:
        class Foo:
            counter = 0

            @pre_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.counter == 2
        assert "__instance_memoized__" not in obj.__dict__

    def test_set_skips_instance_cache(self) -> None:
        class Foo:
            @pre_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                return 42

        desc = Foo.__dict__["prop"]
        obj = Foo()
        desc.__set__(obj, 100)
        cache = obj.__dict__.get("__instance_memoized__", {})
        assert "prop" not in cache

    def test_set_uses_class_cache(self) -> None:
        class Foo:
            @pre_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                return 42

        desc = Foo.__dict__["prop"]
        desc.__set__(Foo, 100)
        assert Foo.__dict__["__class_memoized__"]["prop"] == 100


class TestPreCachedProperty:
    """Tests for pre_cached_property (plain variant)."""

    def test_class_access_caches_on_accessed_class(self) -> None:
        class Base:
            counter = 0

            @pre_cached_property
            def prop(self_or_cls: Any) -> str:
                Base.counter += 1
                return self_or_cls.__name__

        class Child(Base):
            pass

        assert Child.prop == "Child"
        assert Child.prop == "Child"
        assert Base.counter == 1
        assert "__class_memoized__" in Child.__dict__

    def test_here_returns_parent_class(self) -> None:
        desc = pre_cached_property.here
        assert desc is pre_parent_cached_property


class TestPostParentCachedProperty:
    """Tests for post_parent_cached_property."""

    def test_instance_access_caches_on_instance(self) -> None:
        class Foo:
            counter = 0

            @post_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_class_access_does_not_cache(self) -> None:
        class Foo:
            counter = 0

            @post_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return 42

        assert Foo.prop == 42
        assert Foo.prop == 42
        assert Foo.counter == 2
        cache = Foo.__dict__["__class_memoized__"]
        assert "prop" not in cache

    def test_set_skips_class_cache(self) -> None:
        class Foo:
            @post_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                return 42

        desc = Foo.__dict__["prop"]
        desc.__set__(Foo, 100)
        cache = Foo.__dict__.get("__class_memoized__", {})
        assert "prop" not in cache

    def test_set_uses_instance_cache(self) -> None:
        class Foo:
            @post_parent_cached_property
            def prop(self_or_cls: Any) -> int:
                return 42

        desc = Foo.__dict__["prop"]
        obj = Foo()
        desc.__set__(obj, 100)
        assert obj.__dict__["__instance_memoized__"]["prop"] == 100


class TestPostCachedProperty:
    """Tests for post_cached_property (plain variant)."""

    def test_instance_access_caches_on_instance(self) -> None:
        class Foo:
            counter = 0

            @post_cached_property
            def prop(self_or_cls: Any) -> int:
                Foo.counter += 1
                return 42

        obj = Foo()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Foo.counter == 1

    def test_class_access_does_not_cache(self) -> None:
        class Base:
            counter = 0

            @post_cached_property
            def prop(self_or_cls: Any) -> str:
                Base.counter += 1
                return self_or_cls.__name__

        class Child(Base):
            pass

        assert Child.prop == "Child"
        assert Child.prop == "Child"
        assert Base.counter == 2
        cache = Child.__dict__.get("__class_memoized__", {})
        assert "prop" not in cache

    def test_here_returns_parent_class(self) -> None:
        desc = post_cached_property.here
        assert desc is post_parent_cached_property
