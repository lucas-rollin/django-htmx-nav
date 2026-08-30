"""
Fixed navigation-scenario matrix shared by every collector, so
"project_team tab swap" means the same request across static analysis,
server timing, payload bytes, and client timing.

POST-based scenarios (ticket_move_status) are deliberately excluded so
repeated collection runs stay idempotent against the shared seeded DB.
"""

from dataclasses import dataclass
from typing import Callable

HX_MAIN = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "main-content"}
HX_TAB = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "tab-content"}
HX_SUBTAB = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "subtab-content"}


@dataclass(frozen=True)
class BenchContext:
    org: object
    project: object
    ticket: object


@dataclass(frozen=True)
class Scenario:
    label: str
    url_name: str
    args: Callable[["BenchContext"], list]
    headers: dict | None = None


def get_context() -> BenchContext:
    """First seeded org that actually has a project, and one of that
    project's tickets. Reimplemented locally (rather than importing a
    test-only helper) so collectors don't depend on the test suite."""
    from core.models import Organization, Ticket

    org = Organization.objects.filter(projects__isnull=False).distinct().first()
    if org is None:
        raise RuntimeError(
            "No seeded organization with a project found. Run the example "
            "app once (e.g. `python manage.py runserver`) so CoreConfig.ready() seeds data."
        )
    project = org.projects.first()
    ticket = Ticket.objects.filter(project=project).first()
    return BenchContext(org=org, project=project, ticket=ticket)


SCENARIOS: list[Scenario] = [
    Scenario("overview_full", "overview", lambda ctx: []),
    Scenario("overview_main_swap", "overview", lambda ctx: [], HX_MAIN),
    Scenario("org_detail_full", "org_detail", lambda ctx: [ctx.org.id]),
    Scenario(
        "project_overview_full",
        "project_overview",
        lambda ctx: [ctx.org.id, ctx.project.id],
    ),
    Scenario(
        "project_overview_main_swap",
        "project_overview",
        lambda ctx: [ctx.org.id, ctx.project.id],
        HX_MAIN,
    ),
    Scenario(
        "project_team_tab_swap",
        "project_team",
        lambda ctx: [ctx.org.id, ctx.project.id],
        HX_TAB,
    ),
    Scenario(
        "project_settings_tab_swap",
        "project_settings",
        lambda ctx: [ctx.org.id, ctx.project.id],
        HX_TAB,
    ),
    Scenario(
        "project_settings_subtab_swap",
        "project_settings_subtab",
        lambda ctx: [ctx.org.id, ctx.project.id, "permissions"],
        HX_SUBTAB,
    ),
    Scenario(
        "kanban_board_tab_swap",
        "kanban_board",
        lambda ctx: [ctx.org.id, ctx.project.id],
        HX_TAB,
    ),
    Scenario("ticket_detail_full", "ticket_detail", lambda ctx: [ctx.ticket.id]),
    Scenario(
        "ticket_detail_main_swap", "ticket_detail", lambda ctx: [ctx.ticket.id], HX_MAIN
    ),
    Scenario(
        "ticket_comments_tab_swap",
        "ticket_comments",
        lambda ctx: [ctx.ticket.id],
        HX_TAB,
    ),
]

# Canonical request subset used for total_template_hx_attributes: one
# full page load (body-level hx-boost, tab bar hx-target) + one tab
# swap (OOB/hx-partial wrapper + morph/hx-select attributes) + one
# subtab swap (deepest nesting, relevant for *_atomic/_declarative).
# Kept small deliberately — this metric is moderate priority.
ATTRIBUTE_COUNT_SCENARIO_LABELS = frozenset(
    {
        "project_overview_full",
        "project_team_tab_swap",
        "project_settings_subtab_swap",
    }
)
