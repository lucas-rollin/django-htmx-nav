# Quickstart Guide

This guide will walk you through installing `django-htmx-nav` and implementing partial rendering, out-of-band updates, shell renderers, and testing.

---

## 1. Installation

Install `django-htmx-nav` via `pip`:

```bash
pip install django-htmx-nav
```

> **Note:** `django-htmx-nav` is a Python package containing lightweight utility functions. You do **not** need to add anything to `INSTALLED_APPS` in your Django `settings.py`.

---

## 2. Basic Partial Rendering (`render_htmx`)

Use `render_htmx` in your view functions instead of standard Django `render`.

```python
# views.py
from htmx_nav.responses import render_htmx
from .models import Project

def project_list(request):
    projects = Project.objects.all()
    return render_htmx(request, "app/project_list.html", {"projects": projects})
```

In your HTML template, mark the partial block using Django 6 inline partials:

```html
<!-- app/templates/app/project_list.html -->
{% extends 'base.html' %}

{% block content %}
{% partialdef content inline %}
  <div id="project-list">
    {% for project in projects %}
      <div class="card">{{ project.name }}</div>
    {% endfor %}
  </div>
{% endpartial %}
{% endblock %}
```

### Behavior

- **Full Page Load:** Renders the full template including `base.html`.
- **HTMX Request:** Renders only the `content` partial, sets `HX-Push-Url` to the request URL, and patches `Vary: HX-Request` for correct HTTP caching.

---

## 3. Out-of-Band Swaps (`Swap`)

When navigating between pages, components outside the main content area (such as sidebars or breadcrumbs) may also need updating. Use `Swap` to append out-of-band fragments:

```python
from htmx_nav.responses import render_htmx, Swap

def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_htmx(
        request,
        "app/project_detail.html",
        {"project": project},
        swaps=[
            Swap("app/_sidebar.html", {"active_pk": project.pk}, target_id="sidebar"),
            Swap("app/_breadcrumbs.html", {"project": project}, target_id="breadcrumbs"),
        ],
    )
```

---

## 4. Shell Rendering (`make_shell_renderer`)

To avoid repeating shell swap definitions across every view, use `make_shell_renderer` to create a reusable `render_shell` helper:

```python
# renderers.py
from htmx_nav.responses import make_shell_renderer

render_shell = make_shell_renderer(
    shell_template="app/_shell.html",
    context_builder=lambda request: {"nav_user": request.user},
)
```

Now views can simply call `render_shell`:

```python
# views.py
from .renderers import render_shell

def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_shell(request, "app/project_detail.html", {"project": project})
```

---

## 5. Class-Based View Integration

If you prefer Django Class-Based Views (CBVs), use `make_shell_view_mixin`:

```python
from django.views.generic import DetailView
from htmx_nav.views import make_shell_view_mixin
from .renderers import render_shell

ShellViewMixin = make_shell_view_mixin(render_shell)

class ProjectDetailView(ShellViewMixin, DetailView):
    model = Project
    template_name = "app/project_detail.html"
```

---

## 6. Verifying Navigation Parity in Tests

Use `assert_shell_parity` from `htmx_nav.testing` to verify that full page loads and HTMX swaps yield identical navigation states:

```python
from htmx_nav.testing import assert_shell_parity

def test_project_detail_navigation(client, project):
    assert_shell_parity(client, f"/projects/{project.pk}/")
```

---

## Next Steps

- Check out the [API Reference / Docstrings](api.md) for full function signatures.
- Explore architectural patterns:
  - [Context Processor & Template Tags](pattern/context_processor_and_templatetags.md)
  - [Centralized Navigation Registry](pattern/registry_pattern.md)
