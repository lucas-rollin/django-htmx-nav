"""
Structural checks on the variant registry itself.

About whether the registry gives every variant a fair, addressable, switchable
slot. These would catch mistakes in `make_family`/`registry.py` before they
ever manifest as a confusing per-page test failure elsewhere.
"""

import pytest
from django.urls import reverse

from .conftest import ALL_VARIANTS


def test_variant_namespaces_are_unique():
    namespaces = [v.namespace for v in ALL_VARIANTS]
    assert len(namespaces) == len(set(namespaces)), "duplicate variant namespace(s)"


def test_variant_url_prefixes_are_unique():
    prefixes = [v.url_prefix for v in ALL_VARIANTS]
    assert len(prefixes) == len(set(prefixes)), "duplicate variant url_prefix(es)"


def test_every_group_has_at_least_one_variant():
    groups = {v.group for v in ALL_VARIANTS}
    assert groups == {"mpa", "vanilla", "package"}


@pytest.mark.django_db
def test_url_prefix_stripping_is_symmetric_across_variants(org_project):
    """
    core/static/core/js/variant-switch.js re-navigates to "the same
    page" under a different variant by stripping the *current*
    variant's url_prefix off window.location.pathname and re-prepending
    the *target* variant's url_prefix. That only works if every variant
    resolves the same view+args to a path with an identical "rest"
    after its own prefix is removed — this test is the server-side
    guarantee that assumption holds for every registered variant.
    """
    org, project = org_project
    rests = set()
    for variant in ALL_VARIANTS:
        path = reverse(
            f"{variant.namespace}:project_overview", args=[org.id, project.id]
        )
        prefix = "/" + variant.url_prefix
        assert path.startswith(prefix), (
            f"{variant.namespace}: {path!r} does not start with its own prefix {prefix!r}"
        )
        rests.add(path[len(prefix) :])

    assert len(rests) == 1, f"variant URL structure diverged across variants: {rests}"
