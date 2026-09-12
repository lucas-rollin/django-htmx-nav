"""
Hand-picked, cross-category panels for the benchmarks overview page.

Meant to display reference data generated via the dockerized bench
along with comments.
"""

from dataclasses import dataclass
from statistics import mean
from typing import Any

from core.navigation.registry import VARIANTS

from .jsonl import read_jsonl, reference_jsonl

FAMILY_ORDER = [
    "mpa",
    "vanilla_htmx_unaware_views",
    "vanilla_htmx_composite",
    "vanilla_htmx_atomic",
    "htmx_nav_baseline",
    "htmx_nav_composite",
    "htmx_nav_declarative",
    "htmx_nav_atomic",
]

SCENARIOS_PAYLOAD = [
    ("project_overview_main_swap", "Main Content"),
    ("project_team_tab_swap", "Tab Swap"),
    ("project_settings_subtab_swap", "Subtab Swap"),
]


@dataclass(frozen=True)
class Panel:
    key: str
    title: str
    caption: str
    chart: dict[str, Any]


def build_panels() -> list[Panel]:
    """Every panel on the overview page, in display order.

    A panel is silently omitted for missing reference file.
    """
    static_rows = _load("static")
    server_rows = _load("server")
    payload_rows = _load("payload")
    client_rows = _load("client")

    candidates = [
        _views_loc(static_rows),
        _server_latency(server_rows),
        _transfer_bytes(payload_rows),
        _queries_vs_swaps(server_rows),
        _htmx_processing(client_rows),
    ]
    return [p for p in candidates if p is not None]


# --- shared helpers ---------------------------------------------------


def _label(namespace: str) -> str:
    variant = VARIANTS.get(namespace)
    return variant.label if variant else namespace


def _load(prefix: str) -> list[dict]:
    path = reference_jsonl(prefix)
    if path is None:
        return []
    return read_jsonl(path)


def _averaged_base(rows: list[dict], metric: str) -> dict[str, float]:
    """variant -> mean value for `metric`, restricted to base (no-axis)
    variants, averaged across however many scenarios that metric has."""
    grouped: dict[str, list[float]] = {}
    for row in rows:
        if row["metric"] != metric:
            continue
        if row["uses_hx_select"] or row["uses_morph"]:
            continue
        v = row["variant"]
        if v == "vanilla_htmx_unaware_view":
            v = "vanilla_htmx_unaware_views"
        grouped.setdefault(v, []).append(row["value"])
    return {variant: round(mean(values), 3) for variant, values in grouped.items()}


def _ordered(values: dict[str, float]) -> tuple[list[str], list[float]]:
    """Restricts + orders `values` by FAMILY_ORDER, dropping anything not
    present rather than guessing a position for it (e.g. a metric that
    wasn't collected for every variant in this run)."""
    present = [v for v in FAMILY_ORDER if v in values]
    return [_label(v) for v in present], [values[v] for v in present]


# --- individual panels --------------------------------------------------


def _views_loc(static_rows) -> Panel | None:
    views = _averaged_base(static_rows, "views_loc")
    attrs = _averaged_base(static_rows, "total_template_hx_attributes")
    variants = [v for v in FAMILY_ORDER if v in views and v in attrs]
    if not variants:
        return None

    labels = [_label(v) for v in variants]
    return Panel(
        key="views_loc",
        title="Code complexity: Views vs. template maintenance",
        caption=(
            "<b>htmx_nav_declarative</b> achieves the lowest Python view footprint "
            "(<b>305 LOC</b>, ~<b>30% fewer lines</b> than plain MPA) by offloading context and swap "
            "logic to a declarative navigation file. In contrast, while Vanilla Unaware views appear identical "
            "to plain MPA in Python LOC (434), pairing them with <code>hx-select</code> pushes "
            "routing plumbing into HTML, quadrupling manual <code>hx-*</code> attributes from 6 "
            "up to <b>27</b>."
        ),
        chart={
            "type": "bar_line",
            "labels": labels,
            "bar_values": [views[v] for v in variants],
            "bar_name": "views LOC (Python)",
            "line_values": [attrs[v] for v in variants],
            "line_name": "template hx-* attributes",
        },
    )


def _server_latency(server_rows) -> Panel | None:
    p50_map = _averaged_base(server_rows, "render_time_ms_median")
    p95_map = _averaged_base(server_rows, "render_time_ms_p95")
    variants = [v for v in FAMILY_ORDER if v in p50_map and v in p95_map]
    if not variants:
        return None

    labels = [_label(v) for v in variants]
    series = [
        {
            "name": "Median (P50)",
            "data": [p50_map[v] for v in variants],
        },
        {
            "name": "Tail Latency (P95)",
            "data": [p95_map[v] for v in variants],
        },
    ]

    return Panel(
        key="server_latency",
        title="Server render time: Median (P50) vs. tail (P95) latency",
        caption=(
            "Server-side navigation synchronization in <b>htmx_nav</b> adds <b>near-zero CPU overhead</b> "
            "(~<b>7.0 ms</b> median across all approaches). Furthermore, partial rendering tightens tail "
            "latency: full-shell rendering under load spikes to <b>11.9 ms</b> (P95) in Vanilla Unaware, "
            "while partial and declarative swaps stay consistently below <b>8.2 ms</b>."
        ),
        chart={
            "type": "grouped_bar",
            "labels": labels,
            "series": series,
            "y_name": "ms",
        },
    )


def _transfer_bytes(payload_rows) -> Panel | None:
    data_by_scenario: dict[str, dict[str, float]] = {sc[0]: {} for sc in SCENARIOS_PAYLOAD}
    for row in payload_rows:
        if row["metric"] != "transfer_bytes":
            continue
        if row["uses_hx_select"] or row["uses_morph"]:
            continue
        sc = row.get("scenario")
        if sc in data_by_scenario:
            v = row["variant"]
            if v == "vanilla_htmx_unaware_view":
                v = "vanilla_htmx_unaware_views"
            data_by_scenario[sc][v] = row["value"]

    present_families = [
        f
        for f in FAMILY_ORDER
        if all(f in data_by_scenario[sc[0]] for sc in SCENARIOS_PAYLOAD)
    ]
    if not present_families:
        return None

    labels = [_label(f) for f in present_families]
    series = [
        {
            "name": display_name,
            "data": [data_by_scenario[sc_key][f] for f in present_families],
        }
        for sc_key, display_name in SCENARIOS_PAYLOAD
    ]

    return Panel(
        key="transfer_bytes",
        title="On-wire payload by swap level (gzip)",
        caption=(
            "Across <b>Main</b>, <b>Tab</b>, and <b>Subtab</b> content swaps, partial rendering "
            "consistently cuts wire transfer in half (~<b>3.0-3.3 KB</b> vs ~<b>6.1-6.3 KB</b> in Pure MPA & Vanilla Unaware). "
            "In deeply nested subtab swaps, <b>Atomic</b> and <b>Declarative</b> strategies achieve the lowest payload "
            "(&lt;<b>3.0 KB</b>) by swapping only the leaf container."
        ),
        chart={
            "type": "grouped_bar",
            "labels": labels,
            "series": series,
            "y_name": "bytes",
        },
    )


def _queries_vs_swaps(server_rows) -> Panel | None:
    queries = _averaged_base(server_rows, "db_query_count")
    swaps = _averaged_base(server_rows, "swap_render_count")
    variants = [v for v in FAMILY_ORDER if v in queries and v in swaps]
    if not variants:
        return None

    labels = [_label(v) for v in variants]
    return Panel(
        key="queries_vs_swaps",
        title="DB queries stay flat as OOB swap count rises",
        caption=(
            "DB queries average <b>4.5</b> across all approaches regardless of "
            "OOB fragment count. Swap context is built once per request via "
            "<b>cache_on_request</b> and reused across fragments, avoiding "
            "per-swap query overhead."
        ),
        chart={
            "type": "bar_line",
            "labels": labels,
            "bar_values": [swaps[v] for v in variants],
            "bar_name": "avg swaps rendered",
            "line_values": [queries[v] for v in variants],
            "line_name": "avg DB queries",
        },
    )


def _htmx_processing(client_rows) -> Panel | None:
    htmx_families = [f for f in FAMILY_ORDER if f != "mpa"]

    series_defs = [
        ("Base (innerHTML)", lambda r: not r.get("uses_hx_select") and not r.get("uses_morph")),
        ("+hx-select", lambda r: r.get("uses_hx_select") and not r.get("uses_morph")),
        ("+Idiomorph", lambda r: not r.get("uses_hx_select") and r.get("uses_morph")),
        ("+hx-select + Morph", lambda r: r.get("uses_hx_select") and r.get("uses_morph")),
    ]

    series = []
    for name, pred in series_defs:
        data = []
        for fam in htmx_families:
            matching = [
                r["value"]
                for r in client_rows
                if r["metric"] == "htmx_processing_ms"
                and (
                    r["family"] == fam
                    or (fam == "vanilla_htmx_unaware_views" and r["family"] in ("vanilla_htmx_unaware_view", "vanilla_htmx_unaware_views"))
                )
                and pred(r)
            ]
            data.append(round(mean(matching), 1) if matching else None)
        series.append({"name": name, "data": data})

    labels = [_label(f) for f in htmx_families]

    return Panel(
        key="htmx_processing_ms",
        title="Client DOM processing across extensions (hx-select vs. morph)",
        caption=(
            "Using <code>hx-select</code> delivers a <b>50-63% reduction</b> in client DOM processing "
            "time (dropping to ~<b>12.7 ms</b> in HTMX-Nav) because the browser only parses the matching subtree. "
            "In contrast, <b>Idiomorph</b> adds ~<b>5-10 ms</b> of JavaScript DOM diffing on full page shells "
            "(Vanilla Unaware jumps to <b>53.5 ms</b>). Combining <code>+hx-select</code> with Idiomorph "
            "provides a balance of morphing state preservation without the large-tree diffing cost."
        ),
        chart={
            "type": "grouped_bar",
            "labels": labels,
            "series": series,
            "y_name": "ms",
        },
    )
