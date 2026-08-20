from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from faker import Faker

from kapro.primitives import bound_property


@pytest.fixture
def descriptor_class_factory(fake: Faker) -> Callable[..., type]:
    """Factory: creates a class with a descriptor attached."""

    def _create(
        descriptor_type: type = bound_property,
        func: Callable[[object], object] | None = None,
        **overrides: object,
    ) -> type:
        if func is None:

            def _default(_self: object) -> int:
                return fake.pyint(min_value=1, max_value=100)

            func = _default
        cls = type(fake.pystr(min_chars=4, max_chars=8), (), {})
        setattr(
            cls,
            fake.pystr(min_chars=3, max_chars=6),
            descriptor_type(func),
        )
        for k, v in overrides.items():
            setattr(cls, k, v)
        return cls

    return _create


@pytest.fixture
def import_path_factory(fake: Faker) -> Callable[..., str]:
    """Factory: generates valid/invalid dotted import path strings."""

    def _create(valid: bool = True) -> str:
        if valid:
            return "os.path.join"
        first = fake.pystr(min_chars=4, max_chars=8)
        second = fake.pystr(min_chars=4, max_chars=8)
        return f"{first}.{second}"

    return _create


@pytest.fixture
def monkeypatch_target_factory(fake: Faker) -> Callable[..., object]:
    """Factory: creates a simple object with patchable attributes."""

    def _create(**overrides: object) -> object:
        class Target:
            attr1 = fake.pystr(min_chars=4, max_chars=8)
            attr2 = fake.pystr(min_chars=4, max_chars=8)

        for k, v in overrides.items():
            setattr(Target, k, v)
        return Target()

    return _create


@pytest.fixture
def signal_callback_factory(fake: Faker) -> Callable[..., Callable[[], Any]]:
    """Factory: creates no-arg callable that records invocation count."""

    def _create(
        raises: type[BaseException] | None = None,
    ) -> Callable[[], object]:
        def _callback() -> object:
            _callback.invocations += 1  # type: ignore[assignment][attr-defined]
            if raises is not None:
                raise raises("boom")
            return fake.pystr()

        _callback.invocations = 0  # type: ignore[assignment][attr-defined]
        return _callback

    return _create
