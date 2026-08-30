"""
Shell renderer for the benchmarks dashboard.
"""

from django.http import HttpRequest
from django.urls import reverse

from htmx_nav import Swap, make_shell_renderer

PAGES = [
    ("overview", "Overview"),
    ("static", "Code Complexity / DX"),
    ("server", "Server Performance"),
    ("payload", "Payload Size"),
    ("client", "Client Performance"),
]


def _sidebar_context(request: HttpRequest) -> dict:
    match = request.resolver_match
    active = match.url_name if match else ""
    return {
        "pages": [
            {
                "key": key,
                "label": label,
                "url": reverse(f"benchmarks:{key}"),
                "active": key == active,
            }
            for key, label in PAGES
        ]
    }


render_shell = make_shell_renderer(
    lambda request: Swap(
        "benchmarks/components/_sidebar.html",
        _sidebar_context(request),
        target_id="benchmarks-sidebar",
    )
)
