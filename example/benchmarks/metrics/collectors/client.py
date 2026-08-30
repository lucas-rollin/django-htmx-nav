"""
Client-side timing via Playwright across every variant: interaction-to-paint
time, htmx client-side processing time, and DOM churn.

No variant is ever skipped for htmx failing to load, including `mpa`
(the baseline everything else is compared against): if htmx.js doesn't
load (typically: no network access to the CDN), this falls back to
measuring via a real full-page navigation (Paint Timing API) instead of
htmx events. The fallback produces interaction_to_paint_ms only,
htmx-specific metrics are omitted, not estimated, since they have no
meaning without htmx events firing.

Run `python manage.py vendor_client_assets` and set HTMX_NAV_BENCHMARK=1
to avoid the fallback path entirely by using local copies of htmx/idiomorph
instead of the CDN.
"""

import statistics
from dataclasses import dataclass

from ..helpers.server_process import DevServer
from ..jsonl import MetricSample, now_iso
from ..registry import Metric
from ..scenarios import get_context
from .base import CollectorContext, run_collector

PORT = 8766


@dataclass(frozen=True)
class ClickScenario:
    label: str
    setup_selector: str | None  # clicked first, unmeasured, to reach the right UI state
    measured_selector: str  # the click that's actually instrumented


CLICK_SCENARIOS = [
    ClickScenario("tab_swap", None, 'a[role="tab"]:has-text("Team")'),
    ClickScenario(
        "subtab_swap",
        'a[role="tab"]:has-text("Settings")',
        '#subtabs a:has-text("Permissions")',
    ),
]

HTMX_ONLY_METRICS = (
    Metric.HTMX_PROCESSING_MS,
    Metric.DOM_MUTATIONS,
    Metric.DOM_NODES_ADDED,
    Metric.DOM_NODES_REMOVED,
)

# Arms instrumentation for exactly one measured interaction: tracks
# htmx:beforeRequest -> htmx:beforeSwap -> htmx:afterSettle timestamps,
# plus a MutationObserver counting records and element-node adds/
# removes, settling on __bench.done after a post-settle double-rAF
# boundary (approximating "visually painted").
ARM_HTMX_JS = """
() => {
  window.__bench = {
    beforeRequest: null, beforeSwap: null, afterSettle: null, paint: null,
    mutationRecords: 0, nodesAdded: 0, nodesRemoved: 0, done: false,
  };

  const countElementNodes = (nodeList) => {
    let n = 0;
    for (const node of nodeList) if (node.nodeType === Node.ELEMENT_NODE) n++;
    return n;
  };

  const observer = new MutationObserver((records) => {
    for (const record of records) {
      window.__bench.mutationRecords += 1;
      window.__bench.nodesAdded += countElementNodes(record.addedNodes);
      window.__bench.nodesRemoved += countElementNodes(record.removedNodes);
    }
  });
  observer.observe(document.body, { childList: true, subtree: true, attributes: true });

  const onBeforeRequest = () => { window.__bench.beforeRequest = performance.now(); };
  const onBeforeSwap = () => { window.__bench.beforeSwap = performance.now(); };
  const onAfterSettle = () => {
    window.__bench.afterSettle = performance.now();
    requestAnimationFrame(() => requestAnimationFrame(() => {
      window.__bench.paint = performance.now();
      window.__bench.done = true;
      observer.disconnect();
      document.body.removeEventListener('htmx:beforeRequest', onBeforeRequest);
      document.body.removeEventListener('htmx:beforeSwap', onBeforeSwap);
      document.body.removeEventListener('htmx:afterSettle', onAfterSettle);
    }));
  };

  document.body.addEventListener('htmx:beforeRequest', onBeforeRequest);
  document.body.addEventListener('htmx:beforeSwap', onBeforeSwap);
  document.body.addEventListener('htmx:afterSettle', onAfterSettle);
}
"""


def collect(
    variants: list,
    run_id: str,
    *,
    repeats: int = 10,
    timeout_ms: int = 8000,
    debug: bool = False,
    stdout=print,
    stderr=print,
) -> list[MetricSample]:
    try:
        from playwright.sync_api import TimeoutError as PWTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError:
        stderr(
            "playwright not installed. Run: pip install -e '.[bench-browser]' && playwright install chromium"
        )
        return []

    bench_ctx = get_context()

    with DevServer(PORT) as server, sync_playwright() as p:
        browser = p.chromium.launch()

        def collect_one(variant, cctx: CollectorContext) -> list[MetricSample]:
            landing = (
                f"{server.base_url}/{variant.url_prefix}"
                f"orgs/{bench_ctx.org.id}/projects/{bench_ctx.project.id}/"
            )
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(cctx.timeout_ms)

            try:
                htmx_ok = _check_htmx_loaded(page, landing, variant, cctx)
                rows = []
                for scenario in CLICK_SCENARIOS:
                    if htmx_ok:
                        rows.extend(
                            _run_scenario_htmx(
                                page,
                                PWTimeoutError,
                                landing,
                                variant,
                                scenario,
                                cctx,
                                run_id,
                            )
                        )
                    else:
                        rows.extend(
                            _run_scenario_fallback(
                                page,
                                PWTimeoutError,
                                landing,
                                variant,
                                scenario,
                                cctx,
                                run_id,
                            )
                        )
                return rows
            finally:
                context.close()

        ctx = CollectorContext(
            run_id=run_id,
            repeats=repeats,
            timeout_ms=timeout_ms,
            debug=debug,
            stdout=stdout,
            stderr=stderr,
        )
        rows = run_collector("client", variants, collect_one, ctx)
        browser.close()
        return rows


def _check_htmx_loaded(page, landing, variant, cctx: CollectorContext) -> bool:
    page.goto(landing, wait_until="networkidle")
    loaded = page.evaluate("() => typeof window.htmx !== 'undefined'")
    if not loaded:
        cctx.stderr(
            f"  [{variant.namespace}] htmx.js did not load at {landing} — likely no network "
            "access to the CDN (cdn.jsdelivr.net / unpkg.com). Falling back to full-page-"
            "navigation timing for this variant (interaction_to_paint_ms only; htmx-specific "
            "metrics omitted). Run `python manage.py vendor_client_assets` and set "
            "HTMX_NAV_BENCHMARK=1 to avoid this."
        )
    return loaded


def _run_scenario_htmx(page, PWTimeoutError, landing, variant, scenario, cctx, run_id):
    common = _common(variant, scenario, run_id)
    all_metrics = (Metric.INTERACTION_TO_PAINT_MS, *HTMX_ONLY_METRICS)
    samples = {m: [] for m in all_metrics}
    failures = 0

    for _ in range(cctx.repeats):
        try:
            page.goto(landing, wait_until="networkidle")
            if scenario.setup_selector:
                page.click(scenario.setup_selector)
                page.wait_for_selector(scenario.measured_selector, state="visible")

            page.evaluate(ARM_HTMX_JS)
            page.click(scenario.measured_selector)
            page.wait_for_function(
                "window.__bench && window.__bench.done", timeout=cctx.timeout_ms
            )

            result = page.evaluate("window.__bench")
            samples[Metric.INTERACTION_TO_PAINT_MS].append(
                result["paint"] - result["beforeRequest"]
            )
            samples[Metric.HTMX_PROCESSING_MS].append(
                result["afterSettle"] - result["beforeSwap"]
            )
            samples[Metric.DOM_MUTATIONS].append(result["mutationRecords"])
            samples[Metric.DOM_NODES_ADDED].append(result["nodesAdded"])
            samples[Metric.DOM_NODES_REMOVED].append(result["nodesRemoved"])
        except PWTimeoutError:
            failures += 1

    if failures:
        cctx.stderr(
            f"  [{variant.namespace}/{scenario.label}] {failures}/{cctx.repeats} repeats timed out."
        )
    if not samples[Metric.INTERACTION_TO_PAINT_MS]:
        cctx.stderr(
            f"  [{variant.namespace}/{scenario.label}] all {cctx.repeats} repeats failed — no data emitted."
        )
        return []

    return [
        _sample(common, metric, round(statistics.median(values), 2))
        for metric, values in samples.items()
        if values
    ]


def _run_scenario_fallback(
    page, PWTimeoutError, landing, variant, scenario, cctx, run_id
):
    common = _common(variant, scenario, run_id)
    timings = []
    failures = 0

    for _ in range(cctx.repeats):
        try:
            page.goto(landing, wait_until="load")
            if scenario.setup_selector:
                with page.expect_navigation(wait_until="load", timeout=cctx.timeout_ms):
                    page.click(scenario.setup_selector)
                page.wait_for_selector(scenario.measured_selector, state="visible")

            with page.expect_navigation(wait_until="load", timeout=cctx.timeout_ms):
                page.click(scenario.measured_selector)

            paint_entries = page.evaluate(
                "() => performance.getEntriesByType('paint').map(e => e.startTime)"
            )
            if paint_entries:
                timings.append(min(paint_entries))
            else:
                timing = page.evaluate("() => performance.timing")
                timings.append(timing["loadEventEnd"] - timing["navigationStart"])
        except PWTimeoutError:
            failures += 1

    if failures:
        cctx.stderr(
            f"  [{variant.namespace}/{scenario.label}] (fallback) {failures}/{cctx.repeats} navigations timed out."
        )
    if not timings:
        cctx.stderr(
            f"  [{variant.namespace}/{scenario.label}] (fallback) all {cctx.repeats} repeats failed — no data emitted."
        )
        return []

    return [
        _sample(
            common, Metric.INTERACTION_TO_PAINT_MS, round(statistics.median(timings), 2)
        )
    ]


def _sample(common: dict, metric: Metric, value: float) -> MetricSample:
    return MetricSample(**common, metric=metric, value=value)


def _common(variant, scenario, run_id) -> dict:
    return dict(
        run_id=run_id,
        collected_at=now_iso(),
        variant=variant.namespace,
        family=variant.family,
        group=variant.group,
        uses_hx_select=variant.uses_hx_select,
        uses_morph=variant.uses_morph,
        scenario=scenario.label,
    )
