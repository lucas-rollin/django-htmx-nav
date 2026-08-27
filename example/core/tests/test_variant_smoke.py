"""
Cheap, broad status-code smoke tests across every variant/view/header combination.

This is deliberately dumber than test_shell_parity.py, no context assertions,
just "did it 200". This is because a single silent 500 on one axis combo
(e.g. the `_morph` suffix of some family) would otherwise only surface once
someone tries to run the actual experiments, which is a much more annoying
place to debug it.
"""

import pytest
from django.test import Client

from .conftest import (
    ALL_VARIANTS,
    HX_HEADERS_MAIN,
    HX_HEADERS_TAB,
    url_for,
    variant_ids,
)

HEADER_CASES = [({}, "full"), (HX_HEADERS_MAIN, "hx_main"), (HX_HEADERS_TAB, "hx_tab")]


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
@pytest.mark.parametrize(
    "headers,header_id", HEADER_CASES, ids=[h for _, h in HEADER_CASES]
)
def test_top_level_pages_all_200(variant, headers, header_id):
    client = Client()
    for view_name in ("overview", "staff_list", "org_list"):
        resp = client.get(url_for(variant, view_name), **headers)
        assert resp.status_code == 200, (
            f"{variant.namespace}:{view_name} [{header_id}] -> {resp.status_code}"
        )


@pytest.mark.django_db
@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=variant_ids(ALL_VARIANTS))
@pytest.mark.parametrize(
    "headers,header_id", HEADER_CASES, ids=[h for _, h in HEADER_CASES]
)
def test_project_and_ticket_pages_all_200(
    variant, org_project, ticket, headers, header_id
):
    client = Client()
    org, project = org_project
    org_args = [org.id]
    project_args = [org.id, project.id]
    ticket_args = [ticket.id]

    checks = [
        ("org_detail", org_args),
        ("project_overview", project_args),
        ("project_team", project_args),
        ("project_settings", project_args),
        ("kanban_board", project_args),
        ("ticket_list", project_args),
        ("ticket_detail", ticket_args),
        ("ticket_comments", ticket_args),
        ("ticket_activity", ticket_args),
        ("ticket_attachments", ticket_args),
    ]
    for view_name, args in checks:
        resp = client.get(url_for(variant, view_name, args), **headers)
        assert resp.status_code == 200, (
            f"{variant.namespace}:{view_name} [{header_id}] -> {resp.status_code}"
        )
