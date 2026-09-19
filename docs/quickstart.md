# Getting Started

Get up and running with `django-htmx-nav` in under 3 minutes.

This guide walks through setting up your first partial view with `render_nav` and synchronizing your first peripheral navigation region with `Swap`.

## 1. Installation

Install `django-htmx-nav` from PyPI:

```bash
pip install django-htmx-nav
```

*(Optional)* If you want to use the visual swap debugging tools during development, add `"htmx_nav"` to `INSTALLED_APPS` in your `settings.py`:

```python
INSTALLED_APPS = [
    ...,
    "htmx_nav",
]
```

## 2. Your First Partial View (`render_nav`)

Use `render_nav` as a drop-in replacement for Django's standard `render()` shortcut:

```python
# views.py
from django.shortcuts import get_object_or_404
from htmx_nav import render_nav
from .models import Project


def project_list(request):
    projects = Project.objects.all()
    return render_nav(
        request,
        "pages/projects.html",
        {"projects": projects},
        title="Projects",
    )
```

In your template, define the main content block using native Django 6 inline partials (`{% partialdef %}`):

```html
<!-- templates/pages/projects.html -->
{% extends "base.html" %}

{% block content %}
{% partialdef content inline %}
  <div id="content" class="space-y-4">
    <h1 class="text-2xl font-bold">Projects</h1>
    <ul class="divide-y">
      {% for project in projects %}
        <li class="py-2">{{ project.name }}</li>
      {% endfor %}
    </ul>
  </div>
{% endpartialdef %}
{% endblock %}
```

Trigger the navigation from your HTMX links targeting `#content`:

```html
<a href="/projects/"
   hx-get="/projects/"
   hx-target="#content"
   hx-push-url="true">
  Projects
</a>
```

### How It Works

- **Direct Browser Visits (GET):** Renders the full template, including `base.html` and surrounding navigation layout.
- **HTMX Navigation (`HX-Request: true`):** Extracts and renders **only** the `content` partial block. `render_nav` automatically sets the `Vary: HX-Request` header so browser caches never mix full pages with partial fragments.
- **Page Title:** The `title="Projects"` argument populates `<title>` for full loads and injects a dynamic `<title>` tag for HTMX to update the browser tab.

## 3. Synchronizing Peripheral Regions (`Swap`)

When HTMX swaps `#content`, the main area updates, but peripheral layout elements (such as active sidebar indicators or breadcrumbs) remain stuck on the previous route.

Use `Swap` to append synchronized out-of-band updates in the same response:

```python
# views.py
from django.shortcuts import get_object_or_404
from htmx_nav import Swap, render_nav
from .models import Project


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)

    return render_nav(
        request,
        "pages/project_detail.html",
        {"project": project},
        # Peripheral regions synced out-of-band:
        swaps=[
            # Auto-wraps nav/_sidebar.html in <div id="sidebar" hx-swap-oob="innerHTML">
            Swap("nav/_sidebar.html", {"active_pk": project.pk}, target_id="sidebar"),
            # Synchronizes the breadcrumb trail:
            Swap("nav/_breadcrumbs.html", {"project": project}, target_id="breadcrumbs"),
        ],
        title=project.name,
    )
```

With this single addition, HTMX updates `#content` with the primary response and simultaneously swaps `#sidebar` and `#breadcrumbs` out-of-band. The URL remains the single source of truth without state drift.

## What's Next?

Now that your first view and swap are wired up, explore the topic guides to build production-grade architectures:

- **[Dynamic Targeting & Nested Navigation](guides/targeting.md):** Coordinate nested tabs, subtabs, and conditional swaps using the unified `Target` condition vocabulary.
- **[Application Shells & Class-Based Views](guides/shells.md):** Eliminate repetitive boilerplate across 20+ views with `make_shell_renderer` and `make_shell_view_mixin`.
- **[Visual Swap Debugging](debugging.md):** Highlight DOM elements with visual animations as they swap during development.
- **[API Reference](api/core.md):** Precise function signatures, parameters, and return types.
