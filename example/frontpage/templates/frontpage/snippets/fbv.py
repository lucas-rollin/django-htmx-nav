from django.shortcuts import get_object_or_404
from htmx_nav import Swap, render_nav


def project_board(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # Full page for direct visits, partial + OOB swaps for HTMX
    return render_nav(
        request,
        "pages/board.html",
        {"project": project},
        swaps=[
            Swap("components/_sidebar.html", {"user": request.user}, target_id="sidebar"),
            Swap("components/_breadcrumbs.html", target_id="breadcrumbs"),
        ],
        title=project.name,
    )