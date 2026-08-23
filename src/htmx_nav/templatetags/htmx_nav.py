from django import template
from django.utils.safestring import mark_safe

from ..debugging import debug_swap_marker

register = template.Library()


@register.simple_tag
def htmx_nav_debug_marker(target_id: str):
    """Renders the same debug-swap marker `Swap(target_id=...)` would,
    for hand-built OOB fragments. See `htmx_nav.debugging.debug_swap_marker`."""
    return mark_safe(debug_swap_marker(target_id))