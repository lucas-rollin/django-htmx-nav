"""
Helpdesk demo views, PURE MULTI-PAGE APP baseline.

This module provides the traditional full-page views for the helpdesk demo,
handling navigation for dashboard overviews, projects, tickets, and staff list.
"""

from core.models import Employee, Organization, Project, Ticket
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView

NAMESPACE = "mpa"
TICKET_PAGE_SIZE = 6


# ---------------------------------------------------------------------------
# Sidebar & Breadcrumbs Helpers
# ---------------------------------------------------------------------------


def _sidebar_context(
    active_org_id: str | None = None,
    active_project_id: str | None = None,
    active_page: str | None = None,
):
    orgs = Organization.objects.prefetch_related("projects").only("id", "name")

    return {
        "orgs": orgs,
        "active_org_id": active_org_id,
        "active_project_id": active_project_id,
        "active_page": active_page,
    }


def _breadcrumbs(*crumbs: tuple[str, str | None]):
    """crumbs: list of (label, url_or_None) tuples."""
    return {"breadcrumbs": [{"label": label, "url": url} for label, url in crumbs]}


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def overview(request: HttpRequest) -> HttpResponse:
    """Displays the primary helpdesk dashboard and high-level summary metrics."""
    context = {
        **_sidebar_context(active_page="overview"),
    }

    return render(request, "pages/overview.html", context)


def staff_list(request: HttpRequest) -> HttpResponse:
    """Displays all staff members alongside their currently active ticket counts."""
    employees: list[dict] = []
    for e in Employee.objects.all():
        active_tickets_count = Ticket.objects.filter(
            assignee_id=e.id, status__in=["open", "in_progress"]
        ).count()

        employees.append({"tickets": active_tickets_count, "details": e})

    context = {
        **_sidebar_context(active_page="staff_list"),
        "employees": employees,
    }
    return render(request, "pages/staff_list.html", context)


def org_list(request: HttpRequest) -> HttpResponse:
    """Displays a list of all client organizations."""
    context = {
        **_sidebar_context(active_page="org_list"),
        "orgs": Organization.objects.all(),
    }
    return render(request, "pages/org_list.html", context)


# ---------------------------------------------------------------------------
# ORG / PROJECT DRILL-DOWN — plain full-page navigation
# ---------------------------------------------------------------------------


def org_detail(request: HttpRequest, org_id: str) -> HttpResponse:
    """Displays single organization details and its associated projects."""
    org = Organization.objects.get(id=org_id)
    context = {
        **_sidebar_context(active_org_id=org_id),
        **_breadcrumbs(
            ("Organizations", reverse(f"{NAMESPACE}:org_list")),
            (org.name, None),
        ),
        "org": org,
        "projects": Project.objects.filter(organization_id=org_id),
    }
    return render(request, "pages/org_detail.html", context)


def project_overview(
    request: HttpRequest, org_id: str, project_id: str
) -> HttpResponse:
    """Displays the overview dashboard tab for a specific project."""
    org = Organization.objects.get(id=org_id)
    project = Project.objects.get(id=project_id)
    context = {
        **_sidebar_context(active_org_id=org_id, active_project_id=project_id),
        **_breadcrumbs(
            ("Organizations", reverse(f"{NAMESPACE}:org_list")),
            (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org_id])),
            (project.name, None),
        ),
        "org": org,
        "project": project,
        "active_tab": "overview",
    }
    return render(request, "pages/project.html", context)


def project_team(request: HttpRequest, org_id: str, project_id: str) -> HttpResponse:
    """Displays assigned staff members under a project's Team tab."""
    org = Organization.objects.get(id=org_id)
    project = Project.objects.get(id=project_id)
    team_members = Employee.objects.filter(tickets__project_id=project_id).distinct()

    context = {
        **_sidebar_context(active_org_id=org_id, active_project_id=project_id),
        **_breadcrumbs(
            ("Organizations", reverse(f"{NAMESPACE}:org_list")),
            (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org_id])),
            (
                project.name,
                reverse(f"{NAMESPACE}:project_overview", args=[org_id, project_id]),
            ),
            ("Team", None),
        ),
        "org": org,
        "project": project,
        "active_tab": "team",
        "team": team_members,
    }
    return render(request, "pages/project.html", context)


def project_settings(
    request: HttpRequest, org_id: str, project_id: str, subtab: str = "general"
) -> HttpResponse:
    """Displays configurable settings for a project under specific sub-tabs."""
    if subtab not in ("general", "permissions", "danger"):
        subtab = "general"

    org = Organization.objects.get(id=org_id)
    project = Project.objects.get(id=project_id)
    context = {
        **_sidebar_context(active_org_id=org_id, active_project_id=project_id),
        **_breadcrumbs(
            ("Organizations", reverse(f"{NAMESPACE}:org_list")),
            (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org_id])),
            (
                project.name,
                reverse(f"{NAMESPACE}:project_overview", args=[org_id, project_id]),
            ),
            ("Settings", None),
        ),
        "org": org,
        "project": project,
        "active_tab": "settings",
        "active_subtab": subtab,
    }
    return render(request, "pages/project.html", context)


# ---------------------------------------------------------------------------
# KANBAN BOARD — full-page form posts, no partial card updates
# ---------------------------------------------------------------------------


@require_http_methods(["POST"])
def ticket_move_status(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """Updates a ticket's status state and redirects to the Kanban board."""
    ticket = Ticket.objects.get(id=ticket_id)
    new_status = request.POST.get("new_status")
    if new_status in ("open", "in_progress", "resolved", "closed"):
        ticket.status = new_status
        ticket.save(update_fields=["status"])
    project = ticket.project
    return redirect(
        f"{NAMESPACE}:kanban_board",
        org_id=project.organization.id,
        project_id=project.id,
    )


def kanban_board(request: HttpRequest, org_id: str, project_id: str) -> HttpResponse:
    """Displays project tickets grouped into visual status columns on a Kanban board."""
    org = Organization.objects.get(id=org_id)
    project = Project.objects.get(id=project_id)

    columns = {
        status: Ticket.objects.filter(
            project_id=project_id, status=status
        ).select_related("assignee")
        for status in ("open", "in_progress", "resolved", "closed")
    }

    context = {
        **_sidebar_context(active_org_id=org_id, active_project_id=project_id),
        **_breadcrumbs(
            ("Organizations", reverse(f"{NAMESPACE}:org_list")),
            (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org_id])),
            (
                project.name,
                reverse(f"{NAMESPACE}:project_overview", args=[org_id, project_id]),
            ),
            ("Board", None),
        ),
        "org": org,
        "project": project,
        "columns": columns,
        "active_tab": "board",
    }
    return render(request, "pages/project.html", context)


# ---------------------------------------------------------------------------
# TICKET LIST — pagination + filtering, as a CBV
# ---------------------------------------------------------------------------


class TicketListView(ListView):
    """Displays a paginated, searchable, and filterable table of project tickets."""

    template_name = "pages/project.html"
    context_object_name = "tickets"
    paginate_by = TICKET_PAGE_SIZE

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.org = Organization.objects.get(id=kwargs["org_id"])
        self.project = Project.objects.get(id=kwargs["project_id"])

    def get_queryset(self):
        tickets = Ticket.objects.filter(project_id=self.project.id).select_related(
            "assignee"
        )

        status = self.request.GET.get("status")
        if status:
            tickets = tickets.filter(status=status)

        priority = self.request.GET.get("priority")
        if priority:
            tickets = tickets.filter(priority=int(priority))

        search = self.request.GET.get("q", "").strip()
        if search:
            tickets = tickets.filter(title__icontains=search)

        # Sort tickets reverse chronologically by creation timestamp
        return tickets.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            _sidebar_context(
                active_org_id=self.org.id, active_project_id=self.project.id
            )
        )
        context.update(
            _breadcrumbs(
                ("Organizations", reverse(f"{NAMESPACE}:org_list")),
                (self.org.name, reverse(f"{NAMESPACE}:org_detail", args=[self.org.id])),
                (
                    self.project.name,
                    reverse(
                        f"{NAMESPACE}:project_overview",
                        args=[self.org.id, self.project.id],
                    ),
                ),
                ("Tickets", None),
            )
        )
        context["org"] = self.org
        context["project"] = self.project
        context["current_status"] = self.request.GET.get("status", "")
        context["current_priority"] = self.request.GET.get("priority", "")
        context["current_query"] = self.request.GET.get("q", "")
        context["active_tab"] = "tickets"
        context["employee_names"] = {e.id: e.name for e in Employee.objects.all()}
        return context


# ---------------------------------------------------------------------------
# TICKET DETAIL + its "tabs" as full pages
# ---------------------------------------------------------------------------


def ticket_detail(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """Displays core metadata, status, and assignee for a single ticket."""
    ticket = Ticket.objects.select_related("project__organization", "assignee").get(
        id=ticket_id
    )
    project = ticket.project
    org = project.organization

    assignee_name = ticket.assignee.name if ticket.assignee else "Unassigned"

    context = {
        **_sidebar_context(active_org_id=org.id, active_project_id=project.id),
        **_breadcrumbs(
            ("Organizations", reverse(f"{NAMESPACE}:org_list")),
            (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org.id])),
            (
                project.name,
                reverse(f"{NAMESPACE}:project_overview", args=[org.id, project.id]),
            ),
            (f"#{ticket.id[:8]}", None),
        ),
        "ticket": ticket,
        "assignee_name": assignee_name,
        "active_tab": "details",
    }
    return render(request, "pages/ticket.html", context)


def ticket_comments(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """Displays the discussion thread and comments for a ticket."""
    ticket = Ticket.objects.select_related("project__organization").get(id=ticket_id)
    project = ticket.project
    org = project.organization

    context = {
        **_sidebar_context(active_org_id=org.id, active_project_id=project.id),
        **_breadcrumbs(
            ("Organizations", reverse(f"{NAMESPACE}:org_list")),
            (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org.id])),
            (
                project.name,
                reverse(f"{NAMESPACE}:project_overview", args=[org.id, project.id]),
            ),
            (
                f"#{ticket.id[:8]}",
                reverse(f"{NAMESPACE}:ticket_detail", args=[ticket.id]),
            ),
            ("Comments", None),
        ),
        "ticket": ticket,
        "active_tab": "comments",
        "comments": ticket.comments,
    }
    return render(request, "pages/ticket.html", context)


def ticket_activity(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """Displays the chronological audit trail and status history of a ticket."""
    ticket = Ticket.objects.select_related("project__organization", "assignee").get(
        id=ticket_id
    )
    project = ticket.project
    org = project.organization

    assignee_name = ticket.assignee.name if ticket.assignee else "Unassigned"

    context = {
        **_sidebar_context(active_org_id=org.id, active_project_id=project.id),
        **_breadcrumbs(
            ("Organizations", reverse(f"{NAMESPACE}:org_list")),
            (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org.id])),
            (
                project.name,
                reverse(f"{NAMESPACE}:project_overview", args=[org.id, project.id]),
            ),
            (
                f"#{ticket.id[:8]}",
                reverse(f"{NAMESPACE}:ticket_detail", args=[ticket.id]),
            ),
            ("Activity", None),
        ),
        "ticket": ticket,
        "active_tab": "activity",
        "activity": [
            f"Ticket created with priority {ticket.priority}",
            f"Assigned to {assignee_name}",
            f"Status set to {ticket.status}",
        ],
    }
    return render(request, "pages/ticket.html", context)


def ticket_attachments(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """Displays uploaded files and media attached to a ticket."""
    ticket = Ticket.objects.select_related("project__organization").get(id=ticket_id)
    project = ticket.project
    org = project.organization

    context = {
        **_sidebar_context(active_org_id=org.id, active_project_id=project.id),
        **_breadcrumbs(
            ("Organizations", reverse(f"{NAMESPACE}:org_list")),
            (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org.id])),
            (
                project.name,
                reverse(f"{NAMESPACE}:project_overview", args=[org.id, project.id]),
            ),
            (
                f"#{ticket.id[:8]}",
                reverse(f"{NAMESPACE}:ticket_detail", args=[ticket.id]),
            ),
            ("Attachments", None),
        ),
        "ticket": ticket,
        "active_tab": "attachments",
    }
    return render(request, "pages/ticket.html", context)


# ---------------------------------------------------------------------------
# MULTI-STEP WIZARD — real multi-page POST/redirect/GET flow
# ---------------------------------------------------------------------------

WIZARD_STEPS = ["basics", "assignment", "review"]
WIZARD_SESSION_KEY = "new_ticket_wizard"


def _wizard_data(request, org_id, project_id):
    key = f"{WIZARD_SESSION_KEY}:{org_id}:{project_id}"
    return key, request.session.get(key, {})


@require_http_methods(["GET", "POST"])
def ticket_wizard_step(
    request: HttpRequest, org_id: str, project_id: str, step: str
) -> HttpResponse:
    """Displays current step form in ticket creation workflow (basics, assignment, or review)."""
    if step not in WIZARD_STEPS:
        step = WIZARD_STEPS[0]

    org = Organization.objects.get(id=org_id)
    project = Project.objects.get(id=project_id)
    session_key, collected = _wizard_data(request, org_id, project_id)

    if request.method == "POST":
        collected = {**collected, **request.POST.dict()}
        request.session[session_key] = collected

        current_index = WIZARD_STEPS.index(step)
        if step == "review":
            request.session.pop(session_key, None)
            # Demo-only, just simulate ticket creation.
            fake_new_ticket = Ticket.objects.first()
            return redirect(
                f"{NAMESPACE}:ticket_detail",
                ticket_id=fake_new_ticket.id if fake_new_ticket else None,
            )

        next_step = WIZARD_STEPS[current_index + 1]
        return redirect(
            f"{NAMESPACE}:ticket_wizard_step",
            org_id=org_id,
            project_id=project_id,
            step=next_step,
        )

    all_employees = Employee.objects.all()

    context = {
        **_sidebar_context(active_org_id=org_id, active_project_id=project_id),
        **_breadcrumbs(
            ("Organizations", reverse(f"{NAMESPACE}:org_list")),
            (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org_id])),
            (
                project.name,
                reverse(f"{NAMESPACE}:project_overview", args=[org_id, project_id]),
            ),
            ("New Ticket", None),
        ),
        "org": org,
        "project": project,
        "step": step,
        "steps": WIZARD_STEPS,
        "step_index": WIZARD_STEPS.index(step),
        "collected": collected,
        "employees": all_employees,
        "employee_names": {e.id: e.name for e in all_employees},
        # Pass title as context since it varies and a single template was used
        "title": f"New ticket · {step}",
    }
    return render(request, f"pages/wizard_{step}.html", context)
