# Example Project

The [`example/`](https://github.com/lucas-rollin/django-htmx-nav/tree/main/example) directory contains a fully functional Django helpdesk app (organizations, projects, tickets, wizards, Kanban board). It demonstrates how to solve **stale navigation regions** across different HTMX and MPA approaches.

## Approaches Overview

All approaches share the same app and URL structure ([`example/core/navigation/registry.py`](https://github.com/lucas-rollin/django-htmx-nav/blob/main/example/core/navigation/registry.py)), allowing direct comparison:

| Family | Description | Trade-off |
| --- | --- | --- |
| **`mpa`** | Plain Django views, full page reloads. | No staleness, but incurs full page loads (~6.1KB) every click. |
| **`pure_htmx`** | Same MPA views wrapped in `hx-boost`. | Adds async UX, but still sends full pages (no payload reduction). |
| **`vanilla_htmx_composite`** | Manual OOB swaps for sidebars/breadcrumbs using `{% include %}`. | No package required, but limited scalability for complex tabs. |
| **`vanilla_htmx_atomic`** | Manual OOB swaps for *all* regions using template conditionals. | Full coverage, but sync logic is baked directly into templates. |
| **`htmx_nav_baseline`** | Simple package using `make_shell_renderer` with fixed swaps. | Minimal boilerplate for standard setups. |
| **`htmx_nav_composite`** | Direct `render_nav` calls per view with inline swaps. | Highly explicit, but repeats setup across views. |
| **`htmx_nav_atomic`** | Explicit `render_nav` covering every region in every view. | Maximum explicitness; acts as a reference implementation. |
| **`htmx_nav_declarative`** | Centralized `NAV_ENTRIES` registry with thin view handlers. | Lowest view code volume, cleanly separating navigation concerns. |

> **Variants:** Each family can combine with **`hx-select`** (client-side extraction) or **`morph`** (DOM morphing via idiomorph). See [`example/core/navigation/variants.py`](https://github.com/lucas-rollin/django-htmx-nav/blob/main/example/core/navigation/variants.py).

## Verified Quality & Tests

Every approach is verified using a shared test suite (`example/core/tests/`):

* **`test_shell_parity.py`**: Ensures identical nav context across full reloads and HTMX swaps.
* **`test_shell_composition.py`**: Validates correct HTML nesting and structure.
* **`test_variant_smoke.py`**: Confirms all family/axis combinations return valid status codes.

For detailed metrics, see **Benchmarks**.

## Quick Start

```bash
pip install -e ".[example]"
python example/manage.py runserver
```

Open [`http://127.0.0.1:8000/`](http://127.0.0.1:8000/) and use the navbar dropdown to switch between implementation approaches on the fly.
