"""
Showcase landing page, architectural guide, and SEO views for django-htmx-nav.
"""

from pathlib import Path
from urllib.parse import urlsplit

from config.constants import EnvironmentChoices
from core.navigation.registry import VARIANTS
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone


def landing(request: HttpRequest) -> HttpResponse:
    """Project showcase overview landing page."""

    # Redirect for the demo
    if settings.ENVIRONMENT == EnvironmentChoices.DEMO:
        return redirect("htmx_nav_declarative:overview")

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
        "headline_metrics": [
            {
                "stat": "~32%",
                "label": "Payload Reduction",
                "desc": "Average wire size reduction compared to views unaware vanilla HTMX.",
            },
            {
                "stat": "<0.5 ms",
                "label": "Render Overhead",
                "desc": "Minimal server-side compute cost for building multi-region OOB swaps.",
            },
            {
                "stat": "4.5 avg",
                "label": "Flat DB Queries",
                "desc": "Request-scoped caching prevents duplicate queries across partials.",
            },
            {
                "stat": "23",
                "label": "Tested Variants",
                "desc": "Comprehensive comparison across MPA, Vanilla HTMX, hx-select, and Idiomorph.",
            },
        ],
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
