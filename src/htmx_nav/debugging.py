"""
Debug-swap marker: Add an inline ``<script>`` to flash a target element
when ``HTMX_NAV_DEBUG_SWAPS`` is enabled.

``_build_marker_script`` is used both by ``Swap.render()`` internally and by
the public ``debug_swap_marker`` templatetag.
"""

import json

from django.http import HttpRequest
from django.middleware.csp import get_nonce
from django.utils.html import escape

__all__ = ["debug_swap_marker"]


def _request_csp_nonce(request: HttpRequest | None) -> str | None:
    """Resolve the active CSP nonce for ``request``, supporting Django 6 CSP and django-csp."""
    if request is None:
        return None
    nonce = get_nonce(request)
    if nonce is None:
        nonce = getattr(request, "csp_nonce", None)
    if nonce is None:
        return None
    value = str(nonce)
    return value or None


def _build_marker_script(target_id: str, *, nonce: str | None = None) -> str:
    """Build the marker script for ``target_id`` unconditionally.

    Reapplies a class to the element so animations retrigger upon
    repeated swaps. Used both by ``Swap.render()`` internally and by the public
    ``debug_swap_marker`` templatetag.
    """
    safe_id = json.dumps(target_id).replace("</", r"<\/")
    nonce_attr = f' nonce="{escape(nonce)}"' if nonce else ""
    return (
        f"<script{nonce_attr}>(function(){{"
        f"var el=document.getElementById({safe_id});"
        "if(!el)return;"
        "el.classList.remove('hn-swap');void el.offsetWidth;"
        "el.classList.add('hn-swap');"
        "})();</script>"
    )


def debug_swap_marker(target_id: str, *, nonce: str | None = None) -> str:
    """Return an inline ``<script>`` tag to trigger a swap highlight animation.

    Args:
        target_id: The DOM element ID to highlight.
        nonce: Optional CSP nonce attached as ``nonce="..."`` on the script tag.

    Returns:
        An HTML script string if ``HTMX_NAV_DEBUG_SWAPS`` is enabled, otherwise
        an empty string.
    """
    from .settings import _debug_swaps_enabled

    if not _debug_swaps_enabled():
        return ""
    return _build_marker_script(target_id, nonce=nonce)
