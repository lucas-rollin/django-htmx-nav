import pytest
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.test import Client
from django.urls import path

from htmx_nav.testing import assert_shell_parity

pytestmark = pytest.mark.urls(__name__)


# -- Minimal views for testing assert_shell_parity in isolation ---------------
# These deliberately avoid make_shell_renderer/real templates so failures here
# can only come from assert_shell_parity itself, not from shell-rendering logic.

def consistent_view(request):
    """Always returns the same context, regardless of headers."""
    return TemplateResponse(request, "tests/_minimal.html", {"value": 42, "label": "same"})


def diverging_view(request):
    """Returns context that differs based on the HX-Target header."""
    target = request.headers.get("HX-Target", "none")
    return TemplateResponse(request, "tests/_minimal.html", {"value": len(target)})


urlpatterns = [
    path("consistent/", consistent_view),
    path("diverging/", diverging_view),
]


# -- Tests ---------------

def test_passes_when_all_responses_agree():
    client = Client()
    responses = assert_shell_parity(
        client, "/consistent/",
        requests={"a": {}, "b": {"HTTP_HX_TARGET": "whatever"}},
        checks={"value": lambda ctx: ctx["value"], "label": lambda ctx: ctx["label"]},
    )
    assert set(responses) == {"a", "b"}
    assert all(r.status_code == 200 for r in responses.values())


def test_raises_when_a_check_diverges():
    client = Client()
    with pytest.raises(AssertionError, match="Shell parity broken"):
        assert_shell_parity(
            client, "/diverging/",
            requests={
                "no_target": {},
                "short_target": {"HTTP_HX_TARGET": "x"},
            },
            checks={"value": lambda ctx: ctx["value"]},
        )


def test_error_message_names_the_failing_check_and_labels():
    client = Client()
    with pytest.raises(AssertionError) as exc_info:
        assert_shell_parity(
            client, "/diverging/",
            requests={
                "no_target": {},
                "short_target": {"HTTP_HX_TARGET": "x"},
            },
            checks={"my_check": lambda ctx: ctx["value"]},
        )
    message = str(exc_info.value)
    assert "my_check" in message
    assert "no_target" in message
    assert "short_target" in message
    assert "/diverging/" in message


def test_evaluates_all_checks_even_after_one_fails():
    """
    A check dict often has multiple independent checks; a caller debugging
    a parity break benefits from seeing every failing check, not just the
    first one encountered dict-iteration-order.
    """
    client = Client()
    seen_checks = []

    def tracking_check(name):
        def _check(ctx):
            seen_checks.append(name)
            return ctx["value"]
        return _check

    with pytest.raises(AssertionError):
        assert_shell_parity(
            client, "/diverging/",
            requests={"a": {}, "b": {"HTTP_HX_TARGET": "xx"}},
            checks={
                "first": tracking_check("first"),
                "second": tracking_check("second"),
            },
        )
    # NOTE: this currently fails fast on "first" and never runs "second".
    # See discussion — may want to change to collect-all-failures behavior.


def test_returns_responses_for_further_assertions():
    client = Client()
    responses = assert_shell_parity(
        client, "/consistent/",
        requests={"only": {}},
        checks={"value": lambda ctx: ctx["value"]},
    )
    assert responses["only"].status_code == 200
    assert responses["only"].context["value"] == 42


def test_single_request_label_always_passes_checks():
    """With only one label, there's nothing to compare against — trivially passes."""
    client = Client()
    assert_shell_parity(
        client, "/diverging/",
        requests={"solo": {"HTTP_HX_TARGET": "anything"}},
        checks={"value": lambda ctx: ctx["value"]},
    )


def test_no_checks_still_makes_all_requests():
    client = Client()
    responses = assert_shell_parity(
        client, "/consistent/",
        requests={"a": {}, "b": {}},
        checks={},
    )
    assert len(responses) == 2