# django-htmx-nav

[![Docs](https://img.shields.io/badge/docs-mkdocs--material-blue)](https://lucas-rollin.github.io/django-htmx-nav/)

Django 6 added native template partials, so a single file can define
both the full page and the fragment HTMX swaps into:

```html
{% extends 'base.html' %}

{% block content %}
{% partialdef content inline %}
  <div>My page!</div>
{% endpartial %}
{% endblock %}
```

That's most of what you need for server-driven, SPA-like UX with MPA
simplicity, the URL stays the source of truth, and a full load vs. an
HTMX swap render the same fragment. What's still missing is the
boilerplate around it: detecting HTMX, picking the partial, setting
`HX-Push-Url` and doing HTMX-safe redirects. And, once your page has more
than one region (a sidebar, breadcrumbs), keeping those regions from
drifting out of sync depending on how the page was reached.

`django-htmx-nav` is two functions for that. Not a Django app, nothing
to add to `INSTALLED_APPS`.

```bash
pip install django-htmx-nav
```

## `render_htmx`: partial rendering, done

```python
from htmx_nav.responses import render_htmx

def project_list(request):
    return render_htmx(request, "app/project_list.html", {"projects": Project.objects.all()})
```

```html
{% extends 'base.html' %}
{% block content %}
{% partialdef content inline %}
  {% for project in projects %}<div>{{ project.name }}</div>{% endfor %}
{% endpartial %}
{% endblock %}
```

Full page load → renders the whole template. HTMX request → renders
only the `content` partial, sets `HX-Push-Url` to the current URL (so
the swap is bookmarkable and reload-safe), and sets `Vary: HX-Request`
so caches never serve one variant to the other kind of request.

## But you likely need to update your sidebar too

A tab click swaps `#content`, but if the sidebar shows an active-item
highlight, or breadcrumbs, those live outside `#content` and won't
update on their own. HTMX's out-of-band swaps solve this: render extra
fragments alongside the main one, each targeting its own DOM id.

```python
from htmx_nav.responses import Swap, render_htmx

def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_htmx(
        request, "app/project_detail.html", {"project": project},
        swaps=[
            Swap("app/_sidebar.html", {"active": project.pk}, target_id="sidebar"),
            Swap("app/_breadcrumbs.html", {"project": project}, target_id="breadcrumbs"),
        ],
    )
```

This works, but every view that touches the sidebar now needs to
rebuild the same nav context and remember to pass the same two `Swap`s,
easy to forget in view #12.

## `make_shell_renderer`: the shell, abstracted away

`make_shell_renderer` bakes a shell template + its context into a
`render_shell` function, so call sites go back to looking like a plain
view — the shell just always comes along for free:

```python
from htmx_nav.responses import make_shell_renderer

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
keyword arguments as `render_htmx` (`extra_swaps`, `partial_name`,
`push_url`, ...), so it's a drop-in.

## Advanced: three-pathway views (e.g. intrapage navigtion with tabs)

Some views have more than two ways they can be entered: a full reload,
an HTMX navigation into the page from elsewhere (targeting the page's
own top-level container), and an HTMX swap *within* the page (e.g.
clicking a tab). The first two should render the whole "content" region
and skip any extra OOB fragments beyond the shell; only the third needs
`extra_swaps` for siblings like a tab strip. `page_target_id` tells
`render_shell` how to fold the first two together automatically:

```python
render_staff = make_shell_renderer(
    "app/_shell.html",
    context_builder=lambda request: {"nav": build_nav_context(request)},
    page_target_id="page-content",   # DOM id of the page's own container
)

def project_tab(request, pk, *, tab_partial_name):
    project = get_object_or_404(Project, pk=pk)
    return render_staff(
        request, "app/project_detail.html", {"project": project},
        partial_name=tab_partial_name,
        extra_swaps=[Swap("app/_tabs.html", {"active": tab_partial_name}, target_id="tabs")],
    )
```

- **Full reload / HTMX targeting `#page-content`:** `render_staff`
  overrides `partial_name` to `"content"` and drops `extra_swaps` down
  to just the shell — nothing else in the DOM exists yet to refresh.
- **Any other HTMX target** (a tab click, a modal retargeted to a tab):
  falls through to `partial_name=tab_partial_name` and the tab strip
  swap, exactly as passed.

The view stays focused on what's actually tab-specific (which partial,
which sibling needs refreshing); the "which of the 3 pathways is this"
branching lives once, inside `render_shell`.

---

**⚠️ This package is young. The API (function signatures, keyword
argument names, module layout) may still change between releases.**