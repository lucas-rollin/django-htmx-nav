"""
Shared fixtures for cross-variant shell parity/composition tests.

Seeded data comes from core.apps.CoreConfig.ready() (shared in-memory
sqlite, deterministic Faker/random seed), so we look up an org/project
pair at test time rather than hardcoding IDs.
"""

import pytest
from core.models import Organization
from core.navigation.registry import VARIANTS

# Every axis combo of every htmx_nav_* family. These are the variants
# whose view source is known here, so context-key assumptions below
# are verifiable rather than guessed.
PACKAGE_VARIANTS = [v for v in VARIANTS.values() if v.group == "package"]

HX_HEADERS_MAIN = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "main-content"}
HX_HEADERS_TAB = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "tab-content"}
HX_HEADERS_SUBTAB = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "subtab-content"}


TARGET_AWARE_VARIANTS = [
    v
    for v in PACKAGE_VARIANTS
    if v.family in ("htmx_nav_atomic", "htmx_nav_declarative")
]
COARSE_VARIANTS = [
    v
    for v in PACKAGE_VARIANTS
    if v.family in ("htmx_nav_baseline", "htmx_nav_composite")
]


@pytest.fixture
def org_project(db):
    """First seeded org that actually has a project, and that project."""
    org = Organization.objects.filter(projects__isnull=False).distinct().first()
    assert org is not None, "seed data missing — check CoreConfig.ready()"
    project = org.projects.first()
    return org, project


def variant_ids(variants):
    return [v.namespace for v in variants]
