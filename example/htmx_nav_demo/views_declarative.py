"""
Views for the declarative variant. Every navigation view calls 
`render_shell` directly, the function `make_shell_renderer` returned 
in registry_declarative.py.

Sidebar, breadcrumbs, tabs, and title are gone from every call site and
are registered once, resolved once per request. What's left per view:
- the page's own content context,
- `partial=` only where the tab-content/step/dict resolution actually
  differs (most views don't need it),
- `extra_swaps=` only for the two page-specific fragments the registry
  deliberately doesn't own: settings' subtab bar, and the wizard's step
  indicator.
"""

from core.models import Employee, Organization, Project, Ticket
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView

from htmx_nav import (
    Swap,
    has_messages,
    htmx_target_is,
    make_shell_view_mixin,
    render_with_swaps,
    targeting,
)

from .registry_declarative import (
    NAMESPACE,
    get_org,
    get_project,
    get_ticket,
    render_shell,
)

TICKET_PAGE_SIZE = 6


def _tab_content_partial(request: HttpRequest, partial_name: str) -> str:
    return partial_name if htmx_target_is(request, "tab-content") else "#content"


# --- top-level pages -------------------------------------------------------


def overview(request: HttpRequest) -> HttpResponse:
    return render_shell(request, "pages/overview.html")


def staff_list(request: HttpRequest) -> HttpResponse:
    employees = [
        {
            "tickets": Ticket.objects.filter(
                assignee_id=e.id, status__in=["open", "in_progress"]
            ).count(),
            "details": e,
        }
        for e in Employee.objects.all()
    ]
    return render_shell(
        request,
        "pages/staff_list.html",
        {"employees": employees},
        partial="pages/_staff_list.html",
    )


def org_list(request: HttpRequest) -> HttpResponse:
    return render_shell(
        request, "pages/org_list.html", {"orgs": Organization.objects.all()}
    )


def org_detail(request: HttpRequest, org_id: str) -> HttpResponse:
    org = get_org(request)
    context = {"org": org, "projects": Project.objects.filter(organization_id=org_id)}
    return render_shell(request, "pages/org_detail.html", context)


# --- project tabs -----------------------------------------------------


def project_overview(
    request: HttpRequest, org_id: str, project_id: str
) -> HttpResponse:
    context = {"org": get_org(request), "project": get_project(request)}
    return render_shell(
        request,
        "pages/project.html",
        context,
        partial=_tab_content_partial(request, "#overview"),
    )


def project_team(request: HttpRequest, org_id: str, project_id: str) -> HttpResponse:
    project = get_project(request)
    context = {
        "org": get_org(request),
        "project": project,
        "team": Employee.objects.filter(tickets__project_id=project.id).distinct(),
    }
    return render_shell(
        request,
        "pages/project.html",
        context,
        partial=_tab_content_partial(request, "#team"),
    )


def project_settings(
    request: HttpRequest, org_id: str, project_id: str, subtab: str = "general"
) -> HttpResponse:
    if subtab not in ("general", "permissions", "danger"):
        subtab = "general"
    context = {
        "org": get_org(request),
        "project": get_project(request),
        "active_subtab": subtab,
    }

    if htmx_target_is(request, "subtab-content"):
        partial = f"#settings-{subtab}"
    elif htmx_target_is(request, "tab-content"):
        partial = "#settings"
    else:
        partial = "#content"

    # The subtab bar showcases extra_swaps: it's page-specific nested
    # nav so it's built here and only sent as OOB when navigating 
    # strictly within it, same pattern as views_atomic.py.
    subtab_swap = Swap(
        "pages/project.html#settings_subtabs",
        target_id="subtabs",
        include_if=targeting("subtab-content"),
    )
    return render_shell(
        request,
        "pages/project.html",
        context,
        partial=partial,
        extra_swaps=[subtab_swap],
    )


def kanban_board(request: HttpRequest, org_id: str, project_id: str) -> HttpResponse:
    columns = {
        status: Ticket.objects.filter(
            project_id=project_id, status=status
        ).select_related("assignee")
        for status in ("open", "in_progress", "resolved", "closed")
    }
    context = {
        "org": get_org(request),
        "project": get_project(request),
        "columns": columns,
        "active_tab": "board",
    }
    return render_shell(
        request,
        "pages/project.html",
        context,
        partial={"pages/_board.html": targeting("tab-content"), "#content": True},
    )


@require_http_methods(["POST"])
def ticket_move_status(request: HttpRequest, ticket_id: str) -> HttpResponse:
    """Pinpoint swap, never touches the shell in any variant."""
    ticket = Ticket.objects.get(id=ticket_id)
    old_status = ticket.status
    new_status = request.POST.get("new_status")
    if new_status in ("open", "in_progress", "resolved", "closed"):
        ticket.status = new_status
        ticket.save(update_fields=["status"])

    swaps = [Swap.delete(f"ticket-{ticket.id}")]
    if new_status != old_status:
        for status in (old_status, new_status):
            count = Ticket.objects.filter(
                project_id=ticket.project.id, status=status
            ).count()
            swaps.append(Swap.text(f"column-count-{status}", str(count)))

    response = render_with_swaps(
        request, "pages/_board.html#ticket-card", {"ticket": ticket}, swaps=swaps
    )
    response["HX-Retarget"] = f"#column-{ticket.status}"
    response["HX-Push-Url"] = "false"
    return response


# --- CBV: make_shell_view_mixin composed directly with render_shell -----

ShellViewMixin = make_shell_view_mixin(render_shell)


class TicketListView(ShellViewMixin, ListView):
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
        if status := self.request.GET.get("status"):
            tickets = tickets.filter(status=status)
        if priority := self.request.GET.get("priority"):
            tickets = tickets.filter(priority=int(priority))
        if search := self.request.GET.get("q", "").strip():
            tickets = tickets.filter(title__icontains=search)
        return tickets.order_by("-created_at")

    def get_partial(self) -> str:
        return _tab_content_partial(self.request, "#tickets")

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


# --- ticket detail (tabbed) ---------------------------------------------


def ticket_detail(request: HttpRequest, ticket_id: str) -> HttpResponse:
    ticket = get_ticket(request)
    assignee_name = ticket.assignee.name if ticket.assignee else "Unassigned"
    context = {"ticket": ticket, "assignee_name": assignee_name}
    messages_swap = Swap("components/_messages.html", include_if=has_messages)
    return render_shell(
        request,
        "pages/ticket.html",
        context,
        partial=_tab_content_partial(request, "#details"),
        extra_swaps=[messages_swap],
    )


def ticket_comments(request: HttpRequest, ticket_id: str) -> HttpResponse:
    ticket = get_ticket(request)
    context = {"ticket": ticket, "comments": ticket.comments}
    return render_shell(
        request,
        "pages/ticket.html",
        context,
        partial=_tab_content_partial(request, "#comments"),
    )


def ticket_activity(request: HttpRequest, ticket_id: str) -> HttpResponse:
    ticket = get_ticket(request)
    assignee_name = ticket.assignee.name if ticket.assignee else "Unassigned"
    context = {
        "ticket": ticket,
        "activity": [
            f"Ticket created with priority {ticket.priority}",
            f"Assigned to {assignee_name}",
            f"Status set to {ticket.status}",
        ],
    }
    return render_shell(
        request,
        "pages/ticket.html",
        context,
        partial=_tab_content_partial(request, "#activity"),
    )


def ticket_attachments(request: HttpRequest, ticket_id: str) -> HttpResponse:
    context = {"ticket": get_ticket(request)}
    return render_shell(
        request,
        "pages/ticket.html",
        context,
        partial=_tab_content_partial(request, "#attachments"),
    )


# --- wizard --------------------------------------------------------------

WIZARD_STEPS = ["basics", "assignment", "review"]
WIZARD_SESSION_KEY = "new_ticket_wizard"

_step_partial = {f"#{s}": s for s in WIZARD_STEPS}
_step_partial["#content"] = True


def _wizard_steps_swap(step: str) -> Swap:
    """Page-specific, one-view-only — built here and passed as
    extra_swaps, same showcase role as the subtab swap above."""
    return Swap(
        "components/_wizard_steps.html",
        {"steps": WIZARD_STEPS, "step_index": WIZARD_STEPS.index(step)},
        target_id="steps",
        include_if=targeting("steps-content"),
    )


def _wizard_data(
    request: HttpRequest, org_id: str, project_id: str
) -> tuple[str, dict]:
    key = f"{WIZARD_SESSION_KEY}:{org_id}:{project_id}"
    return key, request.session.get(key, {})


@require_http_methods(["GET", "POST"])
def ticket_wizard_step(
    request: HttpRequest, org_id: str, project_id: str, step: str
) -> HttpResponse:
    if step not in WIZARD_STEPS:
        step = WIZARD_STEPS[0]

    org, project = get_org(request), get_project(request)
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
        "org": org,
        "project": project,
        "step": step,
        "collected": collected,
        "employees": all_employees,
        "employee_names": {e.id: e.name for e in all_employees},
    }
    return render_shell(
        request,
        "pages/wizard.html",
        context,
        partial=_step_partial,
        extra_swaps=[_wizard_steps_swap(step)],
    )
