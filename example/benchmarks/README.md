# Benchmark Suite & Experiments

This directory contains the automated performance measurement harness for `django-htmx-nav`. It collects code-complexity, server-performance, payload-size, and client-performance metrics across all 8 Helpdesk implementation variants and presents them in interactive dashboards at `/benchmarks/`.

## 1. Running Benchmarks via Docker (Recommended)

Running the benchmark collector inside Docker is the recommended approach. The test container already includes Playwright, headless browser binaries, and vendored assets, preventing local host configuration issues and external network dependencies.

```bash
# Run all benchmark collectors in one command:
docker compose run --rm bench
```

- **Persistence**: Results are written as timestamped `.jsonl` files to `./example/benchmarks/data/`, which is volume-mounted to your host machine.
- **Environment**: Automatically runs with `HTMX_NAV_DEBUG_SWAPS=False` (to eliminate swap animation overhead) and `HTMX_NAV_BENCHMARK_LOCAL_ASSETS=True` (to eliminate external CDN network latency).

## 2. Running Benchmarks Locally (Native Python)

If you prefer running collectors directly on your host machine:

### A. Prerequisites

```bash
# 1. Install benchmark dependencies (radon, playwright, beautifulsoup4):
pip install -e ".[example,bench]"

# 2. Download offline HTMX assets so tests do not depend on CDN availability:
python example/manage.py vendor_client_assets

# 3. Install Playwright browser engines:
playwright install chromium
```

### B. Run Metric Collectors

Run the full benchmark suite:

```bash
python example/manage.py collect_all_metrics
```

Or run individual categories independently:

```bash
python example/manage.py collect_static_metrics   # Code complexity (LOC, hx-* attribute counts)
python example/manage.py collect_server_metrics   # Server render times, query counts, swap counts
python example/manage.py collect_payload_metrics  # Wire transfer bytes (gzipped on-the-wire)
python example/manage.py collect_client_metrics   # Interaction-to-paint timing & DOM mutations
```

### C. Useful Command Flags

- `--variants NS [NS ...]`: Scope collection to specific variant namespaces (e.g. `--variants mpa htmx_nav_baseline`).
- `--families KEY [KEY ...]`: Scope collection to specific implementation families (e.g. `--families mpa htmx_nav_composite`).
- `--debug`: Print full Python tracebacks for any per-variant failure.
- `--skip static server payload client`: (Available on `collect_all_metrics`) Skip specific categories (e.g. `--skip client` for quick iterations).
- `--repeats N`: Number of iterations to sample per scenario (used by server and client collectors).

## 3. Viewing the Results

Start the web server:

```bash
python example/manage.py runserver
# or with docker:
docker compose up dev
```

Open [http://127.0.0.1:8000/benchmarks/](http://127.0.0.1:8000/benchmarks/) in your browser.

- **Overview Page (`/benchmarks/`)**: Displays cross-category headline findings based on pinned reference datasets (`example/benchmarks/data/reference_*.jsonl`).
- **Category Dashboards (`/benchmarks/{static,server,payload,client}/`)**: Automatically detects and loads the freshest `.jsonl` run in `data/`, falling back to the reference snapshot if no local run has been recorded.

## 4. Extending the Benchmark Suite

To add a new metric category or custom collector:

1. **Create Collector (`benchmarks/metrics/collectors/<name>.py`):**
   - Expose `collect(variants, run_id, *, repeats=10, timeout_ms=8000, debug=False, stdout=print, stderr=print) -> list[MetricSample]`.
   - Delegate the per-variant loop to `benchmarks.metrics.collectors.base.run_collector(label, variants, collect_one, ctx)` for failure isolation and progress reporting.
2. **Create Command (`benchmarks/management/commands/collect_<name>_metrics.py`):**
   - Parse CLI arguments, call `resolve_variants()`, invoke your collector function, and save records using `write_jsonl(out, rows)`.
3. **Register Metrics in Registry (`benchmarks/metrics/registry.py`):**
   - Add new identifiers to `Metric(str, Enum)` and define presentation metadata (`label`, `description`, `unit`, `lower_is_better`) in `METRICS`.
   - Add the collector to `COLLECTORS` in `collect_all_metrics.py`.

## Related Resources

- **[Example Application Overview](../README.md)**: Architecture and local run instructions for the Helpdesk testbed.
- **[Live Benchmark Dashboard](https://django-htmx-nav.onrender.com/benchmarks/)**: Online interactive dashboard comparing reference results.
