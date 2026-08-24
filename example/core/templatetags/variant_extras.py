from django import template
from django.utils.safestring import mark_safe

from core.navigation.oob import oob_components

register = template.Library()


@register.simple_tag(takes_context=True)
def hx_select_attrs(context, target_id: str) -> str:
    """Client-side sync for whatever component_swaps doesn't already cover.
    
    Composable with uses_htmx_nav, e.g. htmx_nav_composite covers only
    sidebar/breadcrumbs via Python Swaps, leaving tabs/subtabs as a real
    gap this can fill. No-op when component_swaps already covers
    everything or when uses_hx_select is False.
    """
    variant = context["active_variant"]
    if not variant.uses_hx_select:
        return ""
    leftover = oob_components(target_id, variant.component_swaps)
    if not leftover:
        return ""
    selectors = ", ".join(f"#{c}" for c in leftover)
    return mark_safe(f'hx-select="#{target_id}" hx-select-oob="{selectors}"')


@register.simple_tag(takes_context=True)
def morph_attrs(context, target_id: str) -> str:
    """hx-swap=morph for target_id, plus morph-OOB for any leftover components."""
    variant = context["active_variant"]
    if not variant.uses_morph:
        return ""
    attrs = ['hx-swap="morph"']
    if leftover := oob_components(target_id, variant.component_swaps):
        selectors = ", ".join(f"#{c}" for c in leftover)
        attrs.append(f'hx-swap-oob="morph:{selectors}"')
    return mark_safe(" ".join(attrs))