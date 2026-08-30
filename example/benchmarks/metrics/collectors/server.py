"""
Server render time / DB query count / Swap-render count, collected
in-process via the Django test client, no browser or subprocess needed.

Directly tests the "does rendering N out-of-band swaps instead of one
kill performance" question: swap_render_count and render_time_ms_median
come from the exact same request, so they're correlatable per
(variant, scenario) rather than just compared across variants.
"""

import statistics
import time

from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

import htmx_nav.swaps as swaps_module

from ..jsonl import MetricSample, now_iso
from ..registry import Metric
from ..scenarios import SCENARIOS, get_context
from .base import CollectorContext, run_collector


def collect(
    variants: list,
    run_id: str,
    *,
    repeats: int = 20,
    timeout_ms: int = 8000,  # unused
    debug: bool = False,
    stdout=print,
    stderr=print,
) -> list[MetricSample]:
    bench_ctx = get_context()
    client = Client()

    if variants:
        warm = SCENARIOS[0]
        url = reverse(
            f"{variants[0].namespace}:{warm.url_name}", args=warm.args(bench_ctx)
        )
        with override_settings(HTMX_NAV_DEBUG_SWAPS=False):
            client.get(
                url
            )  # warm DB connection / template loader cache before timing starts

    def collect_one(variant, cctx: CollectorContext) -> list[MetricSample]:
        rows = []
        with override_settings(HTMX_NAV_DEBUG_SWAPS=False):
            for scenario in SCENARIOS:
                url = reverse(
                    f"{variant.namespace}:{scenario.url_name}",
                    args=scenario.args(bench_ctx),
                )
                headers = scenario.headers or {}

                durations_ms, ok = [], True
                for _ in range(cctx.repeats):
                    start = time.perf_counter()
                    response = client.get(url, **headers)
                    durations_ms.append((time.perf_counter() - start) * 1000)
                    ok = ok and response.status_code == 200

                query_count, swap_render_count = _single_sample(client, url, headers)
                rows.extend(
                    _rows(
                        run_id,
                        variant,
                        scenario.label,
                        durations_ms,
                        query_count,
                        swap_render_count,
                        ok,
                    )
                )
        return rows

    ctx = CollectorContext(
        run_id=run_id,
        repeats=repeats,
        timeout_ms=timeout_ms,
        debug=debug,
        stdout=stdout,
        stderr=stderr,
    )
    return run_collector("server", variants, collect_one, ctx)


def _single_sample(client, url, headers):
    original_render = swaps_module.Swap.render
    counter = {"n": 0}

    def counted(self, *a, **kw):
        counter["n"] += 1
        return original_render(self, *a, **kw)

    swaps_module.Swap.render = counted
    try:
        with CaptureQueriesContext(connection) as queries:
            client.get(url, **headers)
    finally:
        swaps_module.Swap.render = original_render

    return len(queries), counter["n"]


def _rows(
    run_id, variant, scenario_label, durations_ms, query_count, swap_render_count, ok
):
    common = dict(
        run_id=run_id,
        collected_at=now_iso(),
        variant=variant.namespace,
        family=variant.family,
        group=variant.group,
        uses_hx_select=variant.uses_hx_select,
        uses_morph=variant.uses_morph,
        scenario=scenario_label,
    )
    return [
        MetricSample(
            **common,
            metric=Metric.RENDER_TIME_MS_MEDIAN,
            value=round(statistics.median(durations_ms), 3),
        ),
        MetricSample(
            **common,
            metric=Metric.RENDER_TIME_MS_P95,
            value=round(_percentile(durations_ms, 0.95), 3),
        ),
        MetricSample(**common, metric=Metric.DB_QUERY_COUNT, value=query_count),
        MetricSample(
            **common, metric=Metric.SWAP_RENDER_COUNT, value=swap_render_count
        ),
        MetricSample(**common, metric=Metric.STATUS_OK, value=1 if ok else 0),
    ]


def _percentile(values, pct):
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    k = (len(values) - 1) * pct
    f, c = int(k), min(int(k) + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)
