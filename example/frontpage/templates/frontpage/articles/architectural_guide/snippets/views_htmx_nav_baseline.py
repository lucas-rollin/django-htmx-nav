# example/htmx_nav_demo/views_baseline.py
from htmx_nav import Swap, make_shell_renderer

# 1. Define standard application shell swaps once:
render_shell = make_shell_renderer([
    Swap("core/components/_sidebar_menu.html", target_id="sidebar"),
    Swap("core/components/_breadcrumbs.html", target_id="breadcrumbs"),
])

# 2. Views use render_shell just like standard Django render():
def overview(request: HttpRequest) -> HttpResponse:
    context = {
        **_sidebar_context(active_page="overview"),
        "org_count": Organization.objects.count(),
        "project_count": Project.objects.count(),
    }
    return render_shell(request, "core/pages/overview.html", context)