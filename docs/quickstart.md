# Quickstart Guide

This guide will walk you through installing `django-htmx-nav` and implementing partial rendering, out-of-band updates, shell renderers, and testing.

---

## 1. Installation

Install `django-htmx-nav` via `pip`:

```bash
pip install django-htmx-nav
```

---

## 2. Basic Partial Rendering (`render_nav`)

Use `render_nav` in your view functions instead of standard Django `render`.

```python
# views.py
from htmx_nav import render_nav
from .models import Project


def project_list(request):
    projects = Project.objects.all()
    return render_nav(request, "app/project_list.html", {"projects": projects})
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
{% endpartialdef %}
{% endblock %}
```

### Behavior

- **Full Page Load:** Renders the full template including `base.html`.
- **HTMX Request:** Renders only the `content` partial, resolves active partials, and patches `Vary: HX-Request` for correct HTTP caching.

---

## 3. Out-of-Band Swaps (`Swap`)

When navigating between pages, components outside the main content area (such as sidebars or breadcrumbs) may also need updating. Use `Swap` to append out-of-band fragments:

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
            Swap(
                "app/_breadcrumbs.html", {"project": project}, target_id="breadcrumbs"
            ),
            Swap.text("notification-badge", "3"),
            Swap.delete("temporary-alert"),
        ],
    )
```

### Ready-made Strings and Deletions

- **`Swap.text(target_id, content)`**: Emits string content directly without template rendering.
- **`Swap.delete(target_id)`**: Generates an out-of-band delete fragment (`<div id="target_id" hx-swap-oob="delete"></div>`).

---

## 4. Shell Rendering (`make_shell_renderer`)

To avoid repeating shell swap definitions across every view, use `make_shell_renderer` to create a reusable `render_shell` helper:

```python
# renderers.py
from htmx_nav import make_shell_renderer

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

## 6. Testing & Visual Debugging

For testing navigation context parity, HTML composition, and using visual swap debugging in development, see the standalone [Testing & Visual Debugging Guide](testing.md).

---

## Next Steps

- Check out the [API Reference / Docstrings](api.md) for full function signatures.
- Learn about [Testing & Visual Debugging](testing.md).
- Explore architectural patterns:
  - [Context Processor & Template Tags](pattern/context_processor_and_templatetags.md)
  - [Centralized Navigation Registry](pattern/registry_pattern.md)
