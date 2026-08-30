"""
Shared fixtures for cross-variant tests to assert behaviour parity.

Spans *every* registered variant: MPA, vanilla HTMX (composite/atomic),
and django-htmx-nav (baseline/composite/atomic/declarative).

This is meant to support experiments comparing the variants so it's
a fair comparison.
"""

import pytest

from core.models import Organization
from core.navigation.registry import VARIANTS

ALL_VARIANTS = list(VARIANTS.values())

HX_HEADERS_MAIN = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "main-content"}
HX_HEADERS_TAB = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "tab-content"}
HX_HEADERS_SUBTAB = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "subtab-content"}
HX_HEADERS_STEPS = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "steps-content"}

# The three "reach the same page three different ways" pathways every
# family needs to agree on.
STANDARD_REQUESTS = {
    "full_reload": {},
    "main_shell": HX_HEADERS_MAIN,
    "tab_shell": HX_HEADERS_TAB,
}

TOP_LEVEL_REQUESTS = {
    "full_reload": {},
    "main_shell": HX_HEADERS_MAIN,
}


@pytest.fixture
def org_project(db):
    """First seeded org that actually has a project, and that project."""
    org = Organization.objects.filter(projects__isnull=False).distinct().first()
    assert org is not None, "seed data missing — check CoreConfig.ready()"
    project = org.projects.first()
    return org, project


@pytest.fixture
def ticket(org_project):
    """First seeded ticket on the org_project fixture's project."""
    _, project = org_project
    t = project.tickets.first()
    assert t is not None, "seed project has no tickets — check core.seed"
    return t


def variant_ids(variants):
    return [v.namespace for v in variants]


def url_for(variant, name, args=None):
    from django.urls import reverse

    return reverse(f"{variant.namespace}:{name}", args=args or [])
