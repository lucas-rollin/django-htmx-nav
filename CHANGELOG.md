## 0.3.1 — 2026-08-11

- Restructured project for maintainability.
- **`htmx_nav.swaps`**:
    - Added `delete` and `text` class methods to `Swap` for convenience.
    - Added `debug-swaps.css` and a toggable setting to highlight a Swap being swapped.
- **`htmx_nav.target`**:
    - Added type alias `Target` to conditionally apply a Swap and `PartialSpec` to condition what partial content to render.

## 0.3.0 — 2026-08-09

- **`htmx_nav.responses`**:
    - Added `include_if` to `Swap` along with the `skip_if_target_in` helper, enabling declarative conditional rendering of OOB swaps based on incoming HTMX targets.
    - Added native `title` support to `render_htmx` (and `make_shell_renderer`), automatically sending the `HX-Title` header on HTMX requests and injecting a `<title>` OOB snippet when needed.
    - **Breaking/Refactor**: Removed automatic `HX-Push-Url` handling from inside `render_htmx`, shifting full control of URL history updates back to the view layer.
- **`htmx_nav.testing`**:
    - Introduced a new testing module containing utilities to verify context parity and final template output across regular and HTMX requests.
- **Documentation & Tooling**:
    - Migrated documentation to **Sphinx** to streamline workflow.
    - Initialized the reference example project.
    - Added **Ruff** and **djLint** for code linting and formatting.
    - Fixed various typos across docstrings and documentation.

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