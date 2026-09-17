from htmx_nav import Swap, make_shell_renderer

# Declarative mapping of route names to navigation parameters/breadcrumbs
NAV_ENTRIES: dict = {
    "overview": {
        "active_page": "overview",
        "breadcrumbs": [("Helpdesk", None)],
    },
    # Other entries...
}

# Create the system to process the registry into Swaps
def _sidebar_ctx(request: HttpRequest) -> dict:
    url_name = request.resolver_match.url_name
    entry = NAV_ENTRIES.get(url_name, {})
    return _sidebar_context(active_page=entry.get("active_page", ""))

def _breadcrumbs_ctx(request: HttpRequest) -> dict:
    url_name = request.resolver_match.url_name
    entry = NAV_ENTRIES.get(url_name, {})
    return _breadcrumbs(entry.get("breadcrumbs", []))

def build_shell_swaps(request: HttpRequest) -> list[Swap]:
    """One Swap per navigation region, resolved dynamically per request."""
    return [
        Swap(
            "core/components/_sidebar_menu.html",
            _sidebar_ctx(request),
            target_id="sidebar",
        ),
        Swap(
            "core/components/_breadcrumbs.html",
            _breadcrumbs_ctx(request),
            target_id="breadcrumbs",
        ),
    ]

# Dynamic renderer: invokes `build_shell_swaps(request)` per request
render_shell = make_shell_renderer(build_shell_swaps)