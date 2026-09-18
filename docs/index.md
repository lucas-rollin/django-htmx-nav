# Documentation

Welcome to the `django-htmx-nav` documentation.

This library provides lightweight primitives to synchronize multi-region navigation chrome (sidebars, breadcrumbs, badges, tabs) during HTMX requests while keeping the URL as the single source of truth.

## Getting Started

If you are new to `django-htmx-nav`, start here:

- **[Quickstart Guide](quickstart.md):** Step-by-step setup, template partials, `render_nav`, and reusable shells.
- **[Configuration & Settings](settings.md):** Available Django settings to customize defaults.
- **[Example Project & Demo](example_project.md):** Overview of the reference Helpdesk application, live sandbox, and source links.
- **<a href="../guide/">Architectural Guide</a>:** Conceptual deep dive into state drift solutions, pattern comparisons, and decision trees.

```{toctree}
:maxdepth: 2
:caption: Intro
:hidden:

quickstart
settings
example_project
glossary
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
:caption: API Reference
:hidden:

api/core
api/targeting
api/shell
api/debugging
api/testing
```
