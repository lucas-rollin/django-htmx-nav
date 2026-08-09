from typing import Any, Protocol

from django.http import HttpRequest
from django.template.response import TemplateResponse

from .responses import ShellRenderer, Swap


class _ShellViewProtocol(Protocol):
    """Typing aid describing what `ShellViewMixin` expects from the view
    it's mixed into (normally a `TemplateResponseMixin` subclass)."""

    request: HttpRequest

    def get_template_names(self) -> list[str]: ...


def make_shell_view_mixin(render_shell: ShellRenderer) -> type:
    """
    Create a mixin that routes a Class-Based View's response through a
    shell renderer produced by `make_shell_renderer`.

    Combine with any `TemplateResponseMixin`-based generic view (`TemplateView`,
    `DetailView`, `ListView`, `FormView`, ...). Put the mixin first in the MRO
    so its `render_to_response` takes precedence over the base view's.

    Args:
        render_shell: A shell rendering function, typically from
            `make_shell_renderer`.

    Returns:
        A mixin class for Django generic views.

    Example:
        .. code-block:: python

            render_shell = make_shell_renderer("partials/nav.html")
            ShellViewMixin = make_shell_view_mixin(render_shell)

            class ProjectDetailView(ShellViewMixin, DetailView):
                model = Project
                template_name = "project/detail.html"
                title = "Project detail"

                def get_extra_swaps(self):
                    return Swap(
                        "partials/breadcrumbs.html",
                        {"project": self.object},
                        target_id="breadcrumbs",
                    )
    """

    class ShellViewMixin:
        title: str | None = None

        def get_extra_swaps(self) -> Swap | list[Swap] | None:
            """Return additional Swap fragment(s) for this response. Override
            to contribute view-specific swaps, e.g. ones referencing
            `self.object`. Defaults to none."""
            return None

        def get_title(self) -> str | None:
            """Return the page title for this response. Defaults to the
            `title` class attribute. Return None to fall back to whatever
            `title` (if any) the context itself already supplies."""
            return self.title

        def get_shell_template_name(self: _ShellViewProtocol) -> str:
            """Return the base template rendered through the shell. Defaults
            to the first entry from `get_template_names()`."""
            return self.get_template_names()[0]

        def render_to_response(
            self: _ShellViewProtocol,
            context: dict[str, Any],
            **response_kwargs: Any,
        ) -> TemplateResponse:
            response_kwargs.setdefault("extra_swaps", self.get_extra_swaps())
            response_kwargs.setdefault("title", self.get_title())
            return render_shell(
                self.request,
                self.get_shell_template_name(),
                context,
                **response_kwargs,
            )

    return ShellViewMixin
