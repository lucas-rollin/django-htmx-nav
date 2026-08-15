# Navigation Patterns

*Supplying `context_builder` to `make_shell_renderer`.*

`make_shell_renderer` exists to stop every view from re-declaring the same
sidebar/breadcrumb `Swap`s. It does this by baking a `context_builder`
function into a `render_shell` closure, so each view just calls
`render_shell(...)` and the nav data comes along for free.

This page is about *how to write that `context_builder`* — the two
patterns below (a Python registry, or Django's own template-tag system)
are the two ends of the spectrum, and most projects land on one or a
blend of both.

## You don't need this at all

`make_shell_renderer` is a convenience layer, not a requirement.
`render_nav` (which it wraps) already does everything needed to swap a
sidebar or breadcrumb region out-of-band:

```python
from htmx_nav import Swap, render_nav


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_nav(
        request,
        "app/project_detail.html",
        {"project": project},
        swaps=[
            Swap("app/_sidebar.html", {"active": project.pk}, target_id="sidebar"),
            Swap(
                "app/_breadcrumbs.html", {"project": project}, target_id="breadcrumbs"
            ),
        ],
    )
```

That's a perfectly valid way to use the package. The tradeoff is purely
about repetition: every view that touches shared nav has to remember to
build and pass those `Swap`s itself, and if you forget on view #12, its
sidebar goes stale on HTMX navigation. `make_shell_renderer` exists
*only* to centralize that so you can't forget it, it trades a small
amount of upfront structure (a `context_builder`, and possibly one of
the two patterns below) for never having to think about it again in a
view. If your project has two or three views and a static sidebar,
that trade often isn't worth making, use `render_nav` directly and
stop reading here.

If you do want that centralization, keep reading.

## The contract

```python
render_shell = make_shell_renderer(
    shell_template="yourapp/_shell.html",
    context_builder=lambda request: {"nav": build_nav_context(request)},
)
```

`context_builder` is any `Callable[[HttpRequest], Mapping[str, Any]]`.
It's called once per request (full load or HTMX) and its return value
becomes the context for `shell_template`, under the `namespace` key if
`make_shell_renderer(..., namespace=...)` was given, otherwise merged
flat alongside the page's own context. Everything below is just advice
on what `build_nav_context` (or whatever you name it) should look like
and where the data it returns should live.

## Pattern A: Centralized registry

A hand-rolled registry of navigation data in one Python module. Best
when the project has enough views that "what does the sidebar look
like from here" needs a single, auditable source of truth.

### Navigation registry

```python
# yourapp/nav.py
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence, Union

from django.http import HttpRequest

from htmx_nav.helpers import cache_on_request, reverse_maybe

DynamicStr = Union[str, Callable[[HttpRequest], str]]


def _label(value: DynamicStr, request: HttpRequest) -> str:
    return value(request) if callable(value) else value


@dataclass(frozen=True)
class Link:
    label: DynamicStr
    view_name: str
    icon: str = ""


@dataclass(frozen=True)
class Crumb:
    label: DynamicStr
    view_name: Optional[str] = None  # None = current page, not linked


@dataclass(frozen=True)
class NavState:
    """Navigation state for a given view."""

    active_link: str = ""
    breadcrumbs: Sequence[Crumb] = field(default_factory=tuple)


# Project-specific navigation data
SIDEBAR = [
    Link("Dashboard", "app:dashboard", ICON_DASHBOARD),
    Link("Projects", "app:project_list", ICON_PROJECTS),
]

NAV_STATES: dict[str, NavState] = {
    "app:dashboard": NavState(
        active_link="app:dashboard", breadcrumbs=[Crumb("Dashboard")]
    ),
    "app:project_list": NavState(
        active_link="app:project_list",
        breadcrumbs=[Crumb("Projects")],
    ),
    "app:project_detail": NavState(
        active_link="app:project_list",
        breadcrumbs=[
            Crumb("Projects", "app:project_list"),
            Crumb(lambda r: r.project.name),
        ],
    ),
}


def build_nav_context(request: HttpRequest) -> dict:
    def _build():
        match = request.resolver_match
        view_name = match.view_name if match else ""
        state = NAV_STATES.get(view_name, NavState())

        sidebar = [
            {
                "label": _label(link.label, request),
                "url": reverse_maybe(link.view_name),
                "icon": link.icon,
                "active": link.view_name == state.active_link,
            }
            for link in SIDEBAR
        ]
        breadcrumbs = [
            {
                "label": _label(crumb.label, request),
                "url": reverse_maybe(
                    crumb.view_name, match.kwargs if match else {}, strict=False
                )
                if crumb.view_name
                else None,
            }
            for crumb in state.breadcrumbs
        ]
        return {"sidebar": sidebar, "breadcrumbs": breadcrumbs}

    return cache_on_request(request, "_yourapp_nav", _build)
```

### Wiring it up

```python
# yourapp/render.py
from htmx_nav import make_shell_renderer

from .nav import build_nav_context

render_shell = make_shell_renderer(
    shell_template="yourapp/_shell.html",
    context_builder=lambda request: {"nav": build_nav_context(request)},
)
```

```python
# yourapp/views.py
from .render import render_shell


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    request.project = project  # needed for the lambda-based crumb above
    return render_shell(request, "yourapp/project_detail.html", {"project": project})
```

### Testing

Because the registry returns plain dicts, you can assert against them
directly, without rendering templates:

```python
from htmx_nav.testing import assert_shell_parity


def test_project_detail_nav_parity(client, project):
    assert_shell_parity(
        client,
        f"/projects/{project.pk}/",
        checks={
            "active_sidebar_item": lambda ctx: [
                i["label"] for i in ctx["nav"]["sidebar"] if i["active"]
            ],
            "breadcrumbs": lambda ctx: [c["label"] for c in ctx["nav"]["breadcrumbs"]],
        },
    )
```

### Extension points

- Add fields to `Link`/`NavState` (e.g. `visible_if: Callable`, `extra: dict`)
- Support multiple structures at once (navbar *and* sidebar)
- Add conditional visibility based on request state
- Attach arbitrary metadata to nav items

### Escape hatch: inline breadcrumbs for one-off views

The registry doesn't have to own *every* view's breadcrumbs. A view
that doesn't fit the general shape can just pass its own:

```python
from htmx_nav.helpers import reverse_maybe


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    breadcrumbs = [
        {"label": "Projects", "url": reverse_maybe("app:project_list")},
        {"label": project.name, "url": None},
    ]
    return render_shell(
        request,
        "yourapp/project_detail.html",
        {"project": project, "breadcrumbs": breadcrumbs},
    )
```

## Pattern B: Context processors + template tags

Leans on Django's own template-tag system instead of a parallel data
structure — navigation markup lives next to the HTML it renders. Best
for small, mostly-static navigation where a registry would just be
indirection.

### Template tags

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
    url = reverse_maybe(
        view_name,
        request.resolver_match.kwargs if request.resolver_match else {},
        strict=False,
    )
    return f'<a href="{url}" class="crumb">{label}</a>'
```

### Shell template

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

Per-view breadcrumbs override the block:

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

### Context processors for the rest

Anything that isn't rendered via a tag (e.g. data every template needs
regardless of nav) can ride in on a normal context processor instead
of `context_builder`:

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

### Wiring it up

Note `context_builder` is optional here. If template tags and context
processors cover everything, `make_shell_renderer` needs nothing more
than the shell template itself:

```python
from htmx_nav import make_shell_renderer

render_shell = make_shell_renderer(shell_template="yourapp/_shell.html")


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_shell(request, "yourapp/project_detail.html", {"project": project})
```

### Testing

Parity here is verified by rendering, not by asserting against plain
data:

```python
from htmx_nav.testing import assert_shell_parity


def test_navigation_parity(client):
    assert_shell_parity(client, "/some-url/")
```

## Choosing between them

| | Registry (A) | Template tags (B) |
|---|---|---|
| Nav structure lives in | Python dataclasses | HTML/templates |
| `context_builder` needed? | Yes, always | Often not at all |
| Scales to many views | Well, one file to audit | Poorly, logic spreads across templates |
| Testable without rendering | Yes, plain dicts | No, requires HTML rendering |
| Upfront cost | Higher (schema + registry) | Lower (uses tags you already know) |
| Conditional/complex nav logic | Straightforward | Awkward, pushes logic into templates |

**Use the registry** if the project has enough views that you want one
place to audit "what nav state does view X produce," or if breadcrumb
relationships are non-trivial and worth centralizing.

**Use template tags** if navigation is small and mostly static, and a
parallel Python data structure would just be indirection over what the
templates already say.

Nothing stops you from mixing them, e.g. a registry for breadcrumbs
(where relationships matter) and template tags for a static sidebar
(where they don't). Both patterns build on the same
`make_shell_renderer(context_builder=...)` seam, so switching later, or
combining them, doesn't touch your views.

And if none of this earns its keep yet, remember the option from the
top of this page: skip `make_shell_renderer` entirely and pass `Swap`s
to `render_nav` per view. Reach for one of these patterns only once
that repetition actually starts to hurt.