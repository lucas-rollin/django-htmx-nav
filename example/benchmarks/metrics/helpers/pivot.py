"""
Pivots a flat list of MetricSample-shaped dicts (read from JSONL) into
the {metrics, charts, table} shape the dashboard templates and
dashboard.js consume.

Variant/family display labels are looked up from core.navigation.registry.VARIANTS
at render time, the same pattern example/config/context_processors.py
already uses for the navbar, rather than stored in JSONL, so a rename
in variants.py is reflected immediately without touching historical data
files. Only the underlying slugs are ever written to JSONL; labels never
enter the stored schema, keeping slug vs. label a presentation-only
concern.
"""

from collections import defaultdict
from statistics import mean
from typing import Any

from core.navigation.registry import VARIANTS


def axis_label(uses_hx_select: bool, uses_morph: bool) -> str:
    bits = [b for b, on in (("hx-select", uses_hx_select), ("morph", uses_morph)) if on]
    return "+".join(bits) or "base"


def _variant_label(namespace: str) -> str:
    variant = VARIANTS.get(namespace)
    return variant.label if variant else namespace


def _family_label(family_key: str) -> str:
    for variant in VARIANTS.values():
        if variant.family == family_key:
            return variant.family_label
    return family_key


def pivot_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"metrics": [], "charts": {}, "table": {"columns": [], "rows": []}}

    variant_meta: dict[str, dict] = {}
    variant_order: list[str] = []
    metrics_seen: list[str] = []
    buckets: dict[tuple[str, str], list[float]] = defaultdict(list)

    for row in rows:
        variant, metric = row["variant"], row["metric"]
        if variant not in variant_meta:
            variant_meta[variant] = {
                "family": row["family"],
                "family_label": _family_label(row["family"]),
                "variant_label": _variant_label(variant),
                "axis": axis_label(row["uses_hx_select"], row["uses_morph"]),
            }
            variant_order.append(variant)
        if metric not in metrics_seen:
            metrics_seen.append(metric)
        buckets[(variant, metric)].append(row["value"])

    # Sort by display label, not slug, so table/chart order matches what
    # the person actually reads, this line is the entire "sort by
    # label" behavior; no separate comparator is needed downstream since
    # the table's own sortedRows just reads row["variant_label"] directly.
    variant_order.sort(key=lambda v: variant_meta[v]["variant_label"])

    averaged = {key: round(mean(values), 3) for key, values in buckets.items()}

    table_rows = []
    for variant in variant_order:
        meta = variant_meta[variant]
        cells = {
            "variant": variant,  # slug — internal key only, never a displayed column
            "variant_label": meta["variant_label"],
            "family": meta[
                "family"
            ],  # slug — internal key only, never a displayed column
            "family_label": meta["family_label"],
            "axis": meta["axis"],
        }
        for metric in metrics_seen:
            cells[metric] = averaged.get((variant, metric))
        table_rows.append(cells)

    charts = {
        metric: {
            "labels": variant_order,  # slugs — used to join back to table.rows in JS
            "display_labels": [variant_meta[v]["variant_label"] for v in variant_order],
            "values": [averaged.get((variant, metric)) for variant in variant_order],
        }
        for metric in metrics_seen
    }

    return {
        "metrics": metrics_seen,
        "charts": charts,
        "table": {
            "columns": ["variant_label", "family_label", "axis", *metrics_seen],
            "rows": table_rows,
        },
    }
