from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from htmx_nav.shell import make_shell_renderer
from htmx_nav.swaps import Swap
from htmx_nav.targeting import not_targeting

from .helpers import htmx_request, non_htmx_request

# =============================================================================
# make_shell_renderer — shell swap composition
# =============================================================================


@pytest.mark.parametrize("wrap_in_list", [True, False])
@patch("htmx_nav.shell.render_nav")
def test_shell_swap_is_first_followed_by_extra_swaps(mock_render_nav, wrap_in_list):
    mock_render_nav.return_value = MagicMock()
    render_shell = make_shell_renderer("tests/_shell.html")
    request = non_htmx_request(RequestFactory())
    extra = Swap("tests/_alert.html", target_id="alerts")

    render_shell(
        request,
        "tests/_page.html",
        {},
        extra_swaps=[extra] if wrap_in_list else extra,
    )

    swaps = mock_render_nav.call_args.kwargs["swaps"]
    assert swaps[0].template_name == "tests/_shell.html"
    assert swaps[-1] is extra


@patch("htmx_nav.shell.render_nav")
def test_shell_swap_carries_target_id_and_include_if(mock_render_nav):
    mock_render_nav.return_value = MagicMock()
    predicate = not_targeting("main-content")
    render_shell = make_shell_renderer(
        "tests/_shell.html", target_id="nav", include_if=predicate
    )
    request = non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {})

    shell_swap = mock_render_nav.call_args.kwargs["swaps"][0]
    assert shell_swap.target_id == "nav"
    assert shell_swap.include_if is predicate


@patch("htmx_nav.shell.render_nav")
def test_context_builder_merges_into_shell_context(mock_render_nav):
    mock_render_nav.return_value = MagicMock()
    render_shell = make_shell_renderer(
        "tests/_shell.html",
        context_builder=lambda request: {"nav": {"sidebar": []}},
    )
    request = non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {"title": "hi"})

    shell_swap = mock_render_nav.call_args.kwargs["swaps"][0]
    assert shell_swap.context["nav"] == {"sidebar": []}
    assert shell_swap.context["title"] == "hi"


def test_render_shell_merges_context_builder_end_to_end():
    render_shell = make_shell_renderer(
        shell_template="tests/_shell.html",
        context_builder=lambda request: {"nav": {"sidebar": []}},
    )
    rf = RequestFactory()
    request = rf.get("/workspace/")
    request.htmx = False  # type: ignore

    response = render_shell(request, "tests/_page.html", {"title": "hi"})
    assert response.context_data["title"] == "hi"  # type: ignore
    assert response.context_data["nav"] == {"sidebar": []}  # type: ignore


@patch("htmx_nav.swaps.render_to_string", return_value="<div>Shell</div>")
def test_make_shell_renderer_default_partial_and_per_call_override(mock_render):
    rf = RequestFactory()
    req = htmx_request(rf, target="main-content")

    render_shell = make_shell_renderer(
        shell_template="shell_nav.html",
        context_builder=lambda r: {"shell_key": "shell_val"},
        target_id="shell-nav",
        partial={"#main_part": "main-content", "#default_part": True},
    )

    response = render_shell(req, "dashboard.html", context={"page_key": "page_val"})
    assert response.template_name == "dashboard.html#main_part"
    assert response.context_data["shell_key"] == "shell_val"  # type: ignore
    assert response.context_data["page_key"] == "page_val"  # type: ignore

    response_override = render_shell(req, "dashboard.html", partial="#custom_part")
    assert response_override.template_name == "dashboard.html#custom_part"


# =============================================================================
# make_shell_renderer — title / merge precedence
# =============================================================================


@patch("htmx_nav.shell.render_nav")
def test_flat_merge_page_title_wins_over_shell_context_title(mock_render_nav):
    mock_render_nav.return_value = MagicMock()
    render_shell = make_shell_renderer(
        "tests/_shell.html",
        context_builder=lambda request: {
            "title": "Shell Title",
            "nav": {"sidebar": []},
        },
    )
    request = non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {"title": "Page Title"})

    page_context = mock_render_nav.call_args.args[2]
    shell_swap = mock_render_nav.call_args.kwargs["swaps"][0]
    assert page_context["title"] == "Page Title"
    assert shell_swap.context["title"] == "Page Title"


def test_flat_merge_shell_title_used_when_page_gives_no_title():
    render_shell = make_shell_renderer(
        "tests/_shell.html",
        context_builder=lambda request: {"title": "Shell Title"},
    )
    rf = RequestFactory()
    request = rf.get("/workspace/")
    request.htmx = False  # type: ignore

    response = render_shell(request, "tests/_page.html", {})
    assert response.context_data["title"] == "Shell Title"  # type: ignore


def test_explicit_title_kwarg_wins_over_flat_shell_context_title():
    render_shell = make_shell_renderer(
        "tests/_shell.html",
        context_builder=lambda request: {"title": "Shell Title"},
    )
    rf = RequestFactory()
    request = rf.get("/workspace/")
    request.htmx = False  # type: ignore

    response = render_shell(request, "tests/_page.html", {}, title="Explicit")
    assert response.context_data["title"] == "Explicit"  # type: ignore


def test_namespaced_shell_title_does_not_leak_into_page_context():
    render_shell = make_shell_renderer(
        "tests/_shell.html",
        context_builder=lambda request: {"title": "Shell Title"},
        namespace="shell",
    )
    rf = RequestFactory()
    request = rf.get("/workspace/")
    request.htmx = False  # type: ignore

    response = render_shell(request, "tests/_page.html", {})
    assert response.context_data["title"] is None  # type: ignore
    assert response.context_data["shell"]["title"] == "Shell Title"  # type: ignore


def test_namespaced_shell_title_coexists_with_explicit_page_title():
    render_shell = make_shell_renderer(
        "tests/_shell.html",
        context_builder=lambda request: {"title": "Shell Title"},
        namespace="shell",
    )
    rf = RequestFactory()
    request = rf.get("/workspace/")
    request.htmx = False  # type: ignore

    response = render_shell(request, "tests/_page.html", {}, title="Explicit")
    assert response.context_data["title"] == "Explicit"  # type: ignore
    assert response.context_data["shell"]["title"] == "Shell Title"  # type: ignore
