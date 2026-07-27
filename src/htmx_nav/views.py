"""
Class-based-view support. Optional — function-based views can just call
`render_shell(request, ...)` directly.
"""
from typing import Callable, Protocol, Sequence, Any
from django.http import HttpRequest


class _DjangoViewProtocol(Protocol):
    request: HttpRequest
    template_name: str | None = None
    def get_template_names(self) -> list[str]: ...
    shell_extra_oob: Sequence[Any]


def make_shell_view_mixin(render_shell: Callable):
    """
    Factory returning a mixin that routes a CBV's `render_to_response`
    through `render_shell` (as produced by
    `htmx_nav.responses.make_shell_renderer`), so views don't each
    hand-wire it.

    Usage:

        # yourapp/views.py
        from htmx_nav.views import make_shell_view_mixin
        from .render import render_shell

        ShellViewMixin = make_shell_view_mixin(render_shell)

        class DemandDetailView(ShellViewMixin, DetailView):
            template_name = "ombudsman/demand_detail.html"
            shell_extra_oob = ()  # optional, see below

    Works with any Django generic view whose `render_to_response(context,
    **response_kwargs)` is the final step (TemplateView, DetailView,
    ListView, FormView, ...). `response_kwargs` (status, content_type,
    etc.) are passed straight through to `render_shell`/`render_htmx`.

    A view can set `shell_extra_oob` (a sequence of `Oob`) to append
    additional out-of-band fragments beyond the fixed shell, e.g. a
    toast or a per-view sidebar badge update.
    """
    class ShellViewMixin:
        shell_extra_oob: tuple = ()

        def render_to_response(self: _DjangoViewProtocol, context: dict[str, Any], **response_kwargs: Any):
            return render_shell(
                self.request,
                self.get_template_names()[0] if hasattr(self, "get_template_names") else self.template_name,
                context,
                extra_oob=self.shell_extra_oob,
                **response_kwargs,
            )

    return ShellViewMixin
