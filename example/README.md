# Example Application & Integration Testbed

This directory contains a complete sample Django application demonstrating `django-htmx-nav` in a realistic web application context.

## Purpose

The example project is designed for three main purposes:

1. **Interactive Demo:** Demonstrates real-world UI patterns such as multi-region navigation (sidebars, breadcrumbs, headers), active-state highlighting, multi-step forms/wizards, and nested tabbed workspaces.
2. **Integration Testbed:** Serves as a full-stack Django environment for validating `django-htmx-nav` behaviors (partial block resolution, OOB swaps, `Vary` headers, redirects) against real browser requests.
3. **Implementation Playground & Experiment:** Enables side-by-side comparison of three common web application architectural approaches:
   - **Multi-Page Application (MPA):** Traditional full-page reloads.
   - **Vanilla HTMX:** Manual `HX-Request` checking, ad-hoc partial rendering, and manual out-of-band swap construction.
   - **`django-htmx-nav`:** Declarative partial specifications, reusable shell renderers (`make_shell_renderer`), and Class-Based View mixins (`make_shell_view_mixin`).

## Installation & Running

### 1. Install Dependencies

From the repository root, install `django-htmx-nav` in editable mode with the `example` extra dependencies (`Faker`):

```bash
pip install -e ".[example]"
```

### 2. Start the Development Server

Run the Django development server:

```bash
python example/manage.py runserver
```

Open your browser and navigate to `http://127.0.0.1:8000/`.

## Running with Docker & Docker Compose

A multi-stage [`Dockerfile`](../Dockerfile) and [`docker-compose.yml`](../docker-compose.yml) are provided at the repository root for local development, reproducible testing/benchmarking, and production deployment.

### 1. Production Simulation (Lean Gunicorn + WhiteNoise)

Runs a lean production image with Gunicorn and WhiteNoise compressed static asset serving:

```bash
docker compose up --build web
```

Navigate to `http://localhost:8000/`.

### 2. Development with Hot Reloading

Mounts local source code into the container with debug mode enabled and swap markers active:

```bash
docker compose up dev
```

### 3. Hermetic Testing (Unit & Parity Tests)

Executes pytest within an isolated container:

```bash
docker compose run --rm test
```

### 4. Running Benchmarks & Playwright Metrics

Runs the full metric collection suite with pre-installed Chromium and system dependencies:

```bash
docker compose run --rm bench
```

---

## Production Deployment Guide

The containerized example application is engineered for cheap, single-container deployments (e.g. Fly.io, Railway, Render, Koyeb, or a minimal VPS) with an idle footprint under 120MB RAM:

- **Static Files**: Assets are served directly via `whitenoise` with compression (`CompressedStaticFilesStorage`), removing the need for external S3 buckets or Nginx.
- **Application Server**: Gunicorn runs with `gthread` workers, request limits, and stdout/stderr logging.
- **Security**: Container runs as a non-privileged user (`app:app` UID 1000).

### Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DEBUG` | `True` | Set to `False` in production. |
| `SECRET_KEY` | *(insecure dev key)* | Secret key for Django cryptographic signing. |
| `ALLOWED_HOSTS` | `127.0.0.1,testserver,localhost` | Comma-separated list of valid hostnames/domains (e.g. `example.com,app.fly.dev`). |
| `CSRF_TRUSTED_ORIGINS` | `""` | Comma-separated trusted origins (e.g. `https://example.com`). |
| `STATIC_ROOT` | `<BASE_DIR>/staticfiles` | Directory where `collectstatic` outputs assets. |

## Project Structure

```plaintext
example/
├── config/              # Django project configuration (settings, root URLs, WSGI)
├── core/                # Shared domain models, mock data generators (Faker), base templates
├── htmx_nav_demo/       # Interactive demo app using django-htmx-nav patterns
├── mpa/                 # Reference implementation using traditional MPA full-page reloads
├── static/              # Static assets and CSS stylesheets
└── manage.py            # Django command-line entrypoint
```

### Key Components

- **`config/settings.py`**: Configured with `HTMX_NAV_DEBUG_SWAPS = True` for visual swap debugging.
- **`core/`**: Defines workspace models, projects, tickets, and employees populated dynamically with mock data.
- **`htmx_nav_demo/`**: Demonstrates `render_nav`, `make_shell_renderer`, `make_shell_view_mixin`, `Swap.text`, and `Swap.delete` across complex nested views.
- **`mpa/`**: Demonstrates the baseline Multi-Page Application workflow for direct comparison.

## Planned Work & Future Experiments

- [x] Add vanilla HTMX variant views (`example/vanilla_htmx/`) to explicitly benchmark code lines and maintenance complexity against `django-htmx-nav`.
- [x] Add interactive toggle in the UI header to seamlessly switch execution modes between MPA, Vanilla HTMX, and `django-htmx-nav`.
- [x] Expand E2E test suites comparing client-side performance and network payload sizes across all three architectural variants.
