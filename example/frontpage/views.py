"""
Showcase landing page, architectural guide, and SEO views for django-htmx-nav.
"""

from pathlib import Path
from urllib.parse import urlsplit

from config.constants import EnvironmentChoices
from core.navigation.registry import VARIANTS
from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone


def _get_default_demo_ids() -> tuple[str, str, str]:
    """Retrieve default mock organization, project, and ticket IDs."""
    try:
        from core.models import Project, Ticket

        project = Project.objects.select_related("organization").first()
        if project:
            org_id = str(project.organization_id)
            project_id = str(project.id)
        else:
            org_id, project_id = "1", "1"

        ticket = Ticket.objects.first()
        ticket_id = str(ticket.id) if ticket else "1"
        return org_id, project_id, ticket_id
    except Exception:
        return "1", "1", "1"


def resolve_demo_target_url(
    variant: str = "htmx_nav_declarative",
    url_name: str | None = None,
) -> str:
    """Resolve a concrete demo URL for a variant without requiring callers to supply mock IDs.

    Defaults to 'project_overview' as the primary showcase page.
    """
    target = url_name or "project_overview"
    org_id, project_id, ticket_id = _get_default_demo_ids()

    if target in (
        "project_overview",
        "project_team",
        "project_settings",
        "ticket_list",
        "kanban_board",
    ):
        args = [org_id, project_id]
    elif target == "project_settings_subtab":
        args = [org_id, project_id, "general"]
    elif target == "ticket_wizard_step":
        args = [org_id, project_id, "details"]
    elif target == "org_detail":
        args = [org_id]
    elif target in (
        "ticket_detail",
        "ticket_comments",
        "ticket_activity",
        "ticket_attachments",
        "ticket_move_status",
    ):
        args = [ticket_id]
    else:
        args = []

    return reverse(f"{variant}:{target}", args=args)


def demo_entry(
    request: HttpRequest,
    variant: str = "htmx_nav_declarative",
    url_name: str | None = None,
) -> HttpResponse:
    """Redirect to a variant's demo page without needing mock data IDs in URLs."""
    if variant not in VARIANTS and variant not in {
        v.namespace for v in VARIANTS.values()
    }:
        raise Http404(f"Unknown demo variant: '{variant}'")

    try:
        target_url = resolve_demo_target_url(variant=variant, url_name=url_name)
    except NoReverseMatch:
        raise Http404(f"Unknown route '{url_name}' for variant '{variant}'")

    if request.GET:
        target_url = f"{target_url}?{request.GET.urlencode()}"
    return redirect(target_url)


def landing(request: HttpRequest) -> HttpResponse:
    """Project showcase overview landing page."""

    # When deployed on the demo host, redirect directly to the flagship demo page (single redirect)
    if settings.ENVIRONMENT == EnvironmentChoices.DEMO:
        target_url = resolve_demo_target_url("htmx_nav_declarative", "project_overview")
        if request.GET:
            target_url = f"{target_url}?{request.GET.urlencode()}"
        return redirect(target_url)

    # Group unique base implementation families
    families = []
    seen = set()
    for variant in VARIANTS.values():
        if variant.family not in seen:
            seen.add(variant.family)
            families.append(variant)

    context = {
        "families": families,
        "variants_count": len(VARIANTS),
        "families_count": len(families),
    }
    return render(request, "frontpage/landing.html", context)


def guide(request: HttpRequest) -> HttpResponse:
    """Architectural guide on solving stale navigation in hypermedia apps."""
    return render(request, "frontpage/articles/architectural_guide/index.html")


def robots_txt(request: HttpRequest) -> HttpResponse:
    """Dynamic robots.txt with sitemap reference."""
    if settings.ROBOTS_DISALLOW_ALL:
        return HttpResponse("User-agent: *\nDisallow: /", content_type="text/plain")

    domain = (settings.SITE_URL or request.build_absolute_uri("/")).rstrip("/")
    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        f"Sitemap: {domain}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def _get_doc_urls(domain: str, now: str) -> list[dict]:
    """Generate doc url for every file in `docs/`.
    Expects the render to <stem>.html by Sphinx.
    """
    docs_dir = Path(__file__).resolve().parent.parent.parent / "docs"
    urls = [
        {
            "loc": f"{domain}/docs/",
            "priority": "0.9",
            "changefreq": "weekly",
            "lastmod": now,
        }
    ]
    if docs_dir.is_dir():
        for doc in sorted(docs_dir.glob("*.md")):
            if doc.stem != "index":
                urls.append(
                    {
                        "loc": f"{domain}/docs/{doc.stem}.html",
                        "priority": "0.8",
                        "changefreq": "monthly",
                        "lastmod": now,
                    }
                )
    return urls


def sitemap_xml(request: HttpRequest) -> HttpResponse:
    """Dynamic sitemap.xml indexing landing, guide, benchmarks, and demo entry points."""
    domain = settings.SITE_URL.rstrip("/") or request.build_absolute_uri("/").rstrip(
        "/"
    )
    parsed = urlsplit(domain)
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else domain
    now = timezone.now().strftime("%Y-%m-%d")

    django_urls = [
        {
            "loc": f"{origin}{reverse('landing')}",
            "priority": "1.0",
            "changefreq": "weekly",
        },
        {
            "loc": f"{origin}{reverse('guide')}",
            "priority": "0.9",
            "changefreq": "weekly",
        },
        {
            "loc": f"{origin}{reverse('benchmarks:overview')}",
            "priority": "0.9",
            "changefreq": "monthly",
        },
        {
            "loc": f"{origin}{reverse('benchmarks:static')}",
            "priority": "0.7",
            "changefreq": "monthly",
        },
        {
            "loc": f"{origin}{reverse('benchmarks:server')}",
            "priority": "0.7",
            "changefreq": "monthly",
        },
        {
            "loc": f"{origin}{reverse('benchmarks:payload')}",
            "priority": "0.7",
            "changefreq": "monthly",
        },
        {
            "loc": f"{origin}{reverse('benchmarks:client')}",
            "priority": "0.7",
            "changefreq": "monthly",
        },
    ]

    sphinx_urls = _get_doc_urls(domain, now)

    urls = django_urls + sphinx_urls

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{u['loc']}</loc>")
        xml_lines.append(f"    <lastmod>{now}</lastmod>")
        xml_lines.append(f"    <changefreq>{u['changefreq']}</changefreq>")
        xml_lines.append(f"    <priority>{u['priority']}</priority>")
        xml_lines.append("  </url>")
    xml_lines.append("</urlset>")

    return HttpResponse("\n".join(xml_lines), content_type="application/xml")
