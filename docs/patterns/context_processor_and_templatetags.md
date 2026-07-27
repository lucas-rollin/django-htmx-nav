# Pattern: context processor + template tags

Good fit when your nav is mostly declared *in templates*, you'd rather
write `{% nav_link "app:dashboard" "Dashboard" %}` next to your HTML than
maintain a separate Python data structure describing the same thing.

This is plain Django: a context processor makes `request` (and anything
else you want) available to every template, and a couple of template
tags do the `reverse()`/active-state work inline. `htmx_nav` doesn't need
to know any of this is happening, it only cares that your shell template
renders correctly as an OOB fragment, which it already does.

## 1. Template tags

```python
# yourapp/templatetags/nav_tags.py
from django import template
from htmx_nav.helpers import reverse_maybe

register = template.Library()


@register.simple_tag(takes_context=True)
def nav_link(context, view_name, label, css_class="nav-link"):
    request = context["request"]
    is_active = request.resolver_match and request.resolver_match.view_name == view_name
    url = reverse_maybe(view_name)
    active_class = f" {css_class}--active" if is_active else ""
    return f'<a href="{url}" class="{css_class}{active_class}">{label}</a>'


@register.simple_tag(takes_context=True)
def nav_crumb(context, label, view_name=None):
    request = context["request"]
    if not view_name:
        return f'<span class="crumb crumb--current">{label}</span>'
    url = reverse_maybe(view_name, request.resolver_match.kwargs if request.resolver_match else {}, strict=False)
    return f'<a href="{url}" class="crumb">{label}</a>'
```

## 2. The shell template, written directly in HTML

```html
{# yourapp/templates/yourapp/_shell.html #}
{% load nav_tags %}
<nav id="sidebar" hx-swap-oob="true">
  {% nav_link "app:dashboard" "Dashboard" %}
  {% nav_link "app:project_list" "Projects" %}
</nav>
<div id="breadcrumbs" hx-swap-oob="true">
  {% block breadcrumbs %}{% endblock %}
</div>
```

Per-view breadcrumbs are just template blocks, overridden per page:

```html
{# yourapp/templates/yourapp/project_detail.html #}
{% extends "yourapp/_shell.html" %}
{% load nav_tags %}
{% block breadcrumbs %}
  {% nav_crumb "Projects" "app:project_list" %}
  {% nav_crumb project.name %}
{% endblock %}
{% partialdef content %}
  ...
{% endpartialdef %}
```

## 3. Wiring it up

No context processor is actually required here, `context={"request": ...}`
is already implied by `TemplateResponse` and `{% load nav_tags %}`'s
`takes_context=True`. If you *do* want some nav-adjacent data (current
user's permissions, active workspace) available without passing it
explicitly on every `render_htmx` call, that's what a context processor
is for:

```python
# yourapp/context_processors.py
def workspace(request):
    return {"active_workspace": get_active_workspace(request)}
```

```python
# settings.py
TEMPLATES = [{
    ...,
    "OPTIONS": {
        "context_processors": [
            ...,
            "yourapp.context_processors.workspace",
        ],
    },
}]
```

Then in views:

```python
from htmx_nav.responses import make_shell_renderer

render_shell = make_shell_renderer(shell_template="yourapp/_shell.html")
# no context_builder needed — the shell template gets everything it
# needs from context processors + {% load nav_tags %}

def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_shell(request, "yourapp/project_detail.html", {"project": project})
```

## Trade-offs

- **Pro:** nav structure lives next to the HTML it produces, easy to see
  what a page actually looks like, no separate data model to keep in sync.
- **Pro:** genuinely zero extra Python data structures; if your nav is
  small (a handful of static links), this is the least code.
- **Con:** "what view maps to what breadcrumbs" isn't centralized anywhere
  — harder to audit at a glance once you have dozens of views, and there's
  no single place to enforce "every registered view has breadcrumbs."
- **Con:** testing nav state means rendering templates (`assert_shell_parity`
  from `htmx_nav.testing` still works here, it inspects rendered context,
  not the templates directly), rather than asserting against plain data.

If that centralization/testability trade-off starts to bite, see
`docs/patterns/registry_pattern.md` for the alternative.
