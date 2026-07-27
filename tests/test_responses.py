from django.test import RequestFactory

from htmx_nav.responses import (
    Oob,
    _is_htmx_request,
    htmx_redirect,
    make_shell_renderer,
    render_htmx,
)


def test_is_htmx_request_uses_raw_header_without_django_htmx():
    rf = RequestFactory()
    plain = rf.get("/workspace/")
    assert _is_htmx_request(plain) is False

    htmx = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    assert _is_htmx_request(htmx) is True
    # note: no `.htmx` attribute was ever set on the request — this is
    # the fallback path exercised with django-htmx absent/uninstalled.
    assert not hasattr(htmx, "htmx")


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


def test_render_htmx_appends_oob_via_raw_header_without_django_htmx():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    # deliberately no request.htmx attribute set, simulating a project
    # without django-htmx installed/enabled

    oob = Oob("tests/_shell.html", {"nav": {"sidebar": [1, 2]}})
    response = render_htmx(request, "tests/_page.html", {"title": "hi"}, oobs=(oob,))
    response.render()

    assert b'<div class="partial">hi</div>' in response.content
    assert b"<nav>2</nav>" in response.content


def test_oob_with_target_id_auto_wraps_fragment():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    oob = Oob("tests/_notification.html", {"message": "Saved"}, target_id="alerts")
    response = render_htmx(request, "tests/_page.html", {"title": "hi"}, oobs=(oob,))
    response.render()
    assert b'<div id="alerts" hx-swap-oob="true"><p>Saved</p></div>' in response.content


def test_oob_without_target_id_does_not_wrap_fragment():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    oob = Oob("tests/_notification.html", {"message": "Saved"})
    response = render_htmx(request, "tests/_page.html", {"title": "hi"}, oobs=(oob,))
    response.render()
    assert b"<p>Saved</p>" in response.content
    assert b"hx-swap-oob" not in response.content


def test_oob_with_no_context_falls_back_to_empty_dict():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    oob = Oob("tests/_notification.html")  # context=None
    response = render_htmx(request, "tests/_page.html", {"title": "hi"}, oobs=(oob,))
    response.render()
    assert b"<p>no message</p>" in response.content


def test_push_url_defaults_to_full_path_on_htmx_requests():
    rf = RequestFactory()
    request = rf.get("/workspace/?tab=response", HTTP_HX_REQUEST="true")
    response = render_htmx(request, "tests/_page.html", {"title": "hi"})
    assert response["HX-Push-Url"] == "/workspace/?tab=response"


def test_push_url_accepts_explicit_override():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    response = render_htmx(request, "tests/_page.html", {"title": "hi"}, push_url="/canonical/")
    assert response["HX-Push-Url"] == "/canonical/"


def test_push_url_false_omits_header():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    response = render_htmx(request, "tests/_page.html", {"title": "hi"}, push_url=False)
    assert "HX-Push-Url" not in response


def test_push_url_omitted_on_non_htmx_requests():
    rf = RequestFactory()
    request = rf.get("/workspace/")
    response = render_htmx(request, "tests/_page.html", {"title": "hi"})
    assert "HX-Push-Url" not in response


def test_vary_header_includes_hx_request():
    rf = RequestFactory()
    request = rf.get("/workspace/")
    response = render_htmx(request, "tests/_page.html", {"title": "hi"})
    assert "HX-Request" in response["Vary"]


def test_htmx_redirect_returns_204_with_hx_redirect_header_on_htmx_requests():
    rf = RequestFactory()
    request = rf.get("/workspace/", HTTP_HX_REQUEST="true")
    response = htmx_redirect(request, "/somewhere/")
    assert response.status_code == 204
    assert response["HX-Redirect"] == "/somewhere/"
    assert response.content == b""


def test_htmx_redirect_returns_normal_redirect_on_plain_requests():
    rf = RequestFactory()
    request = rf.get("/workspace/")
    response = htmx_redirect(request, "/somewhere/")
    assert response.status_code == 302
    assert response["Location"] == "/somewhere/"


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
    response.render()

    assert calls["called"] is True
    assert b"hi" in response.content
