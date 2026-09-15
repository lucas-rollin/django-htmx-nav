# example/htmx_nav_demo/registry_declarative.py
from htmx_nav import make_shell_renderer
from htmx_nav.helpers import cache_on_request

# Request-scoped caching prevents duplicate queries:
def get_project(request: HttpRequest) -> Project:
    project_id = request.resolver_match.kwargs["project_id"]
    return cache_on_request(
        request,
        "_project",
        lambda: Project.objects.get(id=project_id),
    )

def build_shell_swaps(request: HttpRequest) -> list[Swap]:
    """One Swap per navigation region, resolved fresh per request."""
    return [
        Swap("core/components/_sidebar_menu.html", sidebar_ctx(request), target_id="sidebar"),
        Swap("core/components/_breadcrumbs.html", crumbs_ctx(request), target_id="breadcrumbs"),
    ]

# The callable form: make_shell_renderer invokes this once per request
# instead of reusing one fixed, request-independent list of Swaps.
render_shell = make_shell_renderer(build_shell_swaps)