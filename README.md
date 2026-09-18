# Stale Navigation in HTMX & `django-htmx-nav`

[![PyPI Version](https://img.shields.io/pypi/v/django-htmx-nav.svg?style=flat-square&color=blue)](https://pypi.org/project/django-htmx-nav/)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-6.0%2B-darkgreen?style=flat-square&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![htmx Version](https://img.shields.io/badge/htmx-2.0%2B-purple?style=flat-square&logo=htmx&logoColor=white)](https://htmx.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

A lightweight helper library for Django + HTMX that eliminates **stale navigation regions (state drift)**, with the URL as the single source of truth.

**[Full Documentation](https://lucas-rollin.github.io/django-htmx-nav/) · [Live Demo](https://django-htmx-nav.onrender.com/htmx-nav/baseline/) · [Benchmarks](https://django-htmx-nav.onrender.com/benchmarks/)**

## The Problem

When an HTMX request updates a single target container (like `#main-content`), regions *outside* that container, active sidebar items, breadcrumb trails, tab indicators, don't update automatically. Main content updates; surrounding navigation chrome still reflects the previous route.

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

## Quick Example

```python
from django.shortcuts import get_object_or_404
from htmx_nav import Swap, make_shell_renderer
from .models import Project

render_shell = make_shell_renderer(
    lambda request: [
        Swap("app/_sidebar.html", {"user": request.user}, target_id="sidebar"),
        Swap("app/_breadcrumbs.html", target_id="breadcrumbs"),
    ]
)


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_shell(
        request,
        "app/project_detail.html",
        {"project": project},
        extra_swaps=[
            Swap("app/_tabs.html", {"active": "overview"}, target_id="project-tabs"),
        ],
    )
```

See the [Quickstart Guide](https://lucas-rollin.github.io/django-htmx-nav/quickstart.html) for the matching template setup and a full walkthrough (partial resolution, OOB swaps, shell renderers, testing).

## Learn More

- **[Full Documentation](https://lucas-rollin.github.io/django-htmx-nav/)** — API reference, architecture guides, testing helpers.
- **[Example Helpdesk Application](https://github.com/lucas-rollin/django-htmx-nav/tree/main/example)** — a runnable testbed comparing 8 implementation strategies (MPA, Vanilla HTMX, `django-htmx-nav`).
- **[Benchmark Experiments](https://github.com/lucas-rollin/django-htmx-nav/tree/main/example/benchmarks)** — reproducible metrics harness (payload size, server overhead, DOM churn).

## License

Released under the [MIT License](LICENSE).
