# django-htmx-nav

**Server-driven, SPA-like user experiences with MPA simplicity in Django.**

`django-htmx-nav` provides lightweight helpers for handling HTMX partial renders, out-of-band (OOB) updates, shell layout rendering, and HTMX-safe redirects in Django projects.

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

`django-htmx-nav` addresses these exact issues without adding heavy dependencies or requiring custom Django app registration.

---

## Core Capabilities

- **`render_htmx`**: Renders only requested partial blocks on HTMX requests, manages `HX-Push-Url`, and appends extra OOB `Swap` fragments seamlessly.
- **`make_shell_renderer`**: Encapsulates common page layouts (sidebar, header, breadcrumbs) into a clean renderer function so view functions remain uncluttered.
- **`htmx_redirect`**: Sends `HX-Redirect` response headers on HTMX requests while performing normal HTTP redirects for standard page reloads.
- **`make_shell_view_mixin`**: Class-Based View (CBV) integration for Django generic views (`DetailView`, `ListView`, `FormView`).
- **`assert_shell_parity`**: Automated test utility to verify navigation state consistency across full loads and HTMX interactions in CI.

---

## Documentation Guide

Explore the documentation sections to get started:

- [**Quickstart**](quickstart.md): Step-by-step guide to installing and integrating `django-htmx-nav` in your Django app.
- [**API Reference / Docstrings**](api.md): Detailed parameter and return type reference for functions, classes, and helpers.
- [**Architectural Patterns**](pattern/context_processor_and_templatetags.md):
    - [Context Processor & Template Tags](pattern/context_processor_and_templatetags.md)
    - [Centralized Navigation Registry](pattern/registry_pattern.md)
