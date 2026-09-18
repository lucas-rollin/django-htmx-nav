"""
Code-complexity / DX metrics for all variants.

This is overall pure static analysis except `total_template_hx_attributes`
which performs a render to count htmx attributes, required to simulate
the handwritten htmx attributes used for the variant without abstractions
used for this multi variant example project.
"""

import functools
import importlib
import re
from pathlib import Path

from django.conf import settings
from django.test import Client, override_settings
from django.urls import reverse

from ..helpers.extra_modules import extra_modules_for
from ..jsonl import MetricSample, now_iso
from ..registry import Metric
from ..scenarios import (
    ATTRIBUTE_COUNT_SCENARIO_LABELS,
    SCENARIOS,
    BenchContext,
    get_context,
)
from .base import CollectorContext, run_collector

NAV_CONCERN_PATTERN = re.compile(
    "|".join(
        [
            r"Swap\(",
            r"Swap\.",
            r"render_nav\(",
            r"render_shell\(",
            r"make_shell_renderer\(",
            r"make_shell_view_mixin\(",
            r"targeting\(",
            r"not_targeting\(",
            r"htmx_target_is\(",
            r"partial=",
        ]
    )
)

HX_ATTR_PATTERN = re.compile(r"^(hx-|data-hx-)")


def collect(
    variants: list,
    run_id: str,
    *,
    repeats: int = 10,  # unused — static analysis has no repeat sampling
    timeout_ms: int = 8000,  # unused
    debug: bool = False,
    stdout=print,
    stderr=print,
) -> list[MetricSample]:
    client = Client()
    bench_ctx = get_context()

    def collect_one(variant, cctx: CollectorContext) -> list[MetricSample]:
        extras = extra_modules_for(variant.family)
        with override_settings(HTMX_NAV_DEBUG_SWAPS=False):
            return collect_variant_static_metrics(
                variant, run_id, client, bench_ctx, extra_module_paths=extras
            )

    ctx = CollectorContext(
        run_id=run_id,
        repeats=repeats,
        timeout_ms=timeout_ms,
        debug=debug,
        stdout=stdout,
        stderr=stderr,
    )
    return run_collector("static", variants, collect_one, ctx)


def collect_variant_static_metrics(
    variant,
    run_id: str,
    client: Client,
    ctx: BenchContext,
    extra_module_paths: list[str] | None = None,
) -> list[MetricSample]:
    common = dict(
        run_id=run_id,
        collected_at=now_iso(),
        variant=variant.namespace,
        family=variant.family,
        group=variant.group,
        uses_hx_select=variant.uses_hx_select,
        uses_morph=variant.uses_morph,
    )

    views_path = _module_path(variant.views_module)
    views_loc = _count_loc(views_path)
    views_nav_loc = _count_nav_concern_loc(views_path)

    extra_paths = [_module_path(m) for m in (extra_module_paths or [])]
    extra_loc = sum(_count_loc(p) for p in extra_paths)
    extra_nav_loc = sum(_count_nav_concern_loc(p) for p in extra_paths)

    shell_paths = _shell_templates(variant)
    shell_loc = sum(_count_loc(p) for p in shell_paths)

    hx_attr_count = _count_rendered_hx_attributes(client, variant, ctx)

    return [
        MetricSample(**common, metric=Metric.VIEWS_LOC, value=views_loc),
        MetricSample(
            **common, metric=Metric.TOTAL_TEMPLATE_HX_ATTRIBUTES, value=hx_attr_count
        ),
        MetricSample(**common, metric=Metric.EXTRA_MODULES_LOC, value=extra_loc),
        MetricSample(**common, metric=Metric.EXTRA_SHELL_TEMPLATE_LOC, value=shell_loc),
        MetricSample(
            **common,
            metric=Metric.TOTAL_NAV_CONCERN_LOC,
            value=views_nav_loc + extra_nav_loc,
        ),
    ]


@functools.lru_cache(maxsize=None)
def _module_path(dotted_module: str) -> Path:
    module = importlib.import_module(dotted_module)
    return Path(module.__file__)


def _count_loc(path: Path) -> int:
    count = 0
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if path.suffix == ".py" and stripped.startswith("#"):
            continue
        count += 1
    return count


def _count_nav_concern_loc(path: Path) -> int:
    """Python-source-only classifier. Templates are no longer scanned
    this way — see total_template_hx_attributes for the template side."""
    return sum(
        1 for line in path.read_text().splitlines() if NAV_CONCERN_PATTERN.search(line)
    )


def _shell_templates(variant) -> list[Path]:
    template_dir = settings.BASE_DIR / variant.app_name / "templates" / variant.app_name
    if not template_dir.is_dir():
        return []
    return sorted(template_dir.glob("_*.html"))


def _count_rendered_hx_attributes(client: Client, variant, ctx: BenchContext) -> int:
    """Renders the variant's canonical page set and counts real
    hx-*/data-hx-* HTML attributes across all of them (main content +
    any OOB/hx-partial fragments — they're all in the same response
    body, so no separate fragment-splitting is needed here)."""
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise ImportError(
            "total_template_hx_attributes requires beautifulsoup4. "
            "Install it via the 'bench' extra."
        ) from exc

    total = 0
    for scenario in SCENARIOS:
        if scenario.label not in ATTRIBUTE_COUNT_SCENARIO_LABELS:
            continue
        url = reverse(
            f"{variant.namespace}:{scenario.url_name}", args=scenario.args(ctx)
        )
        response = client.get(url, **(scenario.headers or {}))
        soup = BeautifulSoup(response.content, "html.parser")
        for tag in soup.find_all(True):
            total += sum(1 for attr in tag.attrs if HX_ATTR_PATTERN.match(attr))

    return total
