# Benchmarks

[Example Project](example_project.md) lists what each approach *does*.
This page is what each one *costs* — quantified, not asserted — drawn
from the `example/benchmarks/` app.

This page is static; the live dashboard at `/benchmarks/` is not — it's
an interactive Alpine/ECharts explorer over the same data
(`example/benchmarks/README.md` covers running it locally). The numbers
below are a **pinned snapshot** (`example/benchmarks/data/reference_*.jsonl`,
run `reference-20260830`), the same one the app's own overview page
reads, so what's written here matches what you'd see live without
depending on you having a Django instance running.

```{admonition} Read this as directional, not authoritative
:class: note
One collection run, on one machine. Client-side timing in particular is
hardware-dependent — treat the *relative ordering* between approaches as
the signal, the exact millisecond values as noise. See
`example/benchmarks/README.md` for the four collector categories and how
to run your own.
```

## What's measured

| Category | What it captures |
| --- | --- |
| **Code complexity / DX** | Lines of view code, lines of nav-concern code specifically (`Swap(...)`, `render_nav(...)`, `targeting(...)`, ...), rendered `hx-*` HTML attribute count. |
| **Server performance** | Render time (median/p95), DB query count, and how many `Swap.render()` calls a single request triggers. |
| **Payload size** | Actual on-wire (gzip'd) response bytes, via a real HTTP request against a running dev server — not the Django test client, which never applies `GZipMiddleware`. |
| **Client performance** | Time from HTMX request start to a settled, painted DOM (`htmx:beforeRequest` → post-`afterSettle` double-`requestAnimationFrame`), plus DOM mutation/node counts. |

## Results

Averaged across the base (no `hx-select`/`morph`) variant of each
family — the axis flags below change *how* a DOM update is delivered,
not what stays in sync, so they're left out here for readability. See
the live `/benchmarks/*` dashboards for the full axis breakdown.

### Code complexity

| Family | Views LOC | Nav-concern LOC | Rendered `hx-*` attrs |
| --- | ---: | ---: | ---: |
| mpa | 434 | 0 | 0 |
| pure_htmx | 434 | 0 | 6 |
| vanilla_htmx_composite | 460 | 0 | 7 |
| vanilla_htmx_atomic | 465 | 0 | 14 |
| htmx_nav_baseline | 525 | 21 | 7 |
| htmx_nav_composite | 574 | 21 | 7 |
| htmx_nav_declarative | **305** | 43 | 12 |
| htmx_nav_atomic | 661 | 44 | 12 |

`htmx_nav_declarative` has the lowest views-module LOC of *any* family,
including plain `mpa` — but its nav-concern total is close to
`htmx_nav_atomic`'s. The code didn't shrink, it moved into a shared,
reusable registry module (counted separately as "extra modules LOC" in
the live dashboard) instead of living inline in every view.

### Server performance

| Family | Render time, median (ms) | DB queries (avg) | Swaps rendered (avg) |
| --- | ---: | ---: | ---: |
| vanilla_htmx_atomic | 6.15 | 4.5 | 0 |
| vanilla_htmx_composite | 6.19 | 4.5 | 0 |
| htmx_nav_baseline | 6.35 | 4.5 | 1.33 |
| htmx_nav_composite | 6.40 | 4.5 | 1.33 |
| htmx_nav_atomic | 6.49 | 4.5 | 1.75 |
| htmx_nav_declarative | 6.71 | 4.5 | 1.75 |
| mpa | 6.82 | 4.5 | 0 |
| pure_htmx | 7.15 | 4.5 | 0 |

DB query count is flat at 4.5 across every family regardless of how
many OOB fragments a response renders — nav context is built once per
request (`cache_on_request`) and reused across every `Swap`, not
re-fetched per fragment. The full render-time spread across every
family here is well under a millisecond, inside normal repeat-to-repeat
noise for this scenario set.

### Payload size

| Family | Transfer bytes, gzip'd (avg) |
| --- | ---: |
| vanilla_htmx_atomic | 4195 |
| htmx_nav_atomic | 4218 |
| htmx_nav_declarative | 4219 |
| vanilla_htmx_composite | 4223 |
| htmx_nav_baseline | 4262 |
| htmx_nav_composite | 4266 |
| mpa | 6140 |
| pure_htmx | 6235 |

The ~32% drop from `mpa`/`pure_htmx` to every partial-rendering
approach is the value of partial rendering itself — every htmx-aware
family, package or hand-written, lands in the same ~4.2KB range.
`django-htmx-nav` doesn't add that win, it just avoids hand-rolling the
OOB fragments to keep it.

### Client performance

| Family | HTMX processing (ms) |
| --- | ---: |
| htmx_nav_declarative | 51.0 |
| vanilla_htmx_atomic | 52.5 |
| htmx_nav_atomic | 53.3 |
| htmx_nav_baseline | 55.3 |
| vanilla_htmx_composite | 55.6 |
| htmx_nav_composite | 55.8 |
| pure_htmx | 65.8 |

Time from `htmx:beforeSwap` to `htmx:afterSettle` — DOM swap/morph and
settle, excluding network/server time. `mpa` is omitted: it never fires
htmx events, so there's nothing on this axis to measure (the live
client dashboard shows its full-navigation paint-timing fallback
separately instead).

## Reading this alongside Example Project

None of this ranks the families — it's meant to make the
[Example Project](example_project.md) table's trade-offs concrete rather
than replace them. `pure_htmx` "loses" on payload by design, not by
accident: it exists to isolate whether the savings above come from
partial rendering or from `django-htmx-nav` specifically (they come from
partial rendering). `htmx_nav_atomic` has the most views-module code on
purpose, as the maximally explicit reference implementation, not because
the declarative pattern in `htmx_nav_declarative` was somehow
unavailable to it.

## Refreshing these numbers

The tables above are hand-transcribed from
`example/benchmarks/data/reference_*.jsonl`, which is a deliberately
pinned snapshot — see `example/benchmarks/data/README.md`. If you
refresh it, update this page's tables and captions in the same change;
a stale table next to fresh reference data is worse than no table at all.
