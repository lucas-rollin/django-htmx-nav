from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory, override_settings

from htmx_nav.responses import (
    Swap,
    _is_htmx_request,
    htmx_target_is,
    make_shell_renderer,
    not_targeting,
    render_htmx,
    targeting,
)


class FakeHtmxDetails:
    """Minimal stand-in for django-htmx's request.htmx."""

    def __init__(self, target=None):
        self.target = target

    def __bool__(self):
        return True


def _htmx_request(rf, target=None, path="/workspace/"):
    request = rf.get(path, HTTP_HX_REQUEST="true")
    request.htmx = FakeHtmxDetails(target=target)
    return request


def _non_htmx_request(rf, path="/workspace/"):
    request = rf.get(path)
    request.htmx = False
    return request


# =============================================================================
# _is_htmx_request
# =============================================================================


def test_is_htmx_request_uses_raw_header_without_django_htmx():
    rf = RequestFactory()
    plain = rf.get("/workspace/")
    assert _is_htmx_request(plain) is False

    htmx = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    assert _is_htmx_request(htmx) is True
    assert not hasattr(htmx, "htmx")


def test_is_htmx_request_true_when_htmx_flag_set():
    assert _is_htmx_request(_htmx_request(RequestFactory())) is True


def test_is_htmx_request_false_when_flag_false():
    assert _is_htmx_request(_non_htmx_request(RequestFactory())) is False


def test_is_htmx_request_false_when_attribute_missing():
    assert _is_htmx_request(RequestFactory().get("/workspace/")) is False


# =============================================================================
# htmx_target_is / targeting / not_targeting
# =============================================================================


def test_htmx_target_is_true_for_matching_target():
    request = _htmx_request(RequestFactory(), target="tab-content")
    assert htmx_target_is(request, "tab-content") is True


@pytest.mark.parametrize("target", ["tab-content", "#tab-content", "div#tab-content"])
def test_htmx_target_is_matches_v2_and_v4_formats(target):
    request = _htmx_request(RequestFactory(), target=target)
    assert htmx_target_is(request, "tab-content") is True


def test_htmx_target_is_false_when_no_match():
    request = _htmx_request(RequestFactory(), target="tab-content")
    assert htmx_target_is(request, "other-id") is False


def test_htmx_target_is_false_without_htmx_details():
    request = RequestFactory().get("/workspace/", HTTP_HX_REQUEST="true")
    assert htmx_target_is(request, "tab-content") is False


def test_targeting_predicate_matches_request_target():
    request = _htmx_request(RequestFactory(), target="tab-content")
    assert targeting("tab-content")(request) is True
    assert targeting("other-id")(request) is False


# =============================================================================
# Swap.applies_to / include_if
# =============================================================================


def test_swap_applies_by_default_with_no_include_if():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_minimal.html", {"value": "x"})
    assert swap.applies_to(request) is True


def test_not_targeting_skips_when_target_matches_ancestor():
    request = _htmx_request(RequestFactory(), target="main-content")
    swap = Swap(
        "tests/_minimal.html",
        target_id="tab-content",
        include_if=not_targeting("main-content"),
    )
    assert swap.applies_to(request) is False


def test_not_targeting_applies_when_target_is_unrelated():
    request = _htmx_request(RequestFactory(), target="something-else")
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
# render_htmx — full vs. partial rendering
# =============================================================================


def test_full_render_renders_whole_template():
    rf = RequestFactory()
    request = rf.get("/workspace/")
    response = render_htmx(request, "tests/_page.html", {"content": "hi"})
    response.render()
    assert b"FULL PAGE:" in response.content
    assert b'<div class="partial">hi</div>' in response.content


def test_htmx_request_renders_only_the_partial():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    response = render_htmx(request, "tests/_page.html", {"content": "hi"})
    response.render()
    assert b"FULL PAGE:" not in response.content
    assert response.content.strip() == b'<div class="partial">hi</div>'


# =============================================================================
# render_htmx — PartialSpec resolution
# =============================================================================


def test_active_partial_set_on_full_page_load_from_mapping_spec():
    rf = RequestFactory()
    request = rf.get("/workspace/")  # no HX-Request
    spec = {"#tab_content": targeting("tabs"), "#content": True}
    response = render_htmx(request, "tests/_page.html", {}, partial=spec)
    assert response.context_data["active_partial"] == "#content"  # type: ignore


def test_active_partial_set_on_htmx_request_matching_earlier_entry():
    request = _htmx_request(RequestFactory(), target="tabs")
    spec = {"#tab_content": targeting("tabs"), "#content": True}
    response = render_htmx(request, "tests/_page_nav.html", {}, partial=spec)
    response.render()
    assert response.context_data["active_partial"] == "#tab_content"  # type: ignore


def test_partial_spec_dotted_key_renders_standalone_template_not_block():
    request = _htmx_request(RequestFactory(), target="tab-content")
    spec = {"tests/_minimal.html": targeting("tab-content"), "#content": True}
    response = render_htmx(request, "tests/_page.html", {"value": "x"}, partial=spec)
    response.render()
    assert (
        response.content.strip() == b"x"
    )  # rendered _minimal.html directly, no #block


@patch("htmx_nav.responses.render_to_string", return_value="<div>Swap Content</div>")
def test_render_htmx_non_htmx_request_still_resolves_active_partial(mock_render):
    """active_partial is resolved on every request, not just HTMX ones, so a
    full-page template can highlight active nav state on first load."""
    rf = RequestFactory()
    req = _non_htmx_request(rf)

    response = render_htmx(
        req,
        "page.html",
        context={"page_var": 123},
        swaps=[Swap("sidebar.html", context={"swap_var": 456})],
        partial="#main_block",
    )

    assert response.template_name == "page.html"  # unresolved: not an HTMX request
    assert response.context_data["page_var"] == 123  # type: ignore
    assert response.context_data["swap_var"] == 456  # type: ignore
    assert response.context_data["active_partial"] == "#main_block"  # type: ignore


@patch("htmx_nav.responses.render_to_string", return_value="<div>OOB</div>")
def test_render_htmx_dict_partial_resolves_matching_entry(mock_render):
    rf = RequestFactory()
    req = _htmx_request(rf, target="tab-content")

    partial_spec = {
        "#tab_partial": "tab-content",
        "#main_partial": "main-content",
        "#default_partial": True,
    }

    response = render_htmx(
        req, "page.html", partial=partial_spec, title="Dynamic Title"
    )

    assert response.template_name == "page.html#tab_partial"
    assert response.context_data["active_partial"] == "#tab_partial"  # type: ignore

    # Manually drive the post-render callback to check the title append.
    response.content = b"<p>Tab Body</p>"
    for callback in response._post_render_callbacks:  # type: ignore
        response = callback(response)

    assert b"<p>Tab Body</p>" in response.content
    assert b"<title>Dynamic Title</title>" in response.content


# =============================================================================
# render_htmx — swaps
# =============================================================================


@pytest.mark.parametrize("wrap_in_list", [True, False])
def test_render_htmx_accepts_swap_with_or_without_list(wrap_in_list):
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_notification.html", {"message": "Saved"}, target_id="alerts")
    response = render_htmx(
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


def test_render_htmx_appends_swap_via_raw_header_without_django_htmx():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_shell.html", {"nav": {"sidebar": [1, 2]}})
    response = render_htmx(request, "tests/_page.html", {"content": "hi"}, swaps=[swap])
    response.render()
    assert b'<div class="partial">hi</div>' in response.content
    assert b"<nav>2</nav>" in response.content


def test_swap_without_target_id_does_not_wrap_fragment():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_notification.html", {"message": "Saved"})
    response = render_htmx(request, "tests/_page.html", {"title": "hi"}, swaps=[swap])
    response.render()
    assert b"<p>Saved</p>" in response.content
    assert b"hx-swap-oob" not in response.content


def test_swap_with_no_context_falls_back_to_empty_dict():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_notification.html")  # context=None
    response = render_htmx(request, "tests/_page.html", {"title": "hi"}, swaps=[swap])
    response.render()
    assert b"<p>no message</p>" in response.content


def test_render_htmx_omits_swap_whose_include_if_is_false():
    request = _htmx_request(RequestFactory(), target="main-content")
    swap = Swap(
        "tests/_notification.html",
        {"message": "Saved"},
        target_id="alerts",
        include_if=not_targeting("main-content"),
    )
    response = render_htmx(request, "tests/_page.html", {"title": "hi"}, swaps=[swap])
    response.render()
    assert b"Saved" not in response.content


def test_render_htmx_includes_swap_whose_include_if_is_true():
    request = _htmx_request(RequestFactory(), target="something-else")
    swap = Swap(
        "tests/_notification.html",
        {"message": "Saved"},
        target_id="alerts",
        include_if=not_targeting("main-content"),
    )
    response = render_htmx(request, "tests/_page.html", {"title": "hi"}, swaps=[swap])
    response.render()
    assert b"Saved" in response.content


@patch("htmx_nav.responses.render_to_string", return_value="<nav>Nav OOB</nav>")
def test_render_htmx_swap_execution_and_filtering(mock_render):
    rf = RequestFactory()
    req = _htmx_request(rf, target="main-content")

    swaps = [
        Swap(
            "sidebar.html",
            target_id="sidebar",
            include_if=not_targeting("main-content"),
        ),
        Swap("header.html", target_id="header", include_if=targeting("main-content")),
    ]

    response = render_htmx(req, "page.html", swaps=swaps, partial="#content")
    assert response.template_name == "page.html#content"

    response.content = b"<main>Main</main>"
    for callback in response._post_render_callbacks:  # type: ignore
        response = callback(response)

    # First swap skipped due to target filter, second swap rendered.
    assert (
        b'<main>Main</main><div id="header" hx-swap-oob="innerHTML"><nav>Nav OOB</nav></div>'
        in response.content
    )


def test_normalize_swaps_rejects_string_instead_of_iterating_characters():
    with pytest.raises(AttributeError):  # str has no .applies_to/.render
        render_htmx(
            RequestFactory().get("/", HTTP_HX_REQUEST="true"),
            "tests/_page.html",
            {},
            swaps="alerts",  # type: ignore
        ).render()


# =============================================================================
# render_htmx — title
# =============================================================================


def test_title_kwarg_added_to_context_on_full_render():
    rf = RequestFactory()
    request = rf.get("/workspace/")
    response = render_htmx(request, "tests/_page.html", {}, title="Hello")
    assert response.context_data["title"] == "Hello"  # type: ignore


def test_title_not_appended_as_tag_on_full_render():
    rf = RequestFactory()
    request = rf.get("/workspace/")
    response = render_htmx(request, "tests/_page.html", {}, title="Hello")
    response.render()
    assert b"<title>Hello</title>" not in response.content


def test_title_appended_as_tag_on_htmx_request():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    response = render_htmx(request, "tests/_page.html", {}, title="Hello")
    response.render()
    assert b"<title>Hello</title>" in response.content


def test_title_is_escaped_on_htmx_request():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    response = render_htmx(
        request, "tests/_page.html", {}, title="<script>bad()</script>"
    )
    response.render()
    assert b"<script>bad()</script>" not in response.content
    assert b"&lt;script&gt;" in response.content


def test_context_supplied_title_used_when_no_kwarg_given():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    response = render_htmx(request, "tests/_page.html", {"title": "From context"})
    response.render()
    assert response.context_data["title"] == "From context"  # type: ignore
    assert b"<title>From context</title>" in response.content


def test_explicit_title_kwarg_overrides_context_title():
    rf = RequestFactory()
    request = rf.get("/workspace/")
    response = render_htmx(
        request, "tests/_page.html", {"title": "From context"}, title="Explicit"
    )
    assert response.context_data["title"] == "Explicit"  # type: ignore


def test_no_title_anywhere_defaults_to_none_and_no_tag_appended():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    response = render_htmx(request, "tests/_page.html", {})
    response.render()
    assert response.context_data["title"] is None  # type: ignore
    assert b"<title>" not in response.content


# =============================================================================
# make_shell_renderer — shell swap composition
# =============================================================================


@pytest.mark.parametrize("wrap_in_list", [True, False])
@patch("htmx_nav.responses.render_htmx")
def test_shell_swap_is_first_followed_by_extra_swaps(mock_render_htmx, wrap_in_list):
    mock_render_htmx.return_value = MagicMock()
    render_shell = make_shell_renderer("tests/_shell.html")
    request = _non_htmx_request(RequestFactory())
    extra = Swap("tests/_alert.html", target_id="alerts")

    render_shell(
        request,
        "tests/_page.html",
        {},
        extra_swaps=[extra] if wrap_in_list else extra,
    )

    swaps = mock_render_htmx.call_args.kwargs["swaps"]
    assert swaps[0].template_name == "tests/_shell.html"
    assert swaps[-1] is extra


@patch("htmx_nav.responses.render_htmx")
def test_shell_swap_carries_target_id_and_include_if(mock_render_htmx):
    mock_render_htmx.return_value = MagicMock()
    predicate = not_targeting("main-content")
    render_shell = make_shell_renderer(
        "tests/_shell.html", target_id="nav", include_if=predicate
    )
    request = _non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {})

    shell_swap = mock_render_htmx.call_args.kwargs["swaps"][0]
    assert shell_swap.target_id == "nav"
    assert shell_swap.include_if is predicate


@patch("htmx_nav.responses.render_htmx")
def test_context_builder_merges_into_shell_context(mock_render_htmx):
    mock_render_htmx.return_value = MagicMock()
    render_shell = make_shell_renderer(
        "tests/_shell.html",
        context_builder=lambda request: {"nav": {"sidebar": []}},
    )
    request = _non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {"title": "hi"})

    shell_swap = mock_render_htmx.call_args.kwargs["swaps"][0]
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


@patch("htmx_nav.responses.render_to_string", return_value="<div>Shell</div>")
def test_make_shell_renderer_default_partial_and_per_call_override(mock_render):
    rf = RequestFactory()
    req = _htmx_request(rf, target="main-content")

    render_shell = make_shell_renderer(
        shell_template="shell_nav.html",
        context_builder=lambda r: {"shell_key": "shell_val"},
        target_id="shell-nav",
        partial={"#main_part": "main-content", "#default_part": True},
    )

    # Uses the factory's default partial spec.
    response = render_shell(req, "dashboard.html", context={"page_key": "page_val"})
    assert response.template_name == "dashboard.html#main_part"
    assert response.context_data["shell_key"] == "shell_val"  # type: ignore
    assert response.context_data["page_key"] == "page_val"  # type: ignore

    # Explicit per-call override.
    response_override = render_shell(req, "dashboard.html", partial="#custom_part")
    assert response_override.template_name == "dashboard.html#custom_part"


# =============================================================================
# make_shell_renderer — title / merge precedence
# =============================================================================


@patch("htmx_nav.responses.render_htmx")
def test_flat_merge_page_title_wins_over_shell_context_title(mock_render_htmx):
    mock_render_htmx.return_value = MagicMock()
    render_shell = make_shell_renderer(
        "tests/_shell.html",
        context_builder=lambda request: {
            "title": "Shell Title",
            "nav": {"sidebar": []},
        },
    )
    request = _non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {"title": "Page Title"})

    page_context = mock_render_htmx.call_args.args[2]
    shell_swap = mock_render_htmx.call_args.kwargs["swaps"][0]
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

@override_settings(HTMX_NAV_DEBUG_SWAPS=True)
def test_swap_render_includes_marker_script_when_debug_enabled():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_minimal.html", {"value": "x"}, target_id="alerts")
    html = swap.render(request)
    assert "getElementById(\"alerts\")" in html
    assert "hn-swap" in html


def test_swap_render_omits_marker_script_by_default():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_minimal.html", {"value": "x"}, target_id="alerts")
    html = swap.render(request)
    assert "<script>" not in html


@override_settings(HTMX_NAV_DEBUG_SWAPS=True)
def test_swap_render_omits_marker_when_no_target_id():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_minimal.html", {"value": "x"})  # no target_id
    html = swap.render(request)
    assert "<script>" not in html


@override_settings(HTMX_NAV_DEBUG_SWAPS=True)
def test_main_content_never_gets_debug_marker_only_swaps_do():
    request = _htmx_request(RequestFactory())
    swap = Swap("tests/_notification.html", {"message": "hi"}, target_id="alerts")
    response = render_htmx(request, "tests/_page.html", {"content": "x"}, swaps=[swap])
    response.render()
    # marker present (from the swap) ...
    assert b"getElementById" in response.content
    # ... but never anywhere near the main partial's own markup
    main_partial_html = response.content.split(b"<script>")[0]
    assert b'<div class="partial">' in main_partial_html
