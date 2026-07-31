from typing import Any, Callable, Protocol, Sequence
from django.http import HttpRequest


class _DjangoViewProtocol(Protocol):
    request: HttpRequest
    template_name: str | None = None
    def get_template_names(self) -> list[str]: ...
    shell_extra_oob: Sequence[Any]


def make_shell_view_mixin(render_shell: Callable) -> type:
    """Creates a mixin that integrates shell rendering into Django Class-Based Views.

    Args:
        render_shell: The shell rendering function to use.

    Returns:
        A mixin class for Django generic views.

    Example:
        .. code-block:: python

            ShellViewMixin = make_shell_view_mixin(render_shell)
            class MyView(ShellViewMixin, DetailView):
                template_name = "item_detail.html"
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