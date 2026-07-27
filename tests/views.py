"""
A minimal example of the "registry pattern" (see
docs/patterns/registry_pattern.md) — plain dicts/functions built from
`htmx_nav.helpers`, no framework classes. Used by the test suite to
exercise `render_shell`/`assert_shell_parity` end-to-end against
something resembling real project code.
"""
from django.http import HttpRequest

from htmx_nav.helpers import cache_on_request, reverse_maybe
from htmx_nav.responses import make_shell_renderer

SIDEBAR_LINKS = [
    {"key": "workspace", "label": "Workspace", "view_name": "nav-workspace"},
]

# view_name -> breadcrumb labels for that view; a real project would
# probably also carry "active" state, tabs, etc. here.
BREADCRUMBS = {
    "nav-workspace": [("Workspace", None)],
    "nav-detail": [("Workspace", "nav-workspace"), ("Detail", None)],
}


def build_nav_context(request: HttpRequest) -> dict:
    def _build():
        match = request.resolver_match
        view_name = match.view_name if match else ""
        kwargs = match.kwargs if match else {}

        sidebar = [
            {**link, "url": reverse_maybe(link["view_name"]), "active": link["view_name"] == view_name}
            for link in SIDEBAR_LINKS
        ]
        breadcrumbs = [
            {"label": label, "url": reverse_maybe(crumb_view, kwargs, strict=False) if crumb_view else None}
            for label, crumb_view in BREADCRUMBS.get(view_name, [])
        ]
        return {"sidebar": sidebar, "breadcrumbs": breadcrumbs}

    return cache_on_request(request, "_test_nav", _build)


render_shell = make_shell_renderer(
    shell_template="tests/_shell.html",
    context_builder=lambda request: {"nav": build_nav_context(request)},
)


def workspace_view(request: HttpRequest, pk=None):
    return render_shell(request, "tests/_page.html", {"title": "hi"})
