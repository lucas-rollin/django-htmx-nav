from core.navigation.registry import VARIANTS


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


def benchmark(request):
    from django.conf import settings

    return {"benchmark_local_assets": settings.HTMX_NAV_BENCHMARK_LOCAL_ASSETS}
