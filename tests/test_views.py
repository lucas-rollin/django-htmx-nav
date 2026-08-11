from django.test import RequestFactory
from django.views.generic import TemplateView

from htmx_nav.shell import make_shell_renderer
from htmx_nav.swaps import Swap
from htmx_nav.views import make_shell_view_mixin

render_shell = make_shell_renderer(
    "tests/_shell.html",
    context_builder=lambda request: {"nav": {"sidebar": [1, 2, 3]}},
)
ShellViewMixin = make_shell_view_mixin(render_shell)


class DemoView(ShellViewMixin, TemplateView):
    template_name = "tests/_page.html"
    title = "Demo Page"


def test_full_render_uses_template_and_title_attribute():
    request = RequestFactory().get("/demo/")
    response = DemoView.as_view()(request)
    response.render()
    assert b"FULL PAGE:" in response.content
    assert response.context_data["title"] == "Demo Page"


def test_htmx_render_includes_shell_swap_and_title_tag():
    request = RequestFactory().get("/demo/", HTTP_HX_REQUEST="true")
    response = DemoView.as_view()(request)
    response.render()
    assert b"FULL PAGE:" not in response.content
    assert b"<nav>3</nav>" in response.content
    assert b"<title>Demo Page</title>" in response.content


def test_get_extra_swaps_default_is_none_and_contributes_nothing_extra():
    request = RequestFactory().get("/demo/", HTTP_HX_REQUEST="true")
    response = DemoView.as_view()(request)
    response.render()
    assert b"hx-swap-oob" not in response.content


def test_get_extra_swaps_can_return_bare_swap_referencing_view_state():
    class RichView(ShellViewMixin, TemplateView):
        template_name = "tests/_page.html"

        def get_extra_swaps(self):
            return Swap(
                "tests/_notification.html",
                {"message": self.request.path},
                target_id="alerts",
            )

    request = RequestFactory().get("/demo-path/", HTTP_HX_REQUEST="true")
    response = RichView.as_view()(request)
    response.render()
    assert b'<div id="alerts" hx-swap-oob="innerHTML">' in response.content
    assert b"/demo-path/" in response.content


def test_get_title_override_takes_precedence_over_class_attribute():
    class TitledView(ShellViewMixin, TemplateView):
        template_name = "tests/_page.html"
        title = "Class Attribute Title"

        def get_title(self):
            return "Overridden Title"

    request = RequestFactory().get("/demo/")
    response = TitledView.as_view()(request)
    response.render()
    assert response.context_data["title"] == "Overridden Title"


def test_no_title_falls_back_to_context_supplied_title():
    class ContextTitledView(ShellViewMixin, TemplateView):
        template_name = "tests/_page.html"

        def get_context_data(self, **kwargs):
            return {**super().get_context_data(**kwargs), "title": "From context"}

    request = RequestFactory().get("/demo/")
    response = ContextTitledView.as_view()(request)
    response.render()
    assert response.context_data["title"] == "From context"


def test_shell_template_name_defaults_to_first_template_name():
    view = DemoView()
    assert view.get_shell_template_name() == "tests/_page.html"


def test_shell_template_name_can_be_overridden():
    class AltTemplateView(ShellViewMixin, TemplateView):
        template_name = "tests/_page.html"

        def get_shell_template_name(self):
            return "tests/_page_nav.html"

    request = RequestFactory().get("/demo/", HTTP_HX_REQUEST="true")
    response = AltTemplateView.as_view()(request)
    response.render()
    assert b'<div class="content">' in response.content


def test_zero_config_shell_view_mixin_needs_no_render_shell():
    Mixin = make_shell_view_mixin()

    class DemoView2(Mixin, TemplateView):
        template_name = "tests/_page.html"

        def get_extra_swaps(self):
            return Swap(
                "tests/_notification.html", {"message": "hi"}, target_id="alerts"
            )

    request = RequestFactory().get("/demo/", HTTP_HX_REQUEST="true")
    response = DemoView2.as_view()(request)
    response.render()
    assert (
        b'<div id="alerts" hx-swap-oob="innerHTML"><p>hi</p></div>' in response.content
    )


def test_default_swaps_combine_with_view_extra_swaps():
    Mixin = make_shell_view_mixin(
        default_swaps=Swap("tests/_minimal.html", {"value": "shell"}, target_id="shell")
    )

    class DemoView3(Mixin, TemplateView):
        template_name = "tests/_page.html"

        def get_extra_swaps(self):
            return Swap(
                "tests/_notification.html", {"message": "view"}, target_id="alerts"
            )

    request = RequestFactory().get("/demo/", HTTP_HX_REQUEST="true")
    response = DemoView3.as_view()(request)
    response.render()
    assert b'id="shell"' in response.content
    assert b'id="alerts"' in response.content
