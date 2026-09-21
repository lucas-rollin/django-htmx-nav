# Settings

All settings are optional and configured in your Django `settings.py`.

| Setting | Default | Description |
| :--- | :--- | :--- |
| `HTMX_NAV_DEFAULT_PARTIAL` | `"#content"` | Default partial block or template path when `partial` is omitted. |
| `HTMX_NAV_DEFAULT_SWAP_WRAP` | `"oob"` | Default HTML wrapper for out-of-band swaps (`"oob"` or `"hx-partial"`). |
| `HTMX_NAV_TITLE_CONTEXT_KEY` | `"title"` | Context key used for automatic `<title>` element injection. |
| `HTMX_NAV_DEBUG_SWAPS` | `False` | Enables visual swap animations during development. |

---

(htmx-nav-default-partial)=
## `HTMX_NAV_DEFAULT_PARTIAL`

- **Type:** `str | PartialResolver | None` (or any `PartialSpec`)
- **Default:** `"#content"`
- **Applies to:** `render_nav`, `make_shell_renderer`, `make_shell_view_mixin`

Specifies the fallback partial block, template path, or resolver when a view does not explicitly pass `partial=...`.

### Inline Partials (Recommended)

When templates define partials internally using `{% block ... %}` (or `{% partialdef %}`):

```python
# settings.py
HTMX_NAV_DEFAULT_PARTIAL = "#main"
```

### Standalone Partial Files (Legacy)

```{note}
Legacy/compatibility support. Prefer inline partials for new projects; this option is for codebases that already keep pages and partials in separate files and don't want to rewrite them.
```

When pages and partials are separate files (e.g. `pages/x.html` and `partials/_x.html`), configure `PathReplace`:

```python
# settings.py
from htmx_nav import PathReplace

HTMX_NAV_DEFAULT_PARTIAL = PathReplace("pages/", "partials/_")
```

See [Separate page and partial files (`PathReplace`)](targeting-path-replace) in the Targeting Guide for details.

To completely bypass partial extraction for full-page renders while keeping out-of-band swaps, pass `partial=None` directly to `render_nav`.

---

(htmx-nav-default-swap-wrap)=
## `HTMX_NAV_DEFAULT_SWAP_WRAP`

- **Type:** `Literal["oob", "hx-partial"]`
- **Default:** `"oob"`
- **Applies to:** `Swap`, `Swap.text`

Controls how out-of-band swap fragments are wrapped in HTML when `wrap` is not specified on the `Swap`:

- `"oob"`: Standard HTMX swap using `<div id="..." hx-swap-oob="...">`.
- `"hx-partial"`: Custom element wrapper using `<hx-partial hx-target="#..." hx-swap="...">`.

```python
# settings.py
HTMX_NAV_DEFAULT_SWAP_WRAP = "hx-partial"
```

---

(htmx-nav-title-context-key)=
## `HTMX_NAV_TITLE_CONTEXT_KEY`

- **Type:** `str`
- **Default:** `"title"`
- **Applies to:** `render_nav`, `make_shell_view_mixin`

The template context variable name used for page titles. Set this to match the variable name used in your `base.html` title tag:

```html
<!-- base.html -->
<title>{% block title %}{{ page_title|default:"Home Page" }}{% endblock %}</title>
```

```python
# settings.py
HTMX_NAV_TITLE_CONTEXT_KEY = "page_title"
```

This keeps page titles in sync across both request modes:

- **Full-page reloads:** Passing `title="Dashboard"` to `render_nav` populates `context["page_title"]`, which `base.html` renders.
- **HTMX requests:** `render_nav` reads `context["page_title"]` and appends an escaped `<title>` tag to the response, which HTMX automatically applies to the browser tab.

---

(htmx-nav-debug-swaps)=
## `HTMX_NAV_DEBUG_SWAPS`

- **Type:** `bool`
- **Default:** `False`
- **Applies to:** `Swap.render`, `debug_swap_marker`

When `True`, appends a small inline `<script>` to swapped fragments that adds the `hn-swap` CSS class to the target DOM element, triggering a highlight animation.

`django-htmx-nav` checks `HTMX_NAV_DEBUG_SWAPS` directly **without inspecting Django's `DEBUG` setting**. This independence allows you to enable debug swaps in staging or demo environments even when `DEBUG = False`.

See the [Debugging Guide](debugging.md) for CSS integration and custom styling.

### Recommended Local Development Recipe

For standard local development, it is recommended to tie this setting directly to your Django `DEBUG` value:

```python
# settings.py
HTMX_NAV_DEBUG_SWAPS = DEBUG
```
