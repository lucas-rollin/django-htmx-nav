from core.navigation.registry import VARIANTS
from django.core.management.base import BaseCommand

from benchmarks.metrics.collectors import client
from benchmarks.metrics.helpers.variant_filter import resolve_variants
from benchmarks.metrics.jsonl import DATA_DIR, new_run_id, write_jsonl


class Command(BaseCommand):
    help = "Collect interaction-to-paint / htmx-processing / DOM-churn metrics via Playwright, for every variant."

    def add_arguments(self, parser):
        parser.add_argument("--variants", nargs="*", default=None)
        parser.add_argument("--families", nargs="*", default=None)
        parser.add_argument("--repeats", type=int, default=10)
        parser.add_argument("--timeout-ms", type=int, default=8000)
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Print full tracebacks for per-variant failures instead of a one-line summary.",
        )

    def handle(self, *args, **options):
        run_id = new_run_id()
        variants = resolve_variants(VARIANTS, options["variants"], options["families"])

        rows = client.collect(
            variants,
            run_id,
            repeats=options["repeats"],
            timeout_ms=options["timeout_ms"],
            debug=options["debug"],
            stdout=self.stdout.write,
            stderr=lambda m: self.stderr.write(self.style.WARNING(m)),
        )

        out = DATA_DIR / f"client_{run_id}.jsonl"
        write_jsonl(out, rows)
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {len(rows)} rows for {len(variants)} variants to {out}"
            )
        )
