"""
Real on-wire payload size (post-gzip). The Django test client never
applies GZipMiddleware, so this spawns the actual dev server (via
DevServer) and hits it with `requests`.
"""

import requests
from django.urls import reverse

from ..helpers.server_process import DevServer
from ..jsonl import MetricSample, now_iso
from ..registry import Metric
from ..scenarios import SCENARIOS, get_context
from .base import CollectorContext, run_collector

PORT = 8765


def collect(
    variants: list,
    run_id: str,
    *,
    repeats: int = 10,  # unused — one real request per scenario is enough for byte counts
    timeout_ms: int = 8000,
    debug: bool = False,
    stdout=print,
    stderr=print,
) -> list[MetricSample]:
    bench_ctx = get_context()
    targets = {
        variant.namespace: [
            (
                scenario,
                reverse(
                    f"{variant.namespace}:{scenario.url_name}",
                    args=scenario.args(bench_ctx),
                ),
            )
            for scenario in SCENARIOS
        ]
        for variant in variants
    }

    with DevServer(PORT) as server:

        def collect_one(variant, cctx: CollectorContext) -> list[MetricSample]:
            rows = []
            for scenario, path in targets[variant.namespace]:
                headers = {
                    "Accept-Encoding": "gzip",
                    **_to_real_headers(scenario.headers or {}),
                }
                resp = requests.get(
                    f"{server.base_url}{path}",
                    headers=headers,
                    timeout=cctx.timeout_ms / 1000,
                )
                transfer_bytes = int(
                    resp.headers.get("Content-Length", len(resp.content))
                )
                decoded_bytes = len(resp.content)

                common = dict(
                    run_id=run_id,
                    collected_at=now_iso(),
                    variant=variant.namespace,
                    family=variant.family,
                    group=variant.group,
                    uses_hx_select=variant.uses_hx_select,
                    uses_morph=variant.uses_morph,
                    scenario=scenario.label,
                )
                rows.append(
                    MetricSample(
                        **common, metric=Metric.TRANSFER_BYTES, value=transfer_bytes
                    )
                )
                rows.append(
                    MetricSample(
                        **common, metric=Metric.DECODED_BYTES, value=decoded_bytes
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
        return run_collector("payload", variants, collect_one, ctx)


def _to_real_headers(test_client_style: dict) -> dict:
    """Converts Django-test-client-style HTTP_X_Y keys to real header names."""
    return {
        (k[5:].replace("_", "-").title() if k.startswith("HTTP_") else k): v
        for k, v in test_client_style.items()
    }
