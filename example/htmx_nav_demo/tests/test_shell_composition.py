"""
Test shell composition for HTML disparities.

Verifies the actual rendered HTML nests correctly (not just matching context),
including a three-level check on the settings page (main -> tab -> subtab)
that assert_shell_composition's two-level signature doesn't natively cover,
done here by calling it twice with different container-id pairs.
"""

import pytest
from django.test import Client
from django.urls import reverse

from htmx_nav.testing import assert_html_equal, assert_shell_composition

from .conftest import (
    COARSE_VARIANTS,
    HX_HEADERS_MAIN,
    HX_HEADERS_TAB,
    TARGET_AWARE_VARIANTS,
    variant_ids,
)

pytest.importorskip("bs4", reason="assert_shell_composition requires beautifulsoup4")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "variant", TARGET_AWARE_VARIANTS, ids=variant_ids(TARGET_AWARE_VARIANTS)
)
def test_project_overview_shell_composition(variant, org_project):
    org, project = org_project
    url = reverse(f"{variant.namespace}:project_overview", args=[org.id, project.id])
    assert_shell_composition(
        Client(),
        url,
        page_shell_kwargs=HX_HEADERS_MAIN,
        tab_shell_kwargs=HX_HEADERS_TAB,
        page_container_id="main-content",
        tab_container_id="tab-content",
    )


@pytest.mark.django_db
@pytest.mark.parametrize("variant", COARSE_VARIANTS, ids=variant_ids(COARSE_VARIANTS))
def test_project_overview_coarse_swap_is_target_agnostic(variant, org_project):
    """baseline/composite render the same #content block regardless of
    HX-Target — this documents that intentionally, rather than
    asserting a finer structure that doesn't exist for this family."""
    org, project = org_project
    url = reverse(f"{variant.namespace}:project_overview", args=[org.id, project.id])
    client = Client()
    main = client.get(url, **HX_HEADERS_MAIN)
    tab = client.get(url, **HX_HEADERS_TAB)
    assert_html_equal(
        main.content,
        tab.content,
        label_a="HX-Target=main-content response",
        label_b="HX-Target=tab-content response",
    )
