# Example Project

The [`example/`](https://github.com/lucas-rollin/django-htmx-nav/tree/main/example) directory contains a fully functional Django Helpdesk application (organizations, projects, Kanban boards, ticket detail views with subtabs, multi-step ticket creation wizards, and staff directories).

It serves as both a runnable reference testbed and an empirical laboratory demonstrating how to solve **stale navigation regions (state drift)** across different architectural paradigms.

## Live Deployment & Interactive Testbed

The example project is deployed and accessible online:

- **{demo}`Live Helpdesk Testbed <htmx-nav/baseline/>`:** Interact with the live application, switch between all 8 implementation families, and toggle `hx-select` or `idiomorph` on the fly.
- **{live}`Benchmark Dashboard <benchmarks/>`:** Compare empirical payload distributions, server render times, and DOM churn across all variants.
- **{live}`Architectural Guide <guide/>`:** Read the comprehensive architectural breakdown of hypermedia state synchronization.

## Implementation Approaches Compared

All 8 approaches implement the exact same Helpdesk application screens, share identical URL structures, and operate over the same Django database models ([`example/core/navigation/registry.py`](https://github.com/lucas-rollin/django-htmx-nav/blob/main/example/core/navigation/registry.py)). This enables rigorous apples-to-apples comparison:

| Family / Live Route | Description | Trade-offs & Performance |
| :--- | :--- | :--- |
| **`mpa`**<br>{demo}`/mpa/ <mpa/>` | Plain Django views with standard browser full-page reloads. | Zero stale navigation, but incurs full HTML transfer (~6.1 KB) and white-flash reloads on every click. |
| **`pure_htmx`**<br>{demo}`/htmx/ <htmx/>` | Same MPA views wrapped in `hx-boost="true"` with full-page rendering. | Adds smooth SPA-like transitions, but still transfers the entire HTML document on every navigation. |
| **`vanilla_htmx_composite`**<br>{demo}`/vanilla-htmx/composite/ <vanilla-htmx/composite/>` | Hand-written `hx-swap-oob` fragments for core regions (sidebar/breadcrumbs) via `{% include %}`. | Eliminates package dependencies, but requires manual OOB wrapper boilerplate in views and templates. |
| **`vanilla_htmx_atomic`**<br>{demo}`/vanilla-htmx/atomic/ <vanilla-htmx/atomic/>` | Hand-written OOB swaps for *all* navigation regions using defensive template conditionals. | High fidelity, but clutters HTML templates with fragile `{% if request.htmx ... %}` branching. |
| **`htmx_nav_baseline`**<br>{demo}`/htmx-nav/baseline/ <htmx-nav/baseline/>` | Uses `make_shell_renderer` with a fixed list of `Swap` primitives for common chrome. | Minimal boilerplate for standard applications with uniform shell layouts. |
| **`htmx_nav_composite`**<br>{demo}`/htmx-nav/composite/ <htmx-nav/composite/>` | Direct `render_nav` calls per view with inline `swaps=[...]` declarations. | Highly explicit and flexible, but view authors must remember to supply swaps for shared regions. |
| **`htmx_nav_atomic`**<br>{demo}`/htmx-nav/atomic/ <htmx-nav/atomic/>` | Granular `render_nav` with explicit swaps for every level (sidebar, breadcrumbs, tabs, subtabs). | Maximum explicitness; serves as a comprehensive reference implementation. |
| **`htmx_nav_declarative`**<br>{demo}`/htmx-nav/declarative/ <htmx-nav/declarative/>` | Route-aware central registry resolving navigation dependencies automatically. | Cleanest views with lowest line count, isolating navigation concerns from business logic. |

### Orthogonal Client-Side Axes

Each HTMX family can also be toggled with two client-side modifier axes via the implementation switcher in the top-right navbar:

- **`+HS` (`hx-select`)**: The server returns a larger fragment and HTMX extracts the target portion client-side.
- **`+M` (`idiomorph`)**: HTMX morphs the target DOM tree instead of replacing innerHTML, preserving active element focus, scroll positions, and CSS transitions.

## Empirical Benchmark Findings

Reference benchmark runs across all Helpdesk routes demonstrate:

1. **Payload Compression (70–80% Savings):** Partial HTMX navigation reduces wire transfer sizes from ~6.1 KB (MPA) down to **~1.2 KB** per request, cutting bandwidth and parse overhead significantly.
2. **Negligible Server Overhead (<0.5 ms):** Generating and auto-wrapping out-of-band swaps in Python adds less than half a millisecond of server execution time.
3. **Flat Database Query Counts (~4.5 avg):** Using request-scoped memoization (`cache_on_request`) prevents duplicate database queries when generating sidebar, breadcrumb, and tab contexts in the same request.

## Automated Quality Verification

The example suite contains automated verification tests (`example/core/tests/` and `example/htmx_nav_demo/tests/`):

- **`test_shell_parity.py`:** Enforces strict parity between full-page reloads and HTMX partial swaps using `assert_shell_parity`. Navigating via HTMX must yield the exact same active items, links, and text as a fresh browser load.
- **`test_shell_composition.py`:** Uses `assert_shell_composition` to verify that shell fragments contain all required DOM markers and container IDs.
- **`test_variant_smoke.py`:** Smoke-tests every single route across all 8 implementation families and modifier axes.
- **`test_variant_registry_symmetry.py`:** Ensures complete URL namespace symmetry across all variants.

## Running the Example Locally

The example application can be run locally on your host machine or inside Docker. Complete development workflow documentation, testing instructions, and directory structures are maintained in the [example project README](https://github.com/lucas-rollin/django-htmx-nav/blob/main/example/README.md).

```bash
# Quick start with Docker (mounts source with hot reload):
docker compose up dev

# Or using native Python:
pip install -e ".[example]"
python example/manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) and use the top-right navbar dropdown to switch between implementations.
