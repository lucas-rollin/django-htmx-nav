"""Shared test doubles/helpers for htmx_nav's test suite."""

from django.test import RequestFactory


class FakeHtmxDetails:
    """Minimal stand-in for django-htmx's request.htmx."""

    def __init__(self, target=None):
        self.target = target

    def __bool__(self):
        return True


def htmx_request(rf: RequestFactory, target=None, path="/workspace/"):
    extra = {"HTTP_HX_REQUEST": "true"}
    if target is not None:
        extra["HTTP_HX_TARGET"] = target
    return rf.get(path, **extra)


def non_htmx_request(rf: RequestFactory, path="/workspace/"):
    return rf.get(path)
