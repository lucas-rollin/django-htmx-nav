# ==========================================
# Base Stage: Minimal Python Runtime
# ==========================================
FROM python:3.14-slim AS python-base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

WORKDIR /workspace

# ==========================================
# Testing & Benchmarking Stage (With Playwright)
# ==========================================
FROM python-base AS test

WORKDIR /workspace

COPY pyproject.toml README.md uv.lock ./
COPY src/ ./src/

# Install test, benchmark, lint, and example dependencies using locked versions
RUN uv sync --frozen --group example --group test --group bench --group lint

# Install Playwright browser & system dependencies
RUN playwright install --with-deps chromium

COPY . /workspace/

RUN python example/manage.py vendor_client_assets
RUN python example/manage.py collectstatic --noinput
CMD ["pytest"]

# ==========================================
# Builder Stage: Install Deps & Build Wheels
# ==========================================
FROM python-base AS builder

WORKDIR /workspace

COPY pyproject.toml README.md uv.lock ./
COPY src/ ./src/

RUN uv sync --frozen --no-editable --no-default-groups --group example

# ==========================================
# Production Stage: Ultra-lean (~150MB)
# ==========================================
FROM python:3.14-slim AS production

# Security: create non-root user
RUN groupadd -g 1000 app && useradd -u 1000 -g app -s /bin/sh -m app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app src/ /workspace/src/
COPY --chown=app:app example/ /workspace/example/

WORKDIR /workspace/example

# Collect static files into STATIC_ROOT during build
ENV DJANGO_SETTINGS_MODULE=config.settings \
    STATIC_ROOT=/workspace/example/staticfiles

USER app
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Healthcheck to verify app responds
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request, os; port = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{port}/').read()" || exit 1

CMD ["sh", "-c", "exec gunicorn config.wsgi:application \
     --bind 0.0.0.0:${PORT:-8000} \
     --workers 2 \
     --threads 2 \
     --worker-class gthread \
     --max-requests 1000 \
     --max-requests-jitter 50 \
     --access-logfile - \
     --error-logfile -"]

