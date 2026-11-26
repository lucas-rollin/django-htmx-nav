# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-11-26

### Added

- **`htmx_nav`**:
  - Exported `cache_on_request` and `debug_swap_marker` in package `__all__`.
- **`htmx_nav.swaps`**:
  - Added `tag` parameter (defaulting to `"div"`) to `Swap` and `Swap.text` for non-`<div>` OOB targets (e.g. `<tr>` or `<tbody>`), with `__post_init__` validation for `wrap` and `tag`.
- **`htmx_nav.shortcuts`**:
  - Added `headers` keyword argument to `render_nav`, forwarded to `TemplateResponse`.
- **Tooling & Docs**:
  - Added cross-platform CI check runner in `scripts/ci.py` and documented it in `CONTRIBUTING.md`.

### Changed

- **`htmx_nav.templatetags.htmx_nav`**:
  - `{% htmx_nav_debug_marker %}` now uses `takes_context=True` to resolve the active request CSP nonce automatically.

### Fixed

- **`htmx_nav.shortcuts`**:
  - Corrected `render_nav` docstring on context merge precedence between `context` and `swap.context`.
- **`htmx_nav.views`**:
  - Removed the stale `get_shell_template_name()` note from `make_shell_view_mixin` docstring (removed in `0.3.3`).
- **`htmx_nav.testing`**:
  - `assert_shell_parity` now raises a clear `AssertionError` when a response has no template context (`resp.context is None`).
  - `_HTMLDocument.split_fragments` now extracts `<template>`-wrapped OOB elements.

### Security

- **`htmx_nav.debugging`**:
  - Escaped `</` in `_build_marker_script` target IDs and forwarded CSP nonces via Django's `get_nonce(request)` (falling back to `request.csp_nonce`) in `Swap.render()`, `debug_swap_marker()`, and `{% htmx_nav_debug_marker %}`.
- **`htmx_nav.swaps`**:
  - HTML-escaped `target_id` and `swap_style` attributes in `Swap.render()`.

## [0.3.3] - 2026-09-21

### Added

- **`htmx_nav.partials`**:
  - `PartialResolver` protocol: derive a partial block or template path from the request and base template.
  - `PathReplace`: built-in resolver that swaps a path segment (e.g. `"pages/"` to `"partials/_"`) for codebases that keep partials in separate files.

### Removed

- **`htmx_nav.views`**:
  - `get_shell_template_name()` hook on views using `make_shell_view_mixin`. Override Django's `get_template_names()` instead.

### Fixed

- **`htmx_nav.views`**:
  - `make_shell_view_mixin` now honors the view's `template_engine` and `content_type`.
  - `make_shell_view_mixin` now defers to the shell renderer's own `partial=` default instead of always overriding it with `"#content"`.
- **`htmx_nav.shell`** / **`htmx_nav.views`**:
  - `HTMX_NAV_DEFAULT_PARTIAL` is now read per request rather than when the renderer or mixin is created, so `override_settings` works.

## [0.3.2] - 2026-09-18

### Added

- **`htmx_nav.settings`**:
  - `HTMX_NAV_DEFAULT_PARTIAL`: Added setting to configure the default `PartialSpec` (defaults to `"#content"`), dynamically resolved across `render_nav`, `make_shell_renderer`, and `make_shell_view_mixin`.

### Changed

- **`htmx_nav.targeting`**:
  - Removed `django-htmx` middleware checks (`request.htmx` and `request.htmx.target`) in favor of relying directly on standard HTTP headers (`HX-Request` and `HX-Target`).

### Removed

- **`htmx_nav.shortcuts`**:
  - Removed `render_with_swaps`. Use `render_nav(..., partial=None)` for responses that append out-of-band swaps without partial resolution.
- **Dependencies**:
  - Removed optional `django-htmx` dependency extra (`[htmx]`) from `pyproject.toml`.

## [0.3.1] - 2026-09-12

### Added

- **`htmx_nav.targeting`**:
  - `has_messages`: Predicate for `Swap.include_if` that returns True if there are pending Django messages.

### Changed

- **`htmx_nav.shell`**:
  - `make_shell_renderer`: Changed to be a simple wrapper around `render_nav` using Swaps instead of a template shell.

### Removed

- **`htmx_nav.helpers`**:
  - `reverse_maybe`: use explicit url resolving instead.

## [0.3.0] - 2026-08-15

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

## [0.2.0] - 2026-07-29

### Changed

- **`htmx_nav.responses`**:
  - Enhanced `make_shell_renderer` to support robust intra-page navigation (e.g., tabs) via a 3-path check: full page render, page container target swaps, and component-level target swaps.
- **Documentation & Quality**:
  - Cleaned up docstrings and added comprehensive **MkDocs Material** documentation with automated `mkdocstrings` API reference generation.

### Removed

- **`htmx_nav.responses`**:
  - Removed `htmx_redirect` (redundant with `django_htmx` HTTP tools).

## [0.1.0]

### Added

- `htmx_nav.responses`: `render_htmx`, `Oob`, `make_shell_renderer`, `htmx_redirect`, `HX-Push-Url`/`Vary: HX-Request` handling.
- `htmx_nav.helpers`: `reverse_maybe`, `cache_on_request`.
- `htmx_nav.views`: `make_shell_view_mixin`.

[unreleased]: https://github.com/lucas-rollin/django-htmx-nav/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/lucas-rollin/django-htmx-nav/compare/v0.3.3...v0.4.0
[0.3.3]: https://github.com/lucas-rollin/django-htmx-nav/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/lucas-rollin/django-htmx-nav/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/lucas-rollin/django-htmx-nav/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/lucas-rollin/django-htmx-nav/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/lucas-rollin/django-htmx-nav/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/lucas-rollin/django-htmx-nav/releases/tag/v0.1.0
