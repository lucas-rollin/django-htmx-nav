# Example Project & Live Demo

The `django-htmx-nav` repository includes a comprehensive, production-style reference Helpdesk application (organizations, projects, Kanban boards, ticket detail views with subtabs, and multi-step creation wizards).

It serves as both a runnable testbed and an empirical laboratory demonstrating how to solve navigation state drift across different architectural paradigms.

## Interactive Resources & Deployments

- **{demo}`Live Helpdesk Sandbox <htmx-nav/declarative/>`:** Live hypermedia application hosted on Render. Experiment with creating tickets, moving Kanban cards, switching variants, and toggling visual swap debugging in real time.
- **<a href="../guide/">Interactive Architectural Guide</a>:** Deep dive into hypermedia state synchronization, code walkthroughs of all 8 implementation variants, and an architectural decision tree.
- **<a href="../benchmarks/">Empirical Benchmark Dashboard</a>:** Live performance measurements across wire payload, render latency, and database query counts.
- **<a href="../">Showcase Overview</a>:** High-level overview and visual comparisons.

## Source Code & Local Setup

All implementation variants, test suites, and Docker configurations are open source in the [`example/`](https://github.com/lucas-rollin/django-htmx-nav/tree/main/example) directory:

- Full setup instructions (Docker Compose hot reload or native Python `runserver`) are maintained in the [example project README](https://github.com/lucas-rollin/django-htmx-nav/blob/main/example/README.md).
- Automated parity verification tests live in [`example/core/tests/`](https://github.com/lucas-rollin/django-htmx-nav/tree/main/example/core/tests) and [`example/htmx_nav_demo/tests/`](https://github.com/lucas-rollin/django-htmx-nav/tree/main/example/htmx_nav_demo/tests).
