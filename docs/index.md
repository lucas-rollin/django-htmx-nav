# django-htmx-nav

**Server-driven, SPA-like user experiences with MPA simplicity in Django.**

`django-htmx-nav` provides lightweight helpers for handling HTMX partial renders, out-of-band (OOB) updates, shell layout rendering, and HTMX-safe redirects in Django projects.

This site documents the package itself — installation, `render_nav`,
`Swap`, `make_shell_renderer`, testing utilities, and so on. The
repository as a whole is broader than the package: it's a comparison of
several ways to solve **stale navigation regions** (a sidebar,
breadcrumbs, or tab bar that doesn't reflect the page HTMX just swapped
in), of which `django-htmx-nav` is one — the most developed one, but not
the only one shown. See [Example Project](example_project.md) for the
full comparison and [Benchmarks](benchmarks.md) for what each approach
actually costs, in code and at runtime.

```{toctree}
:maxdepth: 2
:caption: Contents

quickstart
glossary
testing
debugging
example_project
benchmarks
nav_context_patterns
api
```

---

## Overview

Django 6 introduced native template partials (`{% partialdef %}`), allowing a single template to define both the full page layout and specific fragments swapped in by HTMX:

```html
{% extends 'base.html' %}

{% block content %}
{% partialdef content inline %}
  <div>My page content!</div>
{% endpartial %}
{% endblock %}
```

While partials solve single-fragment swapping, real-world web applications often face additional challenges:

1. **Header & Sidebar Synchronization:** Swapping `#content` leaves sidebars, breadcrumbs, and active navigation indicators out of sync unless out-of-band (OOB) fragments are rendered alongside.
2. **Browser History Management:** HTMX swaps should properly push URLs (`HX-Push-Url`) and set appropriate HTTP cache headers (`Vary: HX-Request`).
3. **HTMX Redirect Handling:** Standard HTTP 302 redirects cause HTMX to swap the target page into the DOM element instead of navigating the browser.

`django-htmx-nav` addresses these exact issues without adding heavy dependencies or requiring custom Django app registration. It isn't the only way to address them, though — a traditional multi-page app sidesteps the problem entirely by never partially swapping anything, and hand-written HTMX with manual OOB swaps addresses it without any package at all. The [example project](example_project.md) implements all three side by side, specifically so the trade-off is visible rather than asserted.

---

## Core Capabilities

- **`render_nav`**: Renders requested template partial blocks on HTMX requests, manages active navigation state, patches `Vary: HX-Request`, and appends extra OOB `Swap` fragments seamlessly.
- **`render_with_swaps`**: Renderer for views that need out-of-band swaps without partial/block resolution logic.
- **`Swap` (`Swap.delete`, `Swap.text`)**: Out-of-band fragment specification supporting template rendering, direct text content, and DOM element deletion (`hx-swap-oob="delete"`).
- **`make_shell_renderer`**: Encapsulates common page layouts (sidebar, header, breadcrumbs) into a clean renderer function so view functions remain uncluttered.
- **`make_shell_view_mixin`**: Class-Based View (CBV) integration for Django generic views (`DetailView`, `ListView`, `FormView`).
- **`assert_shell_parity` & `assert_shell_composition`**: Automated test utilities to verify navigation state consistency and HTML composition across full loads and HTMX swaps in CI.
