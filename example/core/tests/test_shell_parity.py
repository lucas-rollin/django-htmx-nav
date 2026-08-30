"""
Context parity tests across variants.

Every check here relies on the same property, documented on `Swap.context`
(see src/htmx_nav/swaps.py): a Swap's context is merged into the *page*
context as a fallback, unconditionally. MPA and vanilla-HTMX variants
get the same parity "for free" since they just build one flat context
dict and pass it to `render()` regardless of headers.
"""

import pytest
from django.test import Client

from htmx_nav.testing import assert_shell_parity

from .conftest import (
    ALL_VARIANTS,
    HX_HEADERS_SUBTAB,
    STANDARD_REQUESTS,
    TOP_LEVEL_REQUESTS,
    url_for,
    variant_ids,
)


def _assert_all_200(responses, label):
    for req_label, resp in responses.items():
        assert resp.status_code == 200, f"{label}/{req_label} -> {resp.status_code}"


# =============================================================================
# Top-level pages (no org/project in the URL)
# =============================================================================


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
def test_overview_shell_parity(variant):
    url = url_for(variant, "overview")
    responses = assert_shell_parity(
        Client(),
        url,
        requests=TOP_LEVEL_REQUESTS,
        checks={
            "active_page": lambda ctx: ctx["active_page"],
            "title": lambda ctx: ctx.get("title"),
        },
    )
    _assert_all_200(responses, variant.namespace)


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
def test_staff_list_shell_parity(variant):
    url = url_for(variant, "staff_list")
    responses = assert_shell_parity(
        Client(),
        url,
        requests=TOP_LEVEL_REQUESTS,
        checks={
            "active_page": lambda ctx: ctx["active_page"],
            "employee_count": lambda ctx: len(ctx["employees"]),
        },
    )
    _assert_all_200(responses, variant.namespace)


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
def test_org_list_shell_parity(variant):
    url = url_for(variant, "org_list")
    responses = assert_shell_parity(
        Client(),
        url,
        requests=TOP_LEVEL_REQUESTS,
        checks={"active_page": lambda ctx: ctx["active_page"]},
    )
    _assert_all_200(responses, variant.namespace)


# =============================================================================
# Org detail
# =============================================================================


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
def test_org_detail_shell_parity(variant, org_project):
    org, _ = org_project
    url = url_for(variant, "org_detail", [org.id])
    responses = assert_shell_parity(
        Client(),
        url,
        requests=TOP_LEVEL_REQUESTS,
        checks={
            "active_org_id": lambda ctx: ctx["active_org_id"],
            "breadcrumb_labels": lambda ctx: [c["label"] for c in ctx["breadcrumbs"]],
        },
    )
    _assert_all_200(responses, variant.namespace)


# =============================================================================
# Project pages (tabbed)
# =============================================================================


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
def test_project_overview_shell_parity(variant, org_project):
    org, project = org_project
    url = url_for(variant, "project_overview", [org.id, project.id])
    responses = assert_shell_parity(
        Client(),
        url,
        requests=STANDARD_REQUESTS,
        checks={
            "active_org_id": lambda ctx: ctx["active_org_id"],
            "active_project_id": lambda ctx: ctx["active_project_id"],
            "active_tab": lambda ctx: ctx["active_tab"],
            "breadcrumb_labels": lambda ctx: [c["label"] for c in ctx["breadcrumbs"]],
            "title": lambda ctx: ctx.get("title"),
        },
    )
    _assert_all_200(responses, variant.namespace)


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
def test_project_team_shell_parity(variant, org_project):
    org, project = org_project
    url = url_for(variant, "project_team", [org.id, project.id])
    responses = assert_shell_parity(
        Client(),
        url,
        requests=STANDARD_REQUESTS,
        checks={
            "active_tab": lambda ctx: ctx["active_tab"],
            "team_size": lambda ctx: len(list(ctx["team"])),
        },
    )
    _assert_all_200(responses, variant.namespace)


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
def test_kanban_board_shell_parity(variant, org_project):
    org, project = org_project
    url = url_for(variant, "kanban_board", [org.id, project.id])
    responses = assert_shell_parity(
        Client(),
        url,
        requests=STANDARD_REQUESTS,
        checks={
            "active_tab": lambda ctx: ctx["active_tab"],
            "column_keys": lambda ctx: sorted(ctx["columns"].keys()),
        },
    )
    _assert_all_200(responses, variant.namespace)


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
def test_ticket_list_shell_parity(variant, org_project):
    """Exercises the CBV path (ListView + ShellViewMixin for the
    htmx_nav families, plain ListView for mpa/vanilla)."""
    org, project = org_project
    url = url_for(variant, "ticket_list", [org.id, project.id])
    responses = assert_shell_parity(
        Client(),
        url,
        requests=STANDARD_REQUESTS,
        checks={
            "active_tab": lambda ctx: ctx["active_tab"],
            "current_status": lambda ctx: ctx["current_status"],
            "current_query": lambda ctx: ctx["current_query"],
        },
    )
    _assert_all_200(responses, variant.namespace)


# =============================================================================
# Project settings — exercises the *nested* subtab level too
# =============================================================================


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
def test_project_settings_default_subtab_parity(variant, org_project):
    org, project = org_project
    url = url_for(variant, "project_settings", [org.id, project.id])
    responses = assert_shell_parity(
        Client(),
        url,
        requests=STANDARD_REQUESTS,
        checks={
            "active_tab": lambda ctx: ctx["active_tab"],
            "active_subtab": lambda ctx: ctx["active_subtab"],
        },
    )
    _assert_all_200(responses, variant.namespace)


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
def test_project_settings_explicit_subtab_parity(variant, org_project):
    org, project = org_project
    url = url_for(
        variant, "project_settings_subtab", [org.id, project.id, "permissions"]
    )
    responses = assert_shell_parity(
        Client(),
        url,
        requests={
            "full_reload": {},
            "tab_shell": {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "tab-content"},
            "subtab_shell": HX_HEADERS_SUBTAB,
        },
        checks={"active_subtab": lambda ctx: ctx["active_subtab"]},
    )
    _assert_all_200(responses, variant.namespace)


# =============================================================================
# Ticket detail pages (a second tab bar, nested under a ticket)
# =============================================================================


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
def test_ticket_detail_shell_parity(variant, ticket):
    url = url_for(variant, "ticket_detail", [ticket.id])
    responses = assert_shell_parity(
        Client(),
        url,
        requests=STANDARD_REQUESTS,
        checks={
            "active_tab": lambda ctx: ctx["active_tab"],
            "assignee_name": lambda ctx: ctx["assignee_name"],
            "breadcrumb_labels": lambda ctx: [c["label"] for c in ctx["breadcrumbs"]],
        },
    )
    _assert_all_200(responses, variant.namespace)


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
def test_ticket_comments_shell_parity(variant, ticket):
    url = url_for(variant, "ticket_comments", [ticket.id])
    responses = assert_shell_parity(
        Client(),
        url,
        requests=STANDARD_REQUESTS,
        checks={
            "active_tab": lambda ctx: ctx["active_tab"],
            "comment_count": lambda ctx: len(ctx["comments"]),
        },
    )
    _assert_all_200(responses, variant.namespace)


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
def test_ticket_activity_shell_parity(variant, ticket):
    url = url_for(variant, "ticket_activity", [ticket.id])
    responses = assert_shell_parity(
        Client(),
        url,
        requests=STANDARD_REQUESTS,
        checks={"active_tab": lambda ctx: ctx["active_tab"]},
    )
    _assert_all_200(responses, variant.namespace)


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
def test_ticket_attachments_shell_parity(variant, ticket):
    url = url_for(variant, "ticket_attachments", [ticket.id])
    responses = assert_shell_parity(
        Client(),
        url,
        requests=STANDARD_REQUESTS,
        checks={"active_tab": lambda ctx: ctx["active_tab"]},
    )
    _assert_all_200(responses, variant.namespace)


# =============================================================================
# Wizard — GET-only parity (POST advances session state, out of scope here)
# =============================================================================


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
@pytest.mark.parametrize("step", ["basics", "assignment", "review"])
def test_ticket_wizard_step_shell_parity(variant, org_project, step):
    org, project = org_project
    url = url_for(variant, "ticket_wizard_step", [org.id, project.id, step])
    responses = assert_shell_parity(
        Client(),
        url,
        requests={
            "full_reload": {},
            "content_shell": {
                "HTTP_HX_REQUEST": "true",
                "HTTP_HX_TARGET": "main-content",
            },
            "steps_shell": {
                "HTTP_HX_REQUEST": "true",
                "HTTP_HX_TARGET": "steps-content",
            },
        },
        checks={
            "step": lambda ctx: ctx["step"],
            "breadcrumb_labels": lambda ctx: [c["label"] for c in ctx["breadcrumbs"]],
        },
    )
    _assert_all_200(responses, variant.namespace)
