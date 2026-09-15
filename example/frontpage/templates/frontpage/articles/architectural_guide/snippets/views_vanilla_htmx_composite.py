# example/vanilla_htmx_composite/views.py
def get_template(request: HttpRequest, template_name: str) -> str:
    """Substitutes a full template for its OOB shell on HTMX requests."""
    if request.headers.get("HX-Request", "") == "true":
        name = template_name.rsplit("/", 1)[-1]
        return f"vanilla_htmx_composite/_{name}"
    return template_name

def overview(request: HttpRequest) -> HttpResponse:
    context = {
        **_sidebar_context(active_page="overview"),
        "org_count": Organization.objects.count(),
        "project_count": Project.objects.count(),
    }
    template = get_template(request, "core/pages/overview.html")
    return render(request, template, context)