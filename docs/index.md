# django-htmx-nav Documentation

**Server-driven, SPA-like user experiences with MPA simplicity in Django.**

`django-htmx-nav` is a lightweight Python helper library designed to streamline partial rendering, out-of-band (OOB) swap construction, reusable shell layout rendering, and HTMX-safe redirects in Django projects.

```html
<!-- templates/app/project_list.html -->
{% extends 'base.html' %}

{% block content %}
{% partialdef content inline %}
  {% for project in projects %}
    <div>{{ project.name }}</div>
  {% endfor %}
{% endpartialdef %}
{% endblock %}

```

## The Problem: Stale Navigation Regions

When an HTMX request updates a single target container (like `#main-content`), regions *outside* that container, such as active sidebar items, breadcrumb trails, tab indicators, or progress bars, do not update automatically.

```plaintext
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

This repository is both package documentation and an empirical study. It explores solutions to stale navigation regions across **8 distinct architectural strategies**, ranging from unassisted Vanilla HTMX and hand-written OOB swaps to declarative registries and baseline MPAs.

- **Live Example Project Showcase:** Compare implementations, template structures, and UI behaviors side-by-side.
- **Benchmark Analysis:** Review exact metrics regarding payload compression (~32% savings), rendering overhead (<0.5 ms), and request-scoped database performance (~4.5 avg queries).

## Core Capabilities

```plaintext
+-----------------------------------------------------------------------+
|                         django-htmx-nav                               |
+-----------------------------------+-----------------------------------+
| View Helpers & Partial Resolution | Out-of-Band & Shell Orchestration |
|  - render_nav                     |  - Swap / Swap.delete / Swap.text |
|  - render_with_swaps              |  - make_shell_renderer            |
|  - targeting                      |  - make_shell_view_mixin          |
+-----------------------------------+-----------------------------------+
| Quality Assurance & Verification  | Architecture & Patterns           |
|  - assert_shell_parity            |  - nav_context_patterns           |
|  - assert_shell_composition       |  - HTMX-safe redirects & caching  |
+-----------------------------------+-----------------------------------+
```

- **Selective Partial Rendering (`render_nav`)**: Integrates with Django 6 template partials (`{% partialdef %}`) to automatically serve isolated fragments on HTMX requests and full layouts on direct browser loads, setting proper `Vary: HX-Request` headers.
- **Explicit OOB Swapping (`Swap`)**: Append secondary DOM updates, raw HTML strings, or deletion directives (`hx-swap-oob="delete"`) alongside primary target responses.
- **Reusable Shell Renderers (`make_shell_renderer` & Mixins)**: Encapsulate shared layout dependencies (sidebars, breadcrumbs, header counters) into a single reusable rendering pipeline for Function-Based and Class-Based Views.
- **Target-Aware Branching (`targeting`)**: Dynamically select template partials based on incoming `HX-Target` headers.
- **Automated Parity Testing (`assert_shell_parity`)**: Test harness tools to enforce DOM consistency between full reloads and HTMX partial swaps in CI/CD pipelines.

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

## Quick Example

```python
from htmx_nav import Swap, make_shell_renderer

# 1. Define reusable shell context
render_shell = make_shell_renderer(
    shell_template="base.html",
    context_builder=lambda request: {"user_nav": get_user_nav(request)},
)

# 2. Render view with automatic OOB/hx_partial sync
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_shell(
        request,
        "app/project_detail.html",
        {"project": project},
        extra_swaps=[
            Swap("app/_breadcrumbs.html", {"project": project}, target_id="breadcrumbs")
        ],
    )
```
