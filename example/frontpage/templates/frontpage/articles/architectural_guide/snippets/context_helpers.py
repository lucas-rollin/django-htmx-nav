from django.http import HttpRequest, HttpResponse

from core.models import Organization, Project

def _sidebar_context(
    active_org_id: str | None = None,
    active_project_id: str | None = None,
    active_page: str | None = None,
):
    orgs = Organization.objects.prefetch_related("projects").only("id", "name")

    return {
        "orgs": orgs,
        "active_org_id": active_org_id,
        "active_project_id": active_project_id,
        "active_page": active_page,
    }

def _breadcrumbs(*crumbs: tuple[str, str | None]):
    """crumbs: list of (label, url_or_None) tuples."""
    return {"breadcrumbs": [{"label": label, "url": url} for label, url in crumbs]}

