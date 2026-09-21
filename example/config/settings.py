"""
Django settings for config project.
"""

from pathlib import Path

import environ

from .constants import EnvironmentChoices

BASE_DIR = Path(__file__).resolve().parent.parent


# Initialize django-environ
env = environ.Env()

ENVIRONMENT = env(
    "ENVIRONMENT", cast=EnvironmentChoices, default=EnvironmentChoices.DEV
)

# --- Per-environment defaults -------------------------------------

_defaults = {
    "DEBUG": True,
    "SITE_URL": "",
    "DEMO_URL": "",
    "ROBOTS_DISALLOW_ALL": False,
    "STATIC_BUILD": False,
    "HTMX_NAV_DEBUG_SWAPS": True,
    "HTMX_NAV_BENCHMARK_LOCAL_ASSETS": False,
}

if ENVIRONMENT == EnvironmentChoices.STATIC:
    # GitHub Pages static freeze pass
    _defaults.update(
        DEBUG=False,
        STATIC_BUILD=True,
        SITE_URL="https://lucas-rollin.github.io/django-htmx-nav",
        DEMO_URL="https://django-htmx-nav.onrender.com",
        ROBOTS_DISALLOW_ALL=False,
    )

elif ENVIRONMENT == EnvironmentChoices.DEMO:
    # Render dynamic sandbox
    _defaults.update(
        DEBUG=False,
        SITE_URL="https://lucas-rollin.github.io/django-htmx-nav",
        DEMO_URL="",  # On Render, demo routes are local
        ROBOTS_DISALLOW_ALL=True,
    )

elif ENVIRONMENT == EnvironmentChoices.BENCH:
    _defaults.update(
        DEBUG=False,
        HTMX_NAV_DEBUG_SWAPS=False,
        HTMX_NAV_BENCHMARK_LOCAL_ASSETS=True,
    )

# --- Actual settings ----------------------------------------------

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-s-+#0r9wl_6j4t8e$ffdg#=&i$@*+xwt=!*q7wmx43%!6l9)p^",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=_defaults["DEBUG"])

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS", default=["127.0.0.1", "testserver", "localhost", "0.0.0.0"]
)

CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS", default=[])

# URL config
DEMO_URL = env("DEMO_URL", default=_defaults["DEMO_URL"])
SITE_URL = env("SITE_URL", default=_defaults["SITE_URL"])
DOCS_URL = env(
    "DOCS_URL", default="https://lucas-rollin.github.io/django-htmx-nav/docs/"
)
REPO_URL = env("REPO_URL", default="https://github.com/lucas-rollin/django-htmx-nav")
PYPI_URL = env("PYPI_URL", default="https://pypi.org/project/django-htmx-nav/")

ROBOTS_DISALLOW_ALL = env.bool(
    "ROBOTS_DISALLOW_ALL", default=_defaults["ROBOTS_DISALLOW_ALL"]
)

HTMX_NAV_DEBUG_SWAPS = env.bool(
    "HTMX_NAV_DEBUG_SWAPS", default=_defaults["HTMX_NAV_DEBUG_SWAPS"]
)
HTMX_NAV_BENCHMARK_LOCAL_ASSETS = env.bool(
    "HTMX_NAV_BENCHMARK_LOCAL_ASSETS",
    default=_defaults["HTMX_NAV_BENCHMARK_LOCAL_ASSETS"],
)

# Application definition

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "htmx_nav",
    "frontpage",
    "core",
    "mpa",
    "vanilla_htmx_composite",
    "vanilla_htmx_atomic",
    "htmx_nav_demo",
    "benchmarks",
    "sandbox",
]

MIDDLEWARE = [
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.variants",
                "config.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "file:mockdata?mode=memory&cache=shared",
        "OPTIONS": {
            "uri": True,
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = env("STATIC_URL", default="static/")
STATIC_ROOT = Path(env("STATIC_ROOT", default=str(BASE_DIR / "staticfiles")))
STATICFILES_DIRS = [p for p in [BASE_DIR / "static"] if p.is_dir()]

# True during CI static freeze / GitHub Pages build
STATIC_BUILD = env.bool("STATIC_BUILD", default=_defaults["STATIC_BUILD"])

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Only enable WhiteNoise when NOT running a static build pass
if not STATIC_BUILD:
    try:
        import whitenoise  # noqa: F401

        STORAGES["staticfiles"] = {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        }

        # Only insert middleware for runtime serving
        if not DEBUG or STATIC_ROOT.is_dir():
            MIDDLEWARE.insert(2, "whitenoise.middleware.WhiteNoiseMiddleware")
    except ImportError:
        pass
