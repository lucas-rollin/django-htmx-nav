from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import set_script_prefix

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

        set_script_prefix(prefix)

        client = Client()
        for path, rel in PAGES:
            resp = client.get(path)
            assert resp.status_code == 200, f"{path} -> {resp.status_code}"
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(resp.content.decode("utf-8"))
