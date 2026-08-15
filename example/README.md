# Example Application & Integration Testbed

This directory contains a complete sample Django application demonstrating `django-htmx-nav` in a realistic web application context.

---

## Purpose

The example project is designed for three main purposes:

1. **Interactive Demo:** Demonstrates real-world UI patterns such as multi-region navigation (sidebars, breadcrumbs, headers), active-state highlighting, multi-step forms/wizards, and nested tabbed workspaces.
2. **Integration Testbed:** Serves as a full-stack Django environment for validating `django-htmx-nav` behaviors (partial block resolution, OOB swaps, `Vary` headers, redirects) against real browser requests.
3. **Implementation Playground & Experiment:** Enables side-by-side comparison of three common web application architectural approaches:
   - **Multi-Page Application (MPA):** Traditional full-page reloads.
   - **Vanilla HTMX:** Manual `HX-Request` checking, ad-hoc partial rendering, and manual out-of-band swap construction.
   - **`django-htmx-nav`:** Declarative partial specifications, reusable shell renderers (`make_shell_renderer`), and Class-Based View mixins (`make_shell_view_mixin`).

---

## Installation & Running

### 1. Install Dependencies

From the repository root, install `django-htmx-nav` in editable mode with the `example` extra dependencies (`Faker`):

```bash
pip install -e ".[example]"
```

### 2. Start the Development Server

Run the Django development server:

```bash
python example/manage.py runserver
```

Open your browser and navigate to `http://127.0.0.1:8000/`.

---

## Project Structure

```
example/
├── config/              # Django project configuration (settings, root URLs, WSGI)
├── core/                # Shared domain models, mock data generators (Faker), base templates
├── htmx_nav_demo/       # Interactive demo app using django-htmx-nav patterns
├── mpa/                 # Reference implementation using traditional MPA full-page reloads
├── static/              # Static assets and CSS stylesheets
└── manage.py            # Django command-line entrypoint
```

### Key Components

- **`config/settings.py`**: Configured with `HTMX_NAV_DEBUG_SWAPS = True` for visual swap debugging.
- **`core/`**: Defines workspace models, projects, tickets, and employees populated dynamically with mock data.
- **`htmx_nav_demo/`**: Demonstrates `render_nav`, `make_shell_renderer`, `make_shell_view_mixin`, `Swap.text`, and `Swap.delete` across complex nested views.
- **`mpa/`**: Demonstrates the baseline Multi-Page Application workflow for direct comparison.

---

## Planned Work & Future Experiments

- [ ] Add vanilla HTMX variant views (`example/vanilla_htmx/`) to explicitly benchmark code lines and maintenance complexity against `django-htmx-nav`.
- [ ] Add interactive toggle in the UI header to seamlessly switch execution modes between MPA, Vanilla HTMX, and `django-htmx-nav`.
- [ ] Expand E2E test suites comparing client-side performance and network payload sizes across all three architectural variants.
