from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from django.http import HttpRequest
from django.template.response import TemplateResponse

from .partials import PartialSpec
from .shell import ShellRenderer
from .shortcuts import render_nav
from .swaps import Swaps, _normalize_swaps


class _ShellViewProtocol(Protocol):
    request: HttpRequest

    def get_template_names(self) -> list[str]: ...
    def get_extra_swaps(self) -> Swaps: ...
    def get_partial(self) -> PartialSpec: ...
    def get_title(self) -> str | None: ...
    def get_shell_template_name(self) -> str: ...


def make_shell_view_mixin(
    render: ShellRenderer | None = None,
    *,
    default_swaps: Swaps = None,
    default_partial: PartialSpec = "#content",
) -> type:
    """Creates a class mixin that routes CBV rendering through a shell renderer.

    Args:
        render: Optional render function, typically created by
            `make_shell_renderer`. When omitted, calls `render_nav` directly.
        default_swaps: Default Swap(s) applied across all views using this mixin.
        default_partial: Partial spec used unless overridden per view.
            Defaults to "#content".

    Returns:
        A mixin class providing `render_to_response` and swap customization hooks.

    Notes:
        Override points on the resulting view class:
            - `get_extra_swaps()`: Returns per-view swaps (runs with `self.object` available).
            - `get_title()` or `title`: Page title override.
            - `get_partial()`: Overrides `default_partial` for the view.
            - `get_shell_template_name()`: Defaults to `get_template_names()[0]`.

    Example:
        .. code-block:: python

            ShellViewMixin = make_shell_view_mixin()

            class TicketListView(ShellViewMixin, ListView):
                template_name = "pages/project.html"

                def get_extra_swaps(self):
                    return [sidebar_swap, breadcrumb_swap]
    """
    defaults = _normalize_swaps(default_swaps)
    render_fn: Callable[..., TemplateResponse] = render or render_nav
    swaps_kwarg = "extra_swaps" if render is not None else "swaps"

    class ShellViewMixin:
        title: str | None = None

        def get_extra_swaps(self) -> Swaps:
            return None

        def get_title(self) -> str | None:
            return self.title

        def get_partial(self) -> PartialSpec:
            return default_partial

        def get_shell_template_name(self: _ShellViewProtocol) -> str:
            return self.get_template_names()[0]

        def render_to_response(
            self: _ShellViewProtocol,
            context: dict[str, Any],
            **response_kwargs: Any,
        ) -> TemplateResponse:
            swaps = [*defaults, *_normalize_swaps(self.get_extra_swaps())]

            response_kwargs.setdefault("partial", self.get_partial())
            response_kwargs.setdefault("title", self.get_title())
            response_kwargs.setdefault(swaps_kwarg, swaps)

            return render_fn(
                self.request,
                self.get_shell_template_name(),
                context,
                **response_kwargs,
            )

    return ShellViewMixin
