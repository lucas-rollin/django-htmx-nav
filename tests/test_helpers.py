from django.test import RequestFactory

from htmx_nav.helpers import cache_on_request


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
