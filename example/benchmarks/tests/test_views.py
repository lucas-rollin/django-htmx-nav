import pytest
from django.http import Http404
from django.test import Client, RequestFactory
from django.urls import reverse

from benchmarks.views import CATEGORIES, metric_page


@pytest.fixture
def client():
    return Client()


def test_benchmarks_overview_full_page(client):
    url = reverse("benchmarks:overview")
    response = client.get(url)

    assert response.status_code == 200
    template_names = [t.name for t in response.templates]
    assert "benchmarks/pages/overview.html" in template_names
    assert "benchmarks/components/_subnav.html" in template_names

    ctx = response.context
    assert "panels" in ctx
    assert "panels_json" in ctx
    assert "families" in ctx
    assert len(ctx["panels"]) >= 4

    for panel in ctx["panels"]:
        assert panel.key
        assert panel.title
        assert panel.caption
        assert isinstance(panel.chart, dict)

    content = response.content.decode()
    assert "<!DOCTYPE html>" in content
    assert "Overview · Benchmarks" in content
    assert 'id="benchmarks-subnav"' in content


def test_benchmarks_overview_htmx_partial(client):
    url = reverse("benchmarks:overview")
    response = client.get(
        url,
        HTTP_HX_REQUEST="true",
        HTTP_HX_TARGET="benchmarks-content",
    )

    assert response.status_code == 200
    content = response.content.decode()

    # In HTMX partial mode rendered via make_shell_renderer,
    # the outer page shell is omitted and the subnav is swapped OOB
    assert "<!DOCTYPE html>" not in content
    assert 'hx-swap-oob="innerHTML"' in content
    assert 'id="benchmarks-subnav"' in content


@pytest.mark.parametrize("category", ["static", "server", "payload", "client"])
def test_metric_pages_full_page(client, category):
    url = reverse(f"benchmarks:{category}")
    response = client.get(url)

    assert response.status_code == 200
    template_names = [t.name for t in response.templates]
    assert "benchmarks/pages/metric.html" in template_names
    assert "benchmarks/components/_subnav.html" in template_names

    ctx = response.context
    assert ctx["page_title"] == CATEGORIES[category]
    assert len(ctx["metrics"]) > 0
    assert "charts" in ctx
    assert "table" in ctx
    assert len(ctx["table"]["rows"]) > 0
    assert len(ctx["descriptions"]) > 0

    content = response.content.decode()
    assert "<!DOCTYPE html>" in content
    assert CATEGORIES[category] in content


@pytest.mark.parametrize("category", ["static", "server", "payload", "client"])
def test_metric_pages_htmx_partial(client, category):
    url = reverse(f"benchmarks:{category}")
    response = client.get(
        url,
        HTTP_HX_REQUEST="true",
        HTTP_HX_TARGET="benchmarks-content",
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "<!DOCTYPE html>" not in content
    assert 'hx-swap-oob="innerHTML"' in content
    assert 'id="benchmarks-subnav"' in content


def test_payload_featured_scenarios(client):
    url = reverse("benchmarks:payload")
    response = client.get(url)

    assert response.status_code == 200
    ctx = response.context
    scenario_views = ctx.get("scenario_views")
    assert scenario_views is not None

    expected_scenarios = [
        "all",
        "project_overview_main_swap",
        "project_team_tab_swap",
        "project_settings_subtab_swap",
    ]
    for sc in expected_scenarios:
        assert sc in scenario_views
        assert "charts" in scenario_views[sc]
        assert "table" in scenario_views[sc]
        assert len(scenario_views[sc]["table"]["rows"]) > 0


def test_subnav_active_indicator(client):
    for cat in ["overview", "static", "server", "payload", "client"]:
        url = reverse(f"benchmarks:{cat}")
        response = client.get(url)
        assert response.status_code == 200

        # Subnav context should mark exactly the current page as active
        subnav_pages = None
        for ctx_dict in response.context:
            if "pages" in ctx_dict:
                subnav_pages = ctx_dict["pages"]
                break

        assert subnav_pages is not None, f"Subnav pages missing for {cat}"
        active_pages = [p for p in subnav_pages if p["active"]]
        assert len(active_pages) == 1
        assert active_pages[0]["key"] == cat


def test_unknown_metric_category_404():
    rf = RequestFactory()
    request = rf.get("/benchmarks/nonexistent/")
    with pytest.raises(Http404, match="Unknown benchmark category: 'nonexistent'"):
        metric_page(request, prefix="nonexistent")
