"""
Helpdesk demo views, VANILLA HTMX variant.

One helper, `get_template()`, picks a full template or its HTMX "shell"
companion. Everything else, context building, OOB swaps, title
injection, is plain Django: `render()`, dicts, and `{% include %}`.

The shells live in templates/vanilla_htmx/ and do the swapping themselves:

    <div id="sidebar" hx-swap-oob="innerHTML">{% include "core/components/_sidebar_menu.html" %}</div>
    <div id="breadcrumbs" hx-swap-oob="innerHTML">{% include "core/components/_breadcrumbs.html" %}</div>
    {% include "core/pages/overview.html#content" %}
    <title>{{ title }}</title>
"""

from core.models import Employee, Organization, Project, Ticket
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView

NAMESPACE = "vanilla_htmx_composite"
TICKET_PAGE_SIZE = 6


# ---------------------------------------------------------------------------
# The only helper. Full load -> template_name. HTMX request -> its shell.
# ---------------------------------------------------------------------------


def get_template(request: HttpRequest, template_name: str) -> str:
    if request.headers.get("HX-Request", "") == "true":
        name = template_name.rsplit("/", 1)[-1]
        return f"vanilla_htmx_composite/_{name}"
    return template_name


# ---------------------------------------------------------------------------
# Plain-dict context helpers, same shape as mpa/views.py.
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
    return {"breadcrumbs": [{"label": label, "url": url} for label, url in crumbs]}


def _project_tabs(request, active: str) -> dict:
    org_id = request.resolver_match.kwargs["org_id"]
    project_id = request.resolver_match.kwargs["project_id"]
    specs = [
        ("overview", "Overview", "project_overview"),
        ("tickets", "Tickets", "ticket_list"),
        ("board", "Board", "kanban_board"),
        ("team", "Team", "project_team"),
        ("settings", "Settings", "project_settings"),
    ]
    ns = request.resolver_match.namespace
    tabs_context = [
        {
            "key": key,
            "label": label,
            "url": reverse(f"{ns}:{view_name}", args=[org_id, project_id]),
            "active": key == active,
        }
        for key, label, view_name in specs
    ]
    return {"active_tab": active, "tabs": tabs_context}


def _ticket_tabs(request, ticket, active: str) -> dict:
    ns = request.resolver_match.namespace
    specs = [
        ("details", "Details", "ticket_detail", None),
        ("comments", "Comments", "ticket_comments", len(ticket.comments) or None),
        ("activity", "Activity", "ticket_activity", None),
        ("attachments", "Attachments", "ticket_attachments", None),
    ]
    tabs_context = [
        {
            "key": key,
            "label": label,
            "badge": badge,
            "active": key == active,
            "url": reverse(f"{ns}:{view_name}", args=[ticket.id]),
        }
        for key, label, view_name, badge in specs
    ]
    return {"active_tab": active, "tabs": tabs_context}


# ---------------------------------------------------------------------------
# Top-Level Dashboard Pages
# ---------------------------------------------------------------------------


def overview(request: HttpRequest) -> HttpResponse:
    context = {
        **_sidebar_context(active_page="overview"),
        **_breadcrumbs(("helpdesk", None)),
        "title": "Organizations · Helpdesk",
    }
    return render(request, get_template(request, "core/pages/overview.html"), context)


def staff_list(request: HttpRequest) -> HttpResponse:
    employees: list[dict] = []
    for e in Employee.objects.all():
        active_tickets_count = Ticket.objects.filter(
            assignee_id=e.id, status__in=["open", "in_progress"]
        ).count()
        employees.append({"tickets": active_tickets_count, "details": e})

    context = {
        **_sidebar_context(active_page="staff_list"),
        **_breadcrumbs(("helpdesk", None)),
        "employees": employees,
        "title": "Staff · Helpdesk",
    }
    return render(request, get_template(request, "core/pages/staff_list.html"), context)


def org_list(request: HttpRequest) -> HttpResponse:
    context = {
        **_sidebar_context(active_page="org_list"),
        **_breadcrumbs(("helpdesk", None)),
        "orgs": Organization.objects.all(),
        "title": "Organizations · Helpdesk",
    }
    return render(request, get_template(request, "core/pages/org_list.html"), context)


def org_detail(request: HttpRequest, org_id: str) -> HttpResponse:
    org = Organization.objects.get(id=org_id)
    context = {
        **_sidebar_context(active_org_id=org_id),
        **_breadcrumbs(
            ("Organizations", reverse(f"{NAMESPACE}:org_list")),
            (org.name, None),
        ),
        "org": org,
        "projects": Project.objects.filter(organization_id=org_id),
        "title": f"{org.name} · Helpdesk",
    }
    return render(request, get_template(request, "core/pages/org_detail.html"), context)


# ===========================================================================
# Project Detail Views (Tabbed Navigation)
# ===========================================================================


def project_overview(
    request: HttpRequest, org_id: str, project_id: str
) -> HttpResponse:
    org = Organization.objects.get(id=org_id)
    project = Project.objects.get(id=project_id)
    context = {
        **_sidebar_context(active_org_id=org_id, active_project_id=project_id),
        **_breadcrumbs(
            ("Organizations", reverse(f"{NAMESPACE}:org_list")),
            (org.name, reverse(f"{NAMESPACE}:org_detail", args=[org_id])),
            (project.name, None),
        ),
        **_project_tabs(request, active="overview"),
        "org": org,
        "project": project,
        "title": f"{project.name} · {org.name}",
    }
    return render(request, get_template(request, "core/pages/project.html"), context)


def project_team(request: HttpRequest, org_id: str, project_id: str) -> HttpResponse:
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
        **_project_tabs(request, active="team"),
        "org": org,
        "project": project,
        "team": team_members,
        "title": f"{project.name} · {org.name}",
    }
    return render(request, get_template(request, "core/pages/project.html"), context)


def project_settings(
    request: HttpRequest, org_id: str, project_id: str, subtab: str = "general"
) -> HttpResponse:
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
        **_project_tabs(request, active="settings"),
        "org": org,
        "project": project,
        "active_subtab": subtab,
        "title": f"{project.name} · {org.name}",
    }
    return render(request, get_template(request, "core/pages/project.html"), context)


# ---------------------------------------------------------------------------
# Kanban Board
# ---------------------------------------------------------------------------


@require_http_methods(["POST"])
def ticket_move_status(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """
    A pinpoint update, not a page/shell swap — there's no "shell" to
    pick here, just a couple of OOB fragments built by hand, same as
    you'd write in any bare htmx + Django view.
    """
    ticket = Ticket.objects.get(id=ticket_id)
    old_status = ticket.status
    new_status = request.POST.get("new_status")
    if new_status in ("open", "in_progress", "resolved", "closed"):
        ticket.status = new_status
        ticket.save(update_fields=["status"])

    html = render_to_string(
        "core/pages/_board.html#ticket-card", {"ticket": ticket}, request=request
    )
    html += f'<div id="ticket-{ticket.id}" hx-swap-oob="delete"></div>'
    if new_status != old_status:
        for status in (old_status, new_status):
            count = Ticket.objects.filter(
                project_id=ticket.project.id, status=status
            ).count()
            html += (
                f'<div id="column-count-{status}" hx-swap-oob="innerHTML">{count}</div>'
            )

    response = HttpResponse(html)
    response["HX-Retarget"] = f"#column-{ticket.status}"
    response["HX-Push-Url"] = "false"
    return response


def kanban_board(request: HttpRequest, org_id: str, project_id: str) -> HttpResponse:
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
        **_project_tabs(request, active="board"),
        "org": org,
        "project": project,
        "columns": columns,
        "title": f"{project.name} · {org.name}",
    }
    return render(request, get_template(request, "core/pages/project.html"), context)


# ---------------------------------------------------------------------------
# Ticket List (Class-Based View) — get_template_names() is all it takes
# ---------------------------------------------------------------------------


class TicketListView(ListView):
    template_name = "core/pages/project.html"
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
        if status := self.request.GET.get("status"):
            tickets = tickets.filter(status=status)
        if priority := self.request.GET.get("priority"):
            tickets = tickets.filter(priority=int(priority))
        if search := self.request.GET.get("q", "").strip():
            tickets = tickets.filter(title__icontains=search)
        return tickets.order_by("-created_at")

    def get_template_names(self):
        # The stock ListView machinery already calls this to pick a
        # template — no render_to_response override needed at all.
        return [get_template(self.request, self.template_name)]

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
        context.update(_project_tabs(self.request, active="tickets"))
        context["org"] = self.org
        context["project"] = self.project
        context["current_status"] = self.request.GET.get("status", "")
        context["current_priority"] = self.request.GET.get("priority", "")
        context["current_query"] = self.request.GET.get("q", "")
        context["employee_names"] = {e.id: e.name for e in Employee.objects.all()}
        context["title"] = f"{self.project.name} · {self.org.name}"
        return context


# ===========================================================================
# Ticket Detail Views
# ===========================================================================


def ticket_detail(request: HttpRequest, ticket_id: str) -> HttpResponse:
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
        **_ticket_tabs(request, ticket, active="details"),
        "ticket": ticket,
        "assignee_name": assignee_name,
        "title": f"#{ticket.id[:8]} · {ticket.title}",
    }
    return render(request, get_template(request, "core/pages/ticket.html"), context)


def ticket_comments(request: HttpRequest, ticket_id: str) -> HttpResponse:
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
        **_ticket_tabs(request, ticket, active="comments"),
        "ticket": ticket,
        "comments": ticket.comments,
        "title": f"#{ticket.id[:8]} · {ticket.title}",
    }
    return render(request, get_template(request, "core/pages/ticket.html"), context)


def ticket_activity(request: HttpRequest, ticket_id: str) -> HttpResponse:
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
        **_ticket_tabs(request, ticket, active="activity"),
        "ticket": ticket,
        "activity": [
            f"Ticket created with priority {ticket.priority}",
            f"Assigned to {assignee_name}",
            f"Status set to {ticket.status}",
        ],
        "title": f"#{ticket.id[:8]} · {ticket.title}",
    }
    return render(request, get_template(request, "core/pages/ticket.html"), context)


def ticket_attachments(request: HttpRequest, ticket_id: str) -> HttpResponse:
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
        **_ticket_tabs(request, ticket, active="attachments"),
        "ticket": ticket,
        "title": f"#{ticket.id[:8]} · {ticket.title}",
    }
    return render(request, get_template(request, "core/pages/ticket.html"), context)


# ---------------------------------------------------------------------------
# Multi-Step Creation Wizard
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
            fake_new_ticket = Ticket.objects.first()
            messages.add_message(
                request, messages.SUCCESS, "Ticket submitted! (Not really ;~;)"
            )
            return redirect(
                f"{NAMESPACE}:ticket_detail",
                ticket_id=fake_new_ticket.id if fake_new_ticket else None,
            )

        return redirect(
            f"{NAMESPACE}:ticket_wizard_step",
            org_id=org_id,
            project_id=project_id,
            step=WIZARD_STEPS[current_index + 1],
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
        "title": f"New ticket · {step}",
    }
    return render(request, get_template(request, "core/pages/wizard.html"), context)
