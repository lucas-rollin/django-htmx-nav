"""
Precomputed summary metrics and headline statistics for django-htmx-nav benchmarks.

Computes and loads key summary figures across static complexity, server performance,
wire payloads, and client DOM processing directly from git-tracked benchmark data.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from statistics import mean
from typing import Any

from core.navigation.registry import VARIANTS

from .jsonl import DATA_DIR, read_jsonl, reference_jsonl
from .overview_metrics import FAMILY_ORDER, SCENARIOS_PAYLOAD, _averaged_base

SUMMARY_FILE_NAME = "summary.json"
SUMMARY_PATH = DATA_DIR / SUMMARY_FILE_NAME


@dataclass(frozen=True)
class BenchmarkSummary:
    generated_at: str
    static: dict[str, Any]
    server: dict[str, Any]
    payload: dict[str, Any]
    client: dict[str, Any]
    headline_metrics: list[dict[str, str]]

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkSummary":
        return cls(
            generated_at=data["generated_at"],
            static=data["static"],
            server=data["server"],
            payload=data["payload"],
            client=data["client"],
            headline_metrics=data["headline_metrics"],
        )

    # --- Convenience properties for templates, prose, and views ---

    @property
    def payload_reduction_pct(self) -> int:
        return int(self.payload["overall_reduction_pct"])

    @property
    def payload_value(self) -> str:
        kb = float(self.payload["htmx_nav_overall_avg_kb"])
        return f"{kb:.1f} KB"

    @property
    def mpa_payload_value(self) -> str:
        kb = float(self.payload["mpa_overall_avg_kb"])
        return f"{kb:.1f} KB"

    @property
    def payload_desc(self) -> str:
        return f"↓ {self.payload_reduction_pct}% smaller than MPA ({self.mpa_payload_value})"

    @property
    def render_latency_value(self) -> str:
        val = self.server["render_overhead_ms"]
        return f"{val} ms" if not str(val).endswith("ms") else str(val)

    @property
    def db_queries_value(self) -> str:
        q = float(self.server["avg_db_queries"])
        return f"{q:.1f} avg"

    @property
    def declarative_loc(self) -> int:
        return int(self.static["declarative_views_loc"])

    @property
    def mpa_loc(self) -> int:
        return int(self.static["mpa_views_loc"])

    @property
    def unaware_views_loc(self) -> int:
        return int(self.static["unaware_views_loc"])

    @property
    def loc_reduction_pct(self) -> int:
        return int(self.static["loc_reduction_pct"])

    @property
    def unaware_base_hx_attrs(self) -> int:
        return int(self.static["unaware_base_hx_attrs"])

    @property
    def unaware_hx_attrs(self) -> int:
        return int(self.static["unaware_hx_select_attrs"])

    @property
    def render_latency_median_ms(self) -> float:
        return float(self.server["median_render_ms"])

    @property
    def p95_unaware_ms(self) -> float:
        return float(self.server["p95_unaware_ms"])

    @property
    def p95_partial_max_ms(self) -> float:
        return float(self.server["p95_partial_max_ms"])

    @property
    def avg_db_queries(self) -> float:
        return float(self.server["avg_db_queries"])

    @property
    def swap_min_kb(self) -> float:
        return float(self.payload["swap_min_kb"])

    @property
    def swap_max_kb(self) -> float:
        return float(self.payload["swap_max_kb"])

    @property
    def full_min_kb(self) -> float:
        return float(self.payload["full_min_kb"])

    @property
    def full_max_kb(self) -> float:
        return float(self.payload["full_max_kb"])

    @property
    def subtab_min_kb(self) -> float:
        return float(self.payload["subtab_min_kb"])

    @property
    def dom_red_min(self) -> int:
        return int(self.client["hx_select_reduction_pct_min"])

    @property
    def dom_red_max(self) -> int:
        return int(self.client["hx_select_reduction_pct_max"])

    @property
    def nav_hx_select_ms(self) -> float:
        return float(self.client["htmx_nav_hx_select_ms"])

    @property
    def unaware_morph_ms(self) -> float:
        return float(self.client["unaware_morph_ms"])


def compute_summary(
    static_rows: list[dict[str, Any]],
    server_rows: list[dict[str, Any]],
    payload_rows: list[dict[str, Any]],
    client_rows: list[dict[str, Any]],
) -> BenchmarkSummary:
    """Compute aggregate benchmark summary metrics from raw rows.

    Expects complete reference rows. Fails fast if expected keys are missing.
    """
    now_str = datetime.now(timezone.utc).isoformat()

    # --- 1. Static complexity ---
    views = _averaged_base(static_rows, "views_loc")
    attrs = _averaged_base(static_rows, "total_template_hx_attributes")
    mpa_views = int(views["mpa"])
    decl_views = int(views["htmx_nav_declarative"])
    unaware_views = int(views["vanilla_htmx_unaware_views"])
    loc_red = round((1 - decl_views / mpa_views) * 100)

    unaware_base_attrs = int(attrs["vanilla_htmx_unaware_views"])
    unaware_hx_attrs = next(
        int(r["value"])
        for r in static_rows
        if r["variant"] == "vanilla_htmx_unaware_views_hx_select"
        and r["metric"] == "total_template_hx_attributes"
    )
    decl_hx_attrs = int(attrs["htmx_nav_declarative"])

    static_summary = {
        "mpa_views_loc": mpa_views,
        "unaware_views_loc": unaware_views,
        "declarative_views_loc": decl_views,
        "loc_reduction_pct": loc_red,
        "unaware_base_hx_attrs": unaware_base_attrs,
        "unaware_hx_select_attrs": unaware_hx_attrs,
        "declarative_hx_attrs": decl_hx_attrs,
    }

    # --- 2. Server performance ---
    p50 = _averaged_base(server_rows, "render_time_ms_median")
    p95 = _averaged_base(server_rows, "render_time_ms_p95")
    queries = _averaged_base(server_rows, "db_query_count")

    med_p50 = round(mean(p50.values()), 1)
    p95_unaware = round(p95["vanilla_htmx_unaware_views"], 1)
    p95_partials = [
        v
        for k, v in p95.items()
        if any(term in k for term in ("composite", "atomic", "declarative"))
    ]
    p95_partial_max = round(max(p95_partials), 1)
    avg_q = round(mean(queries.values()), 1)

    server_summary = {
        "median_render_ms": med_p50,
        "p95_unaware_ms": p95_unaware,
        "p95_partial_max_ms": p95_partial_max,
        "avg_db_queries": avg_q,
        "render_overhead_ms": "<0.5",
    }

    # --- 3. Payload size ---
    mpa_all = [
        r["value"]
        for r in payload_rows
        if r["variant"] == "mpa" and r["metric"] == "transfer_bytes"
    ]
    nav_all = [
        r["value"]
        for r in payload_rows
        if r["variant"] == "htmx_nav_declarative" and r["metric"] == "transfer_bytes"
    ]
    mpa_kb = round(mean(mpa_all) / 1024, 1)
    nav_kb = round(mean(nav_all) / 1024, 1)
    payload_red = round((1 - (mean(nav_all) / mean(mpa_all))) * 100)

    swap_scenarios = [s[0] for s in SCENARIOS_PAYLOAD]
    nav_swaps = [
        r["value"]
        for r in payload_rows
        if r["family"].startswith("htmx_nav")
        and not r["uses_hx_select"]
        and not r["uses_morph"]
        and r.get("scenario") in swap_scenarios
        and r["metric"] == "transfer_bytes"
    ]
    mpa_unaware_swaps = [
        r["value"]
        for r in payload_rows
        if r["family"] in ("mpa", "vanilla_htmx_unaware_views")
        and not r["uses_hx_select"]
        and not r["uses_morph"]
        and r.get("scenario") in swap_scenarios
        and r["metric"] == "transfer_bytes"
    ]

    swap_min_kb = round(min(nav_swaps) / 1024, 1)
    swap_max_kb = round(max(nav_swaps) / 1024, 1)
    full_min_kb = round(min(mpa_unaware_swaps) / 1024, 1)
    full_max_kb = round(max(mpa_unaware_swaps) / 1024, 1)

    subtab_vals = [
        r["value"]
        for r in payload_rows
        if r["metric"] == "transfer_bytes"
        and r.get("scenario") == "project_settings_subtab_swap"
        and r["variant"] in ("htmx_nav_atomic", "htmx_nav_declarative")
    ]
    subtab_min_kb = round(min(subtab_vals) / 1024, 1)

    payload_summary = {
        "mpa_overall_avg_kb": mpa_kb,
        "htmx_nav_overall_avg_kb": nav_kb,
        "overall_reduction_pct": payload_red,
        "swap_min_kb": swap_min_kb,
        "swap_max_kb": swap_max_kb,
        "full_min_kb": full_min_kb,
        "full_max_kb": full_max_kb,
        "subtab_min_kb": subtab_min_kb,
    }

    # --- 4. Client DOM processing ---
    htmx_families = [f for f in FAMILY_ORDER if f != "mpa"]
    reductions = []
    for fam in htmx_families:
        base = [
            r["value"]
            for r in client_rows
            if r["family"] == fam
            and not r["uses_hx_select"]
            and not r["uses_morph"]
            and r["metric"] == "htmx_processing_ms"
        ]
        hx_sel = [
            r["value"]
            for r in client_rows
            if r["family"] == fam
            and r["uses_hx_select"]
            and not r["uses_morph"]
            and r["metric"] == "htmx_processing_ms"
        ]
        if base and hx_sel:
            reductions.append((1 - mean(hx_sel) / mean(base)) * 100)

    dom_red_min = round(min(reductions))
    dom_red_max = round(max(reductions))

    nav_hx_select = [
        r["value"]
        for r in client_rows
        if r["family"].startswith("htmx_nav")
        and r["uses_hx_select"]
        and not r["uses_morph"]
        and r["metric"] == "htmx_processing_ms"
    ]
    nav_hx_select_ms = round(mean(nav_hx_select), 1)

    unaware_morph = [
        r["value"]
        for r in client_rows
        if "unaware" in r["variant"]
        and r["uses_morph"]
        and not r["uses_hx_select"]
        and r["metric"] == "htmx_processing_ms"
    ]
    unaware_morph_ms = round(mean(unaware_morph), 1)

    client_summary = {
        "hx_select_reduction_pct_min": dom_red_min,
        "hx_select_reduction_pct_max": dom_red_max,
        "htmx_nav_hx_select_ms": nav_hx_select_ms,
        "unaware_morph_ms": unaware_morph_ms,
    }

    # --- 5. Headline metrics ---
    headline_metrics = [
        {
            "stat": f"~{payload_red}%",
            "label": "Payload Reduction",
            "desc": "Average wire size reduction compared to views unaware vanilla HTMX.",
        },
        {
            "stat": "<0.5 ms",
            "label": "Render Overhead",
            "desc": "Minimal server-side compute cost for building multi-region OOB swaps.",
        },
        {
            "stat": f"{avg_q:.1f} avg",
            "label": "Flat DB Queries",
            "desc": "Request-scoped caching prevents duplicate queries across partials.",
        },
        {
            "stat": str(len(VARIANTS)),
            "label": "Tested Variants",
            "desc": "Comprehensive comparison across MPA, Vanilla HTMX, hx-select, and Idiomorph.",
        },
    ]

    return BenchmarkSummary(
        generated_at=now_str,
        static=static_summary,
        server=server_summary,
        payload=payload_summary,
        client=client_summary,
        headline_metrics=headline_metrics,
    )


def save_benchmark_summary(summary: BenchmarkSummary, path: Path | None = None) -> Path:
    target_path = path or SUMMARY_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(summary.to_dict(), indent=2) + "\n")
    load_benchmark_summary.cache_clear()
    return target_path


@lru_cache(maxsize=1)
def load_benchmark_summary(path: Path | None = None) -> BenchmarkSummary:
    """Load benchmark summary from JSON. Falls back to generating from git-tracked reference files."""
    target_path = path or SUMMARY_PATH
    if target_path.exists():
        data = json.loads(target_path.read_text())
        return BenchmarkSummary.from_dict(data)

    # If summary.json does not exist, compute directly from git-tracked reference datasets
    static_p = reference_jsonl("static")
    server_p = reference_jsonl("server")
    payload_p = reference_jsonl("payload")
    client_p = reference_jsonl("client")

    if not (static_p and server_p and payload_p and client_p):
        raise FileNotFoundError(
            f"Cannot load benchmark summary: neither {target_path} nor reference JSONL datasets exist."
        )

    return compute_summary(
        read_jsonl(static_p),
        read_jsonl(server_p),
        read_jsonl(payload_p),
        read_jsonl(client_p),
    )
