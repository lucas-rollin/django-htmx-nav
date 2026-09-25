# Security Policy

## Supported Versions

`django-htmx-nav` is pre-1.0 and released as a single rolling line.
Security fixes are made against the latest release on PyPI; older
0.x releases are not backported.

|     Version      | Supported |
| ---------------- | --------- |
| Latest (`0.3.x`) | ✅        |
| Older 0.x        | ❌        |

## Reporting a Vulnerability

Please **do not open a public GitHub issue** for security reports.

Instead, use GitHub's private vulnerability reporting for this repo
([Security tab → "Report a vulnerability"](https://github.com/lucas-rollin/django-htmx-nav/security/advisories/new)).
If that's unavailable to you, open a regular issue asking for a private
contact channel and avoid including exploit details until one is set up.

Please include:

- The version of `django-htmx-nav` and Django you're using
- A minimal reproduction (a `Swap(...)` / `render_nav(...)` call and the
  request headers involved is usually enough)
- The potential impact as you understand it

You should get an acknowledgement within a few days. This is a
single-maintainer project, so response and fix timelines aren't
guaranteed, but genuine vulnerabilities will be prioritized over other
work.
