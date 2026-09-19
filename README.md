# django-htmx-nav

[![PyPI Version](https://img.shields.io/pypi/v/django-htmx-nav.svg?style=flat-square&color=blue)](https://pypi.org/project/django-htmx-nav/)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-6.0%2B-darkgreen?style=flat-square&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![htmx Version](https://img.shields.io/badge/htmx-2.0%2B-purple?style=flat-square&logo=htmx&logoColor=white)](https://htmx.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

A lightweight helper library for Django + HTMX that keeps navigation chrome synchronized with the URL, preventing stale sidebars, breadcrumbs, titles, and other surrounding UI.

**[Homepage](https://lucas-rollin.github.io/django-htmx-nav/) · [Documentation](https://lucas-rollin.github.io/django-htmx-nav/docs/) · [Live Demo](https://django-htmx-nav.onrender.com/htmx-nav/baseline/)**

## The Problem

When an HTMX request updates a single container (like `#content`), regions *outside* that container, such as active sidebar items, breadcrumb trails, and badge counts, do not update automatically. The main content updates, but surrounding navigation chrome still reflects the previous route.

```text
┌─────────────────────────────────────────────────────────────┐
│ Header / Breadcrumbs (Stale: Page 1)                        │
├──────────────┬──────────────────────────────────────────────┤
│ Sidebar      │  Main Content (Updated: Page 2)              │
│ (Stale)      │  Targeted element swapped; surrounding       │
│              │  navigation controls did not.                │
└──────────────┴──────────────────────────────────────────────┘
```

## Installation

```bash
pip install django-htmx-nav
```

*Zero configuration required. Uses Django 6+ native template partials.*

## How It Works

### 1. Automatic Partial Selection (`render_nav`)

Use `render_nav` as a drop-in replacement for Django's `render()`. It serves the full template (with `base.html`) on direct visits or full-page reloads, and returns the matching Django partial on HTMX requests:

```python
# views.py
from htmx_nav import render_nav

def project_list(request):
    projects = Project.objects.all()
    # Direct GET: renders base.html layout
    # HTMX request: returns only the #content block
    return render_nav(request, "projects/list.html", {"projects": projects})
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

### 2. Synchronizing Navigation Chrome (`Swap`)

Attach out-of-band swaps to update surrounding navigation elements (sidebars, breadcrumbs, titles) alongside the main response:

```python
# views.py
from django.shortcuts import get_object_or_404
from htmx_nav import render_nav, Swap
from .models import Project

def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_nav(
        request,
        "projects/detail.html",
        {"project": project},
        swaps=[
            # Update persistent navigation regions alongside the main content:
            Swap("components/_sidebar.html", {"active": project.id}, target_id="sidebar"),
            Swap("components/_breadcrumbs.html", target_id="breadcrumbs"),
        ],
        title=project.name,  # Injects <title> tag on HTMX; sets context["title"] on F5
    )
```

### 3. Reusable Navigation Shells (`make_shell_renderer`)

Avoid repeating recurring swaps across views by bundling your navigation shell into a reusable renderer:

```python
# shells.py
from htmx_nav import make_shell_renderer, Swap

# Define recurring navigation updates once and reuse them across views.
render_shell = make_shell_renderer(
    lambda request: [
        Swap("components/_sidebar.html", target_id="sidebar"),
        Swap("components/_breadcrumbs.html", target_id="breadcrumbs"),
    ]
)

# views.py
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    # Shell swaps are included automatically:
    return render_shell(request, "tickets/detail.html", {"ticket": ticket})
```

## Learn More

- **[Quickstart Guide](https://lucas-rollin.github.io/django-htmx-nav/docs/quickstart.html)** — Install the library and build your first URL-driven HTMX navigation flow.
- **[Architectural Guide](https://lucas-rollin.github.io/django-htmx-nav/guide/)** — Compare approaches to stale navigation and use the decision tree to choose an architecture.
- **[Benchmark Experiments](https://github.com/lucas-rollin/django-htmx-nav/tree/main/example/benchmarks)** — Reproduce the benchmark comparing 8 implementation strategies, including MPA, vanilla HTMX, and `django-htmx-nav`.

## License

Released under the [MIT License](LICENSE).
