# Pattern: a hand-rolled registry

Good fit once a project has enough views that "what breadcrumbs/tabs does
this view have" needs one obvious place to look, and/or you want to
assert nav state in tests without rendering templates.

**This code is meant to be copied into your project (e.g. `yourapp/nav.py`)
and adapted — `htmx_nav` does not ship a `Registry`/`LinkItem`/`NavState`
class.** An earlier version of this package did ship exactly that as a
framework; it turned out to be more machinery than most projects need,
and the wrong machinery for projects with a different shape (a navbar
instead of a sidebar, no breadcrumbs, etc.). The version below is
intentionally plain — dataclasses and dicts, ~40 lines — so you can bend
it to your project instead of the other way around.

## `yourapp/nav.py`

```python
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
    view_name: Optional[str] = None  # None = current page, not a link


@dataclass(frozen=True)
class NavState:
    """What a given view_name means for nav purposes."""
    active_link: str = ""
    breadcrumbs: Sequence[Crumb] = field(default_factory=tuple)


# --- your project's actual data — this is the part that's genuinely
# project-specific, and the part worth keeping in one obvious place ---

SIDEBAR = [
    Link("Dashboard", "app:dashboard", ICON_DASHBOARD),
    Link("Projects", "app:project_list", ICON_PROJECTS),
]

NAV_STATES: dict[str, NavState] = {
    "app:dashboard": NavState(active_link="app:dashboard", breadcrumbs=[Crumb("Dashboard")]),
    "app:project_list": NavState(
        active_link="app:project_list",
        breadcrumbs=[Crumb("Projects")],
    ),
    "app:project_detail": NavState(
        active_link="app:project_list",
        breadcrumbs=[Crumb("Projects", "app:project_list"), Crumb(lambda r: r.project.name)],
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
                "url": reverse_maybe(crumb.view_name, match.kwargs if match else {}, strict=False)
                if crumb.view_name else None,
            }
            for crumb in state.breadcrumbs
        ]
        return {"sidebar": sidebar, "breadcrumbs": breadcrumbs}

    return cache_on_request(request, "_yourapp_nav", _build)
```

Note `Crumb(lambda r: r.project.name)` for the project-detail breadcrumb —
this assumes something upstream (a decorator, a mixin, `get_object`)
stashed the resolved object on `request` before nav context gets built.
That's a project-specific wiring detail worth deciding deliberately rather
than copying blind — the alternative is computing breadcrumbs inside the
view itself (see "Skipping the registry entirely" below) once a view's
breadcrumbs need data that's expensive to fetch twice.

## Wiring it up

```python
# yourapp/render.py
from htmx_nav.responses import make_shell_renderer
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
    request.project = project  # if using the lambda-crumb wiring above
    return render_shell(request, "yourapp/project_detail.html", {"project": project})
```

## Testing it

Because `build_nav_context` returns plain dicts, you can assert against
it directly, on top of the cross-cutting check from `htmx_nav.testing`:

```python
from htmx_nav.testing import assert_shell_parity

def test_project_detail_nav_parity(client, project):
    assert_shell_parity(
        client, f"/projects/{project.pk}/",
        checks={
            "active_sidebar_item": lambda ctx: [i["label"] for i in ctx["nav"]["sidebar"] if i["active"]],
            "breadcrumbs": lambda ctx: [c["label"] for c in ctx["nav"]["breadcrumbs"]],
        },
    )
```

## Extending it

Add fields to `Link`/`NavState` as your project actually needs them,
`visible_if: Callable[[HttpRequest], bool]` for conditional visibility,
`extra: dict` for arbitrary per-item metadata, a second `NAVBAR` list plus
a second entry in the returned context dict for a navbar alongside the
sidebar, and so on. There's no base class to satisfy and no required
shape beyond "produces a dict `render_shell`'s `context_builder` can
return" — grow it in whatever direction your actual UI needs, not in the
direction a generic framework guessed you might need.

## Skipping the registry entirely

For a handful of views, even this might be more structure than you need
— compute breadcrumbs inline in the view instead:

```python
from htmx_nav.helpers import reverse_maybe

def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    breadcrumbs = [
        {"label": "Projects", "url": reverse_maybe("app:project_list")},
        {"label": project.name, "url": None},
    ]
    return render_shell(request, "yourapp/project_detail.html", {
        "project": project,
        "breadcrumbs": breadcrumbs,
    })
```

This is the same idea as the registry, just not centralized, reach for
the registry once "which views need updating when I rename a breadcrumb"
becomes a real question, not before.
