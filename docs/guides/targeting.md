# Targeting & Nested Navigation

In a simple HTMX application, every navigation request swaps the same primary container (such as `#content`). Real interfaces quickly add nested regions: tabs, subtabs, drawer panels, inline filters.

When a user clicks a tab inside `#content`, two questions come up:

1. **Which fragment should be the primary response?** Re-rendering all of `#content` when only `#tab_content` changed wastes queries and payload.
2. **Which other regions should ride along?** A tab click may need to update the tab header, but not the sidebar or breadcrumbs.

`django-htmx-nav` answers both with one condition vocabulary, used by the primary partial (`partial=`) and by out-of-band updates (`Swap(..., include_if=...)`).

## The Unified Target Vocabulary

Both `partial=` (as mapping values) and `include_if=` accept the same `Target` conditions:

| Target type | Example | Matches when |
| --- | --- | --- |
| **DOM ID string** | `"tab-content"` or `"#tab-content"` | The `HX-Target` header equals the ID (a leading `#` and any tag prefix like `div#` are stripped). |
| **Predicate** | `targeting("tab-content", "subtabs")` | `HX-Target` is any of the listed IDs. |
| **Inverted predicate** | `not_targeting("sidebar")` | The request is not targeting any of the listed IDs. Also true when `HX-Target` is absent. |
| **Boolean** | `True` / `False` | Always / never. |
| **Callable** | `lambda req: req.user.is_staff` | The callable returns a truthy value for the request. |

## Specifying the Primary Partial (`partial=`)

`partial` decides what `render_nav` returns as the main response **on HTMX requests**. On non-HTMX requests, `render_nav` renders `template_name` in full. `partial` accepts the forms below.

### 1. Default block (`#content`)

When omitted, `partial` falls back to `HTMX_NAV_DEFAULT_PARTIAL` (default `"#content"`):

```python
return render_nav(request, "projects/detail.html", context)
# HTMX request:     renders "projects/detail.html#content"
# Non-HTMX request: renders all of "projects/detail.html"
```

### 2. Explicit block or standalone template

```python
# A different block in the same template
render_nav(request, "projects/detail.html", context, partial="#tickets")

# A standalone partial file
render_nav(request, "projects/detail.html", context, partial="partials/_tickets.html")
```

### 3. Target routing dictionary

Map partials to `Target` conditions. Entries are checked in order and the first match wins:

```python
render_nav(
    request,
    "projects/detail.html",
    context,
    partial={
        "#tab_content": targeting("tab-content"),
        "#content": True,  # fallback
    },
)
```

```{tip}
End every routing dictionary with a `True` entry. If nothing matches, the mapping resolves to `None` and the **full template** is rendered, which is rarely what an HTMX request wants.
```

### 4. Callable

A function taking `request` and returning a partial (or `None` for the full template):

```python
def resolve_partial(request):
    if htmx_target_is(request, "modal-body"):
        return "#modal"
    return "#content"


render_nav(request, "projects/detail.html", context, partial=resolve_partial)
```

The callable receives only the request. If you need the template name, use a resolver (next section).

(targeting-path-replace)=
### 5. Separate page and partial files (`PathReplace`)

If your team keeps partials in their own files rather than `{% partialdef %}` blocks, organize templates by directory:

- `templates/pages/project_list.html`: extends `base.html` and includes the partial
- `templates/partials/_project_list.html`: the partial markup

`PathReplace` derives the partial path from the base template name:

```python
from htmx_nav import PathReplace, render_nav

render_nav(
    request,
    "pages/project_list.html",
    context,
    partial=PathReplace("pages/", "partials/_"),
)
```

- **Non-HTMX request:** renders `pages/project_list.html` in full.
- **HTMX request:** renders `partials/_project_list.html`.
- **No match:** if the template name does not contain `old` (for example `auth/login.html`), `PathReplace` returns the name unchanged, so the view renders that template as-is.
- **Path replacement:** replaces the first occurrence of `old`. It works for root templates (`pages/x.html` $\rightarrow$ `partials/_x.html`) as well as namespaced app templates (`app/pages/x.html` $\rightarrow$ `app/partials/_x.html`). Use a more specific `old` if needed.

To make this the project-wide default see [`HTMX_NAV_DEFAULT_PARTIAL`](htmx-nav-default-partial)

Resolvers can also be mapping keys, mixed with plain paths and blocks:

```python
partial={
    "partials/_tab_content.html": targeting("tab-content"),
    PathReplace("pages/", "partials/_"): True,  # fallback
}
```

### 6. Swaps only: `partial=None`

`partial=None` disables partial selection. `template_name` is rendered in full on every request, HTMX or not, and any `swaps` are appended on HTMX requests.

Use it for non-navigation endpoints: actions that are only ever triggered by HTMX, have no full-page equivalent, and don't change the URL (deleting a row, toggling a flag, dismissing a banner):

```python
def delete_ticket(request, ticket_id):
    get_object_or_404(Ticket, id=ticket_id).delete()
    messages.success(request, f"Ticket #{ticket_id} deleted.")

    return render_nav(
        request,
        "tickets/_empty_state.html",
        partial=None,
        swaps=[
            Swap.delete(f"ticket-row-{ticket_id}"),
            Swap.text("open-tickets-count", str(Ticket.objects.filter(status="open").count())),
            Swap("nav/_messages.html", target_id="messages", include_if=has_messages),
        ],
    )
```

## Coordinating Main Partials with Companion Swaps

Combining `partial=` routing with `Swap(..., include_if=...)` is where this pays off. Consider a project page with tabs:

```python
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)

    return render_nav(
        request,
        "projects/detail.html",
        {"project": project},
        # 1. Main response partials:
        partial={
            "#tab_content": targeting("tab-content"),
            "#content": True,
        },
        # 2. Out-of-band updates
        swaps=[
            # Only when just the tab content is swapped: refresh the tab header
            Swap("projects/_tabs.html", target_id="tabs", include_if=targeting("tab-content")),
            # No include_if: rides along on every HTMX request
            Swap("nav/_breadcrumbs.html", target_id="breadcrumbs"),
        ],
        title=project.name,
    )
```

### How requests resolve

- **Tab click (`HX-Target: tab-content`):** the primary response is `#tab_content`. The tabs swap matches and updates the active tab. Breadcrumbs also ride along, since they are unconditional.
- **Navigation click (`HX-Target: content`):** the primary response is the `#content` fallback. Breadcrumbs update. The tabs swap is skipped because it only applies to `tab-content`.
- **Direct visit (no HTMX headers):** the full document renders. Swaps are not rendered, but their `context` is still merged into the page context as a fallback, so shell templates get the same data as on HTMX requests.

To skip breadcrumbs on tab clicks, add `include_if=not_targeting("tab-content")`.

## Conditionals Beyond Targeting

`include_if` can depend on application state, permissions, or query parameters:

```python
from htmx_nav import Swap, has_messages, not_targeting, targeting

swaps = [
    Swap("nav/_tabs.html", target_id="tabs", include_if=targeting("tab-content", "subtabs")),
    # Skip the sidebar when the request came from inside the sidebar
    Swap("nav/_sidebar.html", target_id="sidebar", include_if=not_targeting("sidebar")),
    # Only when Django messages are queued
    Swap("nav/_messages.html", target_id="messages", include_if=has_messages),
    # Permission check
    Swap("nav/_admin_toolbar.html", target_id="admin-toolbar", include_if=lambda req: req.user.is_staff),
]
```

## Performance: Short-Circuit Evaluation

Keeping targeting logic in Python, rather than branching in templates on `request.headers.HX_Target`, means:

- A `Swap` whose `include_if` is false is **never rendered**.
- If that swap relies on isolated context or helper functions, those functions and their underlying database queries are never triggered.
- Templates stay agnostic of HTTP headers, so they are easier to reuse and test in isolation.
