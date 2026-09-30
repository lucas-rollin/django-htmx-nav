# Contributing to django-htmx-nav

Thanks for considering a contribution! This document covers everything needed to get a local dev environment running, pass checks, and follow codebase conventions.

## Getting Started

Clone the repo and install dependencies based on what you are working on:

```bash
git clone https://github.com/lucas-rollin/django-htmx-nav.git
cd django-htmx-nav

# Core test + lint tooling (needed for most contributions)
uv sync --group test --group lint

# Optional dependency groups for docs or the example project
uv sync --group docs
uv sync --group example
```

Requires **Python 3.12+** and **Django 6.0+** (see `pyproject.toml`).

## Project Layout

- `src/htmx_nav/` — The installable library package shipped to PyPI.
- `tests/` — The main test suite, run against `tests/settings.py`.
- `docs/` — Sphinx + MyST documentation source.
- `example/` — A reference Helpdesk app demonstrating 8 implementation variants (MPA, vanilla HTMX, etc.). It has its own dependencies and test suite.

If your change affects behavior described in `docs/`, please update the relevant `.md` file in the same PR.

## Running the Test Suite

Run the main test suite:

```bash
uv run pytest
```

If you are modifying the example project, run its separate test suite:

```bash
uv sync --group example
uv run pytest example/
```

## Linting and Code Quality

Run all quality checks locally before opening a PR:

```bash
uv run ruff check .
uv run ruff format --check .
uv run djlint .
uv run mypy src/
```

### Type Checking (`mypy`)

- **Scope:** Mypy runs exclusively against `src/`.
- **Standard:** The library package is `strict` and fully typed using
the `django-stubs` plugin. New public functions and classes in `src/htmx_nav/` must include complete type annotations.

### Template Formatting (`djlint`)

- **Scope:** DjLint is configured to check templates in the `example/` app.
- **Note:** Minimal test fixtures under `tests/templates/` are intentionally excluded in `pyproject.toml` since they only exist to exercise rendering logic.

### Docstring Convention

- **Format:** All public functions, classes, and methods in `src/htmx_nav/` must include docstrings following the **Google-style format** (`Args:`, `Returns:`, `Raises:`, `Example:`).
- **Integration:** These docstrings are pulled directly into the Sphinx API reference via `autodoc`.

## Building the Docs

```bash
uv sync --group docs
uv run sphinx-build -b html docs docs/_build
```

If you add a new public symbol, register it in the relevant `docs/api/*.md`
page using `automodule` rather than duplicating prose.

## Making a Pull Request

1. **Open an issue first** for anything beyond a small fix or doc update.
2. **Keep PRs focused** on a single change to make review easier.
3. **Add tests** for any bug fix or behavior change.
4. **Update docs** and `docs/glossary.md` if you introduce new terminology.
5. **Verify checks pass** (`pytest`, `ruff check`, `djlint`, and `mypy src/`).
6. **Do not bump versions** in `pyproject.toml`; versioning is handled at release time.

## Reporting Bugs / Requesting Features

Use the issue templates. For bugs, please include a minimal reproduction
(e.g., a single `Swap(...)` or `render_nav(...)` call alongside relevant
request headers).

## Code of Conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).
