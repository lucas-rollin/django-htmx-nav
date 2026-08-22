"""
Data navigation registry and `render_shell` definition.

This exemplifies the use of a declarative system to simplify the views
while achieving the same specificity as the `views_atomic.py` variant.

The registry can contain any shape as long as it resolves to a Swaps
for `make_shell_renderer`. Here dataclasses were used to compose the 
constants containing the navigation component structural data and their
state for each view. This was then resolved into Swaps via functions.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from core.models import Organization, Project, Ticket
from django.http import HttpRequest
from django.urls import reverse_lazy

from htmx_nav import Swap, make_shell_renderer
from htmx_nav.helpers import cache_on_request

NAMESPACE = "htmx_nav_declarative"

Resolvable = str | Callable[[HttpRequest], str]
"""A literal, or a value resolved lazily against the request — used for
the handful of genuinely dynamic labels/urls (org name, project name)."""


# --- navigation components dataclasses -----------------------------------


@dataclass(frozen=True)
class Crumb:
    label: Resolvable
    url: Resolvable | None = None  # None = current page, not a link


@dataclass(frozen=True)
class Tab:
    key: str
    label: str
    view_name: str
    args: Callable[[HttpRequest], Sequence] = lambda r: ()


@dataclass(frozen=True)
class NavEntry:
    breadcrumbs: Sequence[Crumb] = field(default_factory=tuple)
    tabs: Sequence[Tab] = field(default_factory=tuple)
    active_tab: str = ""
    title: Resolvable | None = None


# --- shared, deduped lookups -------------------------------------------


def get_org(request: HttpRequest) -> Organization:
    org_id = request.resolver_match.kwargs["org_id"]  # type: ignore
    return cache_on_request(
        request, "_org", lambda: Organization.objects.get(id=org_id)
    )


def get_project(request: HttpRequest) -> Project:
    project_id = request.resolver_match.kwargs["project_id"]  # type: ignore
    return cache_on_request(
        request, "_project", lambda: Project.objects.get(id=project_id)
    )


def get_ticket(request: HttpRequest) -> Ticket | None:
    """None on any view without a ticket_id kwarg."""
    match = request.resolver_match
    ticket_id = match.kwargs.get("ticket_id") if match else None
    if ticket_id is None:
        return None
    return cache_on_request(
        request,
        "_ticket",
        lambda: Ticket.objects.select_related("project__organization", "assignee").get(
            id=ticket_id
        ),
    )


def _org_label(r: HttpRequest) -> str:
    return get_org(r).name


def _org_url(r: HttpRequest) -> str:
    return reverse_lazy(
        f"{NAMESPACE}:org_detail", args=[r.resolver_match.kwargs["org_id"]]
    )


def _project_label(r: HttpRequest) -> str:
    return get_project(r).name


def _project_url(r: HttpRequest) -> str:
    kw = r.resolver_match.kwargs
    return reverse_lazy(
        f"{NAMESPACE}:project_overview", args=[kw["org_id"], kw["project_id"]]
    )


def _ticket_short_id(r: HttpRequest) -> str:
    return f"#{get_ticket(r).id[:8]}"


def _ticket_org_label(r: HttpRequest) -> str:
    return get_ticket(r).project.organization.name


def _ticket_org_url(r: HttpRequest) -> str:
    return reverse_lazy(
        f"{NAMESPACE}:org_detail", args=[get_ticket(r).project.organization_id]
    )


def _ticket_project_label(r: HttpRequest) -> str:
    return get_ticket(r).project.name


def _ticket_project_url(r: HttpRequest) -> str:
    ticket = get_ticket(r)
    return reverse_lazy(
        f"{NAMESPACE}:project_overview",
        args=[ticket.project.organization_id, ticket.project_id],
    )


def _project_tab_args(r: HttpRequest) -> Sequence:
    kw = r.resolver_match.kwargs
    return [kw["org_id"], kw["project_id"]]


def _ticket_tab_args(r: HttpRequest) -> Sequence:
    return [get_ticket(r).id]


# --- shared tab bars ------------------------------------------

PROJECT_TABS = (
    Tab("overview", "Overview", "project_overview", _project_tab_args),
    Tab("tickets", "Tickets", "ticket_list", _project_tab_args),
    Tab("board", "Board", "kanban_board", _project_tab_args),
    Tab("team", "Team", "project_team", _project_tab_args),
    Tab("settings", "Settings", "project_settings", _project_tab_args),
)

TICKET_TABS = (
    Tab("details", "Details", "ticket_detail", _ticket_tab_args),
    Tab("comments", "Comments", "ticket_comments", _ticket_tab_args),
    Tab("activity", "Activity", "ticket_activity", _ticket_tab_args),
    Tab("attachments", "Attachments", "ticket_attachments", _ticket_tab_args),
)

_project_crumbs = (
    Crumb("Organizations", reverse_lazy(f"{NAMESPACE}:org_list")),
    Crumb(_org_label, _org_url),
    Crumb(_project_label, _project_url),
)

_ticket_crumbs = (
    Crumb("Organizations", reverse_lazy(f"{NAMESPACE}:org_list")),
    Crumb(_ticket_org_label, _ticket_org_url),
    Crumb(_ticket_project_label, _ticket_project_url),
)


# --- the registry, one entry per url_name -----------------------------

NAV_ENTRIES: dict[str, NavEntry] = {
    "overview": NavEntry(
        breadcrumbs=(Crumb("helpdesk"),),
        title="Organizations · Helpdesk",
    ),
    "staff_list": NavEntry(
        breadcrumbs=(Crumb("helpdesk"),),
        title="Staff · Helpdesk",
    ),
    "org_list": NavEntry(
        breadcrumbs=(Crumb("helpdesk"),),
        title="Organizations · Helpdesk",
    ),
    "org_detail": NavEntry(
        breadcrumbs=(
            Crumb("Organizations", reverse_lazy(f"{NAMESPACE}:org_list")),
            Crumb(_org_label),
        ),
        title=lambda r: f"{_org_label(r)} · Helpdesk",
    ),
    "project_overview": NavEntry(
        breadcrumbs=_project_crumbs,
        tabs=PROJECT_TABS,
        active_tab="overview",
        title=lambda r: f"{_project_label(r)} · {_org_label(r)}",
    ),
    "project_team": NavEntry(
        breadcrumbs=(*_project_crumbs, Crumb("Team")),
        tabs=PROJECT_TABS,
        active_tab="team",
        title=lambda r: f"{_project_label(r)} · {_org_label(r)}",
    ),
    "project_settings": NavEntry(
        breadcrumbs=(*_project_crumbs, Crumb("Settings")),
        tabs=PROJECT_TABS,
        active_tab="settings",
        title=lambda r: f"{_project_label(r)} · {_org_label(r)}",
    ),
    "kanban_board": NavEntry(
        breadcrumbs=(*_project_crumbs, Crumb("Board")),
        tabs=PROJECT_TABS,
        active_tab="board",
        title=lambda r: f"{_project_label(r)} · {_org_label(r)}",
    ),
    "ticket_list": NavEntry(
        breadcrumbs=(*_project_crumbs, Crumb("Tickets")),
        tabs=PROJECT_TABS,
        active_tab="tickets",
        title=lambda r: f"{_project_label(r)} · {_org_label(r)}",
    ),
    "ticket_detail": NavEntry(
        breadcrumbs=(*_ticket_crumbs, Crumb(_ticket_short_id)),
        tabs=TICKET_TABS,
        active_tab="details",
        title=lambda r: f"{_ticket_short_id(r)} · {get_ticket(r).title}",
    ),
    "ticket_comments": NavEntry(
        breadcrumbs=(
            *_ticket_crumbs,
            Crumb(
                _ticket_short_id,
                lambda r: reverse_lazy(
                    f"{NAMESPACE}:ticket_detail", args=[get_ticket(r).id]
                ),
            ),
            Crumb("Comments"),
        ),
        tabs=TICKET_TABS,
        active_tab="comments",
        title=lambda r: f"{_ticket_short_id(r)} · {get_ticket(r).title}",
    ),
    "ticket_activity": NavEntry(
        breadcrumbs=(
            *_ticket_crumbs,
            Crumb(
                _ticket_short_id,
                lambda r: reverse_lazy(
                    f"{NAMESPACE}:ticket_detail", args=[get_ticket(r).id]
                ),
            ),
            Crumb("Activity"),
        ),
        tabs=TICKET_TABS,
        active_tab="activity",
        title=lambda r: f"{_ticket_short_id(r)} · {get_ticket(r).title}",
    ),
    "ticket_attachments": NavEntry(
        breadcrumbs=(
            *_ticket_crumbs,
            Crumb(
                _ticket_short_id,
                lambda r: reverse_lazy(
                    f"{NAMESPACE}:ticket_detail", args=[get_ticket(r).id]
                ),
            ),
            Crumb("Attachments"),
        ),
        tabs=TICKET_TABS,
        active_tab="attachments",
        title=lambda r: f"{_ticket_short_id(r)} · {get_ticket(r).title}",
    ),
    "ticket_wizard_step": NavEntry(
        breadcrumbs=(*_project_crumbs, Crumb("New Ticket")),
        title=lambda r: f"New ticket · {r.resolver_match.kwargs.get('step', '')}",  # type: ignore
    ),
}

# project_settings and project_settings_subtab use the same entry
NAV_ENTRIES["project_settings_subtab"] = NAV_ENTRIES["project_settings"]


# --- resolution function for Swaps ---------------------------


def _current_entry(request: HttpRequest) -> NavEntry:
    match = request.resolver_match
    return NAV_ENTRIES.get(match.url_name if match else "", NavEntry())


_TOP_LEVEL_PAGES = {"overview", "staff_list", "org_list"}


def _resolve_sidebar(request: HttpRequest) -> dict:
    match = request.resolver_match
    url_name = match.url_name if match else ""
    kwargs = match.kwargs if match else {}

    ticket = get_ticket(request)
    if ticket is not None:
        active_org_id, active_project_id = (
            ticket.project.organization_id,
            ticket.project_id,
        )
    else:
        active_org_id = kwargs.get("org_id")
        active_project_id = kwargs.get("project_id")

    return {
        "orgs": Organization.objects.prefetch_related("projects").only("id", "name"),
        "active_org_id": active_org_id,
        "active_project_id": active_project_id,
        "active_page": url_name if url_name in _TOP_LEVEL_PAGES else None,
    }


def _resolve_crumb(crumb: Crumb, request: HttpRequest) -> dict:
    label = crumb.label(request) if callable(crumb.label) else crumb.label
    url = crumb.url(request) if callable(crumb.url) else crumb.url
    return {"label": label, "url": url}


def _resolve_tabs(entry: NavEntry, request: HttpRequest) -> list[dict]:
    tabs_context = [
        {
            "key": tab.key,
            "label": tab.label,
            "url": reverse_lazy(f"{NAMESPACE}:{tab.view_name}", args=tab.args(request)),
            "active": tab.key == entry.active_tab,
        }
        for tab in entry.tabs
    ]
    return {"active_tab": entry.active_tab, "tabs": tabs_context}


def build_shell_swaps(request: HttpRequest) -> list[Swap]:
    """Render one Swap per navigation region"""
    entry = _current_entry(request)

    swaps = [
        Swap(
            "components/_sidebar_menu.html",
            _resolve_sidebar(request),
            target_id="sidebar",
        ),
        Swap(
            "components/_breadcrumbs.html",
            {
                "breadcrumbs": [_resolve_crumb(c, request) for c in entry.breadcrumbs],
                "title": entry.title(request) if callable(entry.title) else entry.title,
            },
            target_id="breadcrumbs",
        ),
    ]

    if entry.tabs:
        swaps.append(
            Swap(
                "components/_tabs.html",
                _resolve_tabs(entry, request),
                target_id="tabs",
            )
        )

    return swaps


render_shell = make_shell_renderer(build_shell_swaps)
