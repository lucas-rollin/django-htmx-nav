from django.shortcuts import render

{% include "frontpage/articles/architectural_guide/snippets/get_template_dispatch.py" %}

def overview(request: HttpRequest) -> HttpResponse:
    context = {
        **_sidebar_context(active_page="overview"),
        **_breadcrumbs(("Helpdesk", None)),
        "org_count": Organization.objects.count(),
        "project_count": Project.objects.count(),
    }
    template = get_template(request, "core/pages/overview.html")
    return render(request, template, context)