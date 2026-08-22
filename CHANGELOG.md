## 0.3.1 — 2026-08-15

### Added
- **`htmx_nav.targeting`**:
    - `has_messages`: Predicate for `Swap.include_if` that returns True if there are pending Django messages.

### Changed
- **`htmx_nav.shell`**:
    - `make_shell_renderer`: Changed to be a simple wrapper around `render_nav` using Swaps instead of a template shell.

## 0.3.0 — 2026-08-15

### Added
- **`htmx_nav.swaps`**:
    - `Swap`: Added `include_if` parameter and `skip_if_target_in` helper for declarative, conditional OOB swap rendering based on incoming HTMX targets.
    - `Swap`: Added `delete` and `text` class methods for convenience.
    - Added `debug-swaps.css` and a toggleable setting to visually highlight swap elements during execution.
- **`htmx_nav.shortcuts`**:
    - Added native `title` support to `render_htmx` (and `make_shell_renderer`), automatically setting the `HX-Title` header on HTMX requests and injecting a `<title>` OOB snippet when appropriate.
- **`htmx_nav.testing`**:
    - Introduced testing utilities to verify context parity and rendered template output across standard and HTMX requests.
- **Docs & Tooling**:
    - Initialized reference example project.
    - Added **Ruff** and **djLint** for linting and formatting.

### Changed
- **`htmx_nav.responses`**:
    - Split module into smaller files to improve maintainability.
- **Docs & Tooling**:
    - Migrated documentation build from MkDocs to **Sphinx**.
    - Fixed typos across docstrings and project documentation.

### Removed
- **`htmx_nav.shortcuts`**:
    - **[BREAKING]** Removed automatic `HX-Push-Url` handling from `render_htmx`, shifting URL history control back to the view layer.

## 0.2.0 — 2026-07-29

- **`htmx_nav.responses`**:
    - Removed `htmx_redirect` (redundant with `django_htmx` HTTP tools).
    - Enhanced `make_shell_renderer` to support robust intra-page navigation (e.g., tabs) via a 3-path check: full page render, page container target swaps, and component-level target swaps.
- **Documentation & Quality**:
    - Cleaned up docstrings and added comprehensive **MkDocs Material** documentation with automated `mkdocstrings` API reference generation.

## 0.1.0 — Initial extraction

- `htmx_nav.responses`: `render_htmx`, `Oob`, `make_shell_renderer`, `htmx_redirect`, `HX-Push-Url`/`Vary: HX-Request` handling.
- `htmx_nav.helpers`: `reverse_maybe`, `cache_on_request`.
- `htmx_nav.views`: `make_shell_view_mixin`.