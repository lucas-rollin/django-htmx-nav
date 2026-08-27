"""
Test shell parity, whether different requests provide the same context.

The nav context — active org/project, active tab, breadcrumbs, title,
must be identical whether reached via full reload, a main-content HTMX
swap, or a tab-content HTMX swap.

hx-select/morph only change *how* a fragment gets applied client-side
(attributes on the response HTML); they never touch what render_shell
puts into the template context. So this suite is agnostic to axis flags.
"""

import pytest
from django.test import Client
from django.urls import reverse

from htmx_nav.testing import assert_shell_parity

from .conftest import HX_HEADERS_MAIN, HX_HEADERS_TAB, PACKAGE_VARIANTS, variant_ids


@pytest.mark.django_db
@pytest.mark.parametrize("variant", PACKAGE_VARIANTS, ids=variant_ids(PACKAGE_VARIANTS))
def test_project_overview_shell_parity(variant, org_project):
    org, project = org_project
    url = reverse(f"{variant.namespace}:project_overview", args=[org.id, project.id])
    client = Client()

    responses = assert_shell_parity(
        client,
        url,
        requests={
            "full_reload": {},
            "main_shell": HX_HEADERS_MAIN,
            "tab_shell": HX_HEADERS_TAB,
        },
        checks={
            "active_org_id": lambda ctx: ctx["active_org_id"],
            "active_project_id": lambda ctx: ctx["active_project_id"],
            "active_tab": lambda ctx: ctx["active_tab"],
            "breadcrumb_labels": lambda ctx: [c["label"] for c in ctx["breadcrumbs"]],
            "title": lambda ctx: ctx["title"],
        },
    )

    for label, resp in responses.items():
        assert resp.status_code == 200, f"{variant.namespace}/{label}"


@pytest.mark.django_db
@pytest.mark.parametrize("variant", PACKAGE_VARIANTS, ids=variant_ids(PACKAGE_VARIANTS))
def test_project_team_shell_parity(variant, org_project):
    """Second page, mainly to catch parity bugs that only show up once
    a page pulls in extra context (team members) alongside the shared
    nav context — a regression here wouldn't necessarily show up on
    project_overview above."""
    org, project = org_project
    url = reverse(f"{variant.namespace}:project_team", args=[org.id, project.id])
    client = Client()

    assert_shell_parity(
        client,
        url,
        requests={
            "full_reload": {},
            "main_shell": HX_HEADERS_MAIN,
            "tab_shell": HX_HEADERS_TAB,
        },
        checks={
            "active_org_id": lambda ctx: ctx["active_org_id"],
            "active_project_id": lambda ctx: ctx["active_project_id"],
            "active_tab": lambda ctx: ctx["active_tab"],
            "breadcrumb_labels": lambda ctx: [c["label"] for c in ctx["breadcrumbs"]],
        },
    )
