import pytest
from django.test import Client
from typing import Any, Callable


def assert_shell_parity(
    client: Client,
    url: str,
    *,
    checks: dict[str, Callable[[Any], Any]],
    **htmx_extra,
):
    """
    GETs `url` twice — once as a normal request, once as an HTMX request
    (`HX-Request: true`) — and asserts that each function in `checks`
    extracts the same value from both responses' template context.

    `checks` maps a short label (used in the assertion message) to a
    `context -> value` extractor, e.g.:

        assert_shell_parity(
            self.client, "/workspace/demands/42/",
            checks={
                "active_sidebar_item": lambda ctx: [
                    i["label"] for s in ctx["nav"]["sidebar"] for i in s["items"] if i["active"]
                ],
                "breadcrumbs": lambda ctx: [c["label"] for c in ctx["nav"]["breadcrumbs"]],
                "active_tab": lambda ctx: next(
                    (t["key"] for t in ctx["nav"]["tabs"] if t["active"]), None
                ),
            },
        )

    Extra keyword arguments are passed through to the HTMX `client.get`
    call (e.g. `HTTP_HX_TARGET="content"`), in case a check depends on
    something htmx-specific about the request.

    Requires `django.test.Client`, which connects to Django's
    `template_rendered` signal and exposes the merged context as
    `response.context` — this works for both `render()` and
    `TemplateResponse` (what `render_htmx` returns) without extra setup.

    Returns `(full_response, htmx_response)` for further assertions.
    """
    full = client.get(url)
    htmx = client.get(url, HTTP_HX_REQUEST="true", **htmx_extra)

    for label, extract in checks.items():
        full_value = extract(full.context)
        htmx_value = extract(htmx.context)
        assert full_value == htmx_value, (
            f"Shell parity broken for check {label!r} at {url!r}: "
            f"full-page render gave {full_value!r}, HTMX render gave {htmx_value!r}. "
            "The URL should produce identical nav/shell state regardless "
            "of how it was requested."
        )

    return full, htmx


CHECKS = {
    "active_sidebar_item": lambda ctx: [i["label"] for i in ctx["nav"]["sidebar"] if i["active"]],
    "breadcrumbs": lambda ctx: [c["label"] for c in ctx["nav"]["breadcrumbs"]],
}


def test_assert_shell_parity_passes_for_consistent_nav():
    client = Client()
    full, htmx = assert_shell_parity(client, "/nav-workspace/", checks=CHECKS)
    assert full.status_code == 200
    assert htmx.status_code == 200


def test_assert_shell_parity_fails_when_state_actually_diverges():
    client = Client()
    # A check whose extractor returns a different value on each call proves
    # assert_shell_parity actually compares full vs. htmx and doesn't just
    # pass vacuously, this simulates a real drift between the two paths.
    seen = iter([1, 2])
    with pytest.raises(AssertionError, match="Shell parity broken"):
        assert_shell_parity(
            client, "/nav-workspace/",
            checks={"artificially_diverging_check": lambda ctx: next(seen)},
        )
