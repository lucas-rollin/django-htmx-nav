from core.navigation.registry import VARIANTS
from django.core.management.base import BaseCommand

from example.benchmarks.metrics.collectors import static
from example.benchmarks.metrics.helpers.variant_filter import resolve_variants
from example.benchmarks.metrics.jsonl import DATA_DIR, new_run_id, write_jsonl


class Command(BaseCommand):
    help = (
        "Collect code-complexity/DX metrics (views_loc, extra_modules_loc, "
        "shell_template_loc, total_nav_concern_loc, total_template_hx_attributes) "
        "for every variant. All variants are needed (not just base axis combos) "
        "because total_template_hx_attributes depends on uses_hx_select/uses_morph."
    )

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

        rows = static.collect(
            variants,
            run_id,
            debug=options["debug"],
            stdout=self.stdout.write,
            stderr=lambda m: self.stderr.write(self.style.WARNING(m)),
        )

        out = DATA_DIR / f"static_{run_id}.jsonl"
        write_jsonl(out, rows)
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {len(rows)} rows for {len(variants)} variants to {out}"
            )
        )
