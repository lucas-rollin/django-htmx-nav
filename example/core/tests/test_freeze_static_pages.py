import pytest
from django.core.management import call_command
from django.urls import get_script_prefix


@pytest.mark.django_db
def test_freeze_static_pages_strips_prefix_from_demo_links(tmp_path, settings):
    settings.DEMO_URL = "https://django-htmx-nav.onrender.com"
    out_dir = tmp_path / "site"

    initial_prefix = get_script_prefix()

    call_command("freeze_static_pages", out=str(out_dir), prefix="/django-htmx-nav/")

    # Script prefix must be restored
    assert get_script_prefix() == initial_prefix

    # Check index.html
    index_file = out_dir / "index.html"
    assert index_file.exists()
    content = index_file.read_text(encoding="utf-8")

    # Internal routes must have script prefix
    assert 'href="/django-htmx-nav/guide/"' in content
    assert 'href="/django-htmx-nav/benchmarks/"' in content

    # Demo routes must NOT have script prefix
    assert "/django-htmx-nav/demo/" not in content
    assert "https://django-htmx-nav.onrender.com/demo/" in content

    # Check guide/index.html
    guide_file = out_dir / "guide" / "index.html"
    assert guide_file.exists()
    guide_content = guide_file.read_text(encoding="utf-8")
    assert "/django-htmx-nav/demo/" not in guide_content
    assert "https://django-htmx-nav.onrender.com/demo/" in guide_content
