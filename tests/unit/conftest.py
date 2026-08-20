from __future__ import annotations

import sys
from collections.abc import Callable, Generator

import pytest


@pytest.fixture
def monkey_target(monkeypatch_target_factory: Callable[..., object]) -> object:
    """Fresh object with patchable attributes for Monkey tests."""
    return monkeypatch_target_factory()


@pytest.fixture
def import_target(import_path_factory: Callable[..., str]) -> str:
    """Valid dotted import path string for importer tests."""
    return import_path_factory(valid=True)


@pytest.fixture
def sys_path_snapshot() -> Generator[list[str]]:
    """Yields a copy of sys.path and restores it after the test."""
    original = list(sys.path)
    yield original
    sys.path[:] = original
