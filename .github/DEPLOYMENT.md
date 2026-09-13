# Maintainer Deployment Guide (Render & Docker)

> **Internal Maintainer Runbook:** Instructions for maintaining and deploying the live reference demo at `https://django-htmx-nav.onrender.com/`.

## 1. Architecture Overview

The containerized demo is engineered for a single-container deployment with an idle memory footprint under 60 MB RAM:

- **Static Files**: Assets are served directly via `whitenoise` with compression (`CompressedStaticFilesStorage`), removing the need for external S3 buckets or Nginx sidecars.
- **Application Server**: Gunicorn runs with `gthread` workers, request limits, and standard stdout/stderr logging.
- **Security**: Container runs as a non-privileged user (`app:app` UID 1000).

## 2. Deploying to Render (Free Web Service)

[Render](https://render.com) provides a free tier for Web Services (512 MB RAM, shared CPU, 750 free instance hours/month) with native Docker support and free automatic SSL certificates.

### Option A: 1-Click Deploy (Render Blueprint)

Deploy using the repository's root [`render.yaml`](../render.yaml) Blueprint:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/lucas-rollin/django-htmx-nav)

### Option B: Manual Web Service Setup

1. Sign up or log in at [render.com](https://render.com) using GitHub.
2. Click **New +** → **Web Service**.
3. Connect the repository: `lucas-rollin/django-htmx-nav`.
4. Configure service settings:
   - **Language / Runtime**: `Docker`
   - **Branch**: `main`
   - **Region**: Any preferred region (e.g. *Oregon (US West)*)
   - **Instance Type**: `Free`
5. Configure Environment Variables:
   - `DEBUG`: `False`
   - `ALLOWED_HOSTS`: `.onrender.com,localhost,127.0.0.1`
   - `CSRF_TRUSTED_ORIGINS`: `https://*.onrender.com`
   - `SECRET_KEY`: *(Generate a secure random key)*
6. Click **Create Web Service**. Render will build the `production` Docker stage and provide a live URL (`https://<service-name>.onrender.com`).

## 3. Environment Variables Reference

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DEBUG` | `True` | Set to `False` in production. |
| `SECRET_KEY` | *(insecure dev key)* | Secret key for Django cryptographic signing. Required in production. |
| `ALLOWED_HOSTS` | `127.0.0.1,testserver,localhost` | Comma-separated list of valid hostnames/domains (e.g. `.onrender.com`). |
| `CSRF_TRUSTED_ORIGINS` | `""` | Comma-separated trusted origins (e.g. `https://*.onrender.com`). |
| `STATIC_ROOT` | `<BASE_DIR>/staticfiles` | Directory where `collectstatic` outputs assets. |
| `PORT` | `8000` | Port for Gunicorn to listen on (Render automatically supplies `PORT=10000`). |

## 4. Local Container Workflows

```bash
# Production image simulation locally (Gunicorn + WhiteNoise)
docker compose up --build web

# Development with hot-reload and local source mounted
docker compose up dev

# Isolated testing
docker compose run --rm test

# Metric & Playwright benchmark collection
docker compose run --rm bench
```
