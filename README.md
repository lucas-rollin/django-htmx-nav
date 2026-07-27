# django-htmx-nav

HTMX does the heavy lifting for server-driven, SPA-like UX with MPA
simplicity, the URL is already the source of truth, and out-of-band
swaps already let you update more than one region of the page in one
response. What's missing isn't a framework; it's a clear road to
implementing that pattern without the two things that bite in practice:
**stale navigation state** (the sidebar/breadcrumbs say something
different depending on whether you full-loaded or HTMX-swapped into a
page) and **cumbersome boilerplate** (hand-wiring OOB fragments, push-url,
redirects, and partial rendering for every view).

This package is small on purpose: two modules, no Django app to install.

- **`htmx_nav.responses`** — `render_htmx`, `Oob`, `htmx_redirect`,
  `make_shell_renderer`. The actual HTMX response mechanics: partial
  rendering, out-of-band fragments, push-url, cache-correct `Vary`
  headers, and HTMX-safe redirects.
- **`htmx_nav.helpers`** (optional) — `reverse_maybe`, `cache_on_request`,
  and `check_template_partials_configured`. Small, generic functions
  useful when building your own nav data; nothing here is required to use
  `responses.py`.
- **`htmx_nav.testing`** — `assert_shell_parity`, which renders a URL both
  as a full page load and an HTMX request and asserts your nav state
  matches — the actual invariant ("stale nav state") this package exists
  to help you avoid, turned into a test you can run in CI.
- **`htmx_nav.views`** — `make_shell_view_mixin`, a CBV convenience.

**How you actually build nav data — a sidebar, breadcrumbs, tabs — is
deliberately not something this package ships a class for.** It's
documented instead, as two worked patterns:

- [`docs/patterns/context_processor_and_templatetags.md`](docs/patterns/context_processor_and_templatetags.md) —
  nav declared inline in templates via template tags + (optionally) a
  context processor.
- [`docs/patterns/registry_pattern.md`](docs/patterns/registry_pattern.md) —
  a small, copy-into-your-project registry (dataclasses + dicts) for when
  centralizing "what nav state does each view have" earns its keep.

## Install

`htmx_nav` is **not** a Django app, nothing to add to `INSTALLED_APPS`.

```bash
pip install django-htmx-nav
```

## Template partials setup

`render_htmx` addresses partial renders as `template_name#partial_name`.

- **Django ≥ 6:** supported natively, nothing to configure. Define
  fragments with `{% partialdef content %}...{% endpartialdef %}`.
- **Django < 6:** requires the `django-template-partials` package
  (already a dependency of `django-htmx-nav`) registered in *your*
  project's `INSTALLED_APPS`:
  ```python
  INSTALLED_APPS = [
      ...,
      "template_partials",
  ]
  ```
  and `{% load partials %}` at the top of any template defining a
  `{% partialdef %}`.

## Usage

### Rendering a view

```python
from htmx_nav.responses import render_htmx

def project_list(request):
    return render_htmx(request, "app/project_list.html", {"projects": Project.objects.all()})
```

On a full page load, this renders `app/project_list.html` in full. On an
HTMX request, it renders only the `{% partialdef content %}` block, sets
`HX-Push-Url` to the current URL (so the swap is bookmarkable/reload-safe),
and sets `Vary: HX-Request` (so caches don't serve the wrong variant to
the wrong request type).

### Keeping a shell (sidebar/nav) in sync via OOB

```python
from htmx_nav.responses import make_shell_renderer
from .nav import build_nav_context  # see docs/patterns/

render_shell = make_shell_renderer(
    shell_template="app/_shell.html",
    context_builder=lambda request: {"nav": build_nav_context(request)},
)

def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render_shell(request, "app/project_detail.html", {"project": project})
```

Every HTMX response from `render_shell` includes the shell template as an
out-of-band fragment, computed from the *same* `build_nav_context`
whichever pattern you chose, so the sidebar/breadcrumbs can never drift
from what a full page load would have shown.

### Ad hoc OOB fragments

```python
from htmx_nav.responses import Oob, render_htmx

def mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk)
    notification.mark_read()
    return render_htmx(
        request, "app/notifications/_item.html", {"notification": notification},
        oobs=[Oob("app/notifications/_badge.html", {"count": unread_count(request.user)}, target_id="unread-badge")],
    )
```

### Redirecting safely from either context

```python
from htmx_nav.responses import htmx_redirect

def create_project(request):
    ...  # create it
    return htmx_redirect(request, reverse("app:project_detail", args=[project.pk]))
```

A plain `HttpResponseRedirect` gets swapped into the DOM as raw HTML when
the triggering request was HTMX. Instead of navigating, `htmx_redirect`
returns `HX-Redirect` + 204 on HTMX requests, a normal redirect otherwise.

### Class-based views

```python
from htmx_nav.views import make_shell_view_mixin
from .render import render_shell

ShellViewMixin = make_shell_view_mixin(render_shell)

class ProjectDetailView(ShellViewMixin, DetailView):
    template_name = "app/project_detail.html"
```

## `htmx_nav.helpers` reference

- **`reverse_maybe(view_name, kwargs=None, *, strict=True)`** — `reverse()`
  with an escape hatch for reusing ambient kwargs (e.g. the current
  page's `request.resolver_match.kwargs`) across several nav links that
  don't all accept them. `strict=True` (default) behaves exactly like
  `reverse()`, pass `strict=False` when the kwargs are ambient/reused
  rather than built specifically for this `view_name`, and a mismatch
  should degrade gracefully (retry with no kwargs) instead of raising.
- **`cache_on_request(request, key, builder)`**, compute `builder()` at
  most once per request, e.g. so a main-content render and an OOB shell
  render in the same response cycle don't rebuild nav context twice.
