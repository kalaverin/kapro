from __future__ import annotations

import pytest
from faker import Faker

from zx.prop.cached.instance import cached_property
from zx.prop.cached.klass import class_cached_property
from zx.prop.cached.mixed import mixed_cached_property
from zx.prop.cached.post import post_cached_property
from zx.prop.cached.pre import pre_cached_property
from zx.prop.class_property import class_property, mixed_property
from zx.prop.primitives import bound_property


@pytest.fixture
def sample_class(fake: Faker) -> type:
    """Dynamically created class with a bound_property descriptor."""

    class Sample:
        attr = bound_property(
            lambda _self: fake.pyint(min_value=1, max_value=100),
        )

    return Sample


@pytest.fixture
def sample_instance(sample_class: type) -> object:
    """Instance of sample_class."""
    return sample_class()


@pytest.fixture(
    params=[
        pytest.param(bound_property, id="bound-property"),
        pytest.param(class_property, id="class-property"),
        pytest.param(mixed_property, id="mixed-property"),
    ],
)
def descriptor_type(request: pytest.FixtureRequest) -> type:
    """Parameterized descriptor type from primitives/class_property."""
    return request.param


@pytest.fixture(
    params=[
        pytest.param(cached_property, id="cached-property"),
        pytest.param(class_cached_property, id="class-cached-property"),
        pytest.param(mixed_cached_property, id="mixed-cached-property"),
        pytest.param(pre_cached_property, id="pre-cached-property"),
        pytest.param(post_cached_property, id="post-cached-property"),
    ],
)
def cached_descriptor_type(request: pytest.FixtureRequest) -> type:
    """Parameterized cached descriptor type."""
    return request.param
