# django-htmx-nav Documentation

**Server-driven hypermedia navigation for Django and HTMX, with the URL as the single source of truth.**

`django-htmx-nav` provides declarative out-of-band (OOB) swaps, zero-boilerplate component auto-wrapping, reusable shell renderers, and automated parity testing for Django applications using HTMX. It ensures that secondary navigation regions, such as sidebars, breadcrumbs, tab bars, notifications, and badges, remain strictly synchronized with the current route during partial page swaps without UI state drift.

```{tip}
**Looking for project overviews or live benchmarks?**
* <a href="../">Showcase Overview</a>: High-level overview, feature summary, and quick links.
* <a href="../guide/">Architectural Guide</a>: Deep dive into solutions to hypermedia state synchronization.
* <a href="../benchmarks/">Benchmark Dashboard</a>: Empirical measurements of payload compression, server overhead, and flat DB query counts across 23 variant implementations.
* {demo}`Live Helpdesk Sandbox <htmx-nav/declarative/>`: Interactive demo application.
```

## Installation

Install `django-htmx-nav` from PyPI:

```bash
pip install django-htmx-nav
```

### Requirements

- **Python:** 3.10, 3.11, 3.12, 3.13, 3.14
- **Django:** 4.2, 5.0, 5.1, 6.0+
- **django-template-partials** *(optional, unnecessary with django 6.0+)*.
- **django-htmx** *(optional)*.

## Core Concepts & Mental Model

```text
+-----------------------------------------------------------------------+
|                         django-htmx-nav                               |
+-----------------------------------+-----------------------------------+
| View Helpers & Partial Resolution | Out-of-Band & Shell Orchestration |
|  - render_nav (FBVs)              |  - Swap / Swap.delete / Swap.text |
|  - render_with_swaps              |  - make_shell_renderer (reusable) |
|  - targeting / not_targeting      |  - make_shell_view_mixin (CBVs)   |
+-----------------------------------+-----------------------------------+
| Quality Assurance & Verification  | Developer Experience & Patterns   |
|  - assert_shell_parity            |  - HTMX_NAV_DEBUG_SWAPS (visual)  |
|  - assert_shell_composition       |  - cache_on_request memoization   |
+-----------------------------------+-----------------------------------+
```

1. **`Swap` (The Atomic Unit):** A frozen dataclass specifying a component template, context, and target DOM element. Auto-wraps fragments with `<div id="..." hx-swap-oob="innerHTML">` on delivery without template tags or manual wrapper boilerplate.
2. **`render_nav`:** A drop-in replacement for Django's `render()`. Renders only requested partial blocks during HTMX requests, and full layouts on initial browser loads, setting `Vary: HX-Request` automatically.
3. **`make_shell_renderer` & `make_shell_view_mixin`:** Encapsulates recurring application shell navigation (sidebars, breadcrumbs, user badges) into a single reusable factory for function-based or class-based views.
4. **`assert_shell_parity`:** Test assertions ensuring that partial HTMX navigation and direct full-page browser loads produce 100% identical navigation context and active element state.

## Quickstart at a Glance

Define reusable shell navigation once using `make_shell_renderer`:

```python
from django.shortcuts import get_object_or_404
from htmx_nav import Swap, make_shell_renderer
from .models import Project

# Define shell navigation dependencies:
render_shell = make_shell_renderer(lambda request: [
    Swap("app/_sidebar.html", {"user": request.user}, target_id="sidebar"),
    Swap("app/_breadcrumbs.html", target_id="breadcrumbs"),
])

def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_shell(
        request,
        "app/project_detail.html",
        {"project": project},
        # Per-view extra swaps:
        extra_swaps=[
            Swap("app/_tabs.html", {"active": "overview"}, target_id="project-tabs"),
        ],
    )
```

In your template (`templates/app/project_detail.html`), use standard blocks or `{% partialdef %}`:

```html
{% extends 'base.html' %}

{% block content %}
{% partialdef content inline %}
  <div id="project-detail">
    <h1>{{ project.name }}</h1>
    <p>{{ project.description }}</p>
  </div>
{% endpartialdef %}
{% endblock %}
```

- **Full Page Request (`GET /projects/42/`):** Renders the full `base.html` document with `#sidebar`, `#breadcrumbs`, and `#content`.
- **HTMX Boosted Request (`HX-Request: true`):** Returns only the `#content` partial, automatically bundling out-of-band swaps for `#sidebar`, `#breadcrumbs`, and `#project-tabs`.

For a step-by-step tutorial, see the [Quickstart Guide](quickstart.md).

## Documentation Index

```{toctree}
:maxdepth: 2
:caption: Getting Started & Guides

quickstart
example_project
nav_context_patterns
```

```{toctree}
:maxdepth: 2
:caption: Operations & Testing

testing
debugging
```

```{toctree}
:maxdepth: 2
:caption: Reference

api
glossary
```
