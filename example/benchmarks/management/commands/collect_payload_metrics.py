from core.navigation.registry import VARIANTS
from django.core.management.base import BaseCommand

from example.benchmarks.metrics.collectors import payload
from example.benchmarks.metrics.helpers.variant_filter import resolve_variants
from example.benchmarks.metrics.jsonl import DATA_DIR, new_run_id, write_jsonl


class Command(BaseCommand):
    help = "Collect real on-wire (gzip'd) payload size metrics against a spawned dev server."

    def add_arguments(self, parser):
        parser.add_argument("--variants", nargs="*", default=None)
        parser.add_argument("--families", nargs="*", default=None)
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Print full tracebacks for per-variant failures instead of a one-line summary.",
        )

    def handle(self, *args, **options):
        run_id = new_run_id()
        variants = resolve_variants(VARIANTS, options["variants"], options["families"])

        rows = payload.collect(
            variants,
            run_id,
            debug=options["debug"],
            stdout=self.stdout.write,
            stderr=lambda m: self.stderr.write(self.style.WARNING(m)),
        )

        out = DATA_DIR / f"payload_{run_id}.jsonl"
        write_jsonl(out, rows)
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {len(rows)} rows for {len(variants)} variants to {out}"
            )
        )
