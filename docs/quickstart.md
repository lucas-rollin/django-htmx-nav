# Quickstart Guide

This guide walks you through installing `django-htmx-nav` and implementing partial rendering, out-of-band updates, reusable shell renderers in Django.

## 1. Installation

Install `django-htmx-nav` from PyPI:

```bash
pip install django-htmx-nav
```

## 2. Basic Partial Rendering (`render_nav`)

Use `render_nav` in your views as a drop-in replacement for Django's standard `render()` function:

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
The `partial` argument defaults to `"#content"`. During an HTMX request, `"app/project_list.html"` automatically resolves to `"app/project_list.html#content"`, matching your `{% partialdef content %}` block. You can change this block name to match your preference, or override it via `partial="#your_block"` or `partial="path/to/template.html"`.
```

### Behavior Under the Hood

- **Direct Browser Navigation (GET):** Renders the entire document, including `base.html`.
- **HTMX Partial Request (`HX-Request: true`):** Extracts and renders only the targeted partial block, automatically setting the `Vary: HX-Request` header for correct browser and proxy caching.

## 3. Out-of-Band Swaps (`Swap`)

When navigating within an application shell, updating only the main content area can leave surrounding controls (such as sidebars, breadcrumbs, and counter badges) out of sync.

Use `Swap` to append synchronized out-of-band updates to your response:

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
            Swap(
                "app/_breadcrumbs.html", {"project": project}, target_id="breadcrumbs"
            ),
            # High-performance raw string update (bypasses the template engine):
            Swap.text("unread-badge", "3"),
            # Delete directive (removes the element from the DOM):
            Swap.delete("flash-notification"),
            # Conditional Django messages integration (sent only if messages are pending):
            Swap("app/_messages.html", target_id="messages", include_if=has_messages),
        ],
    )

```

## 4. Reusable Shell Rendering (`make_shell_renderer`)

To avoid duplicating sidebar and breadcrumb `Swap` configurations across dozens of views, encapsulate them into a reusable `render_shell` helper:

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

Now, any view in your application can call `render_shell` directly:

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
**Request-Scoped Memoization:** If your shell builder performs database queries (such as fetching an organization, active project, or user permissions), use `cache_on_request(request, "key", fetch_func)` from `htmx_nav.helpers` to prevent redundant database hits during the same request lifecycle.
```

## 5. Class-Based View Integration (`make_shell_view_mixin`)

For projects utilizing Django's generic Class-Based Views (`DetailView`, `ListView`, `CreateView`), you can generate a corresponding mixin using `make_shell_view_mixin`:

```python
# views.py
from django.views.generic import DetailView
from htmx_nav import Swap, make_shell_view_mixin
from .models import Project
from .renderers import render_shell 

# Reuse render_shell, or instantiate the mixin without parameters if preset swaps aren't needed.
ProjectShellMixin = make_shell_view_mixin(render_shell)


class ProjectDetailView(ProjectShellMixin, DetailView):
    model = Project
    template_name = "app/project_detail.html"

    def get_extra_swaps(self):
        # Dynamically access self.object and self.request
        return [
            Swap("app/_tabs.html", {"active": "overview"}, target_id="project-tabs"),
        ]
```

## Next Steps

- Explore the deployed {demo}`Live Demo Testbed <htmx-nav/declarative/>` and compare multiple implementations.
- Review the <a href="../benchmarks/">Interactive Benchmark Suite</a> for empirical payload and latency metrics.
- Read the <a href="../guide/">Architectural Guide</a> for an in-depth exploration of state drift solutions.
- Learn how to get instant visual feedback with Swaps in [Debugging](debugging.md).
- Reference full function signatures in the [API Reference](https://www.google.com/search?q=api/core.md&utm_source=gemini).
