def demo_mode(request):
    ns = request.resolver_match.namespace if request.resolver_match else ""
    mode = "htmx" if ns == "htmx" else "mpa"
    return {
        "demo_mode": mode,
        "is_htmx_demo": mode == "htmx",
    }
