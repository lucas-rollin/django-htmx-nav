# django-htmx-nav

**Server-driven, SPA-like user experiences with MPA simplicity in Django.**

`django-htmx-nav` provides lightweight helpers for handling HTMX partial renders, out-of-band (OOB) updates, shell layout rendering, and HTMX-safe redirects in Django projects.

```{toctree}
:maxdepth: 2
:caption: Contents

quickstart
testing
example_project
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

`django-htmx-nav` addresses these exact issues without adding heavy dependencies or requiring custom Django app registration.

---

## Core Capabilities

- **`render_nav`**: Renders requested template partial blocks on HTMX requests, manages active navigation state, patches `Vary: HX-Request`, and appends extra OOB `Swap` fragments seamlessly.
- **`render_with_swaps`**: Renderer for views that need out-of-band swaps without partial/block resolution logic.
- **`Swap` (`Swap.delete`, `Swap.text`)**: Out-of-band fragment specification supporting template rendering, direct text content, and DOM element deletion (`hx-swap-oob="delete"`).
- **`make_shell_renderer`**: Encapsulates common page layouts (sidebar, header, breadcrumbs) into a clean renderer function so view functions remain uncluttered.
- **`make_shell_view_mixin`**: Class-Based View (CBV) integration for Django generic views (`DetailView`, `ListView`, `FormView`).
- **`assert_shell_parity` & `assert_shell_composition`**: Automated test utilities to verify navigation state consistency and HTML composition across full loads and HTMX swaps in CI.
