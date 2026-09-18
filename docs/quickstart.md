# Quickstart Guide

This guide walks you through installing `django-htmx-nav` and implementing partial rendering, out-of-band updates, reusable shell renderers, and visual debugging in Django.

## 1. Installation

Install `django-htmx-nav` from PyPI:

```bash
pip install django-htmx-nav
```

Optionally, if you want [visual debugging](debugging.md), register the app and activate the setting.

```python
# settings.py
INSTALLED_APPS = [
    ...,
    "htmx_nav",
    ...,
]

# Activate it in development
HTMX_NAV_DEBUG_SWAPS = True
```

## 2. Basic Partial Rendering (`render_nav`)

Use `render_nav` in your view functions as a drop-in replacement for Django's standard `render()`:

```python
# views.py
from django.shortcuts import get_object_or_404
from htmx_nav import render_nav
from .models import Project


def project_list(request):
    projects = Project.objects.all()
    return render_nav(request, "app/project_list.html", {"projects": projects})
```

In your HTML template, define the partial block using native Django 6 inline partials (`{% partialdef %}`):

```html
<!-- app/templates/app/project_list.html -->
{% extends 'base.html' %}

{% block content %}
{% partialdef content inline %}
  <div id="project-list" class="space-y-4">
    {% for project in projects %}
      <div class="card p-4 border rounded">{{ project.name }}</div>
    {% endfor %}
  </div>
{% endpartialdef %}
{% endblock %}
```

```{tip}
`partial` defaults to `"#content"`, so on HTMX requests `"app/project_list.html"` becomes `"app/project_list.html#content"`, matched by Django's `{% partialdef content %}` block. Name your block `content` to match, or override via `partial="#your_block"` / `partial="path/to/template.html"`.
```

### Behavior Under the Hood

- **Direct Browser Navigation (GET):** Renders the entire document including `base.html`.
- **HTMX Partial Request (`HX-Request: true`):** Extracts and renders only the targeted partial block, setting `Vary: HX-Request` for correct HTTP caching.

## 3. Out-of-Band Swaps (`Swap`)

When navigating within an application shell, updating only the center container causes surrounding controls (sidebars, breadcrumbs, counter badges) to go stale.

Use `Swap` to append synchronized out-of-band updates alongside your response:

```python
from django.shortcuts import get_object_or_404
from htmx_nav import Swap, render_nav, has_messages
from .models import Project


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_nav(
        request,
        "app/project_detail.html",
        {"project": project},
        swaps=[
            # Auto-wrapped template swap:
            Swap("app/_sidebar.html", {"active_pk": project.pk}, target_id="sidebar"),
            Swap("app/_breadcrumbs.html", {"project": project}, target_id="breadcrumbs"),

            # High-performance raw string update (skips template engine):
            Swap.text("unread-badge", "3"),

            # Delete directive (removes element from DOM):
            Swap.delete("flash-notification"),

            # Django messages integration (only sent if messages are pending):
            Swap("app/_messages.html", target_id="messages", include_if=has_messages),
        ],
    )
```

## 4. Reusable Shell Rendering (`make_shell_renderer`)

To avoid declaring the same sidebar and breadcrumb `Swap`s repeatedly across dozens of views, encapsulate them into a reusable `render_shell` helper:

```python
# renderers.py
from htmx_nav import Swap, make_shell_renderer


def build_shell_swaps(request):
    return [
        Swap("app/_sidebar.html", {"user": request.user}, target_id="sidebar"),
        Swap("app/_breadcrumbs.html", target_id="breadcrumbs"),
    ]


render_shell = make_shell_renderer(build_shell_swaps)
```

Now any view in your application calls `render_shell` directly:

```python
# views.py
from django.shortcuts import get_object_or_404
from htmx_nav import Swap
from .models import Project
from .renderers import render_shell


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_shell(
        request,
        "app/project_detail.html",
        {"project": project},
        # Per-view extra swaps attach automatically alongside shell swaps:
        extra_swaps=[
            Swap("app/_tabs.html", {"active": "overview"}, target_id="project-tabs"),
        ],
    )
```

```{note}
**Request-Scoped Memoization:** If your shell builder queries the database (e.g. fetching an organization, project, or user permissions), use `cache_on_request(request, "key", fetch_func)` from `htmx_nav.helpers` to prevent duplicate database hits on the same request.
```

## 5. Class-Based View Integration (`make_shell_view_mixin`)

For projects utilizing Django generic Class-Based Views (`DetailView`, `ListView`, `CreateView`), generate a mixin with `make_shell_view_mixin`:

```python
# views.py
from django.views.generic import DetailView
from htmx_nav import Swap, make_shell_view_mixin
from .models import Project
from .renderers import render_shell 
 
ProjectShellMixin = make_shell_view_mixin(render_shell)


class ProjectDetailView(ProjectShellMixin, DetailView):
    model = Project
    template_name = "app/project_detail.html"

    def get_extra_swaps(self):
        # Access self.object and self.request dynamically
        return [
            Swap("app/_tabs.html", {"active": "overview"}, target_id="project-tabs"),
        ]
```

## Next Steps

- Explore the deployed {demo}`Live Demo Testbed <htmx-nav/declarative/>` and compare multiple implementations.
- Check out the <a href="../benchmarks/">Interactive Benchmark Suite</a> for empirical payload and latency metrics.
- Read the <a href="../guide/">Architectural Guide</a> for an in-depth exploration of state drift solutions.
- Learn about automated parity verification in the [Testing Guide](testing.md).
- Reference full signatures in the [API Reference](api/core.md).
