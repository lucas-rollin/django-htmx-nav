# Example Project

The `django-htmx-nav` repository includes a fully functional sample Django application located in the [`example/`](https://github.com/lucas-rollin/django-htmx-nav/tree/main/example) directory.

---

## Overview

The example project serves three primary purposes:

1. **Demonstration & Reference:** Provides an interactive working demo of complex multi-region navigation (sidebars, breadcrumbs, multi-step wizards, and tabbed workspaces).
2. **Integration Testbed:** Acts as a real-world Django app for manual and automated integration testing across HTMX interactions.
3. **Architectural Comparison:** Serves as an experimental playground comparing three distinct implementation approaches side-by-side:
   - **Multi-Page Application (MPA):** Standard Django views and full page reloads.
   - **Vanilla HTMX:** Basic partial rendering and manually constructed out-of-band and hx-select swaps.
   - **`django-htmx-nav`:** Declarative partial specs, shell renderers (`make_shell_renderer`), and CBV mixins (`make_shell_view_mixin`).
