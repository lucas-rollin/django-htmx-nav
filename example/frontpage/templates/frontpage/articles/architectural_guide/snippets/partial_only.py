from django.shortcuts import get_object_or_404
from htmx_nav import render_nav

def project_board(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    return render_nav(
        request, 
        "pages/board.html", 
        {"project": project}
    )