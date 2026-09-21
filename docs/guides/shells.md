# Shells & Class Based Views

In a multi-page web application, most views share the same outer layout: a sidebar showing active section highlights, a breadcrumb trail, and user profile widgets.

Declaring the same `Swap` list across dozens of views quickly introduces repetitive boilerplate. `django-htmx-nav` provides **Application Shells** to encapsulate shared navigation chrome in one place while allowing individual views to add custom out-of-band updates as needed.

## Defining a Shell Renderer (`make_shell_renderer`)

To build a reusable shell, define a function that returns the base swaps for your application layout, then pass it to `make_shell_renderer`:

```python
# app/renderers.py
from htmx_nav import Swap, make_shell_renderer


def build_shell_swaps(request):
    return [
        Swap("nav/_sidebar.html", target_id="sidebar"),
        Swap("nav/_breadcrumbs.html", target_id="breadcrumbs"),
    ]


# Create a reusable renderer:
render_shell = make_shell_renderer(build_shell_swaps)
```

Now, views in your application can call `render_shell` as a drop-in replacement for `render_nav`:

```python
# app/views.py
from django.shortcuts import get_object_or_404
from .models import Project
from .renderers import render_shell


def project_list(request):
    projects = Project.objects.all()
    # Automatically renders with sidebar and breadcrumbs synced out-of-band:
    return render_shell(request, "projects/list.html", {"projects": projects})
```

## Adding View-Specific Swaps (`extra_swaps`)

A specific view often needs to update additional regions beyond the global shell. Pass `extra_swaps` to append view-specific out-of-band updates alongside the base shell swaps:

```python
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)

    return render_shell(
        request,
        "projects/detail.html",
        {"project": project},
        # Appends view-specific swaps after the standard shell swaps:
        extra_swaps=[
            Swap("projects/_tabs.html", target_id="tabs"),
        ],
        title=project.name,
    )
```

## Request-Scoped Memoization (`cache_on_request`)

Application shells often need database data to render navigation widgets, such as fetching an active workspace, checking user roles, or counting unread notifications.

If both your shell builder and your view need the same data, you want to avoid redundant database queries during a single HTTP request. `django-htmx-nav` provides `cache_on_request` to store cached results on the `request` object:

```python
# app/renderers.py
from htmx_nav import Swap, make_shell_renderer
from htmx_nav.helpers import cache_on_request
from .models import Workspace


def get_current_workspace(request):
    # Runs the query once; subsequent calls in the same request return the cached instance:
    return cache_on_request(
        request,
        "current_workspace",
        lambda: Workspace.objects.filter(members=request.user).first(),
    )


def build_shell_swaps(request):
    workspace = get_current_workspace(request)
    return [
        Swap("nav/_sidebar.html", {"workspace": workspace}, target_id="sidebar"),
        Swap("nav/_breadcrumbs.html", target_id="breadcrumbs"),
    ]


render_shell = make_shell_renderer(build_shell_swaps)
```

Because `cache_on_request` attaches directly to the ephemeral `request` instance, the cache is automatically discarded when the HTTP response completes, eliminating any risk of cross-request cache leaks.

## Class-Based View Integration (`make_shell_view_mixin`)

If your project utilizes Django's generic class-based views (`ListView`, `DetailView`, `CreateView`, etc.), use `make_shell_view_mixin` to generate a compatible mixin:

```python
# app/views.py
from django.views.generic import DetailView
from htmx_nav import Swap, make_shell_view_mixin
from .models import Project
from .renderers import render_shell

# Generate a mixin bound to your shell renderer:
ProjectShellMixin = make_shell_view_mixin(render_shell)


class ProjectDetailView(ProjectShellMixin, DetailView):
    model = Project
    template_name = "projects/detail.html"

    # Optional: override to attach dynamic, object-level swaps:
    def get_extra_swaps(self):
        return [
            Swap("projects/_tabs.html", {"project": self.object}, target_id="tabs"),
        ]

    # Optional: set a dynamic page title:
    def get_title(self):
        return self.object.name
```

### Mixin Customization Hooks

| Method | Default | Purpose |
| :--- | :--- | :--- |
| `get_extra_swaps()` | `None` | Swaps specific to this view. `self.object` and `self.request` are available. May return one `Swap` or a list. |
| `get_title()` | `self.title` | Page and browser-tab title. Set the `title` attribute for a static one. |
| `get_partial()` | The mixin's `default_partial`, else the renderer's default | Any `PartialSpec`, including a routing mapping. |
| `get_template_names()` | Django's own | Only the **first** entry is rendered, because partial resolution needs one concrete template name. |

`make_shell_view_mixin(render, default_swaps=..., default_partial=...)` also
accepts `default_swaps` (applied to every view using the mixin) and
`default_partial`. Place the mixin **before** the Django view class so its
`render_to_response` takes precedence.
