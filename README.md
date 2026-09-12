# Stale Navigation in HTMX & `django-htmx-nav`

A reference repository and lightweight helper library exploring solutions for **stale navigation regions** in HTMX-driven Django applications.

## The Problem

When an HTMX request updates a single target container (like `#main-content`), regions *outside* that container, such as active sidebar items, breadcrumb trails, tab indicators, or multi-step progress bars, do not update automatically.

This creates UI state drift: the main content updates, but surrounding navigation elements still reflect the previous route. HTMX targets and swaps single elements by default, leaving multi-region layout updates to the developer.

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

## Solutions & Benchmark Comparison

There is no single "correct" way to handle multi-region updates. The right approach depends on application complexity, payload constraints, and developer ergonomics.

The accompanying [example project](https://lucas-rollin.github.io/django-htmx-nav/example_project.html) and [benchmark suite](https://lucas-rollin.github.io/django-htmx-nav/benchmarks.html) evaluate **8 distinct strategies** across the same demo application:

| Category | Method / Strategy | Live Demo Route | Description |
| --- | --- | --- | --- |
| **Baseline** | Plain MPA | `/mpa/` | Standard multi-page app with full reloads. |
| **Vanilla HTMX** | `hx-boost` Only | `/htmx/` | Full HTML shells returned on every boosted request. |
| **Vanilla HTMX** | Hand-Written OOB (Partial) | `/vanilla-htmx/composite/` | Views manually build `hx-swap-oob` fragments for core regions. |
| **Vanilla HTMX** | Hand-Written OOB (Full) | `/vanilla-htmx/atomic/` | Explicit OOB updates for all regions with template branching. |
| **Package** | Baseline Shell | `/htmx-nav/baseline/` | Static shell rendering using `make_shell_renderer`. |
| **Package** | Per-View Swaps | `/htmx-nav/composite/` | Dynamic `Swap` lists attached per view. |
| **Package** | Explicit Atomic | `/htmx-nav/atomic/` | Granular per-region swaps attached in views. |
| **Package** | Declarative Registry | `/htmx-nav/declarative/` | Route-aware central registry resolving swaps automatically. |

> **Client-Side Variants:** Many HTMX strategy in the demo can also be toggled to evaluate **`hx-select`** (extracting regions client-side) and **Idiomorph** (DOM morphing instead of inner/outer HTML swapping).

## Benchmark Highlights

Key observations from reference benchmark runs:

- **Payload Savings:** Partial updates reduce on-wire transfer size by **~32%** compared to full-page reloads, whether implemented via vanilla OOB fragments or `django-htmx-nav`.
- **Server Overhead:** Building multi-region OOB updates via `django-htmx-nav` adds **<0.5 ms** of server-side rendering time over base views.
- **Database Performance:** Request-scoped caching (`cache_on_request`) keeps database query counts flat (**~4.5 avg**) regardless of how many OOB fragments are generated per request.

## What is `django-htmx-nav`?

`django-htmx-nav` is an optional, lightweight Python helper designed to streamline out-of-band (OOB) swap construction and partial resolution in Django views without forcing a rigid architecture.

```bash
pip install django-htmx-nav
```

### 1. Basic Partial Rendering (`render_nav`)

Native Django partials allow a single template to serve both full-page requests and partial HTMX swaps:

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

`render_nav` inspects incoming headers to render either the full shell (on direct loads) or the isolated `content` partial (on HTMX requests), while setting appropriate `Vary: HX-Request` headers:

```python
from htmx_nav import render_nav

def project_list(request):
    return render_nav(
        request, 
        "app/project_list.html", 
        {"projects": Project.objects.all()}
    )
```

### 2. Manual OOB Swaps (`Swap`)

When a sub-region (such as `#content`) changes, you can append specific OOB swaps for surrounding navigation elements:

```python
from htmx_nav import Swap, render_nav

def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_nav(
        request,
        "app/project_detail.html",
        {"project": project},
        swaps=[
            Swap("app/_sidebar.html", {"active_pk": project.pk}, target_id="sidebar"),
            Swap("app/_breadcrumbs.html", {"project": project}, target_id="breadcrumbs"),
        ],
    )
```

### 3. Reusable Shell Rendering (`make_shell_renderer`)

To avoid repeating OOB swap lists across every view, `make_shell_renderer` abstracts common shell and navigation context into a reusable render function:

```python
from htmx_nav import make_shell_renderer

render_shell = make_shell_renderer(
    shell_template="app/_shell.html",
    context_builder=lambda request: {"nav": build_nav_context(request)},
)

def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    # Automatically attaches shell-level OOB swaps derived from build_nav_context
    return render_shell(request, "app/project_detail.html", {"project": project})
```

---

### 4. Target-Aware Resolution (`targeting`)

Views can dynamically adjust rendered partials based on the incoming `HX-Target` header:

```python
from htmx_nav import Swap, make_shell_renderer, targeting

render_project = make_shell_renderer(
    "app/_shell.html",
    context_builder=lambda request: {"nav": build_nav_context(request)},
)

def project_tab(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_project(
        request,
        "app/project_detail.html",
        {"project": project},
        partial={
            "#tab_content": targeting("tab-content"),
            "#main_content": targeting("main-content"),
            "#content": True,
        },
        extra_swaps=[
            Swap("app/_tabs.html", {"active": "overview"}, target_id="tabs")
        ],
    )
```
