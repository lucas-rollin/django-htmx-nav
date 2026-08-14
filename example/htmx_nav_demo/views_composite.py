"""
Helpdesk demo views using django-htmx-nav.

Demonstrates how to build full-page, multi-level navigation (sidebar,
breadcrumbs, tabs, subtabs) with HTMX out-of-band (OOB) swaps while maintaining
a clean, full-page fallback baseline for non-HTMX requests.
"""

from core.models import Employee, Organization, Project, Ticket
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView

from htmx_nav import (
    Swap,
    make_shell_view_mixin,
    render_nav,
    targeting,
)

NAMESPACE = "htmx_nav_composite"
TICKET_PAGE_SIZE = 6


# ---------------------------------------------------------------------------
# Sidebar & Breadcrumb OOB Swap Helpers
# ---------------------------------------------------------------------------


def _sidebar_swap(
    active_org_id: str | None = None,
    active_project_id: str | None = None,
    active_page: str | None = None,
) -> Swap:
    """Return an out-of-band Swap fragment for updating the main sidebar navigation.

    Generates a `Swap` instance targeting HTML element ID `#sidebar`. When included
    in `render_nav`, HTMX swaps this fragment OOB to update active navigation
    states without re-rendering the outer shell.

    Args:
        active_org_id: ID of the currently selected organization, if any.
        active_project_id: ID of the currently selected project, if any.
        active_page: Key identifying the currently active top-level page/link.
    """
    orgs = Organization.objects.prefetch_related("projects").only("id", "name")

    context = {
        "orgs": orgs,
        "active_org_id": active_org_id,
        "active_project_id": active_project_id,
        "active_page": active_page,
    }

    return Swap("components/_sidebar_menu.html", context, target_id="sidebar")


def _breadcrumb_swap(*crumbs: tuple[str, str | None]) -> Swap:
    """Return an out-of-band Swap fragment for updating breadcrumb navigation.

    Generates a `Swap` instance targeting HTML element ID `#breadcrumbs`.

    Args:
        *crumbs: Tuples in the format `(label, url)`. If `url` is None, the item
            is treated as the current (non-clickable) active breadcrumb.
    """
    context = {"breadcrumbs": [{"label": label, "url": url} for label, url in crumbs]}
    return Swap("components/_breadcrumbs.html", context, target_id="breadcrumbs")


# ---------------------------------------------------------------------------
# Top-Level Dashboard Pages
# ---------------------------------------------------------------------------


def overview(request: HttpRequest) -> HttpResponse:
    """Display the main helpdesk overview dashboard."""
    return render_nav(
        request,
        "pages/overview.html",
        swaps=[
            _sidebar_swap(active_page="overview"),
            _breadcrumb_swap(("helpdesk", None)),
        ],
        title="Organizations · Helpdesk",
    )


def staff_list(request: HttpRequest) -> HttpResponse:
    """Display the staff directory along with active ticket counts.

    Demonstrates rendering a standalone partial template (`pages/_staff_list.html`)
    for HTMX partial updates rather than using Django 6+ inline template block syntax.
    """
    employees: list[dict] = []
    for e in Employee.objects.all():
        active_tickets_count = Ticket.objects.filter(
            assignee_id=e.id, status__in=["open", "in_progress"]
        ).count()

        employees.append({"tickets": active_tickets_count, "details": e})

    return render_nav(
        request,
        "pages/staff_list.html",
        {"employees": employees},
        partial="pages/_staff_list.html",  # Explicit standalone template partial
        swaps=[
            _sidebar_swap(active_page="staff_list"),
            _breadcrumb_swap(("helpdesk", None)),
        ],
        title="Staff · Helpdesk",
    )


def org_list(request: HttpRequest) -> HttpResponse:
    """Display a list of all client organizations."""
    return render_nav(
        request,
        "pages/org_list.html",
        {"orgs": Organization.objects.all()},
        swaps=[
            _sidebar_swap(active_page="org_list"),
            _breadcrumb_swap(("helpdesk", None)),
        ],
        title="Organizations · Helpdesk",
    )


def org_detail(request: HttpRequest, org_id: str) -> HttpResponse:
    """Display details and associated projects for a single organization."""
    org = Organization.objects.get(id=org_id)
    context = {
        "org": org,
        "projects": Project.objects.filter(organization_id=org_id),
    }
    return render_nav(
        request,
        "pages/org_detail.html",
        context,
        swaps=[
            _sidebar_swap(active_org_id=org_id),
            _breadcrumb_swap(
                ("Organizations", reverse(f"{NAMESPACE}:org_list")),
                (org.name, None),
            ),
        ],
        title=f"{org.name} · Helpdesk",
    )


# ===========================================================================
# Project Detail Views (Tabbed Navigation)
# ===========================================================================


def project_overview(
    request: HttpRequest, org_id: str, project_id: str
) -> HttpResponse:
    """Display the project overview tab."""
    org = Organization.objects.get(id=org_id)
    project = Project.objects.get(id=project_id)
    context = {
        "org": org,
        "project": project,
        "active_tab": "overview",
    }
    return render_nav(
        request,
        "pages/project.html",
        context,
        swaps=[
            _sidebar_swap(active_org_id=org_id, active_project_id=project_id),
            _breadcrumb_swap(
                ("Organizations", reverse(f"{NAMESPACE}:org_list")),
                (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org_id])),
                (project.name, None),
            ),
        ],
        title=f"{project.name} · {org.name}",
    )


def project_team(request: HttpRequest, org_id: str, project_id: str) -> HttpResponse:
    """Display assigned team members under the project's Team tab."""
    org = Organization.objects.get(id=org_id)
    project = Project.objects.get(id=project_id)
    team_members = Employee.objects.filter(tickets__project_id=project_id).distinct()

    context = {
        "org": org,
        "project": project,
        "active_tab": "team",
        "team": team_members,
    }
    return render_nav(
        request,
        "pages/project.html",
        context,
        swaps=[
            _sidebar_swap(active_org_id=org_id, active_project_id=project_id),
            _breadcrumb_swap(
                ("Organizations", reverse(f"{NAMESPACE}:org_list")),
                (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org_id])),
                (
                    project.name,
                    reverse(f"{NAMESPACE}:project_overview", args=[org_id, project_id]),
                ),
                ("Team", None),
            ),
        ],
        title=f"{project.name} · {org.name}",
    )


def project_settings(
    request: HttpRequest, org_id: str, project_id: str, subtab: str = "general"
) -> HttpResponse:
    """Display configurable project settings with support for nested subtabs."""
    if subtab not in ("general", "permissions", "danger"):
        subtab = "general"

    org = Organization.objects.get(id=org_id)
    project = Project.objects.get(id=project_id)
    context = {
        "org": org,
        "project": project,
        "active_tab": "settings",
        "active_subtab": subtab,
    }

    return render_nav(
        request,
        "pages/project.html",
        context,
        swaps=[
            _sidebar_swap(active_org_id=org_id, active_project_id=project_id),
            _breadcrumb_swap(
                ("Organizations", reverse(f"{NAMESPACE}:org_list")),
                (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org_id])),
                (
                    project.name,
                    reverse(f"{NAMESPACE}:project_overview", args=[org_id, project_id]),
                ),
                ("Settings", None),
            ),
        ],
        title=f"{project.name} · {org.name}",
    )


# ---------------------------------------------------------------------------
# Kanban Board Views
# ---------------------------------------------------------------------------


@require_http_methods(["POST"])
def ticket_move_status(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """Update a ticket's status and redirect back to the Kanban board.

    Standard POST-redirect-GET handler. Works seamlessly with both HTMX form
    submissions and standard browser form posts.
    """
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
    """Display project tickets structured in visual status columns on a Kanban board.

    Demonstrates mapping target conditions directly using a dict spec for `partial`:
    - Renders target fragment `pages/_board.html` when targeting "tab-content".
    - Fallback target `#content` renders the primary content shell.
    """
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
    return render_nav(
        request,
        "pages/project.html",
        context,
        partial={"pages/_board.html": targeting("tab-content"), "#content": True},
        swaps=[
            _sidebar_swap(active_org_id=org_id, active_project_id=project_id),
            _breadcrumb_swap(
                ("Organizations", reverse(f"{NAMESPACE}:org_list")),
                (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org_id])),
                (
                    project.name,
                    reverse(f"{NAMESPACE}:project_overview", args=[org_id, project_id]),
                ),
                ("Board", None),
            ),
        ],
        title=f"{project.name} · {org.name}",
    )


# ---------------------------------------------------------------------------
# Ticket List View (Class-Based View Example)
# ---------------------------------------------------------------------------

ShellViewMixin = make_shell_view_mixin()


class TicketListView(ShellViewMixin, ListView):
    """Paginated and filterable ticket list view integrated with ShellViewMixin.

    Demonstrates class-based view (CBV) integration using `ShellViewMixin`.
    The mixin hook methods (`get_extra_swaps`, `get_partial`, `title`) align CBV
    lifecycle methods directly with the behavior of `render_nav`.
    """

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

    def title(self) -> str:
        return f"{self.project.name} · {self.org.name}"

    def get_extra_swaps(self) -> list[Swap]:
        return [
            _sidebar_swap(active_org_id=self.org.id, active_project_id=self.project.id),
            _breadcrumb_swap(
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
            ),
        ]

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
# Ticket Detail Views (Full Page URLs with Tab UI)
# ===========================================================================


def ticket_detail(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """Display core details, status, and assignment for a single ticket."""
    ticket = Ticket.objects.select_related("project__organization", "assignee").get(
        id=ticket_id
    )
    project = ticket.project
    org = project.organization

    assignee_name = ticket.assignee.name if ticket.assignee else "Unassigned"

    context = {
        "ticket": ticket,
        "assignee_name": assignee_name,
        "active_tab": "details",
    }
    return render_nav(
        request,
        "pages/ticket.html",
        context,
        swaps=[
            _sidebar_swap(active_org_id=org.id, active_project_id=project.id),
            _breadcrumb_swap(
                ("Organizations", reverse(f"{NAMESPACE}:org_list")),
                (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org.id])),
                (
                    project.name,
                    reverse(f"{NAMESPACE}:project_overview", args=[org.id, project.id]),
                ),
                (f"#{ticket.id[:8]}", None),
            ),
        ],
        title=f"#{ticket.id[:8]} · {ticket.title}",
    )


def ticket_comments(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """Display discussion threads and comments attached to a ticket."""
    ticket = Ticket.objects.select_related("project__organization").get(id=ticket_id)
    project = ticket.project
    org = project.organization

    context = {
        "ticket": ticket,
        "active_tab": "comments",
        "comments": ticket.comments,
    }
    return render_nav(
        request,
        "pages/ticket.html",
        context,
        swaps=[
            _sidebar_swap(active_org_id=org.id, active_project_id=project.id),
            _breadcrumb_swap(
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
        ],
        title=f"#{ticket.id[:8]} · {ticket.title}",
    )


def ticket_activity(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """Display the chronological event audit trail and status changes for a ticket."""
    ticket = Ticket.objects.select_related("project__organization", "assignee").get(
        id=ticket_id
    )
    project = ticket.project
    org = project.organization

    assignee_name = ticket.assignee.name if ticket.assignee else "Unassigned"

    context = {
        "ticket": ticket,
        "active_tab": "activity",
        "activity": [
            f"Ticket created with priority {ticket.priority}",
            f"Assigned to {assignee_name}",
            f"Status set to {ticket.status}",
        ],
    }
    return render_nav(
        request,
        "pages/ticket.html",
        context,
        swaps=[
            _sidebar_swap(active_org_id=org.id, active_project_id=project.id),
            _breadcrumb_swap(
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
        ],
        title=f"#{ticket.id[:8]} · {ticket.title}",
    )


def ticket_attachments(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """Display uploaded files and attachments related to a ticket."""
    ticket = Ticket.objects.select_related("project__organization").get(id=ticket_id)
    project = ticket.project
    org = project.organization

    context = {
        "ticket": ticket,
        "active_tab": "attachments",
    }

    return render_nav(
        request,
        "pages/ticket.html",
        context,
        swaps=[
            _sidebar_swap(active_org_id=org.id, active_project_id=project.id),
            _breadcrumb_swap(
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
        ],
        title=f"#{ticket.id[:8]} · {ticket.title}",
    )


# ---------------------------------------------------------------------------
# Multi-Step Creation Wizard (POST / Redirect / GET Flow)
# ---------------------------------------------------------------------------

WIZARD_STEPS = ["basics", "assignment", "review"]
WIZARD_SESSION_KEY = "new_ticket_wizard"


def _wizard_data(
    request: HttpRequest, org_id: str, project_id: str
) -> tuple[str, dict]:
    """Retrieve session storage key and collected state dictionary for a wizard instance."""
    key = f"{WIZARD_SESSION_KEY}:{org_id}:{project_id}"
    return key, request.session.get(key, {})


@require_http_methods(["GET", "POST"])
def ticket_wizard_step(
    request: HttpRequest, org_id: str, project_id: str, step: str
) -> HttpResponse:
    """Handle multi-step ticket creation ("basics" -> "assignment" -> "review").

    Implements a POST-Redirect-GET pattern using Django sessions for state storage.
    HTMX forms submit via POST, save step context to session, and redirect to the
    next step's URL. `django-htmx-nav` handles standard redirects cleanly across
    HTMX and full-page request models.
    """
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
            # Demo-only: simulated creation landing view
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
        "org": org,
        "project": project,
        "step": step,
        "collected": collected,
        "employees": all_employees,
        "employee_names": {e.id: e.name for e in all_employees},
    }
    return render_nav(
        request,
        "pages/wizard.html",
        context,
        swaps=[
            _sidebar_swap(active_org_id=org_id, active_project_id=project_id),
            _breadcrumb_swap(
                ("Organizations", reverse(f"{NAMESPACE}:org_list")),
                (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org_id])),
                (
                    project.name,
                    reverse(f"{NAMESPACE}:project_overview", args=[org_id, project_id]),
                ),
                ("New Ticket", None),
            ),
        ],
        title=f"New ticket · {step}",
    )
