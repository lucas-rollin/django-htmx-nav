# Example Project

The `django-htmx-nav` repository includes a fully functional sample Django application located in the [`example/`](https://github.com/lucas-rollin/django-htmx-nav/tree/main/example) directory. It's the primary way this project explains itself: not just "here's a package," but "here's a problem, here are several ways to solve it, and here's what each one actually costs."

---

## The problem: stale navigation regions

Django 6's native `{% partialdef %}` solves swapping a single content
region over HTMX. It doesn't solve what happens *around* that region.
Swap `#content` on its own and anything outside it — an active sidebar
link, a breadcrumb trail, a tab bar's highlighted tab — keeps showing
whatever it showed before the swap, because HTMX only touched the one
element it targeted. That's the "stale navigation" this project is
about: not a rendering bug, a *synchronization* problem between however
many regions a page has and however many ways a user can arrive at it
(full reload, a swap into the page shell, a swap into just one region).

There's more than one reasonable way to solve that. This project builds
the same helpdesk demo app — organizations, projects, tickets, a
multi-step wizard, a Kanban board — against every approach it wants to
compare, so the comparison is between real, working code rather than
prose claims.

## Purposes

1. **Demonstration & Reference:** an interactive working demo of complex multi-region navigation (sidebars, breadcrumbs, multi-step wizards, and tabbed workspaces), for each approach below.
2. **Integration Testbed:** a real Django app for automated parity/composition testing (`assert_shell_parity`, `assert_shell_composition`) and manual HTMX testing.
3. **Architectural Comparison:** the same app, built multiple times, to make the trade-offs between approaches visible instead of asserted. See [Benchmarks](benchmarks.md) for what each one costs in code volume and at runtime.

---

## The approaches

Every approach lives under its own Django app / URL prefix
(`example/core/navigation/registry.py` wires them all up), so the same
org/project/ticket can be reached at e.g. `/mpa/orgs/.../` or
`/htmx-nav/declarative/orgs/.../` and should look and behave the same.

| Family | What it does | The trade-off |
|---|---|---|
| **`mpa`** | Plain Django views, full page reloads. No HTMX at all. | Staleness can't happen — there's nothing partial to go stale. Costs a full page (~6.1KB gzipped here) and a full navigation on every click. |
| **`pure_htmx`** | The *same* MPA views, wrapped only in `hx-boost`. | Async navigation UX from `hx-boost`, but every response is still the full page — no partial-rendering payload win, because nothing is actually partial. Confirms the payload savings below come from partials, not from any particular sync strategy. |
| **`vanilla_htmx_composite`** | Hand-written OOB swaps, but only for sidebar + breadcrumbs. One shell template per page (`_project.html`, `_ticket.html`, ...) wraps the partial in `hx-swap-oob` `<div>`s. | No package, no abstraction — just HTMX and Django's `{% include %}`. Tabs/subtabs aren't independently synced, so a tab-only interaction just re-renders through `#content` instead of a targeted OOB fragment. Doesn't scale past a couple of always-synced regions without duplicating the shell-template pattern per page. |
| **`vanilla_htmx_atomic`** | Hand-written OOB swaps for *every* region (sidebar, breadcrumbs, tabs, subtabs, steps). | Same "no package" honesty, full region coverage — at the cost of `{% if request\|hx_target:"..." %}...{% elif %}...{% else %}` branching baked directly into each shell template to decide which fragments a given `HX-Target` needs. Correct, but the sync logic lives in template conditionals rather than anywhere more testable. |
| **`htmx_nav_baseline`** | `make_shell_renderer` with a *fixed* list of Swaps (sidebar, breadcrumbs), default `#content` partial. | The simplest package-based option, matching `vanilla_htmx_composite`'s scope. One `render_shell` closure instead of N hand-written shell templates. |
| **`htmx_nav_composite`** | `render_nav(..., swaps=[...])` called directly per view, building sidebar/breadcrumb `Swap`s inline each time. | Same scope as baseline, but without the centralizing closure — every view rebuilds its own `Swap`s, which is why it has more views-module LOC than baseline for identical coverage. Useful as the "no indirection, see exactly what's being called" version. |
| **`htmx_nav_atomic`** | `render_nav` with *every* Swap (sidebar, breadcrumbs, tabs, subtabs, steps) built explicitly, inline, in every view. | Full region coverage, most explicit — and the most views-module code of any approach here on purpose: it's the reference implementation for "what does `render_nav` actually do," not the recommended day-to-day pattern. |
| **`htmx_nav_declarative`** | A `NAV_ENTRIES` registry (`registry_declarative.py`) resolved once per request via `cache_on_request`; views call a thin `render_shell` and mostly just supply page content. | Full region coverage with the *fewest* views-module lines of any approach — even below `mpa`. The nav-concern code didn't disappear, it moved into a separate, reusable, independently testable module. Worth it once enough views share nav structure; overhead for a two-page app. |

Each family can additionally be explored along two independent,
orthogonal axes that change *how* a DOM update is applied, not *what*
stays in sync: `hx-select` (client-side fragment extraction instead of
server-built OOB) and `morph` (idiomorph DOM morphing instead of a full
`innerHTML`/`outerHTML` swap). See `example/core/navigation/variants.py`
for how these compose with the families above.

## How "pros and cons" get checked, not just asserted

Every family is exercised by the same shared test suite in
`example/core/tests/`:

- `test_shell_parity.py` — the nav-relevant context (active sidebar
  item, breadcrumb labels, active tab, ...) must be identical whether a
  page is reached via full reload, a page-level HTMX swap, or a
  tab-level HTMX swap, for every family.
- `test_shell_composition.py` — beyond matching context, the actual
  rendered HTML has to nest correctly (a tab-swap response really does
  fit inside what the full page renders for that region).
- `test_variant_smoke.py` / `test_variant_registry_symmetry.py` —
  every family/axis combination 200s, and the URL-prefix-stripping the
  in-app variant switcher relies on holds for every combination.

That's what makes the comparison in [Benchmarks](benchmarks.md)
meaningful: every approach being measured is independently verified to
solve the staleness problem correctly first, not just quickly or
concisely.

## Installation & Running

```bash
pip install -e ".[example]"
python example/manage.py runserver
```

Open `http://127.0.0.1:8000/` — the navbar's dropdown switches between
every family/axis combination on the page you're currently viewing.
