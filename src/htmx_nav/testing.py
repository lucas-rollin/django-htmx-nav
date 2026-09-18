"""Testing utilities for django-htmx-nav.

Provides assertion helpers for Django and HTMX test suites to verify
navigation parity and HTML fragment composition.
"""

import difflib
import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from django.test import Client
from django.test.html import parse_html

if TYPE_CHECKING:
    from bs4 import BeautifulSoup, Tag
else:
    try:
        from bs4 import BeautifulSoup, Tag
    except ImportError:
        BeautifulSoup = None
        Tag = None

__all__ = ["assert_shell_parity", "assert_shell_composition", "assert_html_equal"]


_DEBUG_MARKER_RE = re.compile(
    r"<script>\(function\(\)\{.*?hn-swap.*?\}\)\(\);</script>", re.DOTALL
)


def _strip_debug_markers(html: str) -> str:
    """Removes debug-swap marker <script> tags from HTML for comparison."""
    return _DEBUG_MARKER_RE.sub("", html)


def assert_shell_parity(
    client: Client,
    url: str,
    *,
    requests: dict[str, dict[str, Any]],
    checks: dict[str, Callable[[Any], Any]],
) -> dict[str, Any]:
    """Asserts that template context remains consistent across request modes.

    Issues GET requests for each scenario in ``requests`` and executes
    extraction callbacks against response contexts to verify shell state
    parity (e.g. active links, breadcrumbs, sidebar items).

    Args:
        client: The Django test client instance.
        url: The target URL to request.
        requests: Mapping of scenario labels to kwargs passed to ``client.get``.
        checks: Mapping of check labels to extraction functions receiving
            ``response.context``.

    Returns:
        Mapping of scenario labels to their Django response objects.

    Raises:
        AssertionError: If any check produces a value that differs from the
            baseline established by the first request.

    Example:
        .. code-block:: python

            requests = {
                "full_reload": {},
                "page_shell": {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "page-content"},
            }
            checks = {
                "active_tab": lambda ctx: ctx["active_tab"],
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
    """Asserts that two HTML documents or fragments are structurally equal.

    Normalizes whitespace and attribute ordering using Django's ``parse_html``
    and strips debug marker scripts before comparing.

    Args:
        a: First HTML document or fragment.
        b: Second HTML document or fragment.
        label_a: Label for ``a`` in unified diff output. Defaults to "a".
        label_b: Label for ``b`` in unified diff output. Defaults to "b".

    Raises:
        AssertionError: If the two documents differ structurally, including
            a unified diff.

    Example:
        .. code-block:: python

            assert_html_equal(response.content, "<div id='main'>Hello</div>")
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
    """Helper for parsing response HTML and extracting DOM fragments."""

    def __init__(self, raw_html: bytes | str):
        if BeautifulSoup is None or Tag is None:
            raise ImportError(
                "assert_shell_composition requires beautifulsoup4. "
                "Install it with: pip install beautifulsoup4"
            )

        if isinstance(raw_html, bytes):
            raw_html = raw_html.decode("utf-8")

        self.soup = BeautifulSoup(_strip_debug_markers(raw_html), "html.parser")

    def _find_element(self, element_id: str) -> Tag:
        element = self.soup.find(id=element_id)
        if element is None or not isinstance(element, Tag):
            raise AssertionError(
                f"Could not find any element with id={element_id!r} in the response HTML."
            )
        return element

    def inner_html(self, element_id: str) -> str:
        """Returns the serialized child nodes of the element."""
        return str(self._find_element(element_id).decode_contents())

    def outer_html(self, element_id: str) -> str:
        """Returns the serialized element including its opening and closing tags."""
        return str(self._find_element(element_id))

    def container_html(self, element_id: str, *, self_wrapped: bool) -> str:
        """Returns outer HTML if self_wrapped is True, otherwise inner HTML."""
        return (
            self.outer_html(element_id) if self_wrapped else self.inner_html(element_id)
        )

    def split_fragments(self) -> tuple[str, dict[str, str]]:
        """Splits the document into primary content and out-of-band swap fragments."""
        fragments: dict[str, str] = {}
        primary_parts: list[str] = []

        for node in list(self.soup.contents):
            if not isinstance(node, Tag):
                primary_parts.append(str(node))
                continue

            name = node.name
            attrs = node.attrs or {}

            if name == "title":
                node.extract()
            elif attrs.get("hx-swap-oob") and attrs.get("id"):
                elem_id = attrs["id"]
                elem_id_str = elem_id if isinstance(elem_id, str) else str(elem_id)
                fragments[elem_id_str] = str(node.decode_contents())
                node.extract()
            elif name == "hx-partial" and (hx_target := attrs.get("hx-target")):
                hx_target_str = (
                    hx_target if isinstance(hx_target, str) else str(hx_target)
                )
                target_id = hx_target_str.lstrip("#")
                if target_id:
                    fragments[target_id] = str(node.decode_contents())
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
    """Asserts that full-page reloads and HTMX swap responses compose identical HTML.

    Performs requests across three interaction tiers (full page reload,
    page-level shell swap, and tab/component swap) and verifies that HTML
    fragments nest and match structurally without state drift.

    Args:
        client: The Django test client instance.
        url: The target endpoint URL.
        page_shell_kwargs: Kwargs for ``client.get`` representing a page-level swap.
        tab_shell_kwargs: Kwargs for ``client.get`` representing a tab-level swap.
        full_reload_kwargs: Optional kwargs for a standard browser GET.
            Defaults to ``{}``.
        page_container_id: DOM element ID targeted by page-level swaps.
            Defaults to "page-content".
        tab_container_id: DOM element ID targeted by tab-level swaps.
            Defaults to "tab-content".
        self_wrapped: Set to True if swap responses re-emit their outer
            container tag (``hx-swap="outerHTML"``). Defaults to False.

    Returns:
        Mapping containing ``"full_reload"``, ``"page_shell"``, and ``"tab_shell"``
        response objects.

    Raises:
        AssertionError: If any response status is not 200, a container ID is
            missing, or fragment markup diverges.
        ImportError: If ``beautifulsoup4`` is not installed.

    Example:
        .. code-block:: python

            responses = assert_shell_composition(
                client,
                "/projects/1/",
                page_shell_kwargs={"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "page-content"},
                tab_shell_kwargs={"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "tab-content"},
                page_container_id="page-content",
                tab_container_id="tab-content",
            )
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
