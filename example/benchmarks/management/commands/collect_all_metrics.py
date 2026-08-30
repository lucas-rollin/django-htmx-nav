"""
Runs every collect_*_metrics category in sequence and writes one
combined JSONL per category — identical output to running each command
individually, using the same variant filtering, the same per-variant
progress printing, and the same failure isolation (courtesy of every
category sharing the collect(variants, run_id, ...) -> list[MetricSample]
contract in benchmarks/metrics/base.py).

Use --debug to print full tracebacks for any per-variant failure
instead of a one-line summary. Use --skip to omit slow categories
(typically `client`) during iteration.
"""

from core.navigation.registry import VARIANTS
from django.core.management.base import BaseCommand

from example.benchmarks.metrics.collectors import (
    client,
    payload,
    server,
    static,
)
from example.benchmarks.metrics.helpers.variant_filter import resolve_variants
from example.benchmarks.metrics.jsonl import DATA_DIR, new_run_id, write_jsonl

# Registering a new category here is the only wiring collect_all_metrics
# needs — see README.md "Collector contract" for what a category module
# must expose to be added.
COLLECTORS = [
    ("static", static.collect),
    ("server", server.collect),
    ("payload", payload.collect),
    ("client", client.collect),
]
COLLECTOR_NAMES = [name for name, _ in COLLECTORS]


class Command(BaseCommand):
    help = "Run every collect_*_metrics collector in sequence and write one combined JSONL per category."

    def add_arguments(self, parser):
        parser.add_argument("--variants", nargs="*", default=None)
        parser.add_argument("--families", nargs="*", default=None)
        parser.add_argument("--repeats", type=int, default=10)
        parser.add_argument("--timeout-ms", type=int, default=8000)
        parser.add_argument(
            "--skip",
            nargs="*",
            default=None,
            choices=COLLECTOR_NAMES,
            help=f"Category names to skip, e.g. --skip client. Choices: {COLLECTOR_NAMES}",
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Print full tracebacks for per-variant failures instead of a one-line summary.",
        )

    def handle(self, *args, **options):
        run_id = new_run_id()
        variants = resolve_variants(VARIANTS, options["variants"], options["families"])
        skip = set(options["skip"] or [])
        active = [(name, fn) for name, fn in COLLECTORS if name not in skip]

        self.stdout.write(
            f"Run {run_id}: {len(variants)} variants, categories: {[name for name, _ in active]}"
        )

        for name, collect_fn in COLLECTORS:
            if name in skip:
                self.stdout.write(f"--- skipping {name} ---")
                continue

            self.stdout.write(f"--- {name} ---")
            rows = collect_fn(
                variants,
                run_id,
                repeats=options["repeats"],
                timeout_ms=options["timeout_ms"],
                debug=options["debug"],
                stdout=self.stdout.write,
                stderr=lambda m: self.stderr.write(self.style.WARNING(m)),
            )
            out = DATA_DIR / f"{name}_{run_id}.jsonl"
            write_jsonl(out, rows)
            self.stdout.write(self.style.SUCCESS(f"Wrote {len(rows)} rows to {out}"))

        self.stdout.write(
            self.style.SUCCESS(f"collect_all_metrics done. run_id={run_id}")
        )
