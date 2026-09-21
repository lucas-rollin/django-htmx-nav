# Visual Swap Debugging

`HTMX_NAV_DEBUG_SWAPS` highlights DOM elements as they're updated by out-of-band HTMX swaps, useful for seeing at a glance what actually changed.

## Enable

```python
# settings.py
INSTALLED_APPS = [
    ...,
    "htmx_nav",
    ...,
]  # needed for static files + {% htmx_nav_debug_marker %}
```

```python
# settings.py
HTMX_NAV_DEBUG_SWAPS = DEBUG # active during development
```

Two stylesheets are provided, depending on whether you want a client-side on/off toggle:

**Toggleable** — highlighting only shows while `data-hn-debug-swaps` is present on `<body>`. Useful since `HTMX_NAV_DEBUG_SWAPS` is a server-side setting that needs a reload to flip, but the body attribute can be toggled instantly client-side (e.g. a dev-only button running `document.body.toggleAttribute('data-hn-debug-swaps')`):

```html
{% load static %}
<head>
    <!-- your head -->
    <link rel="stylesheet" href="{% static 'htmx_nav/debug-swaps.css' %}">
</head>
<body data-hn-debug-swaps>
    <!-- your body -->
</body>
```

**Always-on** — highlighting fires any time a swap happens while `HTMX_NAV_DEBUG_SWAPS` is enabled, no body attribute needed:

```html
{% load static %}
<link rel="stylesheet" href="{% static 'htmx_nav/debug-swaps-always.css' %}">
```

## How it works

With the setting on, any `Swap(target_id=...)` appends a script that toggles a `.hn-swap` class on that element (with a forced reflow, so repeated swaps retrigger it):

```html
<script>
    (function(){
        var el = document.getElementById("TARGET_ID");
        if (!el) return;
        el.classList.remove('hn-swap'); void el.offsetWidth; el.classList.add('hn-swap');
    })();
</script>
```

`debug-swaps.css` flashes the background of any `.hn-swap` element:

```css
[data-hn-debug-swaps] .hn-swap {
  animation: hn-flash-pulse 900ms ease-out;
}
@keyframes hn-flash-pulse {
  from { background-color: #fef08a; }
  to   { background-color: transparent; }
}
```

## Two requirements for the flash to actually show up

**A stable id on a persistent element.** The script runs `getElementById` *after* the swap lands, so `target_id` must be on a node that already exists in the page and keeps the same id every render. Put it on the wrapper in your base/shell template, not inside the swapped partial:

```html
<!-- base.html -->
<div id="sidebar">{% include "components/_sidebar_menu.html" %}</div>
```

```python
Swap("components/_sidebar_menu.html", context, target_id="sidebar")
```

An id that only exists inside the fragment, or that changes per render (`id="sidebar-{{ project.id }}"`), means `getElementById` finds nothing, or a stale node.

**No opaque background covering the target.** The flash paints on the element `target_id` resolves to. If a child fully covers it with its own solid background, the flash renders underneath and is invisible:

```html
<!-- Hidden: <ul>'s own bg-base-200 covers #sidebar -->
<div id="sidebar"><ul class="menu bg-base-200 w-64 p-4">...</ul></div>

<!-- Visible: background lives on the target itself -->
<div id="sidebar" class="bg-base-200"><ul class="menu w-64 p-4">...</ul></div>
```

## Manual OOB wrapping

`target_id` bundles two things: which id the marker flashes, and telling `Swap` to auto-wrap your fragment in `<div hx-swap-oob>`. Writing the OOB wrapper yourself (e.g. via a `#oob` partial, for swap styles or attributes `wrap` doesn't cover) opts out of both, `Swap` never sees your markup to inject a marker into.

Use `{% htmx_nav_debug_marker %}` instead, placed *inside* the wrapper (same wrapper-stripping reason as above), with the same id string:

```html
{% load htmx_nav %}
{% partialdef oob %}
  <div id="breadcrumbs" hx-swap-oob="innerHTML">
    {% partial breadcrumbs %}
    {% htmx_nav_debug_marker "breadcrumbs" %}
  </div>
{% endpartialdef %}
```

It respects `HTMX_NAV_DEBUG_SWAPS` the same way (empty when disabled) and is the same script `Swap` would've emitted, one implementation either way.

## Related Resources

- **[Debugging Utilities API Reference](api/debugging.md):** Detailed signatures for `debug_swap_marker` and `{% htmx_nav_debug_marker %}`.
- **{demo}`Live Demo in Debug Mode <htmx-nav/declarative/?debug-swaps=1>`:** Test visual swap highlighting in real time in the live sandbox.
