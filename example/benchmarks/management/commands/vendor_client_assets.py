"""
Downloads htmx.js and idiomorph locally so collect_client_metrics
doesn't depend on cdn.jsdelivr.net/unpkg.com at collection time. An
unreachable CDN otherwise causes htmx to silently fail to load and
every click falls back to a real browser navigation, which the client
collector now handles gracefully, but avoiding it entirely gives
cleaner, htmx-instrumented data for every variant.
"""

import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand

# .../example/benchmarks/management/commands/vendor_client_assets.py
# parents[3] = .../example
VENDOR_DIR = (
    Path(__file__).resolve().parents[3] / "core" / "static" / "core" / "js" / "vendor"
)

ASSETS = {
    "htmx.min.js": "https://cdn.jsdelivr.net/npm/htmx.org@4.0.0/dist/htmx.min.js",
    # "idiomorph-ext.min.js": "https://unpkg.com/idiomorph@0.7.4/dist/idiomorph-ext.min.js",
}


class Command(BaseCommand):
    help = "Download htmx.js/idiomorph.js locally for offline-safe Playwright client-metric collection."

    def handle(self, *args, **options):
        VENDOR_DIR.mkdir(parents=True, exist_ok=True)
        for filename, url in ASSETS.items():
            dest = VENDOR_DIR / filename
            self.stdout.write(f"Downloading {url} -> {dest}")
            urllib.request.urlretrieve(url, dest)
        self.stdout.write(
            self.style.SUCCESS(
                f"Vendored {len(ASSETS)} assets to {VENDOR_DIR}. "
                "Set HTMX_NAV_BENCHMARK=1 when running the dev server/collectors "
                "to use these local copies instead of the CDN."
            )
        )
