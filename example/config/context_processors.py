from core.navigation.registry import VARIANTS
from django.conf import settings


def variants(request):
    ns = request.resolver_match.namespace if request.resolver_match else ""
    active_variant = VARIANTS.get(ns)

    families: dict[str, list] = {}
    for variant in VARIANTS.values():
        families.setdefault(variant.family, []).append(variant)

    variant_families = [
        {"label": items[0].family_label, "variants": items}
        for items in families.values()
    ]

    return {
        "active_variant": active_variant,
        "all_variants": VARIANTS,
        "variant_families": variant_families,
    }


def site_settings(request):
    return {
        "BENCHMARK_LOCAL_ASSETS": settings.HTMX_NAV_BENCHMARK_LOCAL_ASSETS,
        "DEMO_URL": settings.DEMO_URL.rstrip("/"),
        "SITE_URL": settings.SITE_URL.rstrip("/"),
        "DOCS_URL": settings.DOCS_URL,
        "DOCS_SITE": settings.DOCS_URL,
        "REPO_URL": settings.REPO_URL.rstrip("/"),
        "PYPI_URL": settings.PYPI_URL.rstrip("/"),
    }
