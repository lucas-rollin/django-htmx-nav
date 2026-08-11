"""
make_shell_renderer: a render_nav wrapper that always includes a fixed
shell/navigation Swap alongside whatever else the caller passes.
"""

from collections.abc import Callable, Mapping
from typing import Any, Protocol

from django.http import HttpRequest
from django.template.response import TemplateResponse

from .partials import PartialSpec
from .shortcuts import render_nav
from .swaps import Swap, Swaps, _normalize_swaps
from .targeting import Target


class ShellRenderer(Protocol):
    """Callable signature for renderers produced by `make_shell_renderer`."""

    def __call__(
        self,
        request: HttpRequest,
        template_name: str,
        context: Mapping[str, Any] | None = None,
        *,
        extra_swaps: Swaps = None,
        partial: PartialSpec = "#content",
        **kwargs: Any,
    ) -> TemplateResponse: ...


def make_shell_renderer(
    shell_template: str,
    context_builder: Callable[[HttpRequest], Mapping[str, Any]] | None = None,
    *,
    target_id: str | None = None,
    include_if: Target = True,
    namespace: str | None = None,
    partial: PartialSpec = "#content",
) -> ShellRenderer:
    """Creates a renderer that automatically injects a shell navigation swap.

    Example:
    ```python
        render_dashboard = make_shell_renderer(
            "partials/navigation.html",
            context_builder=lambda req: {"unread": req.user.unread_count},
            target_id="nav-bar",
        )

        return render_dashboard(request, "pages/projects.html", {"projects": projects})
    ```
    """
    default_partial: PartialSpec = (
        dict(partial) if isinstance(partial, Mapping) else partial
    )

    def render_shell(
        request: HttpRequest,
        template_name: str,
        context: Mapping[str, Any] | None = None,
        *,
        extra_swaps: Swaps = None,
        partial: PartialSpec = default_partial,
        **kwargs: Any,
    ) -> TemplateResponse:
        page_context = dict(context or {})
        shell_context = dict(
            context_builder(request) if context_builder is not None else {}
        )

        if namespace is not None:
            shell_swap_context: dict[str, Any] = {namespace: shell_context}
        else:
            shell_swap_context = {**shell_context, **page_context}

        shell_swap = Swap(
            shell_template,
            context=shell_swap_context,
            target_id=target_id,
            include_if=include_if,
        )

        return render_nav(
            request,
            template_name,
            page_context,
            partial=partial,
            swaps=[shell_swap, *_normalize_swaps(extra_swaps)],
            **kwargs,
        )

    return render_shell
