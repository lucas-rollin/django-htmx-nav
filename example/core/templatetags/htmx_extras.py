from django import template

register = template.Library()


@register.filter
def hx_target(request, dom_id):
    """True if HX-Target matches dom_id. Same normalization htmx_nav's
    htmx_target_is does (strips 'div#foo' / '#foo' down to 'foo')."""
    target = request.headers.get("HX-Target", "")
    return target.rsplit("#", 1)[-1] == dom_id
