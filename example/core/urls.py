"""
Generate resuable urls for the different variants.
"""

from django.urls import path


def generate_variant_urls(views):
    return [
        path("", views.overview, name="overview"),
        path("staff/", views.staff_list, name="staff_list"),
        path("orgs/", views.org_list, name="org_list"),
        path("orgs/<str:org_id>/", views.org_detail, name="org_detail"),
        path(
            "orgs/<str:org_id>/projects/<str:project_id>/",
            views.project_overview,
            name="project_overview",
        ),
        path(
            "orgs/<str:org_id>/projects/<str:project_id>/team/",
            views.project_team,
            name="project_team",
        ),
        path(
            "orgs/<str:org_id>/projects/<str:project_id>/settings/",
            views.project_settings,
            name="project_settings",
        ),
        path(
            "orgs/<str:org_id>/projects/<str:project_id>/settings/<str:subtab>/",
            views.project_settings,
            name="project_settings_subtab",
        ),
        path(
            "orgs/<str:org_id>/projects/<str:project_id>/tickets/",
            views.TicketListView.as_view(),
            name="ticket_list",
        ),
        path(
            "orgs/<str:org_id>/projects/<str:project_id>/board/",
            views.kanban_board,
            name="kanban_board",
        ),
        path(
            "tickets/<str:ticket_id>/move/",
            views.ticket_move_status,
            name="ticket_move_status",
        ),
        path(
            "orgs/<str:org_id>/projects/<str:project_id>/tickets/new/<str:step>/",
            views.ticket_wizard_step,
            name="ticket_wizard_step",
        ),
        path("tickets/<str:ticket_id>/", views.ticket_detail, name="ticket_detail"),
        path(
            "tickets/<str:ticket_id>/comments/",
            views.ticket_comments,
            name="ticket_comments",
        ),
        path(
            "tickets/<str:ticket_id>/activity/",
            views.ticket_activity,
            name="ticket_activity",
        ),
        path(
            "tickets/<str:ticket_id>/attachments/",
            views.ticket_attachments,
            name="ticket_attachments",
        ),
    ]
