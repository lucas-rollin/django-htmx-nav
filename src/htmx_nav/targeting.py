"""
HTMX request-targeting: the Target condition type, predicates built from
it, low-level HX-Target matching, and Target evaluation.
"""

from collections.abc import Callable
from typing import TypeAlias

from django.http import HttpRequest

Target: TypeAlias = str | Callable[[HttpRequest], bool] | bool
"""Condition deciding whether a partial or swap applies to an HTMX request.

Examples:
    .. code-block:: python

        "main-content"  # Matches HX-Target header
        targeting("main-content", "modal")
        not_targeting("sidebar")
        True
        False
"""


def _is_htmx_request(request: HttpRequest) -> bool:
    """Determines whether the request is an HTMX request."""
    htmx_attr = getattr(request, "htmx", None)
    if htmx_attr is not None:
        return bool(htmx_attr)
    return request.headers.get("HX-Request", "") == "true"


def _htmx_target_header(request: HttpRequest) -> str | None:
    """Resolve the effective HX-Target value for this request.

    Prefers request.htmx.target (django-htmx) when django-htmx's middleware
    has populated it; otherwise falls back to reading the raw HX-Target
    header directly.
    """
    htmx = getattr(request, "htmx", None)
    if htmx is not None:
        return getattr(htmx, "target", None)
    return request.headers.get("HX-Target")


def _dom_id(value: str) -> str:
    """Normalizes selector strings like 'div#foo' or '#foo' to 'foo'."""
    return value.rsplit("#", 1)[-1]


def _htmx_target_is(target: str | None, dom_id: str) -> bool:
    """Checks if an HX-Target header matches a DOM ID across HTMX versions."""
    if not target:
        return False
    return _dom_id(target) == _dom_id(dom_id)


def htmx_target_is(request: HttpRequest, *dom_ids: str) -> bool:
    """Checks if the request's `HX-Target` header matches any given DOM ID.

    Args:
        request: The incoming HTTP request.
        *dom_ids: DOM element IDs to match against (e.g., `"content"`, `"#content"`).

    Returns:
        True if the request target matches any provided ID.

    Example:
        .. code-block:: python

            if htmx_target_is(request, "tab-content", "modal-body"):
                ...
    """
    target = _htmx_target_header(request)
    return any(_htmx_target_is(target, dom_id) for dom_id in dom_ids)


def targeting(*dom_ids: str) -> Callable[[HttpRequest], bool]:
    """Creates a predicate checking if a request targets any specified DOM ID.

    Example:
        .. code-block:: python

            Swap(
                "partials/tabs.html",
                target_id="tabs",
                include_if=targeting("tab-content", "tabs"),
            )
    """

    def predicate(request: HttpRequest) -> bool:
        return htmx_target_is(request, *dom_ids)

    return predicate


def not_targeting(*dom_ids: str) -> Callable[[HttpRequest], bool]:
    """Creates a predicate checking that a request does NOT target specified DOM IDs.

    Example:
        .. code-block:: python

            Swap(
                "partials/sidebar.html",
                target_id="sidebar",
                include_if=not_targeting("main-content"),
            )
    """

    def predicate(request: HttpRequest) -> bool:
        return not htmx_target_is(request, *dom_ids)

    return predicate


def _eval_target(spec: Target, request: HttpRequest) -> bool:
    """Evaluates a `Target` specification against an HTTP request."""
    if spec is True:
        return True
    if spec is False:
        return False
    if isinstance(spec, str):
        return htmx_target_is(request, spec)
    if callable(spec):
        return bool(spec(request))
    raise TypeError(f"Invalid Target value: {spec!r}")
