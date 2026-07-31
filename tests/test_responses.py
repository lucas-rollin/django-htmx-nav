from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from htmx_nav.responses import (
    Swap,
    _is_htmx_request,
    make_shell_renderer,
    render_htmx,
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


# --- _is_htmx_request --------------------------------------------------

def test_is_htmx_request_uses_raw_header_without_django_htmx():
    rf = RequestFactory()
    plain = rf.get("/workspace/")
    assert _is_htmx_request(plain) is False

    htmx = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    assert _is_htmx_request(htmx) is True
    assert not hasattr(htmx, "htmx")


def test_is_htmx_request_true_when_htmx_flag_set():
    request = _htmx_request(RequestFactory())
    assert _is_htmx_request(request) is True


def test_is_htmx_request_false_when_flag_false():
    request = _non_htmx_request(RequestFactory())
    assert _is_htmx_request(request) is False


def test_is_htmx_request_false_when_attribute_missing():
    request = RequestFactory().get("/workspace/")
    assert _is_htmx_request(request) is False


# --- render_htmx: full vs. partial rendering ----------------------------

def test_full_render_renders_whole_template():
    rf = RequestFactory()
    request = rf.get("/workspace/")  # no HX-Request header
    response = render_htmx(request, "tests/_page.html", {"title": "hi"})
    response.render()
    assert b"FULL PAGE:" in response.content
    assert b'<div class="partial">hi</div>' in response.content


def test_htmx_request_renders_only_the_partial():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    response = render_htmx(request, "tests/_page.html", {"title": "hi"})
    response.render()
    assert b"FULL PAGE:" not in response.content
    assert response.content.strip() == b'<div class="partial">hi</div>'


# --- render_htmx: swaps ---------------------------------------------------

def test_render_htmx_appends_swap_via_raw_header_without_django_htmx():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    # deliberately no request.htmx attribute set, simulating a project
    # without django-htmx installed/enabled
    swap = Swap("tests/_shell.html", {"nav": {"sidebar": [1, 2]}})
    response = render_htmx(request, "tests/_page.html", {"title": "hi"}, swaps=(swap,))
    response.render()

    assert b'<div class="partial">hi</div>' in response.content
    assert b"<nav>2</nav>" in response.content


def test_swap_with_target_id_auto_wraps_fragment():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_notification.html", {"message": "Saved"}, target_id="alerts")
    response = render_htmx(request, "tests/_page.html", {"title": "hi"}, swaps=(swap,))
    response.render()
    assert b'<div id="alerts" hx-swap-oob="true"><p>Saved</p></div>' in response.content


def test_swap_without_target_id_does_not_wrap_fragment():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_notification.html", {"message": "Saved"})
    response = render_htmx(request, "tests/_page.html", {"title": "hi"}, swaps=(swap,))
    response.render()
    assert b"<p>Saved</p>" in response.content
    assert b"hx-swap-oob" not in response.content


def test_swap_with_no_context_falls_back_to_empty_dict():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    swap = Swap("tests/_notification.html")  # context=None
    response = render_htmx(request, "tests/_page.html", {"title": "hi"}, swaps=(swap,))
    response.render()
    assert b"<p>no message</p>" in response.content


# --- make_shell_renderer: page_target_id routing --------------------------

@patch("htmx_nav.responses.render_htmx")
def test_non_htmx_uses_page_partial_name(mock_render_htmx):
    mock_render_htmx.return_value = MagicMock()
    render_shell = make_shell_renderer(
        "tests/_shell.html", page_target_id="page-content",
    )
    request = _non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {}, partial_name="tab_content")

    assert mock_render_htmx.call_args.kwargs["partial_name"] == "content"


@patch("htmx_nav.responses.render_htmx")
def test_htmx_page_target_uses_page_partial_name(mock_render_htmx):
    mock_render_htmx.return_value = MagicMock()
    render_shell = make_shell_renderer(
        "tests/_shell.html", page_target_id="page-content",
    )
    request = _htmx_request(RequestFactory(), target="page-content")

    render_shell(request, "tests/_page.html", {}, partial_name="tab_content")

    assert mock_render_htmx.call_args.kwargs["partial_name"] == "content"


@patch("htmx_nav.responses.render_htmx")
def test_htmx_other_target_keeps_callers_partial_name(mock_render_htmx):
    mock_render_htmx.return_value = MagicMock()
    render_shell = make_shell_renderer(
        "tests/_shell.html", page_target_id="page-content",
    )
    request = _htmx_request(RequestFactory(), target="tab-content")

    render_shell(request, "tests/_page.html", {}, partial_name="tab_content")

    assert mock_render_htmx.call_args.kwargs["partial_name"] == "tab_content"


@pytest.mark.parametrize("target", ["page-content", "#page-content", "div#page-content"])
@patch("htmx_nav.responses.render_htmx")
def test_page_target_matches_v2_and_v4_formats(mock_render_htmx, target):
    mock_render_htmx.return_value = MagicMock()
    render_shell = make_shell_renderer(
        "tests/_shell.html", page_target_id="page-content",
    )
    request = _htmx_request(RequestFactory(), target=target)

    render_shell(request, "tests/_page.html", {}, partial_name="tab_content")

    assert mock_render_htmx.call_args.kwargs["partial_name"] == "content"


@patch("htmx_nav.responses.render_htmx")
def test_without_page_target_id_always_uses_callers_partial_name(mock_render_htmx):
    mock_render_htmx.return_value = MagicMock()
    render_shell = make_shell_renderer("tests/_shell.html")
    request = _non_htmx_request(RequestFactory())

    render_shell(request, "tests/_page.html", {}, partial_name="tab_content")

    assert mock_render_htmx.call_args.kwargs["partial_name"] == "tab_content"


# --- make_shell_renderer: shell swap + context ----------------------------

@patch("htmx_nav.responses.render_htmx")
def test_shell_swap_is_first_swap_followed_by_extra_swaps(mock_render_htmx):
    mock_render_htmx.return_value = MagicMock()
    render_shell = make_shell_renderer("tests/_shell.html")
    request = _non_htmx_request(RequestFactory())
    extra = Swap("tests/_alert.html", target_id="alerts")

    render_shell(request, "tests/_page.html", {}, extra_swaps=(extra,))

    swaps = mock_render_htmx.call_args.kwargs["swaps"]
    assert swaps[0].template_name == "tests/_shell.html"
    assert swaps[-1] is extra


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


def test_render_shell_merges_context_builder(tmp_path, settings):
    calls = {}

    def context_builder(request):
        calls["called"] = True
        return {"nav": {"sidebar": []}}

    render_shell = make_shell_renderer(
        shell_template="tests/_shell.html",
        context_builder=context_builder,
    )
    rf = RequestFactory()
    request = rf.get("/workspace/")
    request.htmx = False  # non-htmx: no OOB append, just main render

    response = render_shell(request, "tests/_page.html", {"title": "hi"})