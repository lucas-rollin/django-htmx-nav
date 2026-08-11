from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from django.http import HttpRequest
from django.template.response import TemplateResponse

from .responses import (
    PartialSpec,
    ShellRenderer,
    Swaps,
    _normalize_swaps,
    render_htmx,
)


class _ShellViewProtocol(Protocol):
    """Protocol defining the interface required by `ShellViewMixin`."""

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
    """Builds a Class-Based View mixin that routes responses through `render_htmx`.

    Args:
        render: Custom render callable (e.g., from `make_shell_renderer`).
            If `None`, delegates directly to `render_htmx`.
        default_swaps: Swaps applied across all views using this mixin.
        default_partial: Fallback `PartialSpec` applied when `get_partial` is un-overridden.

    Returns:
        A mixin class providing HTMX rendering capabilities for CBVs.

    Example:
        ```python
        ShellViewMixin = make_shell_view_mixin()


        class TicketListView(ShellViewMixin, ListView):
            template_name = "pages/project.html"

            def get_extra_swaps(self):
                return [sidebar_swap]

            def get_partial(self):
                return {
                    "#main_content": targeting("main-content"),
                    "#content": True,
                }
        ```
    """
    defaults = _normalize_swaps(default_swaps)
    render_fn: Callable[..., TemplateResponse] = render or render_htmx
    swaps_kwarg = "extra_swaps" if render is not None else "swaps"

    class ShellViewMixin:
        title: str | None = None

        def get_extra_swaps(self) -> Swaps:
            """Returns additional swaps specific to this view instance."""
            return None

        def get_title(self) -> str | None:
            """Returns the page title for context and HTMX updates."""
            return self.title

        def get_partial(self) -> PartialSpec:
            """Returns the `PartialSpec` configuration for this view."""
            return default_partial

        def get_shell_template_name(self: _ShellViewProtocol) -> str:
            """Returns the template path to render."""
            return self.get_template_names()[0]

        def render_to_response(
            self: _ShellViewProtocol,
            context: dict[str, Any],
            **response_kwargs: Any,
        ) -> TemplateResponse:
            """Renders the view context using the configured HTMX renderer."""
            swaps = [
                *defaults,
                *_normalize_swaps(self.get_extra_swaps()),
            ]

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
