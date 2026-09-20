"""
Rendering helper for the benchmarks dashboard.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse

PAGES = [
    ("overview", "Overview"),
    ("static", "Code Complexity / DX"),
    ("server", "Server Performance"),
    ("payload", "Payload Size"),
    ("client", "Client Performance"),
]


def subnav_context(request: HttpRequest) -> dict:
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


def render_benchmark(
    request: HttpRequest,
    template_name: str,
    context: dict | None = None,
    *,
    title: str | None = None,
) -> HttpResponse:
    """Render full benchmark page with intra-benchmark navigation context."""
    ctx = {**subnav_context(request), **(context or {})}
    if title:
        ctx["title"] = title
    return render(request, template_name, ctx)
