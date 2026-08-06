"""
Testing utilities for projects that use htmx_nav.
"""

from collections.abc import Callable
from typing import Any

from django.test import Client
from django.test.html import parse_html

__all__ = ["assert_shell_parity"]


def assert_shell_parity(
    client: Client,
    url: str,
    *,
    requests: dict[str, dict],
    checks: dict[str, Callable[[Any], Any]],
) -> dict[str, Any]:
    """
    GETs `url` once per entry in `requests` and asserts shell parity.

    This is useful for verifying that a shell-rendered page produces
    identical nav/breadcrumb/sidebar state whether it's requested as a
    full page load, an HTMX page-shell swap, or an HTMX partial-tab swap.

    Args:
        client: The Django test client instance used to make requests.
        url: The target URL to request.
        requests: A dictionary mapping labels to keyword arguments passed
            to `client.get`.
        checks: A dictionary mapping check labels to extraction functions
            that take a response context and return a value to compare.

    Returns:
        dict[str, Any]: A dictionary mapping each request label to its
        corresponding Django response object for further assertions.

    Example:
        ```python
        from django.test import Client
        from htmx_nav.testing import assert_shell_parity

        client = Client()
        requests = {
            "full_reload": {},
            "page_shell": {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "page-content"},
            "tab_shell": {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "tab-content"},
        }
        checks = {
            "sidebar_labels": lambda ctx: [i["label"] for i in ctx["nav"]["sidebar"] if i["active"]],
            "breadcrumbs": lambda ctx: [c["label"] for c in ctx["nav"]["breadcrumbs"]],
        }
        responses = assert_shell_parity(
            client, "/nav-workspace/record/42/",
            requests=requests,
            checks=checks,
        )
        ```
    """
    responses = {label: client.get(url, **kwargs) for label, kwargs in requests.items()}

    for check_label, extract in checks.items():
        values = {label: extract(resp.context) for label, resp in responses.items()}
        baseline_label, baseline_value = next(iter(values.items()))
        for label, value in values.items():
            assert value == baseline_value, (
                f"Shell parity broken for check {check_label!r} at {url!r}: "
                f"{baseline_label!r} gave {baseline_value!r}, {label!r} gave {value!r}."
            )

    return responses


def _extract_fragment(html: bytes | str, element_id: str) -> str:
    """Extracts the outer HTML of the element with the given id."""
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise ImportError(
            "assert_shell_composition requires beautifulsoup4. "
            "Install it with: pip install beautifulsoup4"
        ) from exc

    if isinstance(html, bytes):
        html = html.decode("utf-8")

    soup = BeautifulSoup(html, "html.parser")
    element = soup.find(id=element_id)
    if element is None:
        raise AssertionError(
            f"Could not find any element with id={element_id!r} in the response HTML."
        )
    return str(element)


def _assert_html_equal(
    a_html: str | bytes, b_html: str | bytes, *, label_a: str, label_b: str
) -> None:
    if isinstance(a_html, bytes):
        a_html = a_html.decode("utf-8")
    if isinstance(b_html, bytes):
        b_html = b_html.decode("utf-8")

    a_parsed = parse_html(a_html)
    b_parsed = parse_html(b_html)
    if a_parsed != b_parsed:
        raise AssertionError(
            f"HTML mismatch between {label_a} and {label_b}:\n"
            f"--- {label_a} ---\n{a_parsed}\n"
            f"--- {label_b} ---\n{b_parsed}"
        )


def assert_shell_composition(
    client: Client,
    url: str,
    *,
    page_shell_kwargs: dict,
    tab_shell_kwargs: dict,
    full_reload_kwargs: dict | None = None,
    page_container_id: str = "page-content",
    tab_container_id: str = "tab-content",
) -> dict[str, Any]:
    """
    Asserts that a shell-rendered page's three HTMX-swap variants actually
    compose into the same HTML, not just the same template context.

    Verifies:
        1. The full-reload response's `#{page_container_id}` fragment
           equals the page-shell response's entire body.
        2. The page-shell response's `#{tab_container_id}` fragment
           equals the tab-shell response's entire body.
        3. (Transitively, checked directly) The full-reload response's
           `#{tab_container_id}` fragment also equals the tab-shell
           response's entire body.

    This catches bugs that `assert_shell_parity` can't see, e.g. a
    partial response missing the wrapper element the client's
    `hx-target` expects to swap into, or template branching on request
    headers that produces different markup from identical context.

    Requires beautifulsoup4 (`pip install beautifulsoup4`).

    Args:
        client: The Django test client instance used to make requests.
        url: The target URL to request.
        page_shell_kwargs: kwargs passed to `client.get` for the
            page-level HTMX swap (e.g. `{"HTTP_HX_REQUEST": "true",
            "HTTP_HX_TARGET": "page-content"}`).
        tab_shell_kwargs: kwargs passed to `client.get` for the
            component-level HTMX swap.
        full_reload_kwargs: kwargs for the full-page GET. Defaults to `{}`.
        page_container_id: the `id` of the page-level swap target.
        tab_container_id: the `id` of the component-level swap target.

    Returns:
        dict[str, Any]: `{"full_reload": resp, "page_shell": resp, "tab_shell": resp}`
        for further assertions.
    """
    full_reload_kwargs = full_reload_kwargs or {}

    full = client.get(url, **full_reload_kwargs)
    page_shell = client.get(url, **page_shell_kwargs)
    tab_shell = client.get(url, **tab_shell_kwargs)

    for label, resp in [
        ("full_reload", full),
        ("page_shell", page_shell),
        ("tab_shell", tab_shell),
    ]:
        assert resp.status_code == 200, (
            f"{label} request to {url!r} returned {resp.status_code}"
        )

    full_page_fragment = _extract_fragment(full.content, page_container_id)
    _assert_html_equal(
        full_page_fragment,
        page_shell.content,
        label_a=f"full reload's #{page_container_id}",
        label_b="page_shell response body",
    )

    page_shell_tab_fragment = _extract_fragment(page_shell.content, tab_container_id)
    _assert_html_equal(
        page_shell_tab_fragment,
        tab_shell.content,
        label_a=f"page_shell's #{tab_container_id}",
        label_b="tab_shell response body",
    )

    full_tab_fragment = _extract_fragment(full.content, tab_container_id)
    _assert_html_equal(
        full_tab_fragment,
        tab_shell.content,
        label_a=f"full reload's #{tab_container_id}",
        label_b="tab_shell response body",
    )

    return {"full_reload": full, "page_shell": page_shell, "tab_shell": tab_shell}
