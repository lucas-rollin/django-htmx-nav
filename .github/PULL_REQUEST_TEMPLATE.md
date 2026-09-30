## What does this change?

<!-- One or two sentences. Link the related issue if there is one. -->

## Why?

<!-- What problem does this solve, or what behavior does it change? -->

## How was this tested?

<!--
If you changed Swap, render_nav, make_shell_renderer, or targeting
behavior, which test file did you add/update?
(tests/test_swaps.py, tests/test_shortcuts.py, tests/test_shell.py,
tests/test_targeting.py, tests/test_partials.py, ...)

If this affects navigation-state parity across request modes, does a
test use assert_shell_parity / assert_shell_composition, rather than
only checking a single request mode in isolation?
-->

## Checklist

- [ ] `pytest` passes locally
- [ ] `ruff check .` / `ruff format --check .` pass locally
- [ ] `mypy src/` passes locally (new public APIs are fully typed)
- [ ] Docstrings added/updated for any new or changed public API (they
      feed directly into `docs/api/*.md` via Sphinx autodoc)
- [ ] Relevant page under `docs/` updated, if this changes documented
      behavior
- [ ] No version bump included (handled at release time)

## Anything reviewers should pay extra attention to?

<!-- Optional: tricky edge cases, deliberate trade-offs, open questions. -->
