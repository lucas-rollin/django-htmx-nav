from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from htmx_nav.responses import (
    Swap,
    _is_htmx_request,
    htmx_target_is,
    make_shell_renderer,
    render_htmx,
    skip_if_target_in,
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


# --- _is_htmx_request / htmx_target_is -------------------------------------


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


# --- render_htmx: full vs. partial rendering --------------------------------


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


# --- render_htmx: swaps -----------------------------------------------------


@pytest.mark.parametrize("wrap_in_list", [True, False])
def test_render_htmx_accepts_swap_with_or_without_list(wrap_in_list):
    """swaps= can be a single Swap or a list; either way it renders and,
    with target_id set, gets OOB-wrapped."""
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_notification.html", {"message": "Saved"}, target_id="alerts")
    response = render_htmx(
        request,
        "tests/_page.html",
        {"title": "hi"},
        swaps=[swap] if wrap_in_list else swap,
    )
    response.render()
    assert b'<div id="alerts" hx-swap-oob="true"><p>Saved</p></div>' in response.content


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


# --- Swap.include_if / skip_if_target_in ------------------------------------


def test_swap_applies_by_default_with_no_include_if():
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_minimal.html", {"value": "x"})
    assert swap.applies_to(request) is True


def test_skip_if_target_in_skips_when_target_matches_ancestor():
    request = _htmx_request(RequestFactory(), target="main-content")
    swap = Swap(
        "tests/_minimal.html",
        target_id="tab-content",
        include_if=skip_if_target_in("main-content"),
    )
    assert swap.applies_to(request) is False


def test_skip_if_target_in_applies_when_target_is_unrelated():
    request = _htmx_request(RequestFactory(), target="something-else")
    swap = Swap(
        "tests/_minimal.html",
        target_id="step-content",
        include_if=skip_if_target_in("main-content", "tab-content"),
    )
    assert swap.applies_to(request) is True


def test_render_htmx_omits_swap_whose_include_if_is_false():
    request = _htmx_request(RequestFactory(), target="main-content")
    swap = Swap(
        "tests/_notification.html",
        {"message": "Saved"},
        target_id="alerts",
        include_if=skip_if_target_in("main-content"),
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
        include_if=skip_if_target_in("main-content"),
    )
    response = render_htmx(request, "tests/_page.html", {"title": "hi"}, swaps=[swap])
    response.render()
    assert b"Saved" in response.content


# --- render_htmx: title ------------------------------------------------------


def test_title_kwarg_added_to_context_on_full_render():
    rf = RequestFactory()
    request = rf.get("/workspace/")
    response = render_htmx(request, "tests/_page.html", {}, title="Hello")
    assert response.context_data["title"] == "Hello"


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
    assert response.context_data["title"] == "From context"
    assert b"<title>From context</title>" in response.content


def test_explicit_title_kwarg_overrides_context_title():
    rf = RequestFactory()
    request = rf.get("/workspace/")
    response = render_htmx(
        request, "tests/_page.html", {"title": "From context"}, title="Explicit"
    )
    assert response.context_data["title"] == "Explicit"


def test_no_title_anywhere_defaults_to_none_and_no_tag_appended():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    response = render_htmx(request, "tests/_page.html", {})
    response.render()
    assert response.context_data["title"] is None
    assert b"<title>" not in response.content


# --- make_shell_renderer: shell swap composition ----------------------------


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
    predicate = skip_if_target_in("main-content")
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


# --- make_shell_renderer: title / merge precedence --------------------------


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


@patch("htmx_nav.responses.render_htmx")
def test_flat_merge_shell_title_used_when_page_gives_no_title(mock_render_htmx):
    mock_render_htmx.return_value = MagicMock()
    render_shell = make_shell_renderer(
        "tests/_shell.html",
        context_builder=lambda request: {"title": "Shell Title"},
    )
    request = _non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {})

    page_context = mock_render_htmx.call_args.args[2]
    assert page_context["title"] == "Shell Title"


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


@patch("htmx_nav.responses.render_htmx")
def test_namespaced_shell_title_does_not_leak_into_page_context(mock_render_htmx):
    mock_render_htmx.return_value = MagicMock()
    render_shell = make_shell_renderer(
        "tests/_shell.html",
        context_builder=lambda request: {"title": "Shell Title"},
        namespace="shell",
    )
    request = _non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {})

    page_context = mock_render_htmx.call_args.args[2]
    assert "title" not in page_context
    assert page_context["shell"]["title"] == "Shell Title"


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
