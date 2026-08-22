from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from htmx_nav.shell import make_shell_renderer
from htmx_nav.swaps import Swap
from htmx_nav.targeting import not_targeting

from .helpers import htmx_request, non_htmx_request

# =============================================================================
# make_shell_renderer — swap composition
# =============================================================================


@pytest.mark.parametrize("wrap_in_list", [True, False])
@patch("htmx_nav.shell.render_nav")
def test_shell_swaps_come_first_followed_by_extra_swaps(mock_render_nav, wrap_in_list):
    mock_render_nav.return_value = MagicMock()
    shell_swap = Swap("tests/_shell.html")
    render_shell = make_shell_renderer(lambda request: shell_swap)
    request = non_htmx_request(RequestFactory())
    extra = Swap("tests/_alert.html", target_id="alerts")

    render_shell(
        request,
        "tests/_page.html",
        {},
        extra_swaps=[extra] if wrap_in_list else extra,
    )

    swaps = mock_render_nav.call_args.kwargs["swaps"]
    assert swaps[0] is shell_swap
    assert swaps[-1] is extra


@patch("htmx_nav.shell.render_nav")
def test_swaps_builder_can_return_multiple_swaps_in_order(mock_render_nav):
    mock_render_nav.return_value = MagicMock()
    sidebar_swap = Swap("tests/_shell.html", target_id="sidebar")
    breadcrumb_swap = Swap("tests/_minimal.html", target_id="breadcrumbs")
    render_shell = make_shell_renderer(lambda request: [sidebar_swap, breadcrumb_swap])
    request = non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {})

    swaps = mock_render_nav.call_args.kwargs["swaps"]
    assert swaps == [sidebar_swap, breadcrumb_swap]


@patch("htmx_nav.shell.render_nav")
def test_swaps_builder_returning_none_yields_no_shell_swaps(mock_render_nav):
    mock_render_nav.return_value = MagicMock()
    render_shell = make_shell_renderer(lambda request: None)
    request = non_htmx_request(RequestFactory())
    extra = Swap("tests/_minimal.html", target_id="alerts")

    render_shell(request, "tests/_page.html", {}, extra_swaps=extra)

    assert mock_render_nav.call_args.kwargs["swaps"] == [extra]


@patch("htmx_nav.shell.render_nav")
def test_swaps_builder_is_called_once_per_render_with_request(mock_render_nav):
    mock_render_nav.return_value = MagicMock()
    calls = []

    def build(request):
        calls.append(request)
        return Swap("tests/_minimal.html", target_id="x")

    render_shell = make_shell_renderer(build)
    request = non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {})

    assert calls == [request]


@patch("htmx_nav.shell.render_nav")
def test_shell_swap_carries_its_own_target_id_and_include_if(mock_render_nav):
    mock_render_nav.return_value = MagicMock()
    predicate = not_targeting("main-content")
    shell_swap = Swap("tests/_shell.html", target_id="nav", include_if=predicate)
    render_shell = make_shell_renderer(lambda request: shell_swap)
    request = non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {})

    swap = mock_render_nav.call_args.kwargs["swaps"][0]
    assert swap.target_id == "nav"
    assert swap.include_if is predicate


@patch("htmx_nav.shell.render_nav")
def test_each_region_swap_keeps_independent_target_id_and_include_if(mock_render_nav):
    """Regression: the previous make_shell_renderer collapsed every
    region into one Swap with one target_id/include_if — one debug
    marker, one conditional. A builder returning several Swaps must
    keep each one's own target_id/include_if untouched, which is what
    restores per-region debug highlighting and per-region conditional
    inclusion (e.g. a tabs Swap included only on certain HX-Targets
    while the sidebar Swap always applies)."""
    mock_render_nav.return_value = MagicMock()
    tab_predicate = not_targeting("tab-content")
    sidebar_swap = Swap("tests/_shell.html", target_id="sidebar")
    tabs_swap = Swap("tests/_minimal.html", target_id="tabs", include_if=tab_predicate)
    render_shell = make_shell_renderer(lambda request: [sidebar_swap, tabs_swap])
    request = non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {})

    swaps = mock_render_nav.call_args.kwargs["swaps"]
    assert swaps[0].target_id == "sidebar"
    assert swaps[0].include_if is True
    assert swaps[1].target_id == "tabs"
    assert swaps[1].include_if is tab_predicate


def test_render_shell_end_to_end_renders_shell_swap_oob_and_page():
    render_shell = make_shell_renderer(
        lambda request: Swap(
            "tests/_shell.html", {"nav": {"sidebar": []}}, target_id="shell"
        )
    )
    request = htmx_request(RequestFactory())

    response = render_shell(request, "tests/_page.html", {"content": "hi"})
    response.render()
    assert b'<div id="shell" hx-swap-oob="innerHTML">' in response.content
    assert b'<div class="partial">hi</div>' in response.content


# =============================================================================
# make_shell_renderer — default partial / per-call override
# =============================================================================


@patch("htmx_nav.swaps.render_to_string", return_value="<div>Shell</div>")
def test_make_shell_renderer_default_partial_and_per_call_override(mock_render):
    req = htmx_request(RequestFactory(), target="main-content")

    render_shell = make_shell_renderer(
        lambda request: Swap(
            "shell_nav.html", {"shell_key": "shell_val"}, target_id="shell-nav"
        ),
        partial={"#main_part": "main-content", "#default_part": True},
    )

    response = render_shell(req, "dashboard.html", context={"page_key": "page_val"})
    assert response.template_name == "dashboard.html#main_part"
    assert response.context_data["page_key"] == "page_val"  # type: ignore
    # shell_key reaches page context via render_with_swaps' fallback
    # merge of every swap's context — see the title tests below.
    assert response.context_data["shell_key"] == "shell_val"  # type: ignore

    response_override = render_shell(req, "dashboard.html", partial="#custom_part")
    assert response_override.template_name == "dashboard.html#custom_part"


# =============================================================================
# make_shell_renderer — title via Swap context fallback
# =============================================================================
# There's no dedicated title/namespace handling in make_shell_renderer
# anymore: `render_with_swaps` already merges every swap's `context`
# into the page context as a fallback before rendering (see its
# docstring), so putting "title" in the builder's Swap context is how a
# make_shell_renderer caller gets a registry-driven title without any
# call site passing title= explicitly.


def test_title_from_shell_swap_context_used_when_no_kwarg_given():
    render_shell = make_shell_renderer(
        lambda request: Swap(
            "tests/_shell.html", {"title": "Shell Title", "nav": {"sidebar": []}}
        )
    )
    request = non_htmx_request(RequestFactory())

    response = render_shell(request, "tests/_page.html", {})
    assert response.context_data["title"] == "Shell Title"  # type: ignore


def test_explicit_page_context_title_wins_over_shell_swap_context_title():
    render_shell = make_shell_renderer(
        lambda request: Swap(
            "tests/_shell.html", {"title": "Shell Title", "nav": {"sidebar": []}}
        )
    )
    request = non_htmx_request(RequestFactory())

    response = render_shell(request, "tests/_page.html", {"title": "Page Title"})
    assert response.context_data["title"] == "Page Title"  # type: ignore


def test_explicit_title_kwarg_wins_over_shell_swap_context_title():
    render_shell = make_shell_renderer(
        lambda request: Swap("tests/_shell.html", {"title": "Shell Title"})
    )
    request = non_htmx_request(RequestFactory())

    response = render_shell(request, "tests/_page.html", {}, title="Explicit")
    assert response.context_data["title"] == "Explicit"  # type: ignore
