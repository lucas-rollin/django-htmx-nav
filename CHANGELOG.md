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