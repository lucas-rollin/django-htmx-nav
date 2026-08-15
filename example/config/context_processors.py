from core.navigation.registry import VARIANTS


def variants(request):
    ns = request.resolver_match.namespace if request.resolver_match else ""

    return {
        "active_variant": VARIANTS[ns],
        "all_variants": VARIANTS,
    }
