# Maintainer Deployment Guide

> **Internal Maintainer Runbook:** Documentation for managing, building, and deploying the static documentation/showcase site on **GitHub Pages** alongside the live interactive demo sandbox on **Render**.

## 1. Architecture & Deployment Topology

The project splits functionality across two distinct deployment targets, while development works normally as one django project.

### Target A: GitHub Pages (Static Showcase & Docs)

- **Host:** `https://lucas-rollin.github.io/django-htmx-nav/`
- **Included Apps & Content:**
  - **`frontpage` App:** Frozen landing page and technical hypermedia synchronization guide (`/guide/`). The live demo landing page includes a redirect pointing visitors to the flagship demo variant on Render.
  - **`benchmark` App:** Frozen empirical charts and latency metrics dashboard (`/benchmarks/`).
  - **Sphinx Docs:** Compiled developer guides and API reference (`/docs/`).
- **Characteristics:** Zero cold start, globally cached CDN, free hosting, and SEO/crawler friendly via `sitemap.xml`.

### Target B: Render (Live Interactive Sandbox)

- **Host:** `https://django-htmx-nav.onrender.com/`
- **Included Components:**
  - Full dynamic Django backend (Python + Django + Gunicorn) running all helpdesk variants (`/mpa/`, `/htmx/`, `/vanilla-htmx/*`, `/htmx-nav/*`).
  - In-memory SQLite database with live mutations (Kanban/cards).
- **Characteristics:** Spin-down after inactivity (~30s cold start), isolated sandbox environment with crawlers blocked via `robots.txt`.

## 2. Environment Profiles (`EnvironmentChoices`)

All configuration is driven by the `ENVIRONMENT` setting ([`example/config/constants.py`](../example/config/constants.py)), eliminating scattered ad-hoc flags:

- **`development` *(default)***
  - **Target:** Local host / Docker `dev`
  - **Settings:** `DEBUG=True`, local paths (`SITE_URL=""`, `DEMO_URL=""`), `ROBOTS_DISALLOW_ALL=False`.
  - **Behavior:** All links stay local on `127.0.0.1:8000`.
- **`static_generation`**
  - **Target:** GitHub Actions CI
  - **Settings:** `DEBUG=False`, `SITE_URL="github.io"`, `DEMO_URL="onrender.com"`, `ROBOTS_DISALLOW_ALL=False`.
  - **Behavior:** Freezes Django pages with script prefix.
- **`demo_production`**
  - **Target:** Render container / Docker `web`
  - **Settings:** `DEBUG=False`, `SITE_URL="github.io"`, `DEMO_URL=""`, `ROBOTS_DISALLOW_ALL=True`.
  - **Behavior:** Serves live variants. Chrome nav links return visitors to GitHub Pages.
- **`benchmark`**
  - **Target:** Docker `bench`
  - **Settings:** `DEBUG=False`, `SITE_URL=""`, `DEMO_URL=""`, `ROBOTS_DISALLOW_ALL=False`.
  - **Behavior:** Disables debug swaps; serves local vendor assets for Playwright runs.

## 3. GitHub Pages Deployment (Static Showcase & Docs)

Deployed automatically on pushes to `main` via [`.github/workflows/docs.yml`](./workflows/docs.yml).

### Build Pipeline

```bash
# 1. Collect all static assets (Tailwind, DaisyUI, local JS/CSS)
python example/manage.py collectstatic --noinput

# 2. Freeze Django frontpage, architectural guide, benchmarks, robots.txt, and sitemap.xml
python example/manage.py freeze_static_pages --out site --prefix /django-htmx-nav/

# 3. Build Sphinx HTML documentation directly into site/docs/
sphinx-build -b html docs site/docs

# 4. Disable GitHub Pages Jekyll processing
touch site/.nojekyll
```

The entire `site/` folder is uploaded and deployed as a single unified GitHub Pages artifact.

## 4. Render Deployment (Interactive Demo Sandbox)

The containerized demo runs as a lean single container with an idle footprint of ~60 MB RAM.

### Option A: 1-Click Blueprint Deploy

Deploy using the repository's root [`render.yaml`](../render.yaml):

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/lucas-rollin/django-htmx-nav)

### Option B: Manual Setup on Render

1. Create a **New Web Service** connected to `lucas-rollin/django-htmx-nav`.
2. Configure runtime parameters:
    - **Language / Runtime:** `Docker`
    - **Branch:** `main`
    - **Region:** Any (e.g., *Oregon (US West)*)
    - **Instance Type:** `Free`

3. Configure Environment Variables:
    - `ENVIRONMENT`: `demo_production`
    - `ALLOWED_HOSTS`: `.onrender.com,localhost,127.0.0.1`
    - `CSRF_TRUSTED_ORIGINS`: `https://*.onrender.com`
    - `SECRET_KEY`: *(Generate a secure key)*

4. Click **Create Web Service**. Render builds the production Docker stage and exposes `https://django-htmx-nav.onrender.com/`.

## 5. Local Docker & Container Workflows

Use the [`docker-compose.yml`](https://www.google.com/search?q=../docker-compose.yml) targets for local verification:

```bash
# 1. Run local development server (hot-reload on port 8000)
docker compose up dev

# 2. Simulate Render production container locally (Gunicorn + WhiteNoise)
docker compose up demo

# 3. Run hermetic pytest test suite
docker compose run --rm test

# 4. Execute Playwright benchmark measurement suite
docker compose run --rm bench
```

### Local Native Static Freeze Verification

To simulate the GitHub Actions static export and preview the frozen showcase/benchmark site locally:

```bash
# 0. Clean up any previous build artifacts to ensure a fresh start
rm -rf /tmp/site

# 1. Collect all static assets directly into the output folder
STATIC_ROOT=/tmp/site/static STATIC_URL=/static/ ENVIRONMENT=static_generation python example/manage.py collectstatic --noinput

# 2. Freeze Django frontpage, architectural guide, and benchmark dashboards with root prefix
ENVIRONMENT=static_generation python example/manage.py freeze_static_pages --out /tmp/site --prefix /

# 3. Build Sphinx HTML documentation into /tmp/site/docs
sphinx-build -b html docs /tmp/site/docs

# 4. Spin up a local Python HTTP server to preview the site
python -m http.server 8080 -d /tmp/site
```

Open [http://127.0.0.1:8080/](http://127.0.0.1:8080/) in your browser. (Press Ctrl+C in your terminal when you're done viewing to stop the server).
