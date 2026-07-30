from typing import Any, Callable

import pytest
from django.test import Client
from django.urls import path

from htmx_nav.responses import make_shell_renderer

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
    page_target_id="page-content",
)


def record_tab_view(request):
    return render_shell(
        request, "tests/_page_nav.html", {"title": "Record #42"},
        partial_name="tab_content",
    )


urlpatterns = [
    path("nav-workspace/record/42/", record_tab_view),
]


# -- Parity testing utilities ---------------

def assert_shell_parity(
    client: Client,
    url: str,
    *,
    requests: dict[str, dict],
    checks: dict[str, Callable[[Any], Any]],
):
    """
    GETs `url` once per entry in `requests` (label -> kwargs passed to
    `client.get`), and asserts every function in `checks` extracts the
    same value from every response's template context.

    Returns {label: response} for further assertions.
    """
    responses = {label: client.get(url, **kwargs) for label, kwargs in requests.items()}

    for check_label, extract in checks.items():
        values = {label: extract(resp.context) for label, resp in responses.items()}
        baseline_label, baseline_value = next(iter(values.items()))
        for label, value in values.items():
            assert value == baseline_value, (
                f"Shell parity broken for check {check_label!r} at {url!r}: "
                f"{baseline_label!r} gave {baseline_value!r}, {label!r} gave {value!r}."
            )

    return responses


# -- Test constants ---------------

RECORD_TAB_REQUESTS = {
    "full_reload": {},
    "page_shell": {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "page-content"},
    "tab_shell": {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "tab-content"},
}

SHELL_CHECKS = {
    "sidebar_labels": lambda ctx: [i["label"] for i in ctx["nav"]["sidebar"] if i["active"]],
    "breadcrumbs": lambda ctx: [c["label"] for c in ctx["nav"]["breadcrumbs"]],
}


# -- Tests ---------------

def test_record_tab_shell_is_consistent_across_all_3_paths():
    client = Client()
    responses = assert_shell_parity(
        client, "/nav-workspace/record/42/",
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
            client, "/nav-workspace/record/42/",
            requests=RECORD_TAB_REQUESTS,
            checks={"artificially_diverging_check": lambda ctx: next(seen)},
        )