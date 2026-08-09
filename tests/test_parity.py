import pytest
from django.test import Client
from django.urls import path

from htmx_nav.responses import make_shell_renderer
from htmx_nav.testing import assert_shell_parity

# Tell pytest to use this module's urlpatterns
pytestmark = pytest.mark.urls(__name__)


# -- Setup for parity tests ---------------

render_shell = make_shell_renderer(
    "tests/_shell_nav.html",
    context_builder=lambda request: {
        "nav": {
            "sidebar": [{"label": "Record 42", "active": True}],
            "breadcrumbs": [{"label": "Workspace"}, {"label": "Record 42"}],
        }
    },
)


def record_tab_view(request):
    return render_shell(
        request,
        "tests/_page_nav.html",
        {"title": "Record #42"},
        partial_name="tab_content",
    )


urlpatterns = [
    path("nav-workspace/record/42/", record_tab_view),
]


# -- Test constants ---------------

RECORD_TAB_REQUESTS = {
    "full_reload": {},
    "page_shell": {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "page-content"},
    "tab_shell": {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "tab-content"},
}

SHELL_CHECKS = {
    "sidebar_labels": lambda ctx: [
        i["label"] for i in ctx["nav"]["sidebar"] if i["active"]
    ],
    "breadcrumbs": lambda ctx: [c["label"] for c in ctx["nav"]["breadcrumbs"]],
}


# -- Tests ---------------


def test_record_tab_shell_is_consistent_across_all_3_paths():
    client = Client()
    responses = assert_shell_parity(
        client,
        "/nav-workspace/record/42/",
        requests=RECORD_TAB_REQUESTS,
        checks=SHELL_CHECKS,
    )
    for label, resp in responses.items():
        assert resp.status_code == 200, label


def test_assert_shell_parity_fails_when_state_actually_diverges():
    client = Client()
    seen = iter([1, 2, 3])
    with pytest.raises(AssertionError, match="Shell parity broken"):
        assert_shell_parity(
            client,
            "/nav-workspace/record/42/",
            requests=RECORD_TAB_REQUESTS,
            checks={"artificially_diverging_check": lambda ctx: next(seen)},
        )
