import pytest
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


# =============================================================================
# Swap.delete
# =============================================================================


def test_delete_produces_bare_oob_delete_markup():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap.delete("target-to-delete")
    html = swap.render(request)
    assert html == '<div id="target-to-delete" hx-swap-oob="delete"></div>'


def test_delete_sets_swap_style_and_wrap():
    swap = Swap.delete("box")
    assert swap.swap_style == "delete"
    assert swap.wrap == "oob"
    assert swap.template_name is None


def test_delete_ignores_configured_default_wrap_setting():
    with override_settings(HTMX_NAV_DEFAULT_SWAP_WRAP="hx-partial"):
        swap = Swap.delete("box")
    assert swap.wrap == "oob"


def test_delete_respects_include_if():
    request = htmx_request(RequestFactory(), target="main-content")
    swap = Swap.delete("box", include_if=not_targeting("main-content"))
    assert swap.applies_to(request) is False


def test_delete_omits_debug_marker_even_when_enabled():
    with override_settings(HTMX_NAV_DEBUG_SWAPS=True):
        request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
        swap = Swap.delete("box")
        html = swap.render(request)
    assert html == '<div id="box" hx-swap-oob="delete"></div>'
    assert "<script>" not in html


def test_delete_without_target_id_raises():
    with pytest.raises(ValueError, match="requires target_id"):
        Swap(swap_style="delete")


def test_non_delete_swap_without_template_name_raises():
    with pytest.raises(
        ValueError,
        match="template_name or content is required unless swap_style='delete'",
    ):
        Swap(target_id="box")


# =============================================================================
# Swap.text
# =============================================================================


def test_text_produces_oob_wrapped_content():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap.text("count", "3")
    html = swap.render(request)
    assert html == '<div id="count" hx-swap-oob="innerHTML">3</div>'


def test_text_escapes_plain_strings():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap.text("label", "<b>3</b>")
    html = swap.render(request)
    assert html == '<div id="label" hx-swap-oob="innerHTML">&lt;b&gt;3&lt;/b&gt;</div>'


def test_text_respects_mark_safe():
    from django.utils.safestring import mark_safe

    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap.text("label", mark_safe("<b>3</b>"))
    html = swap.render(request)
    assert html == '<div id="label" hx-swap-oob="innerHTML"><b>3</b></div>'


def test_text_respects_swap_style_and_wrap():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap.text("count", "3", swap_style="outerHTML", wrap="hx-partial")
    html = swap.render(request)
    assert html == '<hx-partial hx-target="#count" hx-swap="outerHTML">3</hx-partial>'


@override_settings(HTMX_NAV_DEBUG_SWAPS=True)
def test_text_includes_debug_marker_when_enabled():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap.text("count", "3")
    html = swap.render(request)
    assert 'getElementById("count")' in html


def test_text_and_template_name_together_raises():
    with pytest.raises(ValueError, match="only one of template_name or content"):
        Swap(template_name="tests/_minimal.html", content="3", target_id="box")


def test_neither_text_nor_template_name_raises():
    with pytest.raises(ValueError, match="template_name or content is required"):
        Swap(target_id="box")
