from core.navigation.registry import VARIANTS


# deprecated
def demo_mode(request):
    ns = request.resolver_match.namespace if request.resolver_match else ""
    mode = "htmx" if ns.startswith("htmx") else "mpa"
    return {
        "demo_mode": mode,
        "uses_htmx": mode == "htmx",
    }

def variants(request):
    ns = request.resolver_match.namespace if request.resolver_match else ""
    
    return {
        "active_variant": VARIANTS[ns],
        "all_variants": VARIANTS,
    }
