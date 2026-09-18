"""
Debug-swap marker: Add an inline ``<script>`` to flash a target element
when ``HTMX_NAV_DEBUG_SWAPS`` is enabled.

``_build_marker_script`` is used both by ``Swap.render()`` internally and by
the public ``debug_swap_marker`` templatetag.
"""

import json

__all__ = ["debug_swap_marker"]


def _build_marker_script(target_id: str) -> str:
    """Build the marker script for ``target_id`` unconditionally.

    Reapplies a class to the element so animations retrigger upon
    repeated swaps. Used both by ``Swap.render()`` internally and by the public
    ``debug_swap_marker`` templatetag.
    """
    return (
        "<script>(function(){"
        f"var el=document.getElementById({json.dumps(target_id)});"
        "if(!el)return;"
        "el.classList.remove('hn-swap');void el.offsetWidth;"
        "el.classList.add('hn-swap');"
        "})();</script>"
    )


def debug_swap_marker(target_id: str) -> str:
    """Return an inline ``<script>`` tag to trigger a swap highlight animation.

    Args:
        target_id: The DOM element ID to highlight.

    Returns:
        An HTML script string if ``HTMX_NAV_DEBUG_SWAPS`` is enabled, otherwise
        an empty string.
    """
    from .settings import _debug_swaps_enabled

    if not _debug_swaps_enabled():
        return ""
    return _build_marker_script(target_id)
