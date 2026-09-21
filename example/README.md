# Example Application & Reference Testbed

This directory contains a complete, runnable Django Helpdesk application designed to demonstrate `django-htmx-nav` patterns and compare them against traditional multi-page architectures and vanilla HTMX techniques.

## Quickstart: Running Locally

You can run the example project directly on your host machine or in an isolated Docker container.

### Option A: Without Docker (Local Virtualenv)

```bash
# 1. From the repository root, install the package and example dependencies:
uv sync --group example

# 2. Start the development server:
uv run python example/manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

### Option B: With Docker (Containerized)

```bash
# Development environment with local directory mount and hot reload:
docker compose up dev

# Or simulate production deployment (Gunicorn + WhiteNoise static serving):
docker compose up --build demo
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

## Exploring the 8 Implementation Strategies

Every screen in the Helpdesk application (Organizations, Projects, Kanban boards, Ticket details with subtabs, and Staff directories) is implemented across **8 distinct architectural paradigms**:

| Family / Namespace | Source File | Description |
| :--- | :--- | :--- |
| **`mpa`** | [`example/mpa/views.py`](mpa/views.py) | Traditional Django multi-page views with full-page browser reloads. |
| **`pure_htmx`** | [`example/mpa/views.py`](mpa/views.py) | Full HTML shells returned on every boosted request (`hx-boost="true"`). |
| **`vanilla_htmx_composite`** | [`example/vanilla_htmx_composite/views.py`](vanilla_htmx_composite/views.py) | Hand-written `hx-swap-oob` fragments for core regions (sidebar/breadcrumbs). |
| **`vanilla_htmx_atomic`** | [`example/vanilla_htmx_atomic/views.py`](vanilla_htmx_atomic/views.py) | Hand-written OOB swaps for all visual regions using template conditionals. |
| **`htmx_nav_baseline`** | [`example/htmx_nav_demo/views_baseline.py`](htmx_nav_demo/views_baseline.py) | Minimal boilerplate using `make_shell_renderer` with shared `Swap` definitions. |
| **`htmx_nav_composite`** | [`example/htmx_nav_demo/views_composite.py`](htmx_nav_demo/views_composite.py) | Direct `render_nav` calls per view with inline `swaps=[...]` declarations. |
| **`htmx_nav_atomic`** | [`example/htmx_nav_demo/views_atomic.py`](htmx_nav_demo/views_atomic.py) | Explicit multi-level swaps across every visual tier (sidebar, breadcrumbs, tabs, subtabs). |
| **`htmx_nav_declarative`** | [`example/htmx_nav_demo/views_declarative.py`](htmx_nav_demo/views_declarative.py) | Route-aware central registry resolving navigation dependencies automatically. |

> **Interactive Switcher:** Use the dropdown in the top-right navbar of any page to switch between these implementations in real time and observe payload differences and DOM updates.

## Directory Structure

```text
example/
├── config/              # Django settings, root URL routing, WSGI/ASGI
├── core/                # Shared domain models, mock data generators, base templates
├── frontpage/           # Showcase landing page, architectural guide, and SEO views
├── benchmarks/          # Empirical metrics dashboards and collection harness
├── htmx_nav_demo/       # Reference implementations of django-htmx-nav patterns
├── mpa/                 # Reference implementation using traditional full-page reloads
├── vanilla_htmx_composite/  # Vanilla HTMX implementation with composite OOB swaps
├── vanilla_htmx_atomic/     # Vanilla HTMX implementation with atomic OOB swaps
├── sandbox/             # Small scale package tests
└── manage.py            # Django management command entrypoint
```

## Running the Example Test Suite

The test suite covers parity between full reloads and HTMX partials, shell composition, and smoke-testing across all variant axes:

```bash
# Run all example tests
uv run --group test pytest example/
```

- **`test_shell_parity.py`**: Asserts that HTMX partial navigation produces the exact same active items, links, and navigation state as a direct full-page browser reload.
- **`test_shell_composition.py`**: Asserts that rendered shells contain all expected container targets and DOM markers.
- **`test_variant_smoke.py`**: Smoke tests all routes across all 8 variants and orthogonal modifier axes (`+HS` / `hx-select`, `+M` / `idiomorph`).

## Related Guides & Resources

- **[Benchmark Suite & Experiments](benchmarks/README.md)**: Guide to running automated Playwright and server-side metrics collections locally or via Docker.
- **[Maintainer Deployment Guide](../.github/DEPLOYMENT.md)**: Production deployment instructions for containerized hosting and static pages freeze.
- **[Sphinx Documentation](https://lucas-rollin.github.io/django-htmx-nav/docs/)**: In-depth API reference and guides.
