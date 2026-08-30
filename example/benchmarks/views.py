"""
Benchmarks dashboard views.
"""

from django.http import Http404, HttpRequest, HttpResponse

from .metrics.helpers.pivot import pivot_rows
from .metrics.jsonl import latest_jsonl, read_jsonl
from .metrics.registry import describe
from .render import render_shell

CATEGORIES = {
    "static": "Code Complexity / DX",
    "server": "Server Performance",
    "payload": "Payload Size",
    "client": "Client Performance",
}

OVERVIEW_PLACEHOLDERS = [
    "Server render time vs. swap-render count",
    "Payload size (gzip) by axis: hx-select vs. morph vs. base",
    "Code complexity vs. correctness pass rate",
    "Files touched per page, by family",
]


def overview(request: HttpRequest) -> HttpResponse:
    """Hand picked charts and experiment overview."""
    return render_shell(
        request,
        "benchmarks/pages/overview.html",
        {"overview_placeholders": OVERVIEW_PLACEHOLDERS},
        title="Overview · Benchmarks",
    )


def metric_page(request: HttpRequest, prefix: str) -> HttpResponse:
    """Auto generated metric dashboards."""
    if prefix not in CATEGORIES:
        raise Http404(f"Unknown benchmark category: {prefix!r}")

    page_title = CATEGORIES[prefix]
    path = latest_jsonl(prefix)
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

    context = {
        "page_title": page_title,
        "run_file": path.name if path else None,
        "metrics": pivoted["metrics"],
        "charts": pivoted["charts"],
        "table": pivoted["table"],
        "descriptions": descriptions,
    }
    return render_shell(
        request,
        "benchmarks/pages/metric.html",
        context,
        title=f"{page_title} · Benchmarks",
    )
