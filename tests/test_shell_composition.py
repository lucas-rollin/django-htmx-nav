import pytest
from django.http import HttpResponse
from django.test import Client
from django.urls import path

from htmx_nav.shortcuts import render_nav
from htmx_nav.swaps import Swap
from htmx_nav.targeting import targeting
from htmx_nav.testing import assert_shell_composition

pytestmark = pytest.mark.urls(__name__)

PAGE_SHELL_KWARGS = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "page-content"}
TAB_SHELL_KWARGS = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "tab-content"}


# =============================================================================
# Real Swap-based fixtures — exercise render_nav/render_with_swaps directly,
# so these tests fail if the Swap splitting logic breaks, not just if
# hand-rolled HttpResponse fixtures happen to agree.
# =============================================================================

_PARTIAL_SPEC = {"#tab_body": targeting("tab-content"), "#content": True}
_SIDEBAR_CONTEXT = {"nav": {"sidebar": [1, 2, 3]}}


def correct_composite_view(request):
    """Two Swaps, one per wrap style (oob + hx-partial), both consistent
    with what the full-page template renders directly for the same ids."""
    swaps = [
        Swap("tests/_shell_nav.html", _SIDEBAR_CONTEXT, target_id="sidebar"),
        Swap(
            "tests/_notification.html",
            {"message": "hi"},
            target_id="breadcrumbs",
            wrap="hx-partial",
        ),
    ]
    return render_nav(
        request,
        "tests/_composition_page.html",
        _SIDEBAR_CONTEXT,
        partial=_PARTIAL_SPEC,
        swaps=swaps,
    )


def oob_drift_view(request):
    """BUG: the sidebar Swap (wrap="oob") renders with different context
    than the full page — simulates a Swap whose data source silently
    diverged from the full-page render. Regression test for the gap where
    assert_shell_composition previously couldn't see OOB fragments at all."""
    swaps = [
        Swap("tests/_shell_nav.html", {"nav": {"sidebar": [1, 2]}}, target_id="sidebar")
    ]
    return render_nav(
        request,
        "tests/_composition_page.html",
        _SIDEBAR_CONTEXT,  # full page still renders 3 sidebar items
        partial=_PARTIAL_SPEC,
        swaps=swaps,
    )


def hx_partial_drift_view(request):
    """Same bug class as above, but on the hx-partial wrap path — confirms
    fragment splitting/comparison isn't accidentally oob-specific."""
    swaps = [
        Swap(
            "tests/_notification.html",
            {"message": "stale"},
            target_id="breadcrumbs",
            wrap="hx-partial",
        )
    ]
    return render_nav(
        request,
        "tests/_composition_page.html",
        _SIDEBAR_CONTEXT,  # full page renders message="hi", not "stale"
        partial=_PARTIAL_SPEC,
        swaps=swaps,
    )


# =============================================================================
# Hand-rolled fixtures — container-nesting bugs unrelated to fragment
# splitting; kept minimal/isolated so failures here can only come from the
# nesting checks themselves.
# =============================================================================


def _tab_fragment() -> str:
    return '<div id="tab-content"><p>Tab body</p></div>'


def _page_fragment(tab_html: str) -> str:
    return f'<div id="page-content"><nav>Breadcrumbs</nav>{tab_html}</div>'


def consistent_view(request):
    """Correctly composed: each swap level is a strict subset of the last."""
    target = request.headers.get("HX-Target")
    tab_html = _tab_fragment()
    page_html = _page_fragment(tab_html)

    if target == "tab-content":
        return HttpResponse(tab_html)
    if target == "page-content":
        return HttpResponse(page_html)
    return HttpResponse(f"<html><body>{page_html}</body></html>")


def missing_wrapper_view(request):
    """BUG: the tab-content swap response omits the id="tab-content"
    wrapper that HTMX's hx-target expects to swap into."""
    target = request.headers.get("HX-Target")
    tab_html = _tab_fragment()
    page_html = _page_fragment(tab_html)

    if target == "tab-content":
        return HttpResponse("<p>Tab body</p>")  # missing wrapper div
    if target == "page-content":
        return HttpResponse(page_html)
    return HttpResponse(f"<html><body>{page_html}</body></html>")


def diverging_content_view(request):
    """BUG: tab-shell response has different content than what's nested in
    the full page."""
    target = request.headers.get("HX-Target")
    page_html = _page_fragment(_tab_fragment())

    if target == "tab-content":
        return HttpResponse('<div id="tab-content"><p>DIFFERENT body</p></div>')
    if target == "page-content":
        return HttpResponse(page_html)
    return HttpResponse(f"<html><body>{page_html}</body></html>")


urlpatterns = [
    path("composite/", correct_composite_view),
    path("oob-drift/", oob_drift_view),
    path("hx-partial-drift/", hx_partial_drift_view),
    path("consistent/", consistent_view),
    path("missing-wrapper/", missing_wrapper_view),
    path("diverging-content/", diverging_content_view),
]


# =============================================================================
# Tests — real Swap fixtures
# =============================================================================


def test_passes_for_real_swap_response_with_oob_and_hx_partial_fragments():
    """The regression case: a genuine render_nav/Swap response, mixing both
    wrap styles, where everything actually agrees with the full page."""
    client = Client()
    responses = assert_shell_composition(
        client,
        "/composite/",
        page_shell_kwargs=PAGE_SHELL_KWARGS,
        tab_shell_kwargs=TAB_SHELL_KWARGS,
    )
    assert set(responses) == {"full_reload", "page_shell", "tab_shell"}


def test_catches_oob_fragment_drifted_from_full_page():
    client = Client()
    with pytest.raises(AssertionError, match="HTML mismatch"):
        assert_shell_composition(
            client,
            "/oob-drift/",
            page_shell_kwargs=PAGE_SHELL_KWARGS,
            tab_shell_kwargs=TAB_SHELL_KWARGS,
        )


def test_catches_hx_partial_fragment_drifted_from_full_page():
    client = Client()
    with pytest.raises(AssertionError, match="HTML mismatch"):
        assert_shell_composition(
            client,
            "/hx-partial-drift/",
            page_shell_kwargs=PAGE_SHELL_KWARGS,
            tab_shell_kwargs=TAB_SHELL_KWARGS,
        )


# =============================================================================
# Tests — hand-rolled container-nesting fixtures
# =============================================================================


def test_passes_when_composition_is_consistent():
    client = Client()
    responses = assert_shell_composition(
        client,
        "/consistent/",
        page_shell_kwargs=PAGE_SHELL_KWARGS,
        tab_shell_kwargs=TAB_SHELL_KWARGS,
        self_wrapped=True,
    )
    assert set(responses) == {"full_reload", "page_shell", "tab_shell"}


def test_catches_missing_swap_wrapper():
    client = Client()
    with pytest.raises(AssertionError, match="HTML mismatch"):
        assert_shell_composition(
            client,
            "/missing-wrapper/",
            page_shell_kwargs=PAGE_SHELL_KWARGS,
            tab_shell_kwargs=TAB_SHELL_KWARGS,
        )


def test_catches_diverging_tab_content():
    client = Client()
    with pytest.raises(AssertionError, match="HTML mismatch"):
        assert_shell_composition(
            client,
            "/diverging-content/",
            page_shell_kwargs=PAGE_SHELL_KWARGS,
            tab_shell_kwargs=TAB_SHELL_KWARGS,
        )


def test_error_message_identifies_which_fragments_mismatched():
    client = Client()
    with pytest.raises(AssertionError) as exc_info:
        assert_shell_composition(
            client,
            "/missing-wrapper/",
            page_shell_kwargs=PAGE_SHELL_KWARGS,
            tab_shell_kwargs=TAB_SHELL_KWARGS,
            self_wrapped=True,
        )
    message = str(exc_info.value)
    assert "tab_container_id" not in message
    assert "tab_shell primary content" in message


def test_raises_clear_error_when_container_id_not_found():
    client = Client()
    with pytest.raises(AssertionError, match="Could not find any element with id"):
        assert_shell_composition(
            client,
            "/consistent/",
            page_shell_kwargs=PAGE_SHELL_KWARGS,
            tab_shell_kwargs=TAB_SHELL_KWARGS,
            tab_container_id="does-not-exist",
            self_wrapped=True,
        )


def test_custom_container_ids():
    def custom_view(request):
        target = request.headers.get("HX-Target")
        tab_html = '<section id="my-tab"><p>x</p></section>'
        page_html = f'<article id="my-page">{tab_html}</article>'
        if target == "my-tab":
            return HttpResponse(tab_html)
        if target == "my-page":
            return HttpResponse(page_html)
        return HttpResponse(f"<html><body>{page_html}</body></html>")

    from django.urls import path as _path

    global urlpatterns
    urlpatterns = urlpatterns + [_path("custom/", custom_view)]

    client = Client()
    assert_shell_composition(
        client,
        "/custom/",
        page_shell_kwargs={"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "my-page"},
        tab_shell_kwargs={"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "my-tab"},
        page_container_id="my-page",
        tab_container_id="my-tab",
        self_wrapped=True,
    )
