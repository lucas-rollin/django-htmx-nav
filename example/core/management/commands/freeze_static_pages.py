from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import get_script_prefix, set_script_prefix

PAGES = [
    ("/", "index.html"),
    ("/guide/", "guide/index.html"),
    ("/benchmarks/", "benchmarks/index.html"),
    ("/benchmarks/static/", "benchmarks/static/index.html"),
    ("/benchmarks/server/", "benchmarks/server/index.html"),
    ("/benchmarks/payload/", "benchmarks/payload/index.html"),
    ("/benchmarks/client/", "benchmarks/client/index.html"),
    ("/robots.txt", "robots.txt"),
    ("/sitemap.xml", "sitemap.xml"),
]


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--out", required=True)
        parser.add_argument("--prefix", default=None, help="e.g. /django-htmx-nav/")

    def handle(self, *args, **opts):
        out = Path(opts["out"])
        prefix = opts["prefix"] or getattr(settings, "FORCE_SCRIPT_NAME", None) or "/"
        if not prefix.endswith("/"):
            prefix += "/"

        old_prefix = get_script_prefix()
        try:
            set_script_prefix(prefix)

            client = Client()
            demo_url = getattr(settings, "DEMO_URL", "").rstrip("/")
            demo_prefix = f"{prefix}demo/"

            for path, rel in PAGES:
                resp = client.get(path)
                assert resp.status_code == 200, f"{path} -> {resp.status_code}"
                dest = out / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                content = resp.content.decode("utf-8")

                if prefix != "/":
                    if demo_url:
                        content = content.replace(
                            f"{demo_url}{demo_prefix}", f"{demo_url}/demo/"
                        )
                        content = content.replace(
                            f'href="{demo_prefix}', f'href="{demo_url}/demo/'
                        )
                        content = content.replace(
                            f"href='{demo_prefix}", f"href='{demo_url}/demo/"
                        )
                    else:
                        content = content.replace(demo_prefix, "/demo/")

                dest.write_text(content)
        finally:
            set_script_prefix(old_prefix)
