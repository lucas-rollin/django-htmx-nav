from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from benchmarks.metrics.jsonl import read_jsonl, reference_jsonl
from benchmarks.metrics.summary import (
    SUMMARY_PATH,
    compute_summary,
    save_benchmark_summary,
)


class Command(BaseCommand):
    help = (
        "Recomputes summary.json from the pinned reference JSONL datasets "
        "(reference_static.jsonl, reference_server.jsonl, reference_payload.jsonl, "
        "reference_client.jsonl). Run this whenever reference benchmarks are updated."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Optional custom output path for the summary JSON file.",
        )

    def handle(self, *args, **options):
        required_categories = ["static", "server", "payload", "client"]
        datasets = {}

        for cat in required_categories:
            path = reference_jsonl(cat)
            if not path or not path.exists():
                raise CommandError(
                    f"Reference dataset missing for '{cat}': expected reference_{cat}.jsonl in benchmarks data directory."
                )
            datasets[cat] = read_jsonl(path)
            self.stdout.write(f"Loaded {len(datasets[cat])} rows from {path.name}")

        summary = compute_summary(
            datasets["static"],
            datasets["server"],
            datasets["payload"],
            datasets["client"],
        )

        out_path = Path(options["output"]) if options["output"] else SUMMARY_PATH
        saved = save_benchmark_summary(summary, out_path)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully generated benchmark summary: {saved}\n"
                f"  - Declarative LOC: {summary.declarative_loc} (↓ {summary.loc_reduction_pct}% vs MPA {summary.mpa_loc})\n"
                f"  - Unaware hx-attrs: {summary.unaware_base_hx_attrs} -> {summary.unaware_hx_attrs} with hx-select\n"
                f"  - Median render time: {summary.render_latency_median_ms} ms (P95 Unaware: {summary.p95_unaware_ms} ms)\n"
                f"  - Average DB queries: {summary.avg_db_queries}\n"
                f"  - Payload reduction: ↓ {summary.payload_reduction_pct}% (HTMX-Nav: {summary.payload_value} vs MPA: {summary.mpa_payload_value})\n"
                f"  - Client DOM reduction with hx-select: {summary.dom_red_min}% - {summary.dom_red_max}%\n"
            )
        )
