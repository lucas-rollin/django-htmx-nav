"""
Single source of truth for metric identifiers and their presentation
metadata (label, description, unit, direction).

`Metric` is the only place a metric name is spelled out as a literal
string. Collectors emit `Metric.X` members instead of hand-typed
strings, so a typo in a collector can't silently diverge from this
registry the way two independently-maintained string literals could.

The `assert set(Metric) == set(METRICS)` check below enforces that every
enum member has a registry entry and vice versa, at import time.
Forgetting one side fails loudly before any collection or rendering
happens, rather than degrading silently into a generic-fallback tooltip.
"""

from dataclasses import dataclass
from enum import Enum


class Metric(str, Enum):
    """Every metric identifier a collector can emit."""

    # --- metrics/static_analysis.py -----------------------------------------
    VIEWS_LOC = "views_loc"
    TOTAL_TEMPLATE_HX_ATTRIBUTES = "total_template_hx_attributes"
    EXTRA_MODULES_LOC = "extra_modules_loc"
    EXTRA_SHELL_TEMPLATE_LOC = "extra_shell_template_loc"
    TOTAL_NAV_CONCERN_LOC = "total_nav_concern_loc"

    # --- metrics/server.py ---------------------------------------------------
    RENDER_TIME_MS_MEDIAN = "render_time_ms_median"
    RENDER_TIME_MS_P95 = "render_time_ms_p95"
    DB_QUERY_COUNT = "db_query_count"
    SWAP_RENDER_COUNT = "swap_render_count"
    STATUS_OK = "status_ok"

    # --- metrics/payload.py ---------------------------------------------------
    TRANSFER_BYTES = "transfer_bytes"
    DECODED_BYTES = "decoded_bytes"

    # --- metrics/client.py ----------------------------------------------------
    INTERACTION_TO_PAINT_MS = "interaction_to_paint_ms"
    HTMX_PROCESSING_MS = "htmx_processing_ms"
    DOM_MUTATIONS = "dom_mutations"
    DOM_NODES_ADDED = "dom_nodes_added"
    DOM_NODES_REMOVED = "dom_nodes_removed"


@dataclass(frozen=True)
class MetricInfo:
    label: str
    description: str
    unit: str
    lower_is_better: bool | None = (
        None  # None = not directional (e.g. bool/count with no inherent "better")
    )


METRICS: dict[Metric, MetricInfo] = {
    # --- metrics/static_analysis.py -----------------------------------------
    Metric.VIEWS_LOC: MetricInfo(
        "Views LOC",
        "Non-blank, non-comment lines in the variant's views module.",
        "lines",
        lower_is_better=True,
    ),
    Metric.TOTAL_TEMPLATE_HX_ATTRIBUTES: MetricInfo(
        "Total Template hx attributes",
        "Count of real hx-*/data-hx-* HTML attributes in the rendered page "
        "sample (post-render, not a source-line count), including any "
        "hx-select/morph attributes the axis flags add.",
        "count",
        lower_is_better=True,
    ),
    Metric.EXTRA_MODULES_LOC: MetricInfo(
        "Extra Modules LOC (views)",
        "Lines in Python extra modules (e.g. registries) that support the views.",
        "lines",
        lower_is_better=True,
    ),
    Metric.EXTRA_SHELL_TEMPLATE_LOC: MetricInfo(
        "Extra Shell templates LOC",
        "Lines in html extra templates needed to wrap swap rendering logic. "
        "Zero for variants where swap-resolution logic stays entirely in Python.",
        "lines",
        lower_is_better=True,
    ),
    Metric.TOTAL_NAV_CONCERN_LOC: MetricInfo(
        "Total Nav-concern LOC",
        "Lines in Python, views and extra modules, that exist specifically to serve partial "
        "resolution / OOB-swap sync (Swap(...), render_nav(...), targeting(...), "
        "HX-Target branches), rather than page content or business logic.",
        "lines",
        lower_is_better=True,
    ),
    # --- metrics/server.py ---------------------------------------------------
    Metric.RENDER_TIME_MS_MEDIAN: MetricInfo(
        "Render time (median)",
        "Median server-side render time across repeated requests for this "
        "scenario, via the Django test client.",
        "ms",
        lower_is_better=True,
    ),
    Metric.RENDER_TIME_MS_P95: MetricInfo(
        "Render time (p95)",
        "95th-percentile server-side render time — tail latency, more sensitive "
        "to occasional slow renders than the median.",
        "ms",
        lower_is_better=True,
    ),
    Metric.DB_QUERY_COUNT: MetricInfo(
        "DB queries",
        "Number of database queries executed for a single request to this scenario.",
        "count",
        lower_is_better=True,
    ),
    Metric.SWAP_RENDER_COUNT: MetricInfo(
        "Swap render count",
        "Number of Swap.render() calls triggered by a single request — i.e. how "
        "many separate out-of-band/hx-partial fragments were rendered alongside "
        "the main response. Compare against render time to see whether "
        "rendering more swaps actually costs meaningful time.",
        "count",
        lower_is_better=None,
    ),
    Metric.STATUS_OK: MetricInfo(
        "Status OK",
        "1 if every sampled request for this scenario returned HTTP 200, else 0.",
        "bool",
        lower_is_better=False,
    ),
    # --- metrics/payload.py ---------------------------------------------------
    Metric.TRANSFER_BYTES: MetricInfo(
        "Transfer size",
        "Actual on-wire response size, gzip-compressed, from a real HTTP request "
        "against a running dev server.",
        "bytes",
        lower_is_better=True,
    ),
    Metric.DECODED_BYTES: MetricInfo(
        "Decoded size",
        "Uncompressed response body size.",
        "bytes",
        lower_is_better=True,
    ),
    # --- metrics/client.py ----------------------------------------------------
    Metric.INTERACTION_TO_PAINT_MS: MetricInfo(
        "Interaction-to-paint",
        "Time from HTMX request initiation until a post-settle animation-frame "
        "boundary, approximating when the updated UI becomes visually observable. "
        "This is a benchmark-specific responsiveness metric, not a Core Web Vital. "
        "For variants where htmx.js fails to load, this falls back to a real "
        "full-page-navigation timing (Paint Timing API) instead.",
        "ms",
        lower_is_better=True,
    ),
    Metric.HTMX_PROCESSING_MS: MetricInfo(
        "HTMX processing",
        "Time from htmx:beforeSwap to htmx:afterSettle, covering client-side "
        "response processing, OOB swaps, DOM swapping, morphing, and settling, "
        "but excluding server and network time. Not emitted for variants using "
        "the full-page-navigation fallback (no htmx events to measure from).",
        "ms",
        lower_is_better=True,
    ),
    Metric.DOM_MUTATIONS: MetricInfo(
        "DOM mutations",
        "Number of MutationObserver records generated while HTMX processes "
        "the navigation.",
        "count",
        lower_is_better=True,
    ),
    Metric.DOM_NODES_ADDED: MetricInfo(
        "DOM nodes added",
        "Number of element nodes inserted into the DOM while HTMX processes "
        "the navigation.",
        "count",
        lower_is_better=True,
    ),
    Metric.DOM_NODES_REMOVED: MetricInfo(
        "DOM nodes removed",
        "Number of element nodes removed from the DOM while HTMX processes "
        "the navigation.",
        "count",
        lower_is_better=True,
    ),
}

assert set(Metric) == set(METRICS), (
    "Metric enum and METRICS registry are out of sync — every Metric member "
    "needs a METRICS entry and vice versa."
)


def describe(metric: str) -> MetricInfo:
    """Looks up presentation metadata for a metric identifier. 
    
    Accepts a plain string (as read back from JSONL, where enum members 
    serialize to their .value) as well as a Metric member directly. Falls 
    back to a generic, non-directional description for any identifier not 
    (yet) registered, e.g. a metric a collector just started emitting, so
    rendering never breaks, it just degrades to a plain label."""
    try:
        member = Metric(metric)
    except ValueError:
        member = None

    if member is not None and member in METRICS:
        return METRICS[member]

    return MetricInfo(
        label=str(metric).replace("_", " "),
        description="No description available yet for this metric.",
        unit="",
        lower_is_better=None,
    )
