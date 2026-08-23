from django.template import Context, Template
from django.test import override_settings

from htmx_nav.debugging import _build_marker_script, debug_swap_marker

# =============================================================================
# _build_marker_script — unconditional builder
# =============================================================================


def test_build_marker_script_looks_up_the_given_target_id():
    script = _build_marker_script("alerts")
    assert 'getElementById("alerts")' in script


def test_build_marker_script_wrapped_in_script_tags():
    script = _build_marker_script("alerts")
    assert script.startswith("<script>")
    assert script.endswith("</script>")


def test_build_marker_script_toggles_hn_swap_class():
    script = _build_marker_script("alerts")
    assert "classList.remove('hn-swap')" in script
    assert "classList.add('hn-swap')" in script


def test_build_marker_script_json_escapes_target_id():
    script = _build_marker_script('a"b')
    assert '"a\\"b"' in script


@override_settings(HTMX_NAV_DEBUG_SWAPS=False)
def test_build_marker_script_ignores_debug_setting():
    # Unconditional: no enabled-check inside the builder itself.
    assert _build_marker_script("x") != ""


# =============================================================================
# debug_swap_marker — public, setting-gated wrapper
# =============================================================================


def test_debug_swap_marker_empty_by_default():
    assert debug_swap_marker("alerts") == ""


@override_settings(HTMX_NAV_DEBUG_SWAPS=False)
def test_debug_swap_marker_empty_when_explicitly_disabled():
    assert debug_swap_marker("alerts") == ""


@override_settings(HTMX_NAV_DEBUG_SWAPS=True)
def test_debug_swap_marker_returns_script_when_enabled():
    marker = debug_swap_marker("alerts")
    assert 'getElementById("alerts")' in marker
    assert "hn-swap" in marker


@override_settings(HTMX_NAV_DEBUG_SWAPS=True)
def test_debug_swap_marker_matches_build_marker_script_exactly():
    # Same implementation underneath, no drift between the two paths
    assert debug_swap_marker("box") == _build_marker_script("box")


# =============================================================================
# {% htmx_nav_debug_marker %} template tag
# =============================================================================


def test_template_tag_renders_nothing_by_default():
    template = Template("{% load htmx_nav %}{% htmx_nav_debug_marker 'breadcrumbs' %}")
    assert template.render(Context({})) == ""


@override_settings(HTMX_NAV_DEBUG_SWAPS=True)
def test_template_tag_renders_marker_when_enabled():
    template = Template("{% load htmx_nav %}{% htmx_nav_debug_marker 'breadcrumbs' %}")
    rendered = template.render(Context({}))
    assert 'getElementById("breadcrumbs")' in rendered


@override_settings(HTMX_NAV_DEBUG_SWAPS=True)
def test_template_tag_output_not_html_escaped():
    template = Template("{% load htmx_nav %}{% htmx_nav_debug_marker 'breadcrumbs' %}")
    rendered = template.render(Context({}))
    assert "<script>" in rendered
    assert "&lt;script&gt;" not in rendered


@override_settings(HTMX_NAV_DEBUG_SWAPS=True)
def test_template_tag_accepts_variable_target_id():
    template = Template("{% load htmx_nav %}{% htmx_nav_debug_marker tid %}")
    rendered = template.render(Context({"tid": "sidebar"}))
    assert 'getElementById("sidebar")' in rendered