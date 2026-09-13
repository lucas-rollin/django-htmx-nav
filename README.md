# Stale Navigation in HTMX & `django-htmx-nav`

[![PyPI Version](https://img.shields.io/pypi/v/django-htmx-nav.svg?style=flat-square&color=blue)](https://pypi.org/project/django-htmx-nav/)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-6.0%2B-darkgreen?style=flat-square&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![htmx Version](https://img.shields.io/badge/htmx-2.0%2B-purple?style=flat-square&logo=htmx&logoColor=white)](https://htmx.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

A reference repository and lightweight helper library exploring solutions for **stale navigation regions (state drift)** in HTMX-driven Django applications, with the URL as the single source of truth.

## Live Links & Showcase

- **[Live Helpdesk Testbed](https://django-htmx-nav.onrender.com/htmx-nav/baseline/):** Explore the live deployed demo app, switching between all 8 implementation families and modifier axes on the fly.
- **[Interactive Benchmarks](https://django-htmx-nav.onrender.com/benchmarks/):** Compare empirical payload distributions, server render times, and DOM churn.
- **[Architectural Guide](https://django-htmx-nav.onrender.com/guide/):** Read the in-depth architectural breakdown of hypermedia state synchronization across frameworks.
- **[Documentation](https://lucas-rollin.github.io/django-htmx-nav/):** Official Sphinx API reference and pattern guides.

## The Problem: Stale Navigation Regions (State Drift)

When an HTMX request updates a single target container (like `#main-content`), regions *outside* that container, such as active sidebar items, breadcrumb trails, tab indicators, or multi-step progress bars, do not update automatically.

This creates UI state drift: the main content updates, but surrounding navigation elements still reflect the previous route. HTMX targets and swaps single elements by default, leaving multi-region layout synchronization to the developer.

```text
┌─────────────────────────────────────────────────────────────┐
│ Header / Breadcrumbs (Stale: Page 1)                        │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│ Sidebar      │  Main Content (Updated: Page 2)              │
│ (Stale:      │                                              │
│  Item 1)     │  Targeted element swapped successfully.      │
│              │  Surrounding navigation controls did not.    │
│              │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

## Solutions & Benchmark Comparison

There is no single "correct" way to handle multi-region updates. The right approach depends on application complexity, payload constraints, and developer ergonomics.

The accompanying [example project](https://django-htmx-nav.onrender.com/htmx-nav/baseline/) and [benchmark suite](https://django-htmx-nav.onrender.com/benchmarks/) evaluate **8 distinct strategies** across the exact same Helpdesk application:

| Category | Method / Strategy | Live Demo Route | Description |
| :--- | :--- | :--- | :--- |
| **Baseline** | Plain MPA | [/mpa/](https://django-htmx-nav.onrender.com/mpa/) | Standard multi-page app with full reloads. |
| **Vanilla HTMX** | `hx-boost` Only | [/htmx/](https://django-htmx-nav.onrender.com/htmx/) | Full HTML shells returned on every boosted request. |
| **Vanilla HTMX** | Hand-Written OOB (Partial) | [/vanilla-htmx/composite/](https://django-htmx-nav.onrender.com/vanilla-htmx/composite/) | Views manually build `hx-swap-oob` fragments for core regions. |
| **Vanilla HTMX** | Hand-Written OOB (Full) | [/vanilla-htmx/atomic/](https://django-htmx-nav.onrender.com/vanilla-htmx/atomic/) | Explicit OOB updates for all regions with template branching. |
| **Package** | Baseline Shell | [/htmx-nav/baseline/](https://django-htmx-nav.onrender.com/htmx-nav/baseline/) | Clean shell rendering using `make_shell_renderer` with `Swap`. |
| **Package** | Per-View Swaps | [/htmx-nav/composite/](https://django-htmx-nav.onrender.com/htmx-nav/composite/) | Dynamic `Swap` lists attached per view. |
| **Package** | Explicit Atomic | [/htmx-nav/atomic/](https://django-htmx-nav.onrender.com/htmx-nav/atomic/) | Granular per-region swaps attached in views. |
| **Package** | Declarative Registry | [/htmx-nav/declarative/](https://django-htmx-nav.onrender.com/htmx-nav/declarative/) | Route-aware central registry resolving swaps automatically. |

> **Client-Side Variants:** Each HTMX strategy in the demo can also be toggled to evaluate **`hx-select`** (extracting regions client-side) and **`morph`** (DOM morphing via Idiomorph).

### Benchmark Highlights

Key observations from reference benchmark runs:

- **Payload Savings (70–80%):** Partial updates reduce on-wire transfer size from ~6.1 KB (MPA) down to **~1.2 KB** per request.
- **Negligible Server Overhead:** Building multi-region OOB updates via `django-htmx-nav` adds **<0.5 ms** of server-side rendering time over base views.
- **Flat Database Queries:** Request-scoped caching (`cache_on_request`) keeps database query counts flat (**~4.5 avg**) regardless of how many OOB fragments are generated per request.

## What is `django-htmx-nav`?

`django-htmx-nav` is a lightweight Python helper designed to streamline out-of-band (OOB) swap construction and partial resolution in Django views without forcing a rigid architecture or template tag DSLs.

```bash
pip install django-htmx-nav
```

### 1. Basic Partial Rendering (`render_nav`)

Native Django 6 inline partials (`{% partialdef %}`) allow a single template to serve both full-page requests and partial HTMX swaps:

```html
<!-- templates/app/project_list.html -->
{% extends 'base.html' %}

{% block content %}
{% partialdef content inline %}
  <div id="project-list">
    {% for project in projects %}
      <div>{{ project.name }}</div>
    {% endfor %}
  </div>
{% endpartialdef %}
{% endblock %}
```

`render_nav` inspects incoming headers to render either the full shell (on direct loads) or the isolated `content` partial (on HTMX requests), while setting appropriate `Vary: HX-Request` headers:

```python
from htmx_nav import render_nav
from .models import Project

def project_list(request):
    return render_nav(
        request, 
        "app/project_list.html", 
        {"projects": Project.objects.all()}
    )
```

### 2. Manual OOB Swaps (`Swap`)

When a sub-region (such as `#content`) changes, you can append specific OOB swaps for surrounding navigation elements without altering component templates:

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
            # Auto-wrapped: template remains clean HTML, Swap adds wire wrapper
            Swap("app/_sidebar.html", {"active_pk": project.pk}, target_id="sidebar"),
            Swap("app/_breadcrumbs.html", {"project": project}, target_id="breadcrumbs"),

            # High-performance raw string update (skips template engine):
            Swap.text("unread-badge", "3"),

            # Instant DOM deletion directive:
            Swap.delete("flash-notification"),

            # Django messages integration (only sent if messages exist):
            Swap("app/_messages.html", target_id="messages", include_if=has_messages),
        ],
    )
```

### 3. Reusable Shell Rendering (`make_shell_renderer`)

To avoid repeating OOB swap lists across every view, `make_shell_renderer` abstracts common shell navigation into a reusable render function:

```python
from htmx_nav import Swap, make_shell_renderer
from .models import Project

render_shell = make_shell_renderer(lambda request: [
    Swap("app/_sidebar.html", {"user": request.user}, target_id="sidebar"),
    Swap("app/_breadcrumbs.html", target_id="breadcrumbs"),
])

def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    # Automatically attaches shell-level OOB swaps; extra_swaps are appended per view:
    return render_shell(
        request, 
        "app/project_detail.html", 
        {"project": project},
        extra_swaps=[
            Swap("app/_tabs.html", {"active": "overview"}, target_id="project-tabs"),
        ],
    )
```

### 4. Class-Based View Integration (`make_shell_view_mixin`)

```python
from django.views.generic import DetailView
from htmx_nav import Swap, make_shell_view_mixin
from .models import Project

ProjectShellMixin = make_shell_view_mixin(render_shell)

class ProjectDetailView(ProjectShellMixin, DetailView):
    model = Project
    template_name = "app/project_detail.html"

    def get_extra_swaps(self):
        return [
            Swap("app/_tabs.html", {"active": "overview"}, target_id="project-tabs"),
        ]
```

### 5. Visual Swap Debugging

Enable visual feedback in development with a single setting:

```python
# settings.py
HTMX_NAV_DEBUG_SWAPS = True
```

Swapped target elements momentarily flash with a visual CSS pulse (`.hn-swap`) in your browser upon arrival, giving instant feedback without opening browser devtools.

## License

Released under the [MIT License](LICENSE).
