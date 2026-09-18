"""
Testing utilities for projects that use htmx_nav.

Provides assertion helpers for Django and HTMX test suites to ensure that
full-page reloads, HTMX page-shell swaps, and HTMX partial-tab swaps yield
identical context state and rendered HTML markup.
"""

import difflib
import re
from collections.abc import Callable
from typing import Any

from django.test import Client
from django.test.html import parse_html

__all__ = ["assert_shell_parity", "assert_shell_composition", "assert_html_equal"]


_DEBUG_MARKER_RE = re.compile(
    r"<script>\(function\(\)\{.*?hn-swap.*?\}\)\(\);</script>", re.DOTALL
)


def _strip_debug_markers(html: str) -> str:
    """Removes htmx_nav's HTMX_NAV_DEBUG_SWAPS marker <script> tags. 
    
    The marker is only ever emitted on swap responses (see Swap.render), 
    so its presence is noise for structural comparison.
    """
    return _DEBUG_MARKER_RE.sub("", html)


def assert_shell_parity(
    client: Client,
    url: str,
    *,
    requests: dict[str, dict[str, Any]],
    checks: dict[str, Callable[[Any], Any]],
) -> dict[str, Any]:
    """Verify that context state remains consistent across different swap modes.

    Issues a GET request to `url` for every entry in `requests` and executes
    assertion callbacks against response contexts to ensure shell state
    parity (e.g. active navigation links, breadcrumbs, sidebar items).

    Args:
        client: The Django test client instance used to execute GET requests.
        url: The target URL endpoint to test.
        requests: A mapping of request scenario labels to keyword arguments
            passed directly to `client.get` (e.g. HTMX headers).
        checks: A mapping of check labels to extraction callables. Each
            callable receives `response.context` and returns an extracted
            value to compare.

    Returns:
        dict[str, Any]: A mapping of request labels to their corresponding
        Django HTTP response objects.

    Raises:
        AssertionError: If any context value produced by a check fails to
            match the baseline value established by the first request.

    Example:
        .. code-block:: python

            requests = {
                "full_reload": {},
                "page_shell": {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "page-content"},
            }
            checks = {
                "breadcrumbs": lambda ctx: [c["label"] for c in ctx["nav"]["breadcrumbs"]],
            }
            responses = assert_shell_parity(
                client, "/dashboard/", requests=requests, checks=checks
            )
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


def assert_html_equal(
    a: bytes | str, b: bytes | str, *, label_a: str = "a", label_b: str = "b"
) -> None:
    """Asserts two HTML documents/fragments are structurally equal.

    Normalizes both inputs with Django's `parse_html` (whitespace/attribute-
    order insensitive) and strips htmx_nav debug-swap markers before
    comparing.
    
    Useful when comparing two full response bodies (e.g. verifying
    a response is identical regardless of `HX-Target`); `assert_shell_composition`
    uses the same comparison internally for its fragment-level checks.

    Args:
        a: First HTML document or fragment, bytes or str.
        b: Second HTML document or fragment, bytes or str.
        label_a: Label for `a` used in the diff output on mismatch.
        label_b: Label for `b` used in the diff output on mismatch.

    Raises:
        AssertionError: If the two documents differ structurally, with a
            unified diff of the normalized HTML.
    """
    if isinstance(a, bytes):
        a = a.decode("utf-8")
    if isinstance(b, bytes):
        b = b.decode("utf-8")

    a_parsed = str(parse_html(_strip_debug_markers(a)))
    b_parsed = str(parse_html(_strip_debug_markers(b)))
    if a_parsed == b_parsed:
        return

    diff = "\n".join(
        difflib.unified_diff(
            a_parsed.splitlines(),
            b_parsed.splitlines(),
            lineterm="",
            fromfile=label_a,
            tofile=label_b,
        )
    )
    raise AssertionError(f"HTML mismatch between {label_a} and {label_b}:\n{diff}")


class _HTMLDocument:
    """Parses a response body once and exposes id-scoped extraction.

    render_with_swaps appends each applicable Swap as a sibling fragment
    onto the response body — `<div id=X hx-swap-oob=...>` (Swap.wrap="oob")
    or `<hx-partial hx-target="#X" ...>` (Swap.wrap="hx-partial") — never
    nested inside the primary target's own markup, plus a trailing
    `<title>` when title= is set. A swap response is therefore not one
    fragment but several: the primary (non-wrapped) content, and zero or
    more independently addressed fragments each destined for their own id
    elsewhere in the DOM. `split_fragments` performs that separation.
    """

    def __init__(self, raw_html: bytes | str):
        try:
            from bs4 import BeautifulSoup
        except ImportError as exc:
            raise ImportError(
                "assert_shell_composition requires beautifulsoup4. "
                "Install it with: pip install beautifulsoup4"
            ) from exc

        if isinstance(raw_html, bytes):
            raw_html = raw_html.decode("utf-8")

        self.soup = BeautifulSoup(_strip_debug_markers(raw_html), "html.parser")

    def _find_element(self, element_id: str):
        element = self.soup.find(id=element_id)
        if element is None:
            raise AssertionError(
                f"Could not find any element with id={element_id!r} in the response HTML."
            )
        return element

    def inner_html(self, element_id: str) -> str:
        """The children of the element with `element_id`, serialized."""
        return self._find_element(element_id).decode_contents()

    def outer_html(self, element_id: str) -> str:
        """The element with `element_id`, including its own tag."""
        return str(self._find_element(element_id))

    def container_html(self, element_id: str, *, self_wrapped: bool) -> str:
        """`outer_html` if the container re-emits its own wrapper
        (`hx-swap="outerHTML"` convention), else `inner_html` — the
        default, matching render_nav/Swap and Django 6 `{% partialdef %}`,
        where htmx swaps into an already-present container via
        `hx-swap="innerHTML"` and the swap response never repeats the
        wrapper it's swapping into."""
        return self.outer_html(element_id) if self_wrapped else self.inner_html(element_id)

    def split_fragments(self) -> tuple[str, dict[str, str]]:
        """Splits this document into (primary_html, fragments_by_id).

        Recognizes `hx-swap-oob` containers (id on the wrapper) and
        `<hx-partial hx-target="#id">` elements (id on hx-target). Drops
        a trailing `<title>` — it isn't part of any single container.
        Everything else is the primary (non-wrapped) content.

        Note: `Swap.delete(...)` also produces an `hx-swap-oob` element
        and will be picked up here as an (empty) fragment. Comparing a
        delete swap's fragment against a full-reload's live rendering of
        that id isn't generally meaningful — assert_shell_composition is
        built for verifying nav/shell regions stay in sync, not for
        delete-swap semantics — so avoid it for views whose swap list
        includes a delete.
        """
        fragments: dict[str, str] = {}
        primary_parts: list[str] = []

        for node in list(self.soup.contents):
            name = getattr(node, "name", None)
            attrs = getattr(node, "attrs", {}) or {}

            if name == "title":
                node.extract()
            elif attrs.get("hx-swap-oob") and attrs.get("id"):
                fragments[attrs["id"]] = node.decode_contents()
                node.extract()
            elif name == "hx-partial" and attrs.get("hx-target", "").lstrip("#"):
                fragments[attrs["hx-target"].lstrip("#")] = node.decode_contents()
                node.extract()
            else:
                primary_parts.append(str(node))

        return "".join(primary_parts), fragments


def assert_shell_composition(
    client: Client,
    url: str,
    *,
    page_shell_kwargs: dict[str, Any],
    tab_shell_kwargs: dict[str, Any],
    full_reload_kwargs: dict[str, Any] | None = None,
    page_container_id: str = "page-content",
    tab_container_id: str = "tab-content",
    self_wrapped: bool = False,
) -> dict[str, Any]:
    """Assert that full-page reloads and HTMX swap variants compose identical HTML.

    Performs requests across three HTMX interaction tiers (full page reload,
    page-shell swap, and component/tab swap) and verifies the resulting
    markup actually nests and matches — catching bugs `assert_shell_parity`
    can't see: a partial response missing the wrapper element its
    `hx-target` expects to swap into, template branching on request headers
    that produces different markup from identical context, or an OOB/
    hx-partial fragment (sidebar, breadcrumbs, tabs, ...) whose content has
    silently drifted from what the full page renders for that same region.

    Verifies, in order:
        1. Full-reload's `#{page_container_id}` vs. page_shell's primary
           (non-fragment) content.
        2. Each OOB/hx-partial fragment on the page_shell response vs. the
           matching id's contents on the full-reload response.
        3. Page_shell's `#{tab_container_id}` vs. tab_shell's primary
           content — the actual nesting check.
        4. Full-reload's `#{tab_container_id}` vs. tab_shell's primary
           content — transitive; catches drift that 1+3 alone could miss
           if page_shell and full reload happened to agree by coincidence.
        5. Each OOB/hx-partial fragment on the tab_shell response vs. the
           matching id's contents on the full-reload response.

    Requires beautifulsoup4 (`pip install beautifulsoup4`).

    Args:
        client: The Django test client instance.
        url: The target endpoint URL.
        page_shell_kwargs: kwargs for `client.get` representing a
            page-level swap (e.g. `{"HTTP_HX_REQUEST": "true",
            "HTTP_HX_TARGET": "page-content"}`).
        tab_shell_kwargs: kwargs for `client.get` representing a
            component/tab-level swap.
        full_reload_kwargs: kwargs for a standard browser GET. Defaults to `{}`.
        page_container_id: The element id targeted by page-level swaps.
        tab_container_id: The element id targeted by tab-level swaps.
        self_wrapped: Whether swap responses re-emit their own container
            wrapper (`hx-swap="outerHTML"` convention) rather than
            rendering only the container's children (the default —
            matches render_nav/Swap and Django 6 `{% partialdef %}`). Only
            affects the primary content comparison; extracted OOB/
            hx-partial fragments are always compared by inner content,
            since Swap.render never re-emits the wrapper it produces.

    Returns:
        dict[str, Any]: `{"full_reload": resp, "page_shell": resp, "tab_shell": resp}`
        for further assertions.

    Raises:
        AssertionError: If any request returns a non-200 status code, if a
            referenced container id isn't found, or if HTML markup diverges
            between response modes.
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

    full_doc = _HTMLDocument(full.content)
    page_doc = _HTMLDocument(page_shell.content)
    tab_doc = _HTMLDocument(tab_shell.content)

    page_primary, page_fragments = page_doc.split_fragments()
    tab_primary, tab_fragments = tab_doc.split_fragments()

    # 1. full reload <-> page_shell primary content
    assert_html_equal(
        full_doc.container_html(page_container_id, self_wrapped=self_wrapped),
        page_primary,
        label_a=f"full reload's #{page_container_id}",
        label_b="page_shell primary content",
    )
    # 2. full reload <-> page_shell fragments
    for frag_id, frag_html in page_fragments.items():
        assert_html_equal(
            full_doc.inner_html(frag_id),
            frag_html,
            label_a=f"full reload's #{frag_id}",
            label_b=f"page_shell #{frag_id} fragment",
        )

    # 3. page_shell <-> tab_shell primary content (nesting)
    assert_html_equal(
        page_doc.container_html(tab_container_id, self_wrapped=self_wrapped),
        tab_primary,
        label_a=f"page_shell's #{tab_container_id}",
        label_b="tab_shell primary content",
    )

    # 4. full reload <-> tab_shell primary content (transitive)
    assert_html_equal(
        full_doc.container_html(tab_container_id, self_wrapped=self_wrapped),
        tab_primary,
        label_a=f"full reload's #{tab_container_id}",
        label_b="tab_shell primary content",
    )
    # 5. full reload <-> tab_shell fragments
    for frag_id, frag_html in tab_fragments.items():
        assert_html_equal(
            full_doc.inner_html(frag_id),
            frag_html,
            label_a=f"full reload's #{frag_id}",
            label_b=f"tab_shell #{frag_id} fragment",
        )

    return {"full_reload": full, "page_shell": page_shell, "tab_shell": tab_shell}