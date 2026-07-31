# django-htmx-nav

**Server-driven, SPA-like user experiences with MPA simplicity in Django.**

`django-htmx-nav` provides lightweight helpers for handling HTMX partial renders, out-of-band (OOB) updates, shell layout rendering, and HTMX-safe redirects in Django projects.

```{toctree}
:maxdepth: 2
:caption: Contents

quickstart
api
pattern/context_processor_and_templatetags
pattern/registry_pattern
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

`django-htmx-nav` addresses these exact issues without adding heavy dependencies or requiring custom Django app registration.

---

## Core Capabilities

- **`render_htmx`**: Renders only requested partial blocks on HTMX requests, manages `HX-Push-Url`, and appends extra OOB `Swap` fragments seamlessly.
- **`make_shell_renderer`**: Encapsulates common page layouts (sidebar, header, breadcrumbs) into a clean renderer function so view functions remain uncluttered.
- **`make_shell_view_mixin`**: Class-Based View (CBV) integration for Django generic views (`DetailView`, `ListView`, `FormView`).
- **`assert_shell_parity`**: Automated test utility to verify navigation state consistency across full loads and HTMX interactions in CI.
