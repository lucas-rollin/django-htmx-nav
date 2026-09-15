# example/mpa/views.py
from django.shortcuts import render

def overview(request: HttpRequest) -> HttpResponse:
    """Classic Django full-page rendering."""
    context = {
        **_sidebar_context(active_page="overview"),
        **_breadcrumbs(("Helpdesk", None)),
        "org_count": Organization.objects.count(),
        "project_count": Project.objects.count(),
    }
    return render(request, "core/pages/overview.html", context)