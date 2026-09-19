from unittest.mock import patch

import pytest
from django.test import RequestFactory, override_settings

from htmx_nav.partials import ReplacePrefix
from htmx_nav.shortcuts import render_nav
from htmx_nav.swaps import Swap
from htmx_nav.targeting import not_targeting, targeting

from .helpers import htmx_request, non_htmx_request

# =============================================================================
# render_nav — full vs. partial rendering
# =============================================================================


def test_full_render_renders_whole_template():
    rf = RequestFactory()
    request = rf.get("/workspace/")
    response = render_nav(request, "tests/_page.html", {"content": "hi"})
    response.render()
    assert b"FULL PAGE:" in response.content
    assert b'<div class="partial">hi</div>' in response.content


def test_htmx_request_renders_only_the_partial():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    response = render_nav(request, "tests/_page.html", {"content": "hi"})
    response.render()
    assert b"FULL PAGE:" not in response.content
    assert response.content.strip() == b'<div class="partial">hi</div>'


# =============================================================================
# render_nav — PartialSpec resolution (integration through TemplateResponse)
# =============================================================================


def test_active_partial_set_on_full_page_load_from_mapping_spec():
    rf = RequestFactory()
    request = rf.get("/workspace/")
    spec = {"#tab_content": targeting("tabs"), "#content": True}
    response = render_nav(request, "tests/_page.html", {}, partial=spec)
    assert response.context_data["active_partial"] == "#content"  # type: ignore


def test_active_partial_set_on_htmx_request_matching_earlier_entry():
    request = htmx_request(RequestFactory(), target="tabs")
    spec = {"#tab_content": targeting("tabs"), "#content": True}
    response = render_nav(request, "tests/_page_nav.html", {}, partial=spec)
    response.render()
    assert response.context_data["active_partial"] == "#tab_content"  # type: ignore


def test_partial_spec_dotted_key_renders_standalone_template_not_block():
    request = htmx_request(RequestFactory(), target="tab-content")
    spec = {"tests/_minimal.html": targeting("tab-content"), "#content": True}
    response = render_nav(request, "tests/_page.html", {"value": "x"}, partial=spec)
    response.render()
    assert response.content.strip() == b"x"


@patch("htmx_nav.swaps.render_to_string", return_value="<div>Swap Content</div>")
def test_render_nav_non_htmx_request_still_resolves_active_partial(mock_render):
    """active_partial is resolved on every request, not just HTMX ones, so a
    full-page template can highlight active nav state on first load."""
    rf = RequestFactory()
    req = non_htmx_request(rf)

    response = render_nav(
        req,
        "page.html",
        context={"page_var": 123},
        swaps=[Swap("sidebar.html", context={"swap_var": 456})],
        partial="#main_block",
    )

    assert response.template_name == "page.html"
    assert response.context_data["page_var"] == 123  # type: ignore
    assert response.context_data["swap_var"] == 456  # type: ignore
    assert response.context_data["active_partial"] == "#main_block"  # type: ignore


@patch("htmx_nav.swaps.render_to_string", return_value="<div>OOB</div>")
def test_render_nav_dict_partial_resolves_matching_entry(mock_render):
    rf = RequestFactory()
    req = htmx_request(rf, target="tab-content")

    partial_spec = {
        "#tab_partial": "tab-content",
        "#main_partial": "main-content",
        "#default_partial": True,
    }

    response = render_nav(req, "page.html", partial=partial_spec, title="Dynamic Title")

    assert response.template_name == "page.html#tab_partial"
    assert response.context_data["active_partial"] == "#tab_partial"  # type: ignore

    response.content = b"<p>Tab Body</p>"
    for callback in response._post_render_callbacks:  # type: ignore
        response = callback(response)

    assert b"<p>Tab Body</p>" in response.content
    assert b"<title>Dynamic Title</title>" in response.content


# =============================================================================
# render_nav — swaps
# =============================================================================


@pytest.mark.parametrize("wrap_in_list", [True, False])
def test_render_nav_accepts_swap_with_or_without_list(wrap_in_list):
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_notification.html", {"message": "Saved"}, target_id="alerts")
    response = render_nav(
        request,
        "tests/_page.html",
        {"content": "hi"},
        swaps=[swap] if wrap_in_list else swap,
    )
    response.render()
    assert (
        b'<div id="alerts" hx-swap-oob="innerHTML"><p>Saved</p></div>'
        in response.content
    )


def test_render_nav_appends_swap_via_raw_header_without_django_htmx():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_shell.html", {"nav": {"sidebar": [1, 2]}})
    response = render_nav(request, "tests/_page.html", {"content": "hi"}, swaps=[swap])
    response.render()
    assert b'<div class="partial">hi</div>' in response.content
    assert b"<nav>2</nav>" in response.content


def test_swap_without_target_id_does_not_wrap_fragment():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_notification.html", {"message": "Saved"})
    response = render_nav(request, "tests/_page.html", {"title": "hi"}, swaps=[swap])
    response.render()
    assert b"<p>Saved</p>" in response.content
    assert b"hx-swap-oob" not in response.content


def test_swap_with_no_context_falls_back_to_empty_dict():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_notification.html")
    response = render_nav(request, "tests/_page.html", {"title": "hi"}, swaps=[swap])
    response.render()
    assert b"<p>no message</p>" in response.content


def test_render_nav_omits_swap_whose_include_if_is_false():
    request = htmx_request(RequestFactory(), target="main-content")
    swap = Swap(
        "tests/_notification.html",
        {"message": "Saved"},
        target_id="alerts",
        include_if=not_targeting("main-content"),
    )
    response = render_nav(request, "tests/_page.html", {"title": "hi"}, swaps=[swap])
    response.render()
    assert b"Saved" not in response.content


def test_render_nav_includes_swap_whose_include_if_is_true():
    request = htmx_request(RequestFactory(), target="something-else")
    swap = Swap(
        "tests/_notification.html",
        {"message": "Saved"},
        target_id="alerts",
        include_if=not_targeting("main-content"),
    )
    response = render_nav(request, "tests/_page.html", {"title": "hi"}, swaps=[swap])
    response.render()
    assert b"Saved" in response.content


@patch("htmx_nav.swaps.render_to_string", return_value="<nav>Nav OOB</nav>")
def test_render_nav_swap_execution_and_filtering(mock_render):
    rf = RequestFactory()
    req = htmx_request(rf, target="main-content")

    swaps = [
        Swap(
            "sidebar.html",
            target_id="sidebar",
            include_if=not_targeting("main-content"),
        ),
        Swap("header.html", target_id="header", include_if=targeting("main-content")),
    ]

    response = render_nav(req, "page.html", swaps=swaps, partial="#content")
    assert response.template_name == "page.html#content"

    response.content = b"<main>Main</main>"
    for callback in response._post_render_callbacks:  # type: ignore
        response = callback(response)

    assert (
        b'<main>Main</main><div id="header" hx-swap-oob="innerHTML"><nav>Nav OOB</nav></div>'
        in response.content
    )


def test_render_nav_surfaces_error_for_a_bare_string_swap():
    # See test_normalize_swaps_does_not_iterate_a_bare_string_into_characters
    # in test_swaps.py — a string swaps= value isn't exploded into chars,
    # it just fails loudly downstream since str has no .applies_to/.render.
    with pytest.raises(AttributeError):
        render_nav(
            RequestFactory().get("/", HTTP_HX_REQUEST="true"),
            "tests/_page.html",
            {},
            swaps="alerts",  # type: ignore
        ).render()


@override_settings(HTMX_NAV_DEBUG_SWAPS=True)
def test_main_content_never_gets_debug_marker_only_swaps_do():
    request = htmx_request(RequestFactory())
    swap = Swap("tests/_notification.html", {"message": "hi"}, target_id="alerts")
    response = render_nav(request, "tests/_page.html", {"content": "x"}, swaps=[swap])
    response.render()
    assert b"getElementById" in response.content
    main_partial_html = response.content.split(b"<script>")[0]
    assert b'<div class="partial">' in main_partial_html


# =============================================================================
# render_nav — title
# =============================================================================


def test_title_kwarg_added_to_context_on_full_render():
    rf = RequestFactory()
    request = rf.get("/workspace/")
    response = render_nav(request, "tests/_page.html", {}, title="Hello")
    assert response.context_data["title"] == "Hello"  # type: ignore


def test_title_not_appended_as_tag_on_full_render():
    rf = RequestFactory()
    request = rf.get("/workspace/")
    response = render_nav(request, "tests/_page.html", {}, title="Hello")
    response.render()
    assert b"<title>Hello</title>" not in response.content


def test_title_appended_as_tag_on_htmx_request():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    response = render_nav(request, "tests/_page.html", {}, title="Hello")
    response.render()
    assert b"<title>Hello</title>" in response.content


def test_title_is_escaped_on_htmx_request():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    response = render_nav(
        request, "tests/_page.html", {}, title="<script>bad()</script>"
    )
    response.render()
    assert b"<script>bad()</script>" not in response.content
    assert b"&lt;script&gt;" in response.content


def test_context_supplied_title_used_when_no_kwarg_given():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    response = render_nav(request, "tests/_page.html", {"title": "From context"})
    response.render()
    assert response.context_data["title"] == "From context"  # type: ignore
    assert b"<title>From context</title>" in response.content


def test_explicit_title_kwarg_overrides_context_title():
    rf = RequestFactory()
    request = rf.get("/workspace/")
    response = render_nav(
        request, "tests/_page.html", {"title": "From context"}, title="Explicit"
    )
    assert response.context_data["title"] == "Explicit"  # type: ignore


def test_no_title_anywhere_defaults_to_none_and_no_tag_appended():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    response = render_nav(request, "tests/_page.html", {})
    response.render()
    assert response.context_data["title"] is None  # type: ignore
    assert b"<title>" not in response.content


# =============================================================================
# render_nav(partial=None) — verbatim rendering with swaps
# =============================================================================


def test_render_nav_with_partial_none_renders_template_verbatim_no_partial_resolution():
    request = htmx_request(RequestFactory())
    response = render_nav(request, "tests/_minimal.html", {"value": "x"}, partial=None)
    response.render()
    assert response.template_name == "tests/_minimal.html"
    assert response.content.strip() == b"x"


def test_render_nav_with_partial_none_appends_swaps():
    request = htmx_request(RequestFactory())
    swap = Swap("tests/_notification.html", {"message": "Saved"}, target_id="alerts")
    response = render_nav(
        request, "tests/_minimal.html", {"value": "x"}, partial=None, swaps=swap
    )
    response.render()
    assert b'<div id="alerts"' in response.content


def test_render_nav_respects_custom_default_partial_setting():
    from django.test import override_settings

    request = htmx_request(RequestFactory())
    with override_settings(HTMX_NAV_DEFAULT_PARTIAL="#custom_block"):
        response = render_nav(request, "tests/_page.html", {"content": "hi"})
        assert response.template_name == "tests/_page.html#custom_block"


# --- ReplacePrefix --------------------------------------


def test_render_nav_with_replace_prefix_htmx_resolves_and_renders():
    rf = RequestFactory()
    request = htmx_request(rf)
    transformer = ReplacePrefix("_page.html", "_minimal.html")

    response = render_nav(
        request, "tests/_page.html", {"value": "transformed"}, partial=transformer
    )
    response.render()
    assert response.template_name == "tests/_minimal.html"
    assert response.content.strip() == b"transformed"


def test_render_nav_with_replace_prefix_non_htmx_renders_full_page():
    rf = RequestFactory()
    request = non_htmx_request(rf)
    transformer = ReplacePrefix("_page.html", "_minimal.html")

    response = render_nav(
        request, "tests/_page.html", {"content": "hi"}, partial=transformer
    )
    response.render()
    assert response.template_name == "tests/_page.html"
    assert b"FULL PAGE:" in response.content


def test_render_nav_with_replace_prefix_in_settings():
    rf = RequestFactory()
    request = htmx_request(rf)
    transformer = ReplacePrefix("_page.html", "_minimal.html")

    with override_settings(HTMX_NAV_DEFAULT_PARTIAL=transformer):
        response = render_nav(request, "tests/_page.html", {"value": "from_setting"})
        response.render()
        assert response.template_name == "tests/_minimal.html"
        assert response.content.strip() == b"from_setting"
