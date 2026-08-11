"""Shared test doubles/helpers for htmx_nav's test suite."""

from django.test import RequestFactory


class FakeHtmxDetails:
    """Minimal stand-in for django-htmx's request.htmx."""

    def __init__(self, target=None):
        self.target = target

    def __bool__(self):
        return True


def htmx_request(rf: RequestFactory, target=None, path="/workspace/"):
    request = rf.get(path, HTTP_HX_REQUEST="true")
    request.htmx = FakeHtmxDetails(target=target)
    return request


def non_htmx_request(rf: RequestFactory, path="/workspace/"):
    request = rf.get(path)
    request.htmx = False
    return request
