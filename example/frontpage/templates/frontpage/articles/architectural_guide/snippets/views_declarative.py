from .registry_declarative import render_shell

def overview(request: HttpRequest) -> HttpResponse:
    # Views only fetch their own data; sidebar and crumbs are handled automatically:
    context = {
        "org_count": Organization.objects.count(),
        "project_count": Project.objects.count(),
    }
    return render_shell(request, "core/pages/overview.html", context)