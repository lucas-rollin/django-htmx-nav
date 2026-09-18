import shutil
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from benchmarks.metrics.jsonl import DATA_DIR, latest_jsonl, read_jsonl, reference_jsonl
from benchmarks.metrics.summary import (
    SUMMARY_PATH,
    compute_summary,
    save_benchmark_summary,
)

REQUIRED_CATEGORIES = ["static", "server", "payload", "client"]


class Command(BaseCommand):
    help = (
        "Recomputes summary.json from the pinned reference JSONL datasets. "
        "Run this whenever reference benchmarks are updated. Pass --promote-latest "
        "to first archive the current reference_*.jsonl files and promote the freshest "
        "collect_all_metrics run to be the new reference before recomputing."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Optional custom output path for the summary JSON file.",
        )
        parser.add_argument(
            "--promote-latest",
            action="store_true",
            help=(
                "Before recomputing: (1) rename each current "
                "reference_<category>.jsonl to old_reference_<category>_<timestamp>.jsonl "
                "so it's no longer git-tracked under the reference_* pattern, and (2) copy "
                "the most recent non-reference <category>_*.jsonl run (e.g. written by "
                "collect_all_metrics) over as the new reference_<category>.jsonl. Fails "
                "loudly if any category has no fresh run to promote."
            ),
        )

    def handle(self, *args, **options):
        if options["promote_latest"]:
            self._promote_latest()

        datasets = {}
        for cat in REQUIRED_CATEGORIES:
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

    def _promote_latest(self):
        """Rename latest metrics to reference*.jsonl and archives old ones."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        for cat in REQUIRED_CATEGORIES:
            latest = latest_jsonl(cat)
            if latest is None:
                raise CommandError(
                    f"--promote-latest requires a freshly collected {cat}_*.jsonl file in "
                    f"{DATA_DIR} — run collect_all_metrics (or collect_{cat}_metrics) first."
                )

            current_ref = reference_jsonl(cat)
            if current_ref is not None and current_ref.exists():
                archived_name = f"old_{current_ref.stem}_{timestamp}.jsonl"
                archived = DATA_DIR / archived_name
                current_ref.rename(archived)
                self.stdout.write(f"Archived {current_ref.name} -> {archived.name}")
            else:
                self.stdout.write(f"No existing reference for '{cat}' to archive.")

            new_ref = DATA_DIR / f"reference_{cat}.jsonl"
            shutil.copy2(latest, new_ref)
            self.stdout.write(f"Promoted {latest.name} -> {new_ref.name}")
