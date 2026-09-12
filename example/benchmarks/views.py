"""
Benchmarks dashboard views.
"""

from core.navigation.registry import VARIANTS
from django.http import Http404, HttpRequest, HttpResponse

from .metrics.helpers.pivot import pivot_rows
from .metrics.jsonl import latest_or_reference_jsonl, read_jsonl
from .metrics.overview_metrics import build_panels
from .metrics.registry import describe
from .render import render_shell

CATEGORIES = {
    "static": "Code Complexity / DX",
    "server": "Server Performance",
    "payload": "Payload Size",
    "client": "Client Performance",
}


def overview(request: HttpRequest) -> HttpResponse:
    """Hand-picked charts + the experiment's headline takeaways.

    Reads only from the pinned example/benchmarks/data/reference_*.jsonl
    snapshot rather than the what's freshest in data/, so these captions never
    drift out of sync with the charts they're describing.
    """
    panels = build_panels()
    panels_json = [
        {"key": p.key, "title": p.title, "caption": p.caption, "chart": p.chart}
        for p in panels
    ]

    # Extract unique base implementation families (excluding +HS / +M suffix variants)
    families = []
    seen = set()
    for variant in VARIANTS.values():
        if (
            variant.family not in seen
            and not variant.uses_hx_select
            and not variant.uses_morph
        ):
            seen.add(variant.family)
            families.append(variant)

    return render_shell(
        request,
        "benchmarks/pages/overview.html",
        {
            "panels": panels,
            "panels_json": panels_json,
            "families": families,
        },
        title="Overview · Benchmarks",
    )


FEATURED_SCENARIOS: dict[str, list[tuple[str, str]]] = {
    "payload": [
        ("project_overview_main_swap", "Main Content Swap"),
        ("project_team_tab_swap", "Tab Swap"),
        ("project_settings_subtab_swap", "Subtab Swap"),
    ],
}


def metric_page(request: HttpRequest, prefix: str) -> HttpResponse:
    """Auto generated, interactive metric dashboards.

    Shows the freshest local collection run if one exists in data/, else
    falls back to the same pinned reference_*.jsonl snapshot the overview.
    """
    if prefix not in CATEGORIES:
        raise Http404(f"Unknown benchmark category: {prefix!r}")

    page_title = CATEGORIES[prefix]
    path = latest_or_reference_jsonl(prefix)
    rows = read_jsonl(path) if path else []
    pivoted = pivot_rows(rows)

    descriptions = {}
    for metric in pivoted["metrics"]:
        info = describe(metric)
        descriptions[metric] = {
            "label": info.label,
            "description": info.description,
            "unit": info.unit,
            "lower_is_better": info.lower_is_better,
        }

    featured = FEATURED_SCENARIOS.get(prefix, [])
    scenario_views = {}
    if featured and rows:
        scenario_views["all"] = {
            "key": "all",
            "label": "All Scenarios (Average)",
            "charts": pivoted["charts"],
            "table": pivoted["table"],
        }
        for sc_key, sc_label in featured:
            sc_rows = [r for r in rows if r.get("scenario") == sc_key]
            if sc_rows:
                sc_pivoted = pivot_rows(sc_rows)
                scenario_views[sc_key] = {
                    "key": sc_key,
                    "label": sc_label,
                    "charts": sc_pivoted["charts"],
                    "table": sc_pivoted["table"],
                }

    context = {
        "page_title": page_title,
        "run_file": path.name if path else None,
        "metrics": pivoted["metrics"],
        "charts": pivoted["charts"],
        "table": pivoted["table"],
        "descriptions": descriptions,
        "scenario_views": scenario_views if scenario_views else None,
    }
    return render_shell(
        request,
        "benchmarks/pages/metric.html",
        context,
        title=f"{page_title} · Benchmarks",
    )
