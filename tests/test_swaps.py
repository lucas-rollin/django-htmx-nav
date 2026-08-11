from django.test import RequestFactory, override_settings

from htmx_nav.swaps import Swap, _normalize_swaps
from htmx_nav.targeting import not_targeting

from .helpers import htmx_request

# =============================================================================
# Swap.applies_to / include_if
# =============================================================================


def test_swap_applies_by_default_with_no_include_if():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_minimal.html", {"value": "x"})
    assert swap.applies_to(request) is True


def test_not_targeting_skips_when_target_matches_ancestor():
    request = htmx_request(RequestFactory(), target="main-content")
    swap = Swap(
        "tests/_minimal.html",
        target_id="tab-content",
        include_if=not_targeting("main-content"),
    )
    assert swap.applies_to(request) is False


def test_not_targeting_applies_when_target_is_unrelated():
    request = htmx_request(RequestFactory(), target="something-else")
    swap = Swap(
        "tests/_minimal.html",
        target_id="step-content",
        include_if=not_targeting("main-content", "tab-content"),
    )
    assert swap.applies_to(request) is True


# =============================================================================
# Swap.render — OOB / hx-partial wrapping
# =============================================================================


def test_swap_default_wrap_is_oob_with_innerhtml():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_minimal.html", {"value": "x"}, target_id="box")
    html = swap.render(request)
    assert html == '<div id="box" hx-swap-oob="innerHTML">x</div>'


def test_swap_custom_swap_style_on_oob():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap(
        "tests/_minimal.html", {"value": "x"}, target_id="box", swap_style="outerHTML"
    )
    html = swap.render(request)
    assert html == '<div id="box" hx-swap-oob="outerHTML">x</div>'


def test_swap_wrap_hx_partial_uses_explicit_target_and_swap():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap(
        "tests/_minimal.html", {"value": "x"}, target_id="box", wrap="hx-partial"
    )
    html = swap.render(request)
    assert html == '<hx-partial hx-target="#box" hx-swap="innerHTML">x</hx-partial>'


def test_swap_wrap_hx_partial_with_custom_swap_style():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap(
        "tests/_minimal.html",
        {"value": "x"},
        target_id="box",
        wrap="hx-partial",
        swap_style="beforeend",
    )
    html = swap.render(request)
    assert html == '<hx-partial hx-target="#box" hx-swap="beforeend">x</hx-partial>'


def test_swap_without_target_id_ignores_wrap_and_swap_style():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap(
        "tests/_minimal.html", {"value": "x"}, wrap="hx-partial", swap_style="outerHTML"
    )
    html = swap.render(request)
    assert html == "x"


@override_settings(HTMX_NAV_DEFAULT_SWAP_WRAP="hx-partial")
def test_default_swap_wrap_setting_changes_default():
    swap = Swap("tests/_minimal.html", target_id="box")
    assert swap.wrap == "hx-partial"


def test_explicit_wrap_overrides_setting():
    with override_settings(HTMX_NAV_DEFAULT_SWAP_WRAP="hx-partial"):
        swap = Swap("tests/_minimal.html", target_id="box", wrap="oob")
    assert swap.wrap == "oob"


# =============================================================================
# Swap.render — debug marker script
# =============================================================================


@override_settings(HTMX_NAV_DEBUG_SWAPS=True)
def test_swap_render_includes_marker_script_when_debug_enabled():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_minimal.html", {"value": "x"}, target_id="alerts")
    html = swap.render(request)
    assert 'getElementById("alerts")' in html
    assert "hn-swap" in html


def test_swap_render_omits_marker_script_by_default():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_minimal.html", {"value": "x"}, target_id="alerts")
    html = swap.render(request)
    assert "<script>" not in html


@override_settings(HTMX_NAV_DEBUG_SWAPS=True)
def test_swap_render_omits_marker_when_no_target_id():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_minimal.html", {"value": "x"})
    html = swap.render(request)
    assert "<script>" not in html


# =============================================================================
# _normalize_swaps
# =============================================================================


def test_normalize_swaps_none_returns_empty_list():
    assert _normalize_swaps(None) == []


def test_normalize_swaps_wraps_single_swap_in_a_list():
    swap = Swap("tests/_minimal.html")
    assert _normalize_swaps(swap) == [swap]


def test_normalize_swaps_passes_through_list_and_tuple():
    swaps = [Swap("tests/_minimal.html"), Swap("tests/_minimal.html")]
    assert _normalize_swaps(swaps) == swaps
    assert _normalize_swaps(tuple(swaps)) == swaps


def test_normalize_swaps_does_not_iterate_a_bare_string_into_characters():
    # Regression: a bare string is Sequence-like; must not be exploded
    # into a list of single-character "swaps".
    assert _normalize_swaps("alerts") == ["alerts"]  # type: ignore
