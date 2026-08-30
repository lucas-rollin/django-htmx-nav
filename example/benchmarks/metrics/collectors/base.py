"""
Shared collector infrastructure.

Every category (static/server/payload/client/...) exposes a top-level

    collect(
        variants, run_id, *,
        repeats: int = 10, timeout_ms: int = 8000, debug: bool = False,
        stdout=print, stderr=print,
    ) -> list[MetricSample]

with this exact signature, even if a given category ignores some of the
kwargs, the uniform signature is what lets collect_all_metrics.py call 
every category generically, and lets every collect_<name>_metrics.py 
command stay a thin wrapper.

Internally, `collect()` should delegate the per-variant loop to
`run_collector()` below, which standardizes progress printing and
per-variant failure isolation so no individual collector has to
reimplement either.
"""

import time
import traceback
from dataclasses import dataclass
from typing import Callable

from ..jsonl import MetricSample


@dataclass
class CollectorContext:
    """Options threaded through a single collect() call. Built once per
    category run and passed to each per-variant collect_one(variant, ctx)."""

    run_id: str
    repeats: int = 10
    timeout_ms: int = 8000
    debug: bool = False
    stdout: Callable[[str], None] = print
    stderr: Callable[[str], None] = print


VariantCollectFn = Callable[[object, "CollectorContext"], list[MetricSample]]
"""A per-variant collector: takes one Variant + the shared
CollectorContext, returns its MetricSample rows (or raises —
run_collector() catches and isolates the failure to that variant)."""


def run_collector(
    label: str,
    variants: list,
    collect_one: VariantCollectFn,
    ctx: CollectorContext,
) -> list[MetricSample]:
    """Runs collector over every variant printing progress.
    
    Isolates per-variant failures so one broken variant never aborts 
    the whole run. `ctx.debug` controls whether a failure prints a full 
    traceback or a one-line summary, pass --debug on any collect_*_metrics
    command (or collect_all_metrics) to see the traceback.
    """
    rows: list[MetricSample] = []
    total = len(variants)

    for i, variant in enumerate(variants, start=1):
        started = time.perf_counter()
        ctx.stdout(f"[{label}] [{i}/{total}] {variant.namespace} — starting...")
        try:
            variant_rows = collect_one(variant, ctx)
            rows.extend(variant_rows)
            elapsed = time.perf_counter() - started
            ctx.stdout(
                f"[{label}] [{i}/{total}] {variant.namespace} — done in "
                f"{elapsed:.1f}s ({len(variant_rows)} rows)"
            )
        except Exception as exc:
            elapsed = time.perf_counter() - started
            ctx.stderr(
                f"[{label}] [{i}/{total}] {variant.namespace} — FAILED after "
                f"{elapsed:.1f}s: {exc}"
            )
            if ctx.debug:
                ctx.stderr(traceback.format_exc())

    return rows
