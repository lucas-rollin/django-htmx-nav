# django-htmx-nav Documentation

**Server-driven hypermedia navigation for Django and HTMX, with the URL as the single source of truth.**

`django-htmx-nav` is a lightweight Python library designed to eliminate **state drift** in HTMX applications. It provides declarative out-of-band (OOB) swaps, zero-boilerplate component auto-wrapping, reusable shell renderers, and robust test helpers—keeping sidebars, breadcrumbs, tabs, badges, and page titles strictly synchronized with the current route.

## The Problem: Stale Navigation Regions (State Drift)

When an HTMX request updates a single target container (such as `#main-content`), regions *outside* that container, such as active sidebar items, breadcrumb trails, tab indicators, or step progress bars, do not update automatically.

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

This creates UI state drift: the main content updates, but the surrounding application chrome still reflects the previous route.

This repository serves as both library documentation and an empirical study. It analyzes and benchmarks solutions across **8 distinct architectural strategies**, ranging from unassisted Vanilla HTMX and hand-written template OOB swaps to declarative registries and baseline MPAs:

- **{demo}`Live Example Project Showcase <htmx-nav/baseline/>`:** Compare implementations, template structures, and UI behaviors side-by-side in a deployed helpdesk app.
- **{live}`Interactive Benchmark Dashboard <benchmarks/>`:** Explore empirical metrics comparing payload size (~70–80% savings over MPAs), server render overhead (<0.5 ms), and request-scoped database efficiency (~4.5 avg queries).
- **{live}`Architectural Guide <guide/>`:** An in-depth guide on hypermedia navigation patterns across Turbo, LiveView, Unpoly, and Django with HTMX.

## Core Capabilities

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

### 1. Centralized on the `Swap` Primitive

At the core of the library is `Swap`, a frozen Python dataclass describing what to render, where to deliver it, and under what conditions.

- **Zero-Boilerplate Auto-Wrapping:** Point `Swap` directly at clean component templates (like `_sidebar.html`). `Swap` automatically wraps them in `<div id="sidebar" hx-swap-oob="innerHTML">...</div>` or `<hx-partial>` at render time. The exact same template can be rendered inside full-page templates without template tag hacks.
- **Pythonic Conditionals (`include_if`):** Replace fragile template checks (`{% if request.htmx ... %}`) with Python predicates: `targeting("content")`, `not_targeting("sidebar")`, `has_messages`, or custom lambdas.
- **Specialized Fast Constructors:**
  - `Swap.delete(target_id)`: Emits `hx-swap-oob="delete"` instantly without touching Django's template engine.
  - `Swap.text(target_id, content)`: Sends raw text or numeric counters directly, skipping template rendering entirely.
  - `has_messages`: Automatically suppresses flash message swaps when no Django messages are pending.

### 2. Universal Python Versatility

- **Function-Based Views (`render_nav`)**: A drop-in replacement for Django's `render()`. Serves partial blocks (`{% partialdef %}`) on HTMX requests and full layouts on direct browser requests, setting appropriate `Vary: HX-Request` headers.
- **Reusable Shell Renderers (`make_shell_renderer`)**: Encapsulates recurring layout dependencies (sidebars, breadcrumbs, user badges) once into a shared renderer. Views call `render_shell(...)` and can append per-view `extra_swaps`.
- **Class-Based Views (`make_shell_view_mixin`)**: Deeply integrates into Django generic views (`ListView`, `DetailView`, `UpdateView`). Override `get_extra_swaps()` with access to `self.request` and `self.object`.

### 3. Built-in Visual Debugging

Enable `HTMX_NAV_DEBUG_SWAPS = True` in development settings to have every out-of-band swap automatically flash with a visual CSS highlight (`.hn-swap`) in the browser. See exactly which layout regions updated on every click.

### 4. Automated Parity Testing

Test helpers (`assert_shell_parity` and `assert_shell_composition`) ensure that navigating via HTMX produces the exact same navigation context and active DOM state as a direct full-page browser reload.

## Quick Example

```python
from django.shortcuts import get_object_or_404
from htmx_nav import Swap, make_shell_renderer
from .models import Project

# 1. Define reusable shell navigation once (fixed list or request callable):
render_shell = make_shell_renderer(lambda request: [
    Swap("app/_sidebar.html", {"user": request.user}, target_id="sidebar"),
    Swap("app/_breadcrumbs.html", target_id="breadcrumbs"),
])

# 2. Views call render_shell exactly like Django's render():
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_shell(
        request,
        "app/project_detail.html",
        {"project": project},
        # Optional per-view extra swaps:
        extra_swaps=[
            Swap("app/_tabs.html", {"active": "overview"}, target_id="project-tabs"),
        ],
    )
```

In your template, define the main content partial with Django inline partials:

```html
<!-- templates/app/project_detail.html -->
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

- **Direct browser load (`GET /projects/42/`)**: Renders full `base.html` shell with all navigation components intact.
- **Boosted HTMX request (`HX-Request: true`)**: Renders only the `#content` partial, automatically appending out-of-band swaps for `#sidebar`, `#breadcrumbs`, and `#project-tabs`.

---

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
