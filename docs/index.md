# Documentation

Welcome to the `django-htmx-nav` documentation.

This library provides lightweight primitives to synchronize multi-region navigation chrome (sidebars, breadcrumbs, badges, tabs) during HTMX requests while keeping the URL as the single source of truth.

---

## Documentation Roadmap

- **[Getting Started](quickstart.md):** 3-minute tutorial to get your first partial view and out-of-band swap working.
- **Topic Guides:**
  - **[Dynamic Targeting & Nested Navigation](guides/targeting.md):** Coordinate nested tabs, subtabs, and conditional swaps using the unified `Target` condition vocabulary.
  - **[Application Shells & Class-Based Views](guides/shells.md):** Eliminate repetitive boilerplate across 20+ views with `make_shell_renderer` and `make_shell_view_mixin`.
  - **[Out-of-Band Swaps Deep Dive](guides/swaps.md):** Learn how to use unwrapped templates, fast text updates (`Swap.text`), element deletion (`Swap.delete`), and flash messages (`has_messages`).
- **Operations & Testing:**
  - **[Visual Swap Debugging](debugging.md):** Highlight DOM elements with visual animations as they swap during development.
  - **[Testing](testing.md):** Write robust unit tests for your swaps and renderers with Django's test client.
- **Architecture & Reference:**
  - **[Settings](settings.md):** Configuration options for default partials and swap wrapping.
  - **[Example Project & Demo](example_project.md):** Overview of the reference Helpdesk application and sandbox.
  - **[API Reference](api/core.md):** Complete function and class signatures.
  - **<a href="../guide/">Architectural Guide</a>:** Conceptual deep dive comparing 3 implementation variants and empirical benchmarks.

```{toctree}
:maxdepth: 2
:caption: Getting Started
:hidden:

quickstart
example_project
```

```{toctree}
:maxdepth: 2
:caption: Topic Guides
:hidden:

guides/targeting
guides/shells
guides/swaps
```

```{toctree}
:maxdepth: 2
:caption: Operations & Testing
:hidden:

debugging
testing
```

```{toctree}
:maxdepth: 2
:caption: Reference
:hidden:

settings
glossary
api/core
api/targeting
api/shell
api/debugging
api/testing
```
