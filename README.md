# django-htmx-nav

[![Docs](https://img.shields.io/badge/docs-furo-blue)](https://lucas-rollin.github.io/django-htmx-nav/)

Django 6 added native template partials, so a single file can define
both the full page and the fragment HTMX swaps into:

```html
{% extends 'base.html' %}

{% block content %}
{% partialdef content inline %}
  <div>My page!</div>
{% endpartialdef %}
{% endblock %}
```

That's most of what you need for server-driven, SPA-like UX with MPA
simplicity: the URL stays the source of truth, and a full load vs. an
HTMX swap render the same fragment. What's still missing is the
boilerplate around it: detecting HTMX, picking the partial, and
doing HTMX-safe redirects. And, once your page has more
than one region (a sidebar, breadcrumbs), keeping those regions from
drifting out of sync depending on how the page was reached.

`django-htmx-nav` provides lightweight helpers for that. Not a Django app, nothing
to add to `INSTALLED_APPS`.

```bash
pip install django-htmx-nav
```

## `render_nav`: partial rendering, done

```python
from htmx_nav import render_nav


def project_list(request):
    return render_nav(
        request, "app/project_list.html", {"projects": Project.objects.all()}
    )
```

```html
{% extends 'base.html' %}
{% block content %}
{% partialdef content inline %}
  {% for project in projects %}<div>{{ project.name }}</div>{% endfor %}
{% endpartialdef %}
{% endblock %}
```

Full page load → renders the whole template. HTMX request → renders
only the `content` partial and sets `Vary: HX-Request`
so caches never serve one variant to the other kind of request.

## But you likely need to update your sidebar too

A tab click swaps `#content`, but if the sidebar shows an active-item
highlight, or breadcrumbs, those live outside `#content` and won't
update on their own. HTMX's out-of-band swaps solve this: render extra
fragments alongside the main one, each targeting its own DOM id.

```python
from htmx_nav import Swap, render_nav


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_nav(
        request,
        "app/project_detail.html",
        {"project": project},
        swaps=[
            Swap("app/_sidebar.html", {"active": project.pk}, target_id="sidebar"),
            Swap(
                "app/_breadcrumbs.html", {"project": project}, target_id="breadcrumbs"
            ),
        ],
    )
```

This works, but every view that touches the sidebar now needs to
rebuild the same nav context and remember to pass the same `Swap`s,
easy to forget in view #12.

## `make_shell_renderer`: the shell, abstracted away

`make_shell_renderer` bakes a shell template + its context into a
`render_shell` function, so call sites go back to looking like a plain
view — the shell just always comes along for free:

```python
from htmx_nav import make_shell_renderer

render_shell = make_shell_renderer(
    shell_template="app/_shell.html",  # renders sidebar + breadcrumbs together
    context_builder=lambda request: {"nav": build_nav_context(request)},
)


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_shell(request, "app/project_detail.html", {"project": project})
```

Every HTMX response from `render_shell` includes the shell as an
out-of-band swap, built from the same `build_nav_context` a full page
load would use, so the sidebar can never show one thing on first load
and another after an HTMX swap. `render_shell` accepts the same
keyword arguments as `render_nav` (`extra_swaps`, `partial` ...),
so it's a drop-in.

## Target-aware partial resolution

Views can resolve different partial blocks dynamically based on `HX-Target` headers using target specifications:

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

The view stays focused on what's actually tab-specific; partial selection and out-of-band shell delivery are handled cleanly by `render_project`.

---

**⚠️ This package is young. The API (function signatures, keyword
argument names, module layout) may still change between releases.**