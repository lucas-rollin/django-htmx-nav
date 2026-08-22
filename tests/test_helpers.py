import pytest
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory
from django.urls import NoReverseMatch, path

from htmx_nav import Swap, make_shell_renderer
from htmx_nav.helpers import cache_on_request, reverse_maybe

# Tell pytest to use this module's urlpatterns
pytestmark = pytest.mark.urls(__name__)

# -- Constants for test navigation setup ---------------

SIDEBAR_LINKS = [
    {"key": "workspace", "label": "Workspace", "view_name": "nav-workspace"},
]

BREADCRUMBS = {
    "nav-workspace": [("Workspace", None)],
    "nav-detail": [("Workspace", "nav-workspace"), ("Detail", None)],
}


# -- Helper functions ---------------


def build_nav_context(request: HttpRequest) -> dict:
    def _build():
        match = request.resolver_match
        view_name = match.view_name if match else ""
        kwargs = match.kwargs if match else {}

        sidebar = [
            {
                **link,
                "url": reverse_maybe(link["view_name"]),
                "active": link["view_name"] == view_name,
            }
            for link in SIDEBAR_LINKS
        ]
        breadcrumbs = [
            {
                "label": label,
                "url": reverse_maybe(crumb_view, kwargs, strict=False)
                if crumb_view
                else None,
            }
            for label, crumb_view in BREADCRUMBS.get(view_name, [])
        ]
        return {"sidebar": sidebar, "breadcrumbs": breadcrumbs}

    return cache_on_request(request, "_test_nav", _build)


render_shell = make_shell_renderer(
    lambda request: Swap("tests/_shell.html", {"nav": build_nav_context(request)})
)


# -- Test Views ---------------


def workspace_view(request: HttpRequest, pk=None):
    """View for testing nav-workspace and nav-detail URLs."""
    return render_shell(request, "tests/_page.html", {"title": "hi"})


# -- URL Configuration ---------------

urlpatterns = [
    path("workspace/", lambda r: HttpResponse("ok"), name="workspace"),
    path("detail/<int:pk>/", lambda r: HttpResponse("ok"), name="detail"),
    path("nav-workspace/", workspace_view, name="nav-workspace"),
    path("nav-detail/<int:pk>/", workspace_view, name="nav-detail"),
]


# -- Tests for helpers ---------------


def test_reverse_maybe_returns_none_for_falsy_view_name():
    assert reverse_maybe(None) is None
    assert reverse_maybe("") is None


def test_reverse_maybe_strict_default_raises_like_plain_reverse():
    with pytest.raises(NoReverseMatch):
        reverse_maybe("detail", {"bogus": 1})


def test_reverse_maybe_non_strict_degrades_gracefully_on_mismatch():
    assert reverse_maybe("workspace", {"pk": 7}, strict=False) == "/workspace/"


def test_reverse_maybe_resolves_normally_with_matching_kwargs():
    assert reverse_maybe("detail", {"pk": 3}) == "/detail/3/"


def test_cache_on_request_calls_builder_once():
    rf = RequestFactory()
    request = rf.get("/")
    calls = []

    def build():
        calls.append(1)
        return {"n": len(calls)}

    first = cache_on_request(request, "_test_cache_key", build)
    second = cache_on_request(request, "_test_cache_key", build)
    assert first is second
    assert len(calls) == 1


def test_cache_on_request_handles_falsy_cached_values():
    rf = RequestFactory()
    request = rf.get("/")
    calls = []

    def build():
        calls.append(1)
        return []

    first = cache_on_request(request, "_test_cache_key", build)
    second = cache_on_request(request, "_test_cache_key", build)
    assert first == [] and second == []
    assert len(calls) == 1
