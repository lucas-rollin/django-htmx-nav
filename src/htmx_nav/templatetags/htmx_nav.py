"""Template tags for django-htmx-nav."""

from django import template
from django.utils.safestring import SafeString, mark_safe

from ..debugging import debug_swap_marker

register = template.Library()


@register.simple_tag
def htmx_nav_debug_marker(target_id: str) -> SafeString:
    """Render a debug-swap marker script for hand-crafted out-of-band fragments.

    Emits the same inline ``<script>`` tag that ``Swap`` produces when
    ``target_id`` is configured and ``HTMX_NAV_DEBUG_SWAPS`` is enabled. Useful
    when writing manual OOB wrappers (e.g. within ``{% partialdef %}`` blocks)
    that bypass ``Swap`` auto-wrapping.

    Args:
        target_id: Target DOM element ID to highlight.

    Returns:
        A safe HTML string containing the inline ``<script>`` tag when
        ``HTMX_NAV_DEBUG_SWAPS`` is enabled, or an empty string.

    Example:
        .. code-block:: django

            {% load htmx_nav %}

            <div id="breadcrumbs" hx-swap-oob="innerHTML">
                {% htmx_nav_debug_marker "breadcrumbs" %}
                <nav>...</nav>
            </div>
    """
    return mark_safe(debug_swap_marker(target_id))
