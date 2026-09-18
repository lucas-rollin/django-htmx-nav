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
    render_shell = make_shell_renderer(shell_swap)
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
def test_swaps_can_be_a_static_list_with_no_callable_wrapper(mock_render_nav):
    """The common case — a fixed set of shell Swaps — needs no
    `lambda request: ...` boilerplate; a bare Swap/list/tuple is
    accepted directly."""
    mock_render_nav.return_value = MagicMock()
    sidebar_swap = Swap("tests/_shell.html", target_id="sidebar")
    breadcrumb_swap = Swap("tests/_minimal.html", target_id="breadcrumbs")
    render_shell = make_shell_renderer([sidebar_swap, breadcrumb_swap])
    request = non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {})

    swaps = mock_render_nav.call_args.kwargs["swaps"]
    assert swaps == [sidebar_swap, breadcrumb_swap]


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
def test_swaps_none_yields_no_shell_swaps(mock_render_nav):
    mock_render_nav.return_value = MagicMock()
    render_shell = make_shell_renderer(None)
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
def test_static_swaps_are_not_called_even_though_swap_is_frozen(mock_render_nav):
    """A bare Swap must be used as-is, never invoked — Swap instances
    aren't callable, but this guards the dispatch logic itself (static
    vs. callable) rather than relying on that accidentally raising."""
    mock_render_nav.return_value = MagicMock()
    shell_swap = Swap("tests/_shell.html", target_id="shell")
    render_shell = make_shell_renderer(shell_swap)
    request = non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {})

    swaps = mock_render_nav.call_args.kwargs["swaps"]
    assert swaps == [shell_swap]


@patch("htmx_nav.shell.render_nav")
def test_shell_swap_carries_its_own_target_id_and_include_if(mock_render_nav):
    mock_render_nav.return_value = MagicMock()
    predicate = not_targeting("main-content")
    shell_swap = Swap("tests/_shell.html", target_id="nav", include_if=predicate)
    render_shell = make_shell_renderer(shell_swap)
    request = non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {})

    swap = mock_render_nav.call_args.kwargs["swaps"][0]
    assert swap.target_id == "nav"
    assert swap.include_if is predicate


@patch("htmx_nav.shell.render_nav")
def test_each_region_swap_keeps_independent_target_id_and_include_if(mock_render_nav):
    """Regression: a builder returning several Swaps must keep each
    one's own target_id/include_if untouched."""
    mock_render_nav.return_value = MagicMock()
    tab_predicate = not_targeting("tab-content")
    sidebar_swap = Swap("tests/_shell.html", target_id="sidebar")
    tabs_swap = Swap("tests/_minimal.html", target_id="tabs", include_if=tab_predicate)
    render_shell = make_shell_renderer([sidebar_swap, tabs_swap])
    request = non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {})

    swaps = mock_render_nav.call_args.kwargs["swaps"]
    assert swaps[0].target_id == "sidebar"
    assert swaps[0].include_if is True
    assert swaps[1].target_id == "tabs"
    assert swaps[1].include_if is tab_predicate


def test_render_shell_end_to_end_renders_shell_swap_oob_and_page():
    render_shell = make_shell_renderer(
        Swap("tests/_shell.html", {"nav": {"sidebar": []}}, target_id="shell")
    )
    request = htmx_request(RequestFactory())

    response = render_shell(request, "tests/_page.html", {"content": "hi"})
    response.render()
    assert b'<div id="shell" hx-swap-oob="innerHTML">' in response.content
    assert b'<div class="partial">hi</div>' in response.content


# =============================================================================
# make_shell_renderer — per-request Swap context via the callable form
# =============================================================================


def resolve_context(request) -> dict:
    """Stand-in for a real nav-context resolver (e.g. reading
    request.resolver_match.kwargs, hitting the DB via cache_on_request,
    etc.) — anything that legitimately differs between two requests
    hitting the same view."""
    label = request.META.get("HTTP_X_TEST_LABEL", "default")
    return {"label": label}


def test_callable_swaps_builder_resolves_fresh_context_per_request():
    render_shell = make_shell_renderer(
        lambda request: Swap(
            "tests/_minimal.html", resolve_context(request), target_id="shell"
        )
    )

    request_a = non_htmx_request(RequestFactory())
    request_a.META["HTTP_X_TEST_LABEL"] = "alpha"
    request_b = non_htmx_request(RequestFactory())
    request_b.META["HTTP_X_TEST_LABEL"] = "beta"

    swap_a = render_shell.__wrapped__ if False else None
    with patch("htmx_nav.shell.render_nav") as mock_render_nav:
        mock_render_nav.return_value = MagicMock()
        render_shell(request_a, "tests/_page.html", {})
        render_shell(request_b, "tests/_page.html", {})

    swap_a = mock_render_nav.call_args_list[0].kwargs["swaps"][0]
    swap_b = mock_render_nav.call_args_list[1].kwargs["swaps"][0]
    assert swap_a.context == {"label": "alpha"}
    assert swap_b.context == {"label": "beta"}


def test_callable_swaps_builder_context_renders_correctly_end_to_end():
    render_shell = make_shell_renderer(
        lambda request: Swap(
            "tests/_minimal.html",
            {"value": resolve_context(request)["label"]},
            target_id="shell",
        )
    )
    request = htmx_request(RequestFactory())
    request.META["HTTP_X_TEST_LABEL"] = "gamma"

    response = render_shell(request, "tests/_page.html", {"content": "hi"})
    response.render()
    assert b'<div id="shell" hx-swap-oob="innerHTML">gamma</div>' in response.content


def test_static_swap_context_does_not_vary_across_requests():
    """Contrast case: a static Swap's context is fixed at construction
    time and identical for every request, unlike the callable form
    above."""
    shell_swap = Swap("tests/_minimal.html", {"value": "fixed"}, target_id="shell")
    render_shell = make_shell_renderer(shell_swap)

    request_a = non_htmx_request(RequestFactory())
    request_b = non_htmx_request(RequestFactory())

    with patch("htmx_nav.shell.render_nav") as mock_render_nav:
        mock_render_nav.return_value = MagicMock()
        render_shell(request_a, "tests/_page.html", {})
        render_shell(request_b, "tests/_page.html", {})

    swap_a = mock_render_nav.call_args_list[0].kwargs["swaps"][0]
    swap_b = mock_render_nav.call_args_list[1].kwargs["swaps"][0]
    assert swap_a is swap_b is shell_swap
    assert swap_a.context == {"value": "fixed"}


# =============================================================================
# make_shell_renderer — default partial / per-call override
# =============================================================================


@patch("htmx_nav.swaps.render_to_string", return_value="<div>Shell</div>")
def test_make_shell_renderer_default_partial_and_per_call_override(mock_render):
    req = htmx_request(RequestFactory(), target="main-content")

    render_shell = make_shell_renderer(
        Swap("shell_nav.html", {"shell_key": "shell_val"}, target_id="shell-nav"),
        partial={"#main_part": "main-content", "#default_part": True},
    )

    response = render_shell(req, "dashboard.html", context={"page_key": "page_val"})
    assert response.template_name == "dashboard.html#main_part"
    assert response.context_data["page_key"] == "page_val"  # type: ignore
    assert response.context_data["shell_key"] == "shell_val"  # type: ignore

    response_override = render_shell(req, "dashboard.html", partial="#custom_part")
    assert response_override.template_name == "dashboard.html#custom_part"


# =============================================================================
# make_shell_renderer — title via Swap context fallback
# =============================================================================


def test_title_from_shell_swap_context_used_when_no_kwarg_given():
    render_shell = make_shell_renderer(
        Swap("tests/_shell.html", {"title": "Shell Title", "nav": {"sidebar": []}})
    )
    request = non_htmx_request(RequestFactory())

    response = render_shell(request, "tests/_page.html", {})
    assert response.context_data["title"] == "Shell Title"  # type: ignore


def test_explicit_page_context_title_wins_over_shell_swap_context_title():
    render_shell = make_shell_renderer(
        Swap("tests/_shell.html", {"title": "Shell Title", "nav": {"sidebar": []}})
    )
    request = non_htmx_request(RequestFactory())

    response = render_shell(request, "tests/_page.html", {"title": "Page Title"})
    assert response.context_data["title"] == "Page Title"  # type: ignore


def test_explicit_title_kwarg_wins_over_shell_swap_context_title():
    render_shell = make_shell_renderer(
        Swap("tests/_shell.html", {"title": "Shell Title"})
    )
    request = non_htmx_request(RequestFactory())

    response = render_shell(request, "tests/_page.html", {}, title="Explicit")
    assert response.context_data["title"] == "Explicit"  # type: ignore


def test_make_shell_renderer_respects_custom_default_partial_setting():
    from django.test import override_settings

    with override_settings(HTMX_NAV_DEFAULT_PARTIAL="#custom_shell_block"):
        render_shell = make_shell_renderer([])
        request = htmx_request(RequestFactory())
        response = render_shell(request, "tests/_page.html", {"content": "hi"})
        assert response.template_name == "tests/_page.html#custom_shell_block"
