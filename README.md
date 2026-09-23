# django-htmx-nav

[![PyPI Version](https://img.shields.io/pypi/v/django-htmx-nav.svg?style=flat-square\&color=blue)](https://pypi.org/project/django-htmx-nav/)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square\&logo=python\&logoColor=white)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-6.0%2B-darkgreen?style=flat-square\&logo=django\&logoColor=white)](https://www.djangoproject.com/)
[![htmx Version](https://img.shields.io/badge/htmx-2.0%2B-purple?style=flat-square\&logo=htmx\&logoColor=white)](https://htmx.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

A lightweight helper library for Django + HTMX that keeps navigation UI synchronized with the URL, preventing stale sidebars, breadcrumbs, titles, and other surrounding elements.

**[Homepage](https://lucas-rollin.github.io/django-htmx-nav/) · [Documentation](https://lucas-rollin.github.io/django-htmx-nav/docs/) · [Interactive Demo](https://django-htmx-nav.onrender.com/htmx-nav/baseline/)**

## The Problem

When an HTMX request updates a single container (like `#content`), regions *outside* that container, such as active sidebar items, breadcrumb trails, and badge counts, do not update automatically. The main content updates, but the surrounding navigation UI still reflects the previous route:

```text
┌─────────────────────────────────────────────────────────────┐
│ Header / Breadcrumbs (Stale: Page 1)                        │
├──────────────┬──────────────────────────────────────────────┤
│ Sidebar      │  Main Content (Updated: Page 2)              │
│ (Stale)      │  Targeted element swapped; surrounding       │
│              │  navigation controls did not.                │
└──────────────┴──────────────────────────────────────────────┘
```

`django-htmx-nav` keeps these regions synchronized by making the URL the source of truth for navigation state regardless of whether it is an HTMX request or a full-page load.

## Installation

```bash
pip install django-htmx-nav
```

## How It Works

### 1. Automatic Partial Selection (`render_nav`)

Use `render_nav` as a drop-in replacement for Django's `render()`. Direct visits and full-page reloads render the complete template, while HTMX requests return the matching Django partial:

```python
# views.py
from htmx_nav import render_nav

def project_list(request):
    projects = Project.objects.all()

    return render_nav(
        request,
        "projects/list.html",
        {"projects": projects},
    )
```

```html
<!-- templates/projects/list.html -->
{% extends "base.html" %}

{% block content %}
{% partialdef content inline %}
  <div id="content">
    {% for project in projects %}
      <div>{{ project.name }}</div>
    {% endfor %}
  </div>
{% endpartialdef %}
{% endblock %}
```

### 2. Synchronizing Navigation UI (`Swap`)

Attach out-of-band swaps to update persistent navigation regions alongside the main response:

```python
# views.py
from django.shortcuts import get_object_or_404
from htmx_nav import Swap, render_nav
from .models import Project

def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)

    return render_nav(
        request,
        "projects/detail.html",
        {"project": project},
        swaps=[
            Swap(
                "components/_sidebar.html",
                {"active": project.id},
                target_id="sidebar",
            ),
            Swap(
                "components/_breadcrumbs.html",
                target_id="breadcrumbs",
            ),
        ],
        title=project.name,
    )
```

The `title` argument updates the document title during an HTMX navigation while also providing `context["title"]` during a full-page render.

### 3. Reusable Navigation Shells (`make_shell_renderer`)

Define recurring navigation updates once and reuse them across views:

```python
# shells.py
from htmx_nav import Swap, make_shell_renderer

render_shell = make_shell_renderer(
    lambda request: [
        Swap("components/_sidebar.html", target_id="sidebar"),
        Swap("components/_breadcrumbs.html", target_id="breadcrumbs"),
    ]
)

# views.py
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    return render_shell(
        request,
        "tickets/detail.html",
        {"ticket": ticket},
        extra_swaps=Swap(
            "components/_status_badge.html",
            target_id="ticket-status",
        ),
    )
```

The shell renderer automatically includes the configured swaps whenever the view is rendered through it. `extra_swaps` lets individual views add their own out-of-band updates.

### 4. Class-Based Views

The same navigation shell can be reused with Django's generic class-based views through `make_shell_view_mixin`:

```python
from django.views.generic import DetailView
from htmx_nav import Swap, make_shell_view_mixin

# Reuse the shell renderer defined above.
ShellViewMixin = make_shell_view_mixin(render_shell)


class ProjectBoardView(ShellViewMixin, DetailView):
    model = Project
    template_name = "pages/board.html"
    context_object_name = "project"

    def get_extra_swaps(self):
        return Swap(
            "components/_status_badge.html",
            target_id="project-status",
        )
```

## Learn More

- **[Quickstart Guide](https://lucas-rollin.github.io/django-htmx-nav/docs/quickstart.html)** — Install the library and build your first URL-driven HTMX navigation flow.
- **[Architectural Guide](https://lucas-rollin.github.io/django-htmx-nav/guide/)** — Compare approaches to stale navigation and explore the decision tree for choosing an architecture.
- **[Benchmark Experiments](https://github.com/lucas-rollin/django-htmx-nav/tree/main/example/benchmarks)** — Reproduce the benchmark comparing 8 implementation strategies, including MPA, vanilla HTMX, and `django-htmx-nav`, or explore the [Dashboard](https://lucas-rollin.github.io/django-htmx-nav/benchmarks/) for live reference results.

## License

Released under the [MIT License](LICENSE).
