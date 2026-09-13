"""
Showcase landing page, architectural guide, and SEO views for django-htmx-nav.
"""

from core.navigation.registry import VARIANTS
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone


def landing(request: HttpRequest) -> HttpResponse:
    """Project showcase overview landing page."""
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
    return render(request, "frontpage/guide.html")


def robots_txt(request: HttpRequest) -> HttpResponse:
    """Dynamic robots.txt with sitemap reference."""
    domain = request.build_absolute_uri("/").rstrip("/")
    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        f"Sitemap: {domain}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def sitemap_xml(request: HttpRequest) -> HttpResponse:
    """Dynamic sitemap.xml indexing landing, guide, benchmarks, and demo entry points."""
    domain = request.build_absolute_uri("/").rstrip("/")
    now = timezone.now().strftime("%Y-%m-%d")

    urls = [
        {"loc": f"{domain}/", "priority": "1.0", "changefreq": "weekly"},
        {"loc": f"{domain}/guide/", "priority": "0.9", "changefreq": "weekly"},
        {"loc": f"{domain}/benchmarks/", "priority": "0.9", "changefreq": "weekly"},
        {
            "loc": f"{domain}/benchmarks/static/",
            "priority": "0.7",
            "changefreq": "monthly",
        },
        {
            "loc": f"{domain}/benchmarks/server/",
            "priority": "0.7",
            "changefreq": "monthly",
        },
        {
            "loc": f"{domain}/benchmarks/payload/",
            "priority": "0.7",
            "changefreq": "monthly",
        },
        {
            "loc": f"{domain}/benchmarks/client/",
            "priority": "0.7",
            "changefreq": "monthly",
        },
        {"loc": f"{domain}/mpa/", "priority": "0.8", "changefreq": "monthly"},
        {
            "loc": f"{domain}/vanilla-htmx/composite/",
            "priority": "0.8",
            "changefreq": "monthly",
        },
        {
            "loc": f"{domain}/vanilla-htmx/atomic/",
            "priority": "0.8",
            "changefreq": "monthly",
        },
        {
            "loc": f"{domain}/htmx-nav/baseline/",
            "priority": "0.8",
            "changefreq": "monthly",
        },
        {
            "loc": f"{domain}/htmx-nav/composite/",
            "priority": "0.8",
            "changefreq": "monthly",
        },
        {
            "loc": f"{domain}/htmx-nav/atomic/",
            "priority": "0.8",
            "changefreq": "monthly",
        },
        {
            "loc": f"{domain}/htmx-nav/declarative/",
            "priority": "0.8",
            "changefreq": "monthly",
        },
    ]

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
