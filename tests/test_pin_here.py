"""Comprehensive tests for the `.here` attribute on cached descriptors."""

from __future__ import annotations

import time

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


class TestClassCachedPropertyHere:
    """Tests for ``class_cached_property.here``."""

    def test_here_returns_parent_class(self) -> None:
        assert class_cached_property.here is class_parent_cached_property

    def test_here_child_access_first_caches_child_value_on_owner(self) -> None:
        class Base:
            counter = 0

            @class_cached_property.here
            def prop(cls) -> str:
                Base.counter += 1
                return cls.__name__

        class Child(Base):
            pass

        # First access on Child: function receives Child,
        # but cache stored on Base
        assert Child.prop == "Child"
        assert Base.prop == "Child"  # shared cache on Base
        assert Base.counter == 1
        assert "__class_memoized__" in Base.__dict__
        assert "__class_memoized__" not in Child.__dict__

    def test_here_base_access_first_caches_base_value(self) -> None:
        class Base:
            counter = 0

            @class_cached_property.here
            def prop(cls) -> str:
                Base.counter += 1
                return cls.__name__

        class Child(Base):
            pass

        assert Base.prop == "Base"
        assert Child.prop == "Base"  # hit shared cache
        assert Base.counter == 1

    def test_plain_vs_here_cache_location(self) -> None:
        class Base:
            counter = 0

            @class_cached_property
            def plain(cls) -> str:
                Base.counter += 1
                return cls.__name__

            @class_cached_property.here
            def here_prop(cls) -> str:
                Base.counter += 1
                return cls.__name__

        class Child(Base):
            pass

        assert Base.plain == "Base"
        assert Child.plain == "Child"
        assert Base.counter == 2

        Base.counter = 0
        assert Child.here_prop == "Child"
        assert Base.here_prop == "Child"
        assert Base.counter == 1

    def test_here_ttl(self) -> None:
        class Base:
            counter = 0

            @class_cached_property.here.ttl(0.01)
            def prop(cls) -> int:
                Base.counter += 1
                return 42

        class Child(Base):
            pass

        assert Child.prop == 42
        assert Base.counter == 1
        time.sleep(0.02)
        assert Base.prop == 42
        assert Base.counter == 2

    def test_here_with_parent(self) -> None:
        class Parent:
            counter = 0

            @class_cached_property.here
            def prop(cls) -> str:
                Parent.counter += 1
                return f"parent_{cls.__name__}"

        class Child(Parent):
            @class_cached_property.here.with_parent
            def prop(cls, parent_value: str) -> str:
                return f"child_{parent_value}"

        assert Child.prop == "child_parent_Child"
        assert Parent.counter == 1

    def test_here_manual_set_on_owner(self) -> None:
        class Base:
            @class_cached_property.here
            def prop(cls) -> str:
                return "original"

        class Child(Base):
            pass

        desc = Base.__dict__["prop"]
        desc.__set__(Base, "override")
        assert Base.prop == "override"
        assert Child.prop == "override"
        desc.__delete__(Base)
        assert Base.prop == "original"


class TestMixedCachedPropertyHere:
    """Tests for ``mixed_cached_property.here``."""

    def test_here_returns_parent_class(self) -> None:
        assert mixed_cached_property.here is mixed_parent_cached_property

    def test_here_instance_caches_on_instance(self) -> None:
        class Base:
            counter = 0

            @mixed_cached_property.here
            def prop(self_or_cls) -> int:
                Base.counter += 1
                return 42

        class Child(Base):
            pass

        obj = Child()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Base.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_here_class_caches_on_owner(self) -> None:
        class Base:
            counter = 0

            @mixed_cached_property.here
            def prop(self_or_cls) -> str:
                Base.counter += 1
                return "shared"

        class Child(Base):
            pass

        assert Child.prop == "shared"
        assert Child.prop == "shared"
        assert Base.counter == 1
        assert "__class_memoized__" in Base.__dict__
        assert "__class_memoized__" not in Child.__dict__

    def test_here_ttl(self) -> None:
        class Base:
            counter = 0

            @mixed_cached_property.here.ttl(0.01)
            def prop(self_or_cls) -> int:
                Base.counter += 1
                return 42

        obj = Base()
        assert obj.prop == 42
        time.sleep(0.02)
        assert obj.prop == 42
        assert Base.counter == 2

    def test_here_with_parent(self) -> None:
        class Parent:
            counter = 0

            @mixed_cached_property.here
            def prop(self_or_cls) -> int:
                Parent.counter += 1
                return 42

        class Child(Parent):
            @mixed_cached_property.here.with_parent
            def prop(self_or_cls, parent_value: int) -> int:
                return parent_value + 10

        assert Child.prop == 52
        assert Child().prop == 52
        assert Parent.counter == 2


class TestPreCachedPropertyHere:
    """Tests for ``pre_cached_property.here``."""

    def test_here_returns_parent_class(self) -> None:
        assert pre_cached_property.here is pre_parent_cached_property

    def test_here_class_caches_on_owner(self) -> None:
        class Base:
            counter = 0

            @pre_cached_property.here
            def prop(self_or_cls) -> str:
                Base.counter += 1
                return "shared"

        class Child(Base):
            pass

        assert Child.prop == "shared"
        assert Child.prop == "shared"
        assert Base.counter == 1
        assert "__class_memoized__" in Base.__dict__

    def test_here_instance_does_not_cache(self) -> None:
        class Base:
            counter = 0

            @pre_cached_property.here
            def prop(self_or_cls) -> int:
                Base.counter += 1
                return 42

        obj = Base()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Base.counter == 2
        cache = obj.__dict__["__instance_memoized__"]
        assert "prop" not in cache

    def test_here_ttl(self) -> None:
        class Base:
            counter = 0

            @pre_cached_property.here.ttl(0.01)
            def prop(self_or_cls) -> int:
                Base.counter += 1
                return 42

        assert Base.prop == 42
        time.sleep(0.02)
        assert Base.prop == 42
        assert Base.counter == 2


class TestPostCachedPropertyHere:
    """Tests for ``post_cached_property.here``."""

    def test_here_returns_parent_class(self) -> None:
        assert post_cached_property.here is post_parent_cached_property

    def test_here_instance_caches_on_instance(self) -> None:
        class Base:
            counter = 0

            @post_cached_property.here
            def prop(self_or_cls) -> int:
                Base.counter += 1
                return 42

        class Child(Base):
            pass

        obj = Child()
        assert obj.prop == 42
        assert obj.prop == 42
        assert Base.counter == 1
        assert "__instance_memoized__" in obj.__dict__

    def test_here_class_does_not_cache(self) -> None:
        class Base:
            counter = 0

            @post_cached_property.here
            def prop(self_or_cls) -> int:
                Base.counter += 1
                return 42

        assert Base.prop == 42
        assert Base.prop == 42
        assert Base.counter == 2
        cache = Base.__dict__["__class_memoized__"]
        assert "prop" not in cache

    def test_here_ttl_instance(self) -> None:
        class Base:
            counter = 0

            @post_cached_property.here.ttl(0.01)
            def prop(self_or_cls) -> int:
                Base.counter += 1
                return 42

        obj = Base()
        assert obj.prop == 42
        time.sleep(0.02)
        assert obj.prop == 42
        assert Base.counter == 2


class TestHereDiamondInheritance:
    """Diamond inheritance with ``.here`` should share one owner cache."""

    def test_diamond_class_cached_property_here(self) -> None:
        class A:
            counter = 0

            @class_cached_property.here
            def prop(cls) -> int:
                A.counter += 1
                return 42

        class B(A):
            pass

        class C(A):
            pass

        class D(B, C):
            pass

        assert A.prop == 42
        assert B.prop == 42
        assert C.prop == 42
        assert D.prop == 42
        assert A.counter == 1
        assert "__class_memoized__" in A.__dict__

    def test_diamond_mixed_cached_property_here(self) -> None:
        class A:
            counter = 0

            @mixed_cached_property.here
            def prop(self_or_cls) -> int:
                A.counter += 1
                return 42

        class B(A):
            pass

        class C(A):
            pass

        class D(B, C):
            pass

        assert B.prop == 42
        assert C.prop == 42
        assert D.prop == 42
        assert A.counter == 1

    def test_diamond_pre_cached_property_here(self) -> None:
        class A:
            counter = 0

            @pre_cached_property.here
            def prop(self_or_cls) -> int:
                A.counter += 1
                return 42

        class B(A):
            pass

        class C(A):
            pass

        class D(B, C):
            pass

        assert B.prop == 42
        assert C.prop == 42
        assert D.prop == 42
        assert A.counter == 1

    def test_diamond_post_cached_property_here_instance(self) -> None:
        class A:
            counter = 0

            @post_cached_property.here
            def prop(self_or_cls) -> int:
                A.counter += 1
                return 42

        class B(A):
            pass

        class C(A):
            pass

        class D(B, C):
            pass

        obj = D()
        assert obj.prop == 42
        assert obj.prop == 42
        assert A.counter == 1
