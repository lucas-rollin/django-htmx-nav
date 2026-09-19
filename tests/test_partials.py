import pytest
from django.test import RequestFactory

from htmx_nav.partials import (
    PartialResolver,
    PathReplace,
    _resolve_partial_name,
    _resolve_template_name,
)
from htmx_nav.targeting import targeting

from .helpers import htmx_request

# =============================================================================
# _resolve_partial_name
# =============================================================================


def test_resolve_partial_name_none_returns_none():
    assert _resolve_partial_name(None, RequestFactory().get("/")) is None


def test_resolve_partial_name_string_returns_itself():
    assert _resolve_partial_name("#content", RequestFactory().get("/")) == "#content"


def test_resolve_partial_name_mapping_returns_first_matching():
    request = htmx_request(RequestFactory(), target="tabs")
    spec = {"#tab_content": targeting("tabs"), "#content": True}
    assert _resolve_partial_name(spec, request) == "#tab_content"


def test_resolve_partial_name_mapping_falls_through_to_catch_all():
    request = RequestFactory().get("/")  # no HX-Target
    spec = {"#tab_content": targeting("tabs"), "#content": True}
    assert _resolve_partial_name(spec, request) == "#content"


def test_resolve_partial_name_mapping_returns_none_when_nothing_matches():
    request = RequestFactory().get("/")
    spec = {"#tab_content": targeting("tabs")}
    assert _resolve_partial_name(spec, request) is None


def test_resolve_partial_name_callable_invoked_with_request():
    request = RequestFactory().get("/")
    calls = []

    def resolver(req):
        calls.append(req)
        return "#custom"

    assert _resolve_partial_name(resolver, request) == "#custom"
    assert calls == [request]


# --- PathReplace ---------------------------------------------
def test_path_replace_resolve():
    request = RequestFactory().get("/")
    transformer = PathReplace("pages/", "partials/_")

    # Root template replacement
    assert transformer.resolve(request, "pages/board.html") == "partials/_board.html"

    # Namespaced template replacement
    assert (
        transformer.resolve(request, "myapp/pages/board.html")
        == "myapp/partials/_board.html"
    )

    # When prefix not found, returns original template_name gracefully
    assert transformer.resolve(request, "custom/board.html") == "custom/board.html"

    # Empty template name
    assert transformer.resolve(request, "") == ""

    # Check PartialResolver protocol
    assert isinstance(transformer, PartialResolver)


def test_resolve_partial_name_with_path_replace():
    request = RequestFactory().get("/")
    transformer = PathReplace("pages/", "partials/_")

    assert (
        _resolve_partial_name(transformer, request, "pages/board.html")
        == "partials/_board.html"
    )
    assert (
        _resolve_partial_name(transformer, request, "myapp/pages/board.html")
        == "myapp/partials/_board.html"
    )


def test_resolve_partial_name_with_custom_partial_resolver_class():
    class CustomResolver:
        def resolve(self, request, template_name):
            return f"transformed/{template_name}"

    request = RequestFactory().get("/")
    resolver = CustomResolver()
    assert isinstance(resolver, PartialResolver)
    assert (
        _resolve_partial_name(resolver, request, "index.html")
        == "transformed/index.html"
    )


def test_resolve_partial_name_mapping_with_resolver():
    request = htmx_request(RequestFactory(), target="tabs")
    transformer = PathReplace("pages/", "partials/_")
    spec = {transformer: targeting("tabs"), "#content": True}
    assert (
        _resolve_partial_name(spec, request, "pages/board.html")
        == "partials/_board.html"
    )


def test_resolve_partial_name_invalid_type_raises():
    with pytest.raises(TypeError):
        _resolve_partial_name(123, RequestFactory().get("/"))  # type: ignore


# =============================================================================
# _resolve_template_name
# =============================================================================


def test_resolve_template_name_full_render_ignores_partial_name():
    assert _resolve_template_name("page.html", "#content", is_htmx=False) == "page.html"


def test_resolve_template_name_htmx_no_partial_name_returns_base():
    assert _resolve_template_name("page.html", None, is_htmx=True) == "page.html"


def test_resolve_template_name_block_syntax_appends_hash_suffix():
    assert (
        _resolve_template_name("page.html", "#content", is_htmx=True)
        == "page.html#content"
    )


def test_resolve_template_name_standalone_path_replaces_base_template():
    assert (
        _resolve_template_name("page.html", "partials/_tab.html", is_htmx=True)
        == "partials/_tab.html"
    )
