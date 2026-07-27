from django.test import RequestFactory
from django.urls import NoReverseMatch
import pytest

from htmx_nav.helpers import cache_on_request, reverse_maybe


def test_reverse_maybe_returns_none_for_falsy_view_name():
    assert reverse_maybe(None) is None
    assert reverse_maybe("") is None


def test_reverse_maybe_strict_default_raises_like_plain_reverse():
    with pytest.raises(NoReverseMatch):
        reverse_maybe("detail", {"bogus": 1})  # strict=True is the default


def test_reverse_maybe_non_strict_degrades_gracefully_on_mismatch():
    # "workspace" takes no kwargs; passing ambient kwargs from elsewhere
    # shouldn't be a hard error when strict=False
    assert reverse_maybe("workspace", {"pk": 7}, strict=False) == "/workspace/"


def test_reverse_maybe_resolves_normally_with_matching_kwargs():
    assert reverse_maybe("detail", {"pk": 3}) == "/detail/3/"


def test_cache_on_request_calls_builder_once():
    rf = RequestFactory()
    request = rf.get("/")
    calls = []

    def build():
        calls.append(1)
        return {"n": len(calls)}

    first = cache_on_request(request, "_test_cache_key", build)
    second = cache_on_request(request, "_test_cache_key", build)
    assert first is second
    assert len(calls) == 1


def test_cache_on_request_handles_falsy_cached_values():
    rf = RequestFactory()
    request = rf.get("/")
    calls = []

    def build():
        calls.append(1)
        return []

    first = cache_on_request(request, "_test_cache_key", build)
    second = cache_on_request(request, "_test_cache_key", build)
    assert first == [] and second == []
    assert len(calls) == 1