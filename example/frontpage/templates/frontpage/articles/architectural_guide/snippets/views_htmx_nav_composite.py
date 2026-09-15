# example/htmx_nav_demo/views_composite.py
from htmx_nav import Swap, render_nav

# Swap helper functions
def _sidebar_swap(active_page: str | None = None) -> Swap:
    return Swap(
        "core/components/_sidebar_menu.html", 
        _sidebar_context(active_page), 
        target_id="sidebar"
    )

def _breadcrumb_swap(*crumbs: tuple[str, str | None]) -> Swap:
    return Swap(
        "core/components/_breadcrumbs.html", 
        _breadcrumbs(*crumbs), 
        target_id="breadcrumbs"
    )

# Call Swaps in the view
def overview(request: HttpRequest) -> HttpResponse:
    """Display the main helpdesk overview dashboard."""
    context = {
        "org_count": Organization.objects.count(),
        "project_count": Project.objects.count(),
    }
    return render_nav(
        request,
        "core/pages/overview.html",
        context,
        swaps=[
            _sidebar_swap(active_page="overview"),
            _breadcrumb_swap(("helpdesk", None)),
        ]
    )
