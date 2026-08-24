"""
Shared debug-swap marker: the inline <script> that flashes a target
element when HTMX_NAV_DEBUG_SWAPS is enabled.

`_build_marker_script` is the single implementation, used both by
Swap.render() internally (target_id-driven auto-wrap) and by the public
`debug_swap_marker` / {% htmx_nav_debug_marker %} (hand-built OOB
fragments that skip Swap's wrapping).
"""

import json

__all__ = ["debug_swap_marker"]


def _build_marker_script(target_id: str) -> str:
    """Unconditionally builds the marker script for `target_id`.

    No enabled-check here — callers decide when to call this at all.
    Survives wrapper-stripping on innerHTML-style OOB/hx-partial swaps
    because it's emitted as a sibling of the fragment's own content,
    inside the wrapper. Class is re-applied with a forced reflow so
    repeated swaps of the same (non-replaced) element retrigger the
    CSS animation each time.
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
    """Inline `<script>` that flashes `target_id` when swap debugging is
    enabled; empty string otherwise.

    Use when hand-building an OOB fragment (writing `hx-swap-oob`
    yourself) instead of letting `Swap(target_id=...)` wrap it, and you
    still want `HTMX_NAV_DEBUG_SWAPS` highlighting. Must be placed
    *inside* the element carrying `target_id`.
    """
    from .settings import _debug_swaps_enabled

    if not _debug_swaps_enabled():
        return ""
    return _build_marker_script(target_id)
