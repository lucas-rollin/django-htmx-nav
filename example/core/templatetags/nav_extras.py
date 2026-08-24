from django import template

register = template.Library()


@register.filter
def dict_get(d, key):
    """Dict get with a None failsafe."""
    if not d:
        return None
    return d.get(key)


@register.filter
def status_badge_class(status):
    return {
        "open": "badge-info",
        "in_progress": "badge-warning",
        "resolved": "badge-success",
        "closed": "badge-neutral",
    }.get(status, "badge-ghost")


@register.filter
def department_label(dept):
    return {
        "product_engineering": "Product Engineering",
        "technical_support": "Technical Support",
        "customer_success": "Customer Success",
    }.get(dept, dept)


@register.filter
def status_label(status):
    return {
        "open": "Open",
        "in_progress": "In progress",
        "resolved": "Resolved",
        "closed": "Closed",
    }.get(status, status)
