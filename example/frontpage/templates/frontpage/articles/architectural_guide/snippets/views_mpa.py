# example/mpa/views.py
def overview(request: HttpRequest) -> HttpResponse:
    """Classic Django full-page rendering."""
    context = {
        # Layout contexts must be manually built into every view dict:
        **_sidebar_context(active_page="overview"),
        "org_count": Organization.objects.count(),
        "project_count": Project.objects.count(),
        "open_ticket_count": Ticket.objects.filter(status=Ticket.Status.OPEN).count(),
        "employee_count": Employee.objects.count(),
    }
    return render(request, "core/pages/overview.html", context)