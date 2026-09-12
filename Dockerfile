# ==========================================
# Base Stage: Minimal Python Runtime
# ==========================================
FROM python:3.14-slim AS python-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PORT=8000

WORKDIR /workspace

# ==========================================
# Testing & Benchmarking Stage (With Playwright)
# ==========================================
FROM python-base AS test

WORKDIR /workspace

# Install Playwright browser & system dependencies first
RUN pip install playwright \
    && playwright install --with-deps chromium

COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install project with test, benchmark, and lint extras
RUN pip install -e .[example,test,bench,lint]

COPY . /workspace/

CMD ["pytest"]

# ==========================================
# Builder Stage: Install Deps & Build Wheels
# ==========================================
FROM python-base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install core package + example dependencies
RUN pip install --prefix=/install .[example]

# ==========================================
# Production Stage: Ultra-lean (~150MB)
# ==========================================
FROM python-base AS production

# Security: create non-root user
RUN groupadd -g 1000 app && useradd -u 1000 -g app -s /bin/sh -m app

COPY --from=builder /install /usr/local
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

