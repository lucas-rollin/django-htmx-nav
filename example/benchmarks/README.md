# Benchmarks

Collects code-complexity, server-performance, payload-size, and
client-performance metrics across every `django-htmx-nav` example variant,
and displays them at `/benchmarks/`.

## Setup

```bash
pip install -e ".[example,bench]" # radon, playwright, beautifulsoup + core deps
```

## Run the test suite before collecting data

The run the example tests in `core/tests/` via pytest before collecting data.
These assert general parity between variants for a fair comparison.

## Collection

Run everything in one go:

```bash
python manage.py collect_all_metrics
```

Or run categories individually (identical underlying collectors,
identical output files):

```bash
python manage.py collect_static_metrics
python manage.py collect_server_metrics
python manage.py collect_payload_metrics
python manage.py collect_client_metrics
```

All commands accept:

- `--variants NS [NS ...]` / `--families KEY [KEY ...]` — scope to a subset
- `--debug` — print full tracebacks for any per-variant failure instead
  of a one-line summary. Failures are always isolated per-variant.

`collect_all_metrics` additionally accepts:

- `--skip static server payload client` — skip one or more categories
  (e.g. `--skip client` while iterating, since it's the slowest)
- `--repeats N` / `--timeout-ms N` — forwarded to whichever collectors
  use them (server, client)

Each writes a timestamped `.jsonl` file to `data/`; the dashboard
always reads the *latest* file per category.

## View results

```bash
python manage.py runserver
open http://127.0.0.1:8000/benchmarks/
```

To add a metrics category or understand how collectors work, follow
these summarized guidelines:

## Adding a New Metrics Category

1. **Create Collector (`benchmarks/metrics/collectors/<name>.py`):**

    - Expose the function:

      ```python
      def collect(
          variants: list,
          run_id: str,
          *,
          repeats: int = 10,
          timeout_ms: int = 8000,
          debug: bool = False,
          stdout=print,
          stderr=print,
      ) -> list[MetricSample]: ...
      ```

    - Delegate per-variant loops to `benchmarks.metrics.collectors.base.run_collector(label, variants, collect_one, ctx)`
      for failure isolation and progress printing.

2. **Create Command (`benchmarks/management/commands/collect_<name>_metrics.py`):**

    - Keep it thin: parse CLI flags, call `resolve_variants()`, invoke `<name>.collect()`,
      and save results using `write_jsonl`. Put zero collection logic here.

3. **Register Collector & Metrics:**

    - Add the category to `COLLECTORS` in `collect_all_metrics.py`.
    - Add new metric keys to both `Metric` and `METRICS` in `benchmarks/metrics/registry.py`
      (specifying `label`, `description`, and `unit`).

---

## Metric Collection Rules & Behavior

- **Static Metrics (`collect_static_metrics`):**

  - Evaluates **all** variants. Code size metrics (`loc`) are identical acrossvariant
    axis combos, but HTML attribute counts (`total_template_hx_attributes`) vary per combo.
  - Map non-view logic files in `benchmarks/metrics/extra_modules.py` under `EXTRA_MODULES_BY_FAMILY`.

- **Client Metrics (`collect_client_metrics`):**

  - Evaluates **all** variants across two scenarios: `tab_swap` and `subtab_swap`.
  - **CDN Fallback:** If `htmx.js` fails to load, it falls back to full-page
    Paint Timing (`interaction_to_paint_ms`) and omits htmx-specific metrics.
    Run `python manage.py vendor_client_assets` to prevent fallback.
  - Flaky repeats trigger timeouts and are logged/skipped rather than failing the overall run.

---

## Known Limitations

- `ticket_move_status` (POST) is excluded from scenarios to keep database collection idempotent.
- `total_template_hx_attributes` only samples 3 scenarios (`ATTRIBUTE_COUNT_SCENARIO_LABELS`) to control run time.
- Client timing metrics depend on local hardware; focus on relative cross-variant differences rather than absolute values.
