import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

import pytest
from core.navigation.registry import VARIANTS
from django.test import Client
from django.urls import reverse


@pytest.fixture
def client():
    return Client()


def test_landing_page(client):
    url = reverse("landing")
    response = client.get(url)

    assert response.status_code == 200
    assert "frontpage/landing.html" in [t.name for t in response.templates]
    assert "frontpage/base.html" in [t.name for t in response.templates]

    ctx = response.context
    assert ctx["variants_count"] == len(VARIANTS)
    assert ctx["families_count"] == len(ctx["families"])
    assert len(ctx["families"]) > 0

    # Ensure families in context are unique
    seen_families = set()
    for fam in ctx["families"]:
        assert fam.family not in seen_families
        seen_families.add(fam.family)

    # Headline metrics validation
    metrics = ctx["headline_metrics"]
    assert len(metrics) >= 4
    for metric in metrics:
        assert "stat" in metric and "label" in metric and "desc" in metric

    # Check key navigation links are in the body
    content = response.content.decode()
    assert 'href="/guide/"' in content
    assert 'href="/benchmarks/"' in content
    assert 'href="/htmx-nav/baseline/' in content


def test_guide_page(client):
    url = reverse("guide")
    response = client.get(url)

    assert response.status_code == 200
    assert "frontpage/articles/architectural_guide/index.html" in [
        t.name for t in response.templates
    ]
    assert "frontpage/base.html" in [t.name for t in response.templates]

    content = response.content.decode()
    # Check key architectural sections and keywords
    assert "Swap" in content
    assert "make_shell_renderer" in content
    assert "Visual Debugging" in content or "debug" in content.lower()


def test_robots_txt(client):
    url = reverse("robots_txt")
    response = client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")

    content = response.content.decode()
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    assert "User-agent: *" in lines
    assert "Allow: /" in lines
    assert "Sitemap: http://testserver/sitemap.xml" in lines


def test_sitemap_xml(client):
    url = reverse("sitemap_xml")
    response = client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/xml")

    try:
        root = ET.fromstring(response.content)
    except ParseError as exc:
        pytest.fail(f"Invalid sitemap XML: {exc}")

    # Namespace handling
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    url_nodes = root.findall("sm:url", ns)
    assert len(url_nodes) > 0

    locs = []
    for node in url_nodes:
        loc = node.find("sm:loc", ns)
        lastmod = node.find("sm:lastmod", ns)
        changefreq = node.find("sm:changefreq", ns)
        priority = node.find("sm:priority", ns)

        assert loc is not None and loc.text
        assert lastmod is not None and lastmod.text
        assert changefreq is not None and changefreq.text in (
            "daily",
            "weekly",
            "monthly",
            "yearly",
        )
        assert priority is not None and float(priority.text) >= 0.0

        locs.append(loc.text)

    # Core URLs present in the sitemap
    assert "http://testserver/" in locs
    assert "http://testserver/guide/" in locs
    assert "http://testserver/benchmarks/" in locs
    assert "http://testserver/benchmarks/static/" in locs
    assert "http://testserver/benchmarks/server/" in locs
    assert "http://testserver/benchmarks/payload/" in locs
    assert "http://testserver/benchmarks/client/" in locs
    assert "http://testserver/docs/" in locs


@pytest.mark.django_db
def test_resolve_demo_target_url():
    from frontpage.views import resolve_demo_target_url

    # Default is project_overview
    url = resolve_demo_target_url("htmx_nav_declarative")
    assert "/htmx-nav/declarative/orgs/" in url
    assert "/projects/" in url

    # Specific url names
    settings_url = resolve_demo_target_url("htmx_nav_declarative", "project_settings")
    assert settings_url.endswith("/settings/")

    subtab_url = resolve_demo_target_url(
        "htmx_nav_declarative", "project_settings_subtab"
    )
    assert subtab_url.endswith("/settings/general/")

    ticket_url = resolve_demo_target_url("htmx_nav_declarative", "ticket_detail")
    assert "/tickets/" in ticket_url

    overview_url = resolve_demo_target_url("htmx_nav_declarative", "overview")
    assert overview_url == "/htmx-nav/declarative/"


@pytest.mark.django_db
def test_demo_entry_default(client):
    url = reverse("demo_entry", args=["htmx_nav_declarative"])
    response = client.get(url)
    assert response.status_code == 302
    assert "/htmx-nav/declarative/orgs/" in response.url
    assert "/projects/" in response.url


@pytest.mark.django_db
def test_demo_entry_no_args(client):
    url = reverse("demo_entry")
    response = client.get(url)
    assert response.status_code == 302
    assert "/htmx-nav/declarative/orgs/" in response.url
    assert "/projects/" in response.url


@pytest.mark.django_db
def test_demo_entry_specific_url_name(client):
    url = reverse("demo_entry", args=["htmx_nav_declarative", "project_settings"])
    response = client.get(url)
    assert response.status_code == 302
    assert response.url.endswith("/settings/")


@pytest.mark.django_db
def test_demo_entry_query_params(client):
    url = reverse("demo_entry", args=["htmx_nav_declarative", "project_overview"])
    response = client.get(f"{url}?debug-swaps=1&foo=bar")
    assert response.status_code == 302
    assert "debug-swaps=1" in response.url
    assert "foo=bar" in response.url


def test_demo_entry_unknown_variant_404(client):
    response = client.get("/demo/unknown_variant_123/")
    assert response.status_code == 404


def test_demo_entry_unknown_url_name_404(client):
    response = client.get("/demo/htmx_nav_declarative/unknown_route_123/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_landing_page_demo_environment_redirect(client, monkeypatch):
    from config.constants import EnvironmentChoices

    monkeypatch.setattr("frontpage.views.settings.ENVIRONMENT", EnvironmentChoices.DEMO)
    url = reverse("landing")
    response = client.get(f"{url}?debug-swaps=1")

    # Single redirect directly to flagship demo
    assert response.status_code == 302
    assert "/htmx-nav/declarative/orgs/" in response.url
    assert "/projects/" in response.url
    assert "debug-swaps=1" in response.url
