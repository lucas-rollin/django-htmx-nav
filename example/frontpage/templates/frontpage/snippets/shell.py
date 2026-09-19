from django.shortcuts import get_object_or_404
from htmx_nav import Swap, make_shell_renderer

# Defined once, reused by every view in the app
render_shell = make_shell_renderer(lambda request: [
    Swap("components/_sidebar.html", {"user": request.user}, target_id="sidebar"),
    Swap("components/_breadcrumbs.html", target_id="breadcrumbs"),
])


def project_board(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # Sidebar & breadcrumbs come along for free, every time
    return render_shell(
        request,
        "pages/board.html",
        {"project": project},
        extra_swaps=Swap(
            "components/_status_badge.html",
            target_id="project-status",
        ),
    )
