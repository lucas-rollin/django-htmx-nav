"""
Helpdesk demo views, PURE MULTI-PAGE APP baseline.

This module provides the traditional full-page views for the helpdesk demo,
handling navigation for dashboard overviews, projects, tickets, and staff list.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView
from mockdata.models import Employee, Organization, Project, Ticket

from htmx_nav import (
    Swap,
    make_shell_renderer,
    make_shell_view_mixin,
    not_targeting,
    targeting,
    render_htmx,
)

TICKET_PAGE_SIZE = 6


# ---------------------------------------------------------------------------
# Sidebar & Breadcrumbs Helpers
# ---------------------------------------------------------------------------


def _sidebar_swap(
    active_org_id: str | None = None,
    active_project_id: str | None = None,
    active_page: str | None = None,
) -> Swap:
    orgs = Organization.objects.prefetch_related("projects").only("id", "name")

    context = {
        "orgs": orgs,
        "active_org_id": active_org_id,
        "active_project_id": active_project_id,
        "active_page": active_page,
    }

    return Swap("components/_sidebar_menu.html", context, target_id="sidebar")


def _breadcrumb_swap(*crumbs: tuple[str, str | None]) -> Swap:
    """Preset Swap for the breadcrumb fragment."""
    context = {"breadcrumbs": [{"label": label, "url": url} for label, url in crumbs]}
    return Swap("components/_breadcrumbs.html", context, target_id="breadcrumbs")


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def overview(request: HttpRequest) -> HttpResponse:
    """Displays the primary helpdesk dashboard and high-level summary metrics."""
    return render_htmx(
        request, "pages/overview.html", swaps=_sidebar_swap(active_page="overview")
    )


def staff_list(request: HttpRequest) -> HttpResponse:
    """Displays all staff members alongside their currently active ticket counts."""
    employees: list[dict] = []
    for e in Employee.objects.all():
        active_tickets_count = Ticket.objects.filter(
            assignee_id=e.id, status__in=["open", "in_progress"]
        ).count()

        employees.append({"tickets": active_tickets_count, "details": e})

    return render_htmx(
        request,
        "pages/staff_list.html",
        {"employees": employees},
        swaps=_sidebar_swap(active_page="staff_list"),
    )


def org_list(request: HttpRequest) -> HttpResponse:
    """Displays a list of all client organizations."""
    return render_htmx(
        request,
        "pages/org_list.html",
        {"orgs": Organization.objects.all()},
        swaps=_sidebar_swap(active_page="org_list"),
    )


def org_detail(request: HttpRequest, org_id: str) -> HttpResponse:
    """Displays single organization details and its associated projects."""
    org = Organization.objects.get(id=org_id)
    context = {
        "org": org,
        "projects": Project.objects.filter(organization_id=org_id),
    }
    return render_htmx(
        request,
        "pages/org_detail.html",
        context,
        swaps=[
            _sidebar_swap(active_org_id=org_id),
            _breadcrumb_swap(
                ("Organizations", reverse("htmx:org_list")),
                (org.name, None),
            ),
        ],
    )

# ===========================================================================
# ORG / PROJECT DRILL-DOWN
# ===========================================================================


def _project_tab_swap(active_tab: str):
    """
    Build the project tabs Swap to update state in intra page navigation.

    We only want to include this if the Swap targets the "tab-content"
    because a that level the layout expects the tabs to be rendered normally,
    as a non Swap fragment.
    """
    return Swap(
        "components/_project_tabs.html",
        {"active_tab": active_tab},
        target_id="project-tabs",
        include_if=targeting("tab-content"),
        # another possibility:
        # include_if=not_targeting("main-content")
    )


# Build the partial spec.
PROJECT_TAB_PARTIAL = {
    "#tab-cotent": targeting("tab-content"),
    "#content": True,
}
"""
It reads:
- If the HX-Target is "tab-content" render the "#tab-content" partial.
- Else if it's an HTMX request render the "#content" partial
- Else, it's not an HTMX request, render the full page.
"""


def project_overview(
    request: HttpRequest, org_id: str, project_id: str
) -> HttpResponse:
    """Displays the overview dashboard tab for a specific project."""
    org = Organization.objects.get(id=org_id)
    project = Project.objects.get(id=project_id)
    context = {
        "org": org,
        "project": project,
    }
    return render_htmx(
        request,
        "pages/project.html",
        context,
        partial=PROJECT_TAB_PARTIAL,
        swaps=[
            _sidebar_swap(active_org_id=org_id, active_project_id=project_id),
            _breadcrumb_swap(
                ("Organizations", reverse("htmx:org_list")),
                (org.name, reverse("htmx:org_detail", args=[org_id])),
                (project.name, None),
            ),
            _project_tab_swap(active_tab="overview"),
        ],
    )


def project_team(request: HttpRequest, org_id: str, project_id: str) -> HttpResponse:
    """Displays assigned staff members under a project's Team tab."""
    org = Organization.objects.get(id=org_id)
    project = Project.objects.get(id=project_id)
    team_members = Employee.objects.filter(tickets__project_id=project_id).distinct()

    context = {
        "org": org,
        "project": project,
        "team": team_members,
    }
    return render_htmx(
        request,
        "pages/project.html",
        context,
        partial=PROJECT_TAB_PARTIAL,
        swaps=[
            _sidebar_swap(active_org_id=org_id, active_project_id=project_id),
            _breadcrumb_swap(
                ("Organizations", reverse("htmx:org_list")),
                (org.name, reverse("htmx:org_detail", args=[org_id])),
                (
                    project.name,
                    reverse("htmx:project_overview", args=[org_id, project_id]),
                ),
                ("Team", None),
            ),
            _project_tab_swap(active_tab="team"),
        ],
    )


def project_settings(
    request: HttpRequest, org_id: str, project_id: str, subtab: str = "general"
) -> HttpResponse:
    """Displays configurable settings for a project under specific sub-tabs."""
    if subtab not in ("general", "permissions", "danger"):
        subtab = "general"

    org = Organization.objects.get(id=org_id)
    project = Project.objects.get(id=project_id)
    context = {
        "org": org,
        "project": project,
        "active_subtab": subtab,
    }
    return render_htmx(
        request,
        "pages/project.html",
        context,
        partial=PROJECT_TAB_PARTIAL,
        swaps=[
            _sidebar_swap(active_org_id=org_id, active_project_id=project_id),
            _breadcrumb_swap(
                ("Organizations", reverse("htmx:org_list")),
                (org.name, reverse("htmx:org_detail", args=[org_id])),
                (
                    project.name,
                    reverse("htmx:project_overview", args=[org_id, project_id]),
                ),
                ("Settings", None),
            ),
            _project_tab_swap(active_tab="settings"),
        ],
    )


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
        "htmx:kanban_board", org_id=project.organization.id, project_id=project.id
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
        "org": org,
        "project": project,
        "columns": columns,
        "active_tab": "board",
    }
    return render_htmx(
        request,
        "pages/project.html",
        context,
        partial=PROJECT_TAB_PARTIAL,
        swaps=[
            _sidebar_swap(active_org_id=org_id, active_project_id=project_id),
            _breadcrumb_swap(
                ("Organizations", reverse("htmx:org_list")),
                (org.name, reverse("htmx:org_detail", args=[org_id])),
                (
                    project.name,
                    reverse("htmx:project_overview", args=[org_id, project_id]),
                ),
                ("Board", None),
            ),
            _project_tab_swap(active_tab="board")
        ],
    )


# ---------------------------------------------------------------------------
# TICKET LIST — pagination + filtering, as a CBV
# ---------------------------------------------------------------------------

ShellViewMixin = make_shell_view_mixin()


class TicketListView(ShellViewMixin, ListView):
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

        return tickets.order_by("-created_at")

    # Add swaps here
    def get_extra_swaps(self):
        return [
            _sidebar_swap(active_org_id=self.org.id, active_project_id=self.project.id),
            _breadcrumb_swap(
                ("Organizations", reverse("htmx:org_list")),
                (self.org.name, reverse("htmx:org_detail", args=[self.org.id])),
                (
                    self.project.name,
                    reverse(
                        "htmx:project_overview", args=[self.org.id, self.project.id]
                    ),
                ),
                ("Tickets", None),
            ),
        ]

    def get_partial(self):
        return PROJECT_TAB_PARTIAL

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["org"] = self.org
        context["project"] = self.project
        context["current_status"] = self.request.GET.get("status", "")
        context["current_priority"] = self.request.GET.get("priority", "")
        context["current_query"] = self.request.GET.get("q", "")
        context["active_tab"] = "tickets"
        context["employee_names"] = {e.id: e.name for e in Employee.objects.all()}
        return context


# ===========================================================================
# TICKET DETAIL + its "tabs" as full pages
# ===========================================================================


def _ticket_tab_swap(active_tab: str):
    """
    Build the ticket tabs Swap to update state in intra page navigation.
    """
    return Swap(
        "components/_ticket_tabs.html",
        {"active_tab": active_tab},
        target_id="project-tabs",
        include_if=targeting("tab-content"),
    )


TICKET_TAB_PARTIAL = {
    "#tab-cotent": targeting("tab-content"),
    "#content": True,
}


def ticket_detail(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """Displays core metadata, status, and assignee for a single ticket."""
    ticket = Ticket.objects.select_related("project__organization", "assignee").get(
        id=ticket_id
    )
    project = ticket.project
    org = project.organization

    assignee_name = ticket.assignee.name if ticket.assignee else "Unassigned"

    context = {
        "ticket": ticket,
        "assignee_name": assignee_name,
    }
    return render_htmx(
        request,
        "pages/ticket.html",
        context,
        partial=TICKET_TAB_PARTIAL,
        swaps=[
            _sidebar_swap(active_org_id=org.id, active_project_id=project.id),
            _breadcrumb_swap(
                ("Organizations", reverse("htmx:org_list")),
                (org.name, reverse("htmx:org_detail", args=[org.id])),
                (
                    project.name,
                    reverse("htmx:project_overview", args=[org.id, project.id]),
                ),
                (f"#{ticket.id[:8]}", None),
            ),
            _ticket_tab_swap(active_tab="details")
        ],
    )


def ticket_comments(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """Displays the discussion thread and comments for a ticket."""
    ticket = Ticket.objects.select_related("project__organization").get(id=ticket_id)
    project = ticket.project
    org = project.organization

    context = {
        "ticket": ticket,
        "comments": ticket.comments,
    }
    return render_htmx(
        request,
        "pages/ticket.html",
        context,
        partial=TICKET_TAB_PARTIAL,
        swaps=[
            _sidebar_swap(active_org_id=org.id, active_project_id=project.id),
            _breadcrumb_swap(
                ("Organizations", reverse("htmx:org_list")),
                (org.name, reverse("htmx:org_detail", args=[org.id])),
                (
                    project.name,
                    reverse("htmx:project_overview", args=[org.id, project.id]),
                ),
                (f"#{ticket.id[:8]}", reverse("htmx:ticket_detail", args=[ticket.id])),
                ("Comments", None),
            ),
            _ticket_tab_swap(active_tab="comments")
        ],
    )


def ticket_activity(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """Displays the chronological audit trail and status history of a ticket."""
    ticket = Ticket.objects.select_related("project__organization", "assignee").get(
        id=ticket_id
    )
    project = ticket.project
    org = project.organization

    assignee_name = ticket.assignee.name if ticket.assignee else "Unassigned"

    context = {
        "ticket": ticket,
        "activity": [
            f"Ticket created with priority {ticket.priority}",
            f"Assigned to {assignee_name}",
            f"Status set to {ticket.status}",
        ],
    }
    return render_htmx(
        request,
        "pages/ticket.html",
        context,
        partial=TICKET_TAB_PARTIAL,
        swaps=[
            _sidebar_swap(active_org_id=org.id, active_project_id=project.id),
            _breadcrumb_swap(
                ("Organizations", reverse("htmx:org_list")),
                (org.name, reverse("htmx:org_detail", args=[org.id])),
                (
                    project.name,
                    reverse("htmx:project_overview", args=[org.id, project.id]),
                ),
                (f"#{ticket.id[:8]}", reverse("htmx:ticket_detail", args=[ticket.id])),
                ("Activity", None),
            ),
            _ticket_tab_swap(active_tab="activity")
        ],
    )


def ticket_attachments(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """Displays uploaded files and media attached to a ticket."""
    ticket = Ticket.objects.select_related("project__organization").get(id=ticket_id)
    project = ticket.project
    org = project.organization

    context = {
        "ticket": ticket,
    }
    return render_htmx(
        request,
        "pages/ticket.html",
        context,
        partial=TICKET_TAB_PARTIAL,
        swaps=[
            _sidebar_swap(active_org_id=org.id, active_project_id=project.id),
            _breadcrumb_swap(
                ("Organizations", reverse("htmx:org_list")),
                (org.name, reverse("htmx:org_detail", args=[org.id])),
                (
                    project.name,
                    reverse("htmx:project_overview", args=[org.id, project.id]),
                ),
                (f"#{ticket.id[:8]}", reverse("htmx:ticket_detail", args=[ticket.id])),
                ("Attachments", None),
            ),
            _ticket_tab_swap(active_tab="attachments")
        ],
    )


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
                "htmx:ticket_detail",
                ticket_id=fake_new_ticket.id if fake_new_ticket else None,
            )

        next_step = WIZARD_STEPS[current_index + 1]
        return redirect(
            "htmx:ticket_wizard_step",
            org_id=org_id,
            project_id=project_id,
            step=next_step,
        )

    all_employees = Employee.objects.all()

    context = {
        "org": org,
        "project": project,
        "step": step,
        "steps": WIZARD_STEPS,
        "step_index": WIZARD_STEPS.index(step),
        "collected": collected,
        "employees": all_employees,
        "employee_names": {e.id: e.name for e in all_employees},
    }
    return render_htmx(
        request,
        f"pages/wizard_{step}.html",
        context,
        swaps=[
            _sidebar_swap(active_org_id=org_id, active_project_id=project_id),
            _breadcrumb_swap(
                ("Organizations", reverse("htmx:org_list")),
                (org.name, reverse("htmx:org_detail", args=[org_id])),
                (
                    project.name,
                    reverse("htmx:project_overview", args=[org_id, project_id]),
                ),
                ("New Ticket", None),
            ),
        ],
    )
