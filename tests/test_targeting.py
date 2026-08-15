import pytest
from django.contrib import messages
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.messages.storage.fallback import FallbackStorage
from django.shortcuts import render
from django.test import RequestFactory

from htmx_nav.swaps import Swap
from htmx_nav.targeting import (
    _eval_target,
    _is_htmx_request,
    has_messages,
    htmx_target_is,
    not_targeting,
    targeting,
)

from .helpers import htmx_request, non_htmx_request

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
    assert _is_htmx_request(htmx_request(RequestFactory())) is True


def test_is_htmx_request_false_when_flag_false():
    assert _is_htmx_request(non_htmx_request(RequestFactory())) is False


def test_is_htmx_request_false_when_attribute_missing():
    assert _is_htmx_request(RequestFactory().get("/workspace/")) is False


# =============================================================================
# htmx_target_is / targeting / not_targeting
# =============================================================================


def test_htmx_target_is_true_for_matching_target():
    request = htmx_request(RequestFactory(), target="tab-content")
    assert htmx_target_is(request, "tab-content") is True


@pytest.mark.parametrize("target", ["tab-content", "#tab-content", "div#tab-content"])
def test_htmx_target_is_matches_v2_and_v4_formats(target):
    request = htmx_request(RequestFactory(), target=target)
    assert htmx_target_is(request, "tab-content") is True


def test_htmx_target_is_false_when_no_match():
    request = htmx_request(RequestFactory(), target="tab-content")
    assert htmx_target_is(request, "other-id") is False


def test_htmx_target_is_false_without_htmx_details():
    request = RequestFactory().get("/workspace/", HTTP_HX_REQUEST="true")
    assert htmx_target_is(request, "tab-content") is False


def test_targeting_predicate_matches_request_target():
    request = htmx_request(RequestFactory(), target="tab-content")
    assert targeting("tab-content")(request) is True
    assert targeting("other-id")(request) is False


def test_not_targeting_predicate_matches_request_target():
    request = htmx_request(RequestFactory(), target="tab-content")
    assert not_targeting("tab-content")(request) is False
    assert not_targeting("other-id")(request) is True


# =============================================================================
# _eval_target
# =============================================================================


def test_eval_target_true_returns_true():
    assert _eval_target(True, RequestFactory().get("/")) is True


def test_eval_target_false_returns_false():
    assert _eval_target(False, RequestFactory().get("/")) is False


def test_eval_target_string_delegates_to_htmx_target_is():
    request = htmx_request(RequestFactory(), target="tabs")
    assert _eval_target("tabs", request) is True
    assert _eval_target("other", request) is False


def test_eval_target_callable_invoked_with_request():
    request = RequestFactory().get("/")
    calls = []

    def predicate(req):
        calls.append(req)
        return True

    assert _eval_target(predicate, request) is True
    assert calls == [request]


def test_eval_target_invalid_type_raises_type_error():
    with pytest.raises(TypeError):
        _eval_target(123, RequestFactory().get("/"))  # type: ignore


# =============================================================================
# has_messages
# =============================================================================


@pytest.fixture
def msg_request():
    """Factory fixture returning a request initialized with message storage."""

    def _factory(*message_texts: str):
        request = RequestFactory().get("/")
        request.session = {}
        request._messages = FallbackStorage(request)
        for text in message_texts:
            messages.add_message(request, messages.INFO, text)
        return request

    return _factory


@pytest.mark.parametrize(
    ("msg_list", "expected"),
    [
        ([], False),
        (["Saved."], True),
        (["First.", "Second."], True),
    ],
)
def test_has_messages_predicate(msg_request, msg_list, expected):
    request = msg_request(*msg_list)
    assert has_messages(request) is expected


def test_has_messages_does_not_consume_messages(msg_request):
    """Evaluating `has_messages` must remain idempotent and keep messages unread."""
    request = msg_request("Ticket #42 updated.")

    # Idempotency check
    assert has_messages(request) is True
    assert has_messages(request) is True

    # Ensure messages are still available during standard template rendering
    rendered = render(request, "tests/_messages.html").content.decode()
    assert "Ticket #42 updated." in rendered


def test_has_messages_swap_integration(msg_request):
    swap = Swap("tests/_messages.html", target_id="messages", include_if=has_messages)

    # Empty messages state
    empty_req = msg_request()
    assert swap.applies_to(empty_req) is False

    # Populated messages state
    populated_req = msg_request("Draft saved.")
    assert swap.applies_to(populated_req) is True

    html = swap.render(populated_req)
    assert "Draft saved." in html
    assert 'id="messages"' in html


def test_has_messages_with_real_middleware():
    """Ensures `has_messages` works when storage is attached via Django middleware."""
    request = RequestFactory().get("/")
    request.session = {}

    middleware = MessageMiddleware(lambda req: None)
    middleware.process_request(request)

    assert has_messages(request) is False

    messages.add_message(request, messages.SUCCESS, "Profile updated.")
    assert has_messages(request) is True
