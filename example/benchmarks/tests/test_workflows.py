import io

import pytest
from core.navigation.registry import VARIANTS
from django.core.management import call_command
from django.urls import reverse

from benchmarks.metrics.collectors import server, static
from benchmarks.metrics.helpers.pivot import pivot_rows
from benchmarks.metrics.helpers.variant_filter import resolve_variants
from benchmarks.metrics.jsonl import (
    MetricSample,
    latest_or_reference_jsonl,
    new_run_id,
    now_iso,
    read_jsonl,
    reference_jsonl,
    write_jsonl,
)
from benchmarks.metrics.overview_metrics import build_panels
from benchmarks.metrics.registry import Metric, describe
from benchmarks.metrics.scenarios import SCENARIOS, get_context


def test_reference_jsonl_exists_and_readable():
    """Verify that committed reference datasets for all 4 categories exist and parse."""
    for category in ["static", "server", "payload", "client"]:
        path = reference_jsonl(category)
        assert path.is_file(), f"Reference jsonl missing for {category}"

        rows = read_jsonl(path)
        assert len(rows) > 0, f"Reference jsonl for {category} is empty"

        sample = rows[0]
        assert "run_id" in sample
        assert "variant" in sample
        assert "metric" in sample
        assert "value" in sample
        assert "collected_at" in sample


def test_jsonl_write_and_read_roundtrip(tmp_path):
    """Verify round-trip serialization and deserialization of MetricSample objects."""
    run_id = new_run_id()
    now = now_iso()
    sample_rows = [
        MetricSample(
            run_id=run_id,
            collected_at=now,
            variant="mpa",
            family="mpa",
            group="mpa",
            uses_hx_select=False,
            uses_morph=False,
            metric="views_loc",
            value=120,
        ),
        MetricSample(
            run_id=run_id,
            collected_at=now,
            variant="htmx_nav_baseline",
            family="htmx_nav_baseline",
            group="htmx_nav",
            uses_hx_select=False,
            uses_morph=False,
            metric="views_loc",
            value=85,
        ),
    ]

    out_file = tmp_path / "test_samples.jsonl"
    write_jsonl(out_file, sample_rows)
    assert out_file.is_file()

    read_back = read_jsonl(out_file)
    assert len(read_back) == 2
    assert read_back[0]["variant"] == "mpa"
    assert read_back[0]["metric"] == "views_loc"
    assert read_back[0]["value"] == 120
    assert read_back[1]["variant"] == "htmx_nav_baseline"
    assert read_back[1]["value"] == 85


def test_latest_or_reference_jsonl_discovery(tmp_path, monkeypatch):
    """Test resolution between latest local runs and pinned reference fallbacks."""
    # Point DATA_DIR to tmp_path
    monkeypatch.setattr("benchmarks.metrics.jsonl.DATA_DIR", tmp_path)

    # 1. No files at all -> None
    assert latest_or_reference_jsonl("custom_cat") is None

    # 2. Only reference file exists
    ref_file = tmp_path / "reference_custom_cat.jsonl"
    ref_file.write_text('{"metric": "test", "value": 1}\n')
    assert latest_or_reference_jsonl("custom_cat") == ref_file

    # 3. Newer timestamped file exists -> picked over reference
    new_run = tmp_path / "custom_cat_20260913_120000.jsonl"
    new_run.write_text('{"metric": "test", "value": 2}\n')
    assert latest_or_reference_jsonl("custom_cat") == new_run


def test_pivot_rows_aggregations():
    """Verify pivoting logic computes correct tables and charts from sample rows."""
    static_ref = reference_jsonl("static")
    rows = read_jsonl(static_ref)

    pivoted = pivot_rows(rows)
    assert "metrics" in pivoted
    assert "charts" in pivoted
    assert "table" in pivoted

    metrics = pivoted["metrics"]
    assert "views_loc" in metrics
    assert "total_nav_concern_loc" in metrics

    table = pivoted["table"]
    columns = table["columns"]
    assert "variant_label" in columns
    assert "views_loc" in columns

    table_rows = table["rows"]
    assert len(table_rows) > 0
    first_row = table_rows[0]
    assert "variant" in first_row
    assert "family" in first_row

    charts = pivoted["charts"]
    assert "views_loc" in charts
    assert "labels" in charts["views_loc"]
    assert "values" in charts["views_loc"]


def test_build_panels_from_reference_snapshots():
    """Verify overview panels build accurately from committed snapshots."""
    panels = build_panels()
    assert len(panels) == 5

    panel_keys = {p.key for p in panels}
    expected_keys = {
        "views_loc",
        "server_latency",
        "transfer_bytes",
        "queries_vs_swaps",
        "htmx_processing_ms",
    }
    assert panel_keys == expected_keys

    for panel in panels:
        assert len(panel.title) > 0
        assert len(panel.caption) > 0
        assert isinstance(panel.chart, dict)
        assert "type" in panel.chart
        assert "labels" in panel.chart
        assert len(panel.chart["labels"]) > 0


@pytest.mark.django_db
def test_metric_registry_and_scenarios():
    """Verify metric registry descriptions and scenario resolution against seed DB."""
    for metric_name in [
        Metric.VIEWS_LOC,
        Metric.TOTAL_TEMPLATE_HX_ATTRIBUTES,
        Metric.RENDER_TIME_MS_MEDIAN,
        Metric.DB_QUERY_COUNT,
        Metric.TRANSFER_BYTES,
        Metric.HTMX_PROCESSING_MS,
    ]:
        info = describe(metric_name)
        assert info.label
        assert info.unit is not None
        assert info.description
        assert isinstance(info.lower_is_better, bool)

    bench_ctx = get_context()
    assert bench_ctx.org is not None
    assert bench_ctx.project is not None
    assert bench_ctx.ticket is not None

    for scenario in SCENARIOS:
        args = scenario.args(bench_ctx)
        assert isinstance(args, list)
        # Test reverse on MPA variant
        url = reverse(f"mpa:{scenario.url_name}", args=args)
        assert url.startswith("/")


def test_resolve_variants_filtering():
    """Test resolving and filtering variant lists."""
    all_vars = resolve_variants(VARIANTS, None, None)
    assert len(all_vars) == len(VARIANTS)

    subset = resolve_variants(VARIANTS, ["mpa", "htmx_nav_baseline"], None)
    assert len(subset) == 2
    assert {v.namespace for v in subset} == {"mpa", "htmx_nav_baseline"}

    mpa_fam = resolve_variants(VARIANTS, None, ["mpa"])
    assert len(mpa_fam) >= 1
    for v in mpa_fam:
        assert v.family == "mpa"


@pytest.mark.django_db
def test_static_collector_workflow():
    """Run static collector in-process on representative variants."""
    target_variants = [VARIANTS["mpa"], VARIANTS["htmx_nav_baseline"]]
    run_id = new_run_id()

    rows = static.collect(
        target_variants,
        run_id=run_id,
        debug=True,
        stdout=lambda m: None,
        stderr=lambda m: None,
    )

    assert len(rows) > 0
    collected_metrics = {r.metric for r in rows}
    assert Metric.VIEWS_LOC in collected_metrics
    assert Metric.TOTAL_TEMPLATE_HX_ATTRIBUTES in collected_metrics
    assert Metric.TOTAL_NAV_CONCERN_LOC in collected_metrics

    for row in rows:
        assert row.run_id == run_id
        assert row.variant in ("mpa", "htmx_nav_baseline")
        assert isinstance(row.value, int)
        assert row.value >= 0


@pytest.mark.django_db
def test_server_collector_workflow():
    """Run server performance collector in-process with repeats=1."""
    target_variants = [VARIANTS["mpa"]]
    run_id = new_run_id()

    rows = server.collect(
        target_variants,
        run_id=run_id,
        repeats=1,
        debug=True,
        stdout=lambda m: None,
        stderr=lambda m: None,
    )

    assert len(rows) > 0
    collected_metrics = {r.metric for r in rows}
    assert Metric.RENDER_TIME_MS_MEDIAN in collected_metrics
    assert Metric.DB_QUERY_COUNT in collected_metrics
    assert Metric.SWAP_RENDER_COUNT in collected_metrics

    for row in rows:
        assert row.variant == "mpa"
        assert row.value >= 0


@pytest.mark.django_db
def test_collect_static_metrics_command(tmp_path, monkeypatch):
    """Test running the collect_static_metrics management command."""
    monkeypatch.setattr(
        "benchmarks.management.commands.collect_static_metrics.DATA_DIR", tmp_path
    )

    out = io.StringIO()
    err = io.StringIO()
    call_command(
        "collect_static_metrics",
        "--variants",
        "mpa",
        "--debug",
        stdout=out,
        stderr=err,
    )

    output = out.getvalue()
    assert "Wrote" in output
    assert "static_" in output

    written_files = list(tmp_path.glob("static_*.jsonl"))
    assert len(written_files) == 1

    rows = read_jsonl(written_files[0])
    assert len(rows) > 0
    assert rows[0]["variant"] == "mpa"


def test_settings_split_dev_prod_vs_benchmark(monkeypatch):
    """Verify settings split: dev & prod default to DEBUG_SWAPS=True and LOCAL_ASSETS=False;
    benchmark test mode sets DEBUG_SWAPS=False and LOCAL_ASSETS=True."""
    import importlib

    import config.settings as app_settings

    # 1. Dev / Production default (no environment variables set)
    monkeypatch.delenv("HTMX_NAV_DEBUG_SWAPS", raising=False)
    monkeypatch.delenv("HTMX_NAV_BENCHMARK_LOCAL_ASSETS", raising=False)
    importlib.reload(app_settings)
    assert app_settings.HTMX_NAV_DEBUG_SWAPS is True
    assert app_settings.HTMX_NAV_BENCHMARK_LOCAL_ASSETS is False

    # 2. Benchmark test mode (configured in docker-compose bench and DevServer)
    monkeypatch.setenv("HTMX_NAV_DEBUG_SWAPS", "False")
    monkeypatch.setenv("HTMX_NAV_BENCHMARK_LOCAL_ASSETS", "True")
    importlib.reload(app_settings)
    assert app_settings.HTMX_NAV_DEBUG_SWAPS is False
    assert app_settings.HTMX_NAV_BENCHMARK_LOCAL_ASSETS is True

    # Cleanup reload to default
    monkeypatch.delenv("HTMX_NAV_DEBUG_SWAPS", raising=False)
    monkeypatch.delenv("HTMX_NAV_BENCHMARK_LOCAL_ASSETS", raising=False)
    importlib.reload(app_settings)


def test_update_reference_summary_command(tmp_path):
    """Test generating summary.json via update_reference_summary command."""
    out_file = tmp_path / "summary.json"
    out = io.StringIO()
    call_command("update_reference_summary", "--output", str(out_file), stdout=out)

    assert out_file.exists()
    content = out.getvalue()
    assert "Successfully generated benchmark summary" in content
    assert "Declarative LOC" in content
    assert "Payload reduction" in content


def test_benchmark_summary_properties():
    """Verify BenchmarkSummary properties and fallback loading."""
    from benchmarks.metrics.summary import load_benchmark_summary

    load_benchmark_summary.cache_clear()
    summary = load_benchmark_summary()
    assert summary.declarative_loc > 0
    assert summary.mpa_loc > summary.declarative_loc
    assert summary.loc_reduction_pct > 0
    assert summary.payload_reduction_pct > 0
    assert "KB" in summary.payload_value
    assert len(summary.headline_metrics) == 4


def test_benchmark_summary_missing_summary_file_uses_reference(tmp_path):
    """If summary.json is absent, load_benchmark_summary computes from reference datasets."""
    from benchmarks.metrics.summary import load_benchmark_summary

    load_benchmark_summary.cache_clear()
    non_existent = tmp_path / "missing_summary.json"
    summary = load_benchmark_summary(non_existent)
    assert summary.declarative_loc > 0
    assert summary.payload_reduction_pct > 0


def test_benchmark_summary_missing_all_files_raises(tmp_path, monkeypatch):
    """If neither summary.json nor reference datasets exist, raise FileNotFoundError."""
    from benchmarks.metrics import jsonl, summary

    summary.load_benchmark_summary.cache_clear()
    monkeypatch.setattr(jsonl, "DATA_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="neither .* nor reference JSONL"):
        summary.load_benchmark_summary(tmp_path / "summary.json")


def test_benchmark_templatetag():
    """Test benchmark_tags templatetag in a Django template."""
    from django.template import Context, Template

    t = Template(
        "{% load benchmark_tags %}"
        "{% get_benchmark_summary as bench %}"
        "{{ bench.payload_reduction_pct }}|{{ bench.declarative_loc }}"
    )
    rendered = t.render(Context())
    parts = rendered.split("|")
    assert len(parts) == 2
    assert int(parts[0]) > 0
    assert int(parts[1]) > 0
