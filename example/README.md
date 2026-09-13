# Example Application & Reference Testbed

This directory contains a complete, runnable Django Helpdesk application designed to demonstrate `django-htmx-nav` patterns in a realistic, multi-region web application.

## What's in this Example?

The application implements a real-world Helpdesk workspace (Organizations, Projects, Kanban boards, Ticket details with subtabs, Multi-step ticket wizards, and Staff directories) across **8 distinct architectural paradigms**:

1. **`mpa`**: Traditional Django full-page reloads.
2. **`pure_htmx`**: Full HTML shells rendered on every boosted request.
3. **`vanilla_htmx_composite`**: Hand-written `hx-swap-oob` fragments for core regions.
4. **`vanilla_htmx_atomic`**: Hand-written OOB swaps for all regions with template branching.
5. **`htmx_nav_baseline`**: Minimal boilerplate using `make_shell_renderer`.
6. **`htmx_nav_composite`**: Direct `render_nav` calls with per-view `swaps=[...]`.
7. **`htmx_nav_atomic`**: Explicit multi-level swaps across every visual tier.
8. **`htmx_nav_declarative`**: Route-aware central registry decoupling navigation from views.

Every page includes an **Implementation Switcher** in the top-right navbar, allowing you to jump between these approaches on any screen and observe behavior, payload sizes, and DOM updates in real time.

## Quick Start (Run Locally in Seconds)

### 1. Install in Editable Mode

From the repository root, install the package and example dependencies:

```bash
pip install -e ".[example]"
```

### 2. Run Migrations & Seed Sample Data

```bash
python example/manage.py migrate
python example/manage.py seed_helpdesk
```

### 3. Start the Development Server

```bash
python example/manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

> **Prefer Docker?** Run `docker compose up dev` to mount local code with auto-reload enabled.

## Where to Look: Exploring Package Patterns

If you are evaluating `django-htmx-nav` for your own project, explore these key files:

| Pattern | Source File | What to Look For |
| :--- | :--- | :--- |
| **Reusable Shell Renderers** | [`example/htmx_nav_demo/views_baseline.py`](htmx_nav_demo/views_baseline.py) | How `make_shell_renderer` defines a shared list of `Swap`s once, keeping views identical to standard `render()`. |
| **Direct & Ad-Hoc Swaps** | [`example/htmx_nav_demo/views_composite.py`](htmx_nav_demo/views_composite.py) | Using `render_nav` with inline `swaps=[...]` for custom or single-view needs. |
| **Multi-Tier Navigation** | [`example/htmx_nav_demo/views_atomic.py`](htmx_nav_demo/views_atomic.py) | Granular swaps synchronizing sidebar, breadcrumbs, tabs, and subtabs simultaneously. |
| **Declarative Registry** | [`example/htmx_nav_demo/views_declarative.py`](htmx_nav_demo/views_declarative.py) | Decoupling navigation rules into a route-aware registry, keeping views exceptionally thin. |
| **Class-Based Views (CBVs)** | [`example/htmx_nav_demo/views_*.py`](htmx_nav_demo/) | Subclassing mixins generated via `make_shell_view_mixin(render_shell)`. |
| **Specialized Swaps** | [`example/htmx_nav_demo/views_*.py`](htmx_nav_demo/) | Usage of `Swap.delete` (instant DOM deletion), `Swap.text` (raw text/counts), and `has_messages`. |
| **Visual Swap Debugging** | [`example/config/settings.py`](config/settings.py) | `HTMX_NAV_DEBUG_SWAPS = True`, which highlights updated DOM regions with an animated pulse. |

## Directory Structure

```text
example/
├── config/              # Django settings, root URL routing, WSGI
├── frontpage/           # Landing page overview and architectural guide
├── benchmarks/          # Empirical metrics dashboards (ECharts + Alpine.js)
├── htmx_nav_demo/       # Reference implementations of django-htmx-nav patterns
├── mpa/                 # Reference implementation using traditional full-page reloads
├── core/                # Shared domain models, mock data generators, base templates
└── manage.py            # Django command-line entrypoint
```

## Running the Example Test Suite

The example project includes automated parity, composition, and smoke test suites:

```bash
# Run all example tests (~560 tests)
PYTHONPATH=example DJANGO_SETTINGS_MODULE=config.settings pytest example/
```

- **`test_shell_parity.py`**: Verifies that HTMX partial responses produce the exact same navigation context as full browser reloads.
- **`test_shell_composition.py`**: Verifies that rendered shells contain all required DOM markers and container IDs.
- **`test_variant_smoke.py`**: Smoke tests all 8 implementation families and orthogonal modifier axes (`+HS` / `hx-select`, `+M` / `idiomorph`).
