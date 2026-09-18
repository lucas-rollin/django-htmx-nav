# Glossary

Terms used throughout these docs and the codebase, defined precisely
because several of them share a word with an unrelated concept nearby.

## partial

The main content selected for a request, either a Django 6 native
`{% partialdef %}` block (`"#name"`), or a standalone template path.
Set via `render_nav(partial=...)` / `PartialSpec`. This matches
Django's own term for `{% partialdef %}`/`{% partial %}`.

## Swap

The `htmx_nav.Swap` dataclass: an additional HTML fragment delivered
alongside the main partial on an HTMX request, via out-of-band (OOB)
delivery or an `<hx-partial>` wrapper. Distinguish from:

- **swap** (lowercase, unqualified) — HTMX's general term for any DOM
  update, used only in an HTMX-general sense in these docs.
- **OOB swap** — a `Swap` rendered with `wrap="oob"` (the default):
  `<div id="..." hx-swap-oob="...">`.
- **`<hx-partial>` swap** — a `Swap` rendered with `wrap="hx-partial"`:
  `<hx-partial hx-target="#..." hx-swap="...">`. Named for the HTML
  element it emits, unrelated to "partial" above.

## target_id

The DOM element id a `Swap` is delivered to. The `id="..."` /
`hx-target="#..."` value in its rendered wrapper.

## HX-Target / htmx_target_is() / targeting()

`HX-Target` is the *request* header attribute HTMX sends and specifies
which DOM element will receive the partial. `htmx_target_is(request, "foo")`
/ `targeting("foo")` read *that* header.

## shell / shell renderer

A `ShellRenderer` (built by `make_shell_renderer`) always includes a
fixed set of navigational `Swap`s (sidebar, breadcrumbs, etc.) chosen
by request. "Shell" refers to that fixed set plus its wrapping renderer,
not any single template file.

## variant

Example-project-only term: one of the 8 full implementations under
`example/` being compared (`mpa`, `vanilla_htmx_*`, and `htmx_nav_*`).
Not used anywhere in the `htmx_nav` package itself.
