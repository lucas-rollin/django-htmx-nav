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
        _nav_concern_vs_render_time(static_rows, server_rows),
        _views_loc(static_rows),
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


def _nav_concern_vs_render_time(static_rows, server_rows) -> Panel | None:
    nav_loc = _averaged_base(static_rows, "total_nav_concern_loc")
    render_ms = _averaged_base(server_rows, "render_time_ms_median")
    variants = [v for v in FAMILY_ORDER if v in nav_loc and v in render_ms]
    if not variants:
        return None

    points = [
        {"name": _label(v), "value": [nav_loc[v], render_ms[v]]} for v in variants
    ]
    return Panel(
        key="nav_concern_vs_render_time",
        title="Nav-sync Python cost vs. server render time",
        caption=(
            "Extra Python for navigation sync buys <b>near-zero render time</b>. "
            "The <b>htmx_nav</b> variants add 21–44 lines of nav-concern code "
            "for a render spread under <b>0.5 ms</b> (well within normal test noise)."
        ),
        chart={
            "type": "scatter",
            "points": points,
            "x_name": "nav-concern LOC",
            "y_name": "render time median (ms)",
        },
    )


def _views_loc(static_rows) -> Panel | None:
    values = _averaged_base(static_rows, "views_loc")
    labels, series = _ordered(values)
    if not labels:
        return None
    return Panel(
        key="views_loc",
        title="Views LOC by approach",
        caption=(
            "<b>htmx_nav_declarative</b> beats the plain MPA baseline in code size "
            "despite syncing full navigation components. <b>htmx_nav_atomic</b> uses "
            "explicit, inline swaps per view to highlight the structural savings "
            "of the declarative approach."
        ),
        chart={"type": "bar", "labels": labels, "values": series, "y_name": "lines"},
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
    values = _averaged_base(client_rows, "htmx_processing_ms")
    labels, series = _ordered(values)
    if not labels:
        return None
    return Panel(
        key="htmx_processing_ms",
        title="Client-side htmx processing time",
        caption=(
            "Measures DOM swap/settle duration (<b>htmx:beforeSwap</b> to "
            "<b>htmx:afterSettle</b>). <b>mpa</b> is omitted as it fires no htmx "
            "events. <i>Note: Treat relative ordering as the primary signal, "
            "as absolute milliseconds are hardware-dependent.</i>"
        ),
        chart={"type": "bar", "labels": labels, "values": series, "y_name": "ms"},
    )
