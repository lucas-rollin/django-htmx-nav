import pytest
from django.http import HttpResponse
from django.test import Client
from django.urls import path

from htmx_nav.testing import assert_shell_composition

pytestmark = pytest.mark.urls(__name__)


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
    """
    BUG: the tab-content swap response omits the id="tab-content" wrapper
    that HTMX's hx-target expects to swap into. Context could still match
    perfectly here since only markup structure is broken.
    """
    target = request.headers.get("HX-Target")
    tab_html = _tab_fragment()
    page_html = _page_fragment(tab_html)

    if target == "tab-content":
        return HttpResponse("<p>Tab body</p>")  # missing wrapper div
    if target == "page-content":
        return HttpResponse(page_html)
    return HttpResponse(f"<html><body>{page_html}</body></html>")


def diverging_content_view(request):
    """BUG: tab-shell response has different content than what's nested in full page."""
    target = request.headers.get("HX-Target")
    page_html = _page_fragment(_tab_fragment())

    if target == "tab-content":
        return HttpResponse('<div id="tab-content"><p>DIFFERENT body</p></div>')
    if target == "page-content":
        return HttpResponse(page_html)
    return HttpResponse(f"<html><body>{page_html}</body></html>")


urlpatterns = [
    path("consistent/", consistent_view),
    path("missing-wrapper/", missing_wrapper_view),
    path("diverging-content/", diverging_content_view),
]

PAGE_SHELL_KWARGS = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "page-content"}
TAB_SHELL_KWARGS = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "tab-content"}


def test_passes_when_composition_is_consistent():
    client = Client()
    responses = assert_shell_composition(
        client,
        "/consistent/",
        page_shell_kwargs=PAGE_SHELL_KWARGS,
        tab_shell_kwargs=TAB_SHELL_KWARGS,
    )
    assert set(responses) == {"full_reload", "page_shell", "tab_shell"}


def test_catches_missing_swap_wrapper():
    """The bug context-parity checking is blind to: no id="tab-content" in the fragment."""
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
        )
    message = str(exc_info.value)
    assert "tab_container_id" not in message  # sanity: no leaked internals
    assert "tab_shell response body" in message


def test_raises_clear_error_when_container_id_not_found():
    client = Client()
    with pytest.raises(AssertionError, match="Could not find any element with id"):
        assert_shell_composition(
            client,
            "/consistent/",
            page_shell_kwargs=PAGE_SHELL_KWARGS,
            tab_shell_kwargs=TAB_SHELL_KWARGS,
            tab_container_id="does-not-exist",
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
    )
