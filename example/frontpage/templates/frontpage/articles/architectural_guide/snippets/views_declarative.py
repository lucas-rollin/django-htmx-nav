# example/htmx_nav_demo/views_declarative.py
def overview(request: HttpRequest) -> HttpResponse:
    # Views only fetch their own data; sidebar and crumbs are handled automatically:
    context = {
        "org_count": Organization.objects.count(),
        "project_count": Project.objects.count(),
        "open_ticket_count": Ticket.objects.filter(status=Ticket.Status.OPEN).count(),
        "employee_count": Employee.objects.count(),
    }
    return render_shell(request, "core/pages/overview.html", context)