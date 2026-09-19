# Out-of-Band Swaps

When an HTMX request updates an inner container (such as `#content`), surrounding layout controls, sidebars, breadcrumb trails, unread notification badges, and flash messages, do not update automatically.

`Swap` represents an out-of-band fragment appended to your HTTP response, instructing HTMX to update those peripheral regions in the same roundtrip.

## Auto-Wrapped vs. Unwrapped Swaps

`django-htmx-nav` supports two distinct templating styles: **auto-wrapped** (declarative Python) and **unwrapped** (self-contained templates).

### 1. Auto-Wrapped Swaps (Default)

When you specify `target_id`, `Swap` automatically wraps your template's inner HTML in a container with the appropriate `hx-swap-oob` attribute:

```python
Swap("nav/_sidebar.html", {"active": "tickets"}, target_id="sidebar")
```

Your template only contains the inner HTML:

```html
<!-- nav/_sidebar.html -->
<ul class="menu">
  <li class="{% if active == 'tickets' %}active{% endif %}"><a href="/tickets/">Tickets</a></li>
</ul>
```

When rendered, `Swap` wraps the output automatically:

```html
<div id="sidebar" hx-swap-oob="innerHTML">
  <ul class="menu">
    <li class="active"><a href="/tickets/">Tickets</a></li>
  </ul>
</div>
```

### 2. Unwrapped Swaps (Avoiding Auto-Wrapping)

If you prefer your templates to own their outer element, or if you are migrating existing HTMX templates, you can **avoid auto-wrapping entirely by omitting `target_id`** (or passing `target_id=None`):

```python
# No target_id specified — template is rendered exactly as-is:
Swap("nav/_sidebar.html", {"active": "tickets"})
```

Your template defines its own root element and `hx-swap-oob` attribute:

```html
<!-- nav/_sidebar.html -->
<aside id="sidebar" class="w-64 bg-base-200 border-r" hx-swap-oob="outerHTML">
  <ul class="menu">
    <li class="{% if active == 'tickets' %}active{% endif %}"><a href="/tickets/">Tickets</a></li>
  </ul>
</aside>
```

#### Why Choose Unwrapped Swaps?

- **Semantic HTML:** You can use `<aside>`, `<nav>`, `<tr>`, or `<tbody>` as the root element without Python wrapping it in a generic `<div>`.
- **Template Independence:** Template designers have full control over layout classes and HTMX attributes.
- **Drop-in Migration:** Existing projects with hand-rolled `hx-swap-oob` fragments can migrate to `django-htmx-nav` without changing a single line of HTML.

## Swap Strategies & Wrappers

### Swap Styles

The `swap_style` argument controls HTMX's swap behavior (defaults to `"innerHTML"`):

```python
# Replace the element itself rather than its contents:
Swap("nav/_navbar.html", target_id="navbar", swap_style="outerHTML")

# Prepend a new item to an existing list:
Swap("chat/_message.html", target_id="chat-feed", swap_style="beforeend")
```

### `<hx-partial>` Wrapper

If you use the `<hx-partial>` web component or custom client-side extensions, configure `wrap="hx-partial"` (or set `HTMX_NAV_DEFAULT_SWAP_WRAP = "hx-partial"` globally):

```python
Swap("nav/_sidebar.html", target_id="sidebar", wrap="hx-partial")
```

Renders:

```html
<hx-partial hx-target="#sidebar" hx-swap="innerHTML">
  ...
</hx-partial>
```

## High-Performance Specialized Constructors

Not every UI update requires compiling a Django template. `Swap` includes specialized constructors designed for zero template overhead.

### 1. Raw Text Swaps (`Swap.text`)

Update notification counters, user handles, or status badges using pure Python strings:

```python
Swap.text("unread-badge", "5")
```

Renders:

```html
<div id="unread-badge" hx-swap-oob="innerHTML">5</div>
```

Text content is automatically HTML-escaped for security.

### 2. Element Deletion (`Swap.delete`)

Remove an element from the DOM after an action (such as dismissing an alert banner or deleting a table row):

```python
Swap.delete("flash-banner")
```

Renders:

```html
<div id="flash-banner" hx-swap-oob="delete"></div>
```

## Flash Messages Integration (`has_messages`)

Displaying Django flash messages during partial navigation often leads to awkward template logic. `django-htmx-nav` provides the `has_messages` predicate:

```python
from htmx_nav import Swap, has_messages

# Appends the message container ONLY when messages are queued:
Swap("components/_messages.html", target_id="flash-container", include_if=has_messages)
```

If `messages.get_messages(request)` is empty, the swap evaluates to `False` and is completely skipped, no templates are parsed and zero bytes are transmitted.

## Context Merging

When a `Swap` specifies a `context` dictionary, it merges with the parent view context:

```python
render_nav(
    request,
    "projects/detail.html",
    {"project": project, "theme": "dark"},
    swaps=[
        # Inherits "project" and "theme", but overrides "active_tab":
        Swap("projects/_tabs.html", {"active_tab": "settings"}, target_id="tabs"),
    ],
)
```

If the user navigates directly via a browser address bar (a full-page GET reload), swap contexts are also merged into the main template context so your base layout remains fully populated.
