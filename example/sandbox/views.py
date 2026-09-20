from django.http import HttpRequest, HttpResponse
from faker import Faker

from htmx_nav import PathReplace, Swap, make_shell_renderer

fake = Faker("en_US")


def _breadcrumbs(*crumbs: tuple[str, str | None]):
    """crumbs: list of (label, url_or_None) tuples."""
    return {"breadcrumbs": [{"label": label, "url": url} for label, url in crumbs]}


render_sandbox = make_shell_renderer(
    [
        Swap("sandbox/components/_sidebar_menu.html", target_id="sidebar"),
        Swap(
            "core/components/_breadcrumbs.html",
            _breadcrumbs(("uwu", None)),
            target_id="breadcrumbs",
        ),
    ],
    partial=PathReplace("pages/", "partials/_"),
)


def item_list(request: HttpRequest) -> HttpResponse:
    items = [{"name": fake.name, "description": fake.text} for i in range(5)]
    return render_sandbox(
        request,
        "sandbox/pages/item_list.html",
        {"items": items},
        title="Items · Sandbox",
    )
