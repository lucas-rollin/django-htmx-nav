# Targeting & Nested Navigation

In a simple HTMX application, every navigation request might swap the same primary container (such as `#content`). However, real-world interfaces quickly introduce nested regions: tabs, subtabs, drawer panels, or inline filters.

When a user clicks a tab inside `#content`:

1. **Which block should be the primary response?** (Rendering the entire `#content` block when only `#tab_content` changed wastes database queries and payload).
2. **Which surrounding regions should ride along?** (A tab click might need to update the tab header controls out-of-band, but doesn't need to re-render the main sidebar or breadcrumbs).

`django-htmx-nav` solves this by providing a unified condition vocabulary for both primary partial selection (`partial=`) and out-of-band updates (`include_if=`).

## The Unified Target Vocabulary

Both `partial=` and `Swap(..., include_if=...)` accept the same `Target` condition types:

| Target Type | Example | When It Matches |
| --- | --- | --- |
| **Exact DOM ID string** | `"tab-content"` or `"#tab-content"` | Matches when HTMX's `HX-Target` header matches the ID (leading `#` is automatically stripped). |
| **Target predicate** | `targeting("tab-content", "subtabs")` | Matches if `HX-Target` is any of the specified element IDs. |
| **Inverted predicate** | `not_targeting("sidebar")` | Matches on any HTMX request *except* when targeting `#sidebar`. |
| **Boolean** | `True` or `False` | Unconditional inclusion or fallback default. |
| **Custom callable** | `lambda req: req.user.is_staff` | Evaluated dynamically against the Django `request` object. |

## Specifying the Primary Partial (`partial=`)

The `partial` argument in `render_nav` determines which fragment of your template is returned as the main response on HTMX requests. For non-HTMX requests `render_nav` renders the specified `template_name` normally. It accepts several formats:

### 1. Default Block (`#content`)

When omitted, `partial` defaults to the value configured in `HTMX_NAV_DEFAULT_PARTIAL` (which defaults to `"#content"`):

```python
return render_nav(request, "projects/detail.html", context)
# Resolves to "projects/detail.html#content" on HTMX requests.
# Non-HTMX requests render the full "projects/detail.html" template.
```

### 2. Explicit Block or Standalone Template

You can explicitly name any block in the template or provide a path to a standalone partial file:

```python
# Render a specific block in the same template:
return render_nav(request, "projects/detail.html", context, partial="#tickets")

# Or render a standalone partial template:
return render_nav(request, "projects/detail.html", context, partial="partials/_tickets.html")
```

### 3. Target Routing Dictionary

To dynamically switch the rendered block based on what HTMX is targeting, pass a dictionary mapping template blocks to `Target` conditions. Entries are evaluated in order; the first condition that evaluates to `True` wins:

```python
return render_nav(
    request,
    "projects/detail.html",
    context,
    partial={
        "#tab_content": targeting("tab-content"),
        "#content": True,  # Fallback for HTMX requests that don't match above.
    },
)
```

```{tip}
Always place `True` as the last entry in a routing dictionary to serve as a reliable fallback for HTMX requests. If no conditions match and no fallback is present, `render_nav` renders the full document.
```

### 4. Callable

You can also supply a function taking `request` and returning a partial name (or `None` to fall back to the full template):

```python
def resolve_partial(request):
    if request.headers.get("HX-Target") == "modal-body":
        return "#modal"
    return "#content"


return render_nav(request, "projects/detail.html", context, partial=resolve_partial)
```

### 5. Multi-File Templates & Pre-Django 6 (`ReplacePrefix`)

Native inline partials (`{% partialdef %}`) were introduced in Django 6.0. If you are on **Django 4.2 LTS or 5.x** (without `django-template-partials`), or if your team prefers keeping partials in separate physical files, template block selectors like `"#content"` cannot be parsed by Django's template engine.

Instead, projects typically organize templates into separate directories:

- `templates/pages/project_list.html` (extends `base.html` and includes the partial)
- `templates/partials/_project_list.html` (standalone partial markup)

Use `ReplacePrefix` to automatically transform the template path for HTMX requests:

```python
from htmx_nav import ReplacePrefix, render_nav

return render_nav(
    request,
    "pages/project_list.html",
    context,
    partial=ReplacePrefix("pages/", "partials/_"),
)

```

- **Direct browser visit (Non-HTMX GET):** Renders `"pages/project_list.html"` in full.
- **HTMX request:** Automatically intercepts and renders `"partials/_project_list.html"` without needing `#block` syntax.
- **Graceful fallback:** If a view renders a template that does not contain `"pages/"` (e.g. `"auth/login.html"`), it falls back gracefully and returns `"auth/login.html"` unmodified.

```{tip}
You can configure this convention globally in your `settings.py` so every view in your project automatically inherits it:

```python
# settings.py
HTMX_NAV_DEFAULT_PARTIAL = ReplacePrefix("pages/", "partials/_")
```

You can also use `ReplacePrefix` inside a target routing dictionary:

```python
partial={
    "partials/_tab_content.html": targeting("tab-content"),
    ReplacePrefix("pages/", "partials/_"): True,  # Fallback for main content on HTMX
}
```

## Coordinating Main Partials with Companion Swaps

The true power of this architecture emerges when combining `partial=` routing with `Swap(..., include_if=...)`.

Consider a project detail page with tabbed sub-navigation:

```python
from django.shortcuts import get_object_or_404
from htmx_nav import Swap, render_nav, targeting
from .models import Project


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)

    return render_nav(
        request,
        "projects/detail.html",
        {"project": project},
        # 1. Main response partials (evaluated only on HTMX requests):
        partial={
            "#tab_content": targeting("tab-content"),
            "#content": True,
        },
        # 2. Out-of-band updates (synced based on include_if rules):
        swaps=[
            # When swapping just the tab content, update active tab headers:
            Swap(
                "projects/_tabs.html",
                target_id="tabs",
                include_if=targeting("tab-content"),
            ),
            # Global shell components stay unconditional:
            Swap("nav/_breadcrumbs.html", target_id="breadcrumbs"),
        ],
        title=project.name,
    )
```

### How the Request Resolves

- **Tab Click (`HX-Target: tab-content`):**
  - `partial` matches `"#tab_content"` $\rightarrow$ only the tab markup is rendered.
  - The `_tabs.html` swap matches `targeting("tab-content")` $\rightarrow$ the active tab button updates.
  - The `_breadcrumbs.html` swap is excluded $\rightarrow$ skipped entirely.
- **Navigation Link Click (`HX-Target: content`):**
  - `partial` matches the fallback `"#content"`.
  - The `_breadcrumbs.html` swap matches `targeting("content")` $\rightarrow$ breadcrumbs update.
  - The `_tabs.html` swap is excluded.
- **Direct Browser Visit (No HTMX headers):**
  - Renders the complete HTML document including `base.html`. `swaps` are not evaluated.

## Conditionals Beyond Targeting

`include_if` is not limited to DOM targets. You can condition swaps on application state, permissions, or query parameters:

```python
from htmx_nav import Swap, has_messages, not_targeting, targeting

swaps = [
    # Match any of multiple DOM targets:
    Swap("nav/_tabs.html", target_id="tabs", include_if=targeting("tab-content", "subtabs")),

    # Inverted targeting: skip updating sidebar if the user clicked inside the sidebar itself:
    Swap("nav/_sidebar.html", target_id="sidebar", include_if=not_targeting("sidebar")),

    # Built-in message queue check (skips if Django messages is empty):
    Swap("nav/_messages.html", target_id="messages", include_if=has_messages),

    # Permission check or query parameter inspection:
    Swap(
        "nav/_admin_toolbar.html",
        target_id="admin-toolbar",
        include_if=lambda req: req.user.is_staff,
    ),
]
```

## Performance: Short-Circuit Evaluation

A critical design advantage of keeping targeting logic in Python (rather than branching inside templates with `{% if request.headers.HX_Target == "..." %}`) is **short-circuit execution**:

- When a `Swap` evaluates its `include_if` condition to `False`, its template is **never rendered**.
- If that swap relies on isolated context or helper functions, those functions and their underlying database queries are never triggered.
- Templates remain completely agnostic of HTTP headers, making them clean, reusable, and testable in isolation.
