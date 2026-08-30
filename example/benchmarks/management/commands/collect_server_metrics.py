from core.navigation.registry import VARIANTS
from django.core.management.base import BaseCommand

from example.benchmarks.metrics.collectors import server
from example.benchmarks.metrics.helpers.variant_filter import resolve_variants
from example.benchmarks.metrics.jsonl import DATA_DIR, new_run_id, write_jsonl


class Command(BaseCommand):
    help = "Collect server render time / DB query count / swap-render count via the Django test client."

    def add_arguments(self, parser):
        parser.add_argument("--variants", nargs="*", default=None)
        parser.add_argument("--families", nargs="*", default=None)
        parser.add_argument("--repeats", type=int, default=20)
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Print full tracebacks for per-variant failures instead of a one-line summary.",
        )

    def handle(self, *args, **options):
        run_id = new_run_id()
        variants = resolve_variants(VARIANTS, options["variants"], options["families"])

        rows = server.collect(
            variants,
            run_id,
            repeats=options["repeats"],
            debug=options["debug"],
            stdout=self.stdout.write,
            stderr=lambda m: self.stderr.write(self.style.WARNING(m)),
        )

        out = DATA_DIR / f"server_{run_id}.jsonl"
        write_jsonl(out, rows)
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {len(rows)} rows for {len(variants)} variants to {out}"
            )
        )
