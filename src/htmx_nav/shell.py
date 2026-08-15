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

    """
    Renders a template with an automatically injected shell navigation swap.

    Args:
        request: The HTTP request object.
        template_name: Path to the main content template.
        context: Optional context for the main template.
        extra_swaps: Additional swaps to include alongside the shell.
        partial: Specifies the partial to render for HTMX requests.
            Defaults to "#content".
        **kwargs: Additional arguments passed to `render_nav`.

    Returns:
        A TemplateResponse with the shell navigation injected.

    Example:
        .. code-block:: python

            render_dashboard = make_shell_renderer(
                "partials/navigation.html",
                context_builder=lambda req: {"unread": req.user.unread_count},
                target_id="nav-bar",
            )
            return render_dashboard(request, "pages/projects.html", {"projects": projects})
    """


def make_shell_renderer(
    shell_template: str,
    context_builder: Callable[[HttpRequest], Mapping[str, Any]] | None = None,
    *,
    target_id: str | None = None,
    include_if: Target = True,
    namespace: str | None = None,
    partial: PartialSpec = "#content",
) -> ShellRenderer:
    """
    Creates a renderer that automatically injects a shell navigation swap.

    This factory produces a renderer that ensures a persistent navigation shell
    (e.g., sidebar, header) is always included in responses, while allowing the
    caller to focus on rendering the main content area.

    Args:
        shell_template: Template path for the shell fragment (e.g., `"partials/nav.html"`).
        context_builder: Optional callable that generates context for the shell
            template. Receives the request and returns a mapping. Useful for
            user-specific data like unread counts or notifications.
        target_id: DOM ID of the main content area where swaps are targeted.
            If not provided, the swap will be out-of-band.
        include_if: Predicate determining if the shell swap applies to the request.
            Can be a boolean or callable receiving the request. Defaults to `True`.
        namespace: Optional namespace prefix for the shell context. If provided,
            shell context is wrapped under this namespace.
        partial: Specifies what partial to render for HTMX requests.
            Defaults to "#content".

    Returns:
        A `render_shell` function with the signature of `ShellRenderer`.

    Example:
        .. code-block:: python

            render_dashboard = make_shell_renderer(
                "partials/navigation.html",
                context_builder=lambda req: {
                    "unread_count": req.user.notifications.unread().count(),
                    "username": req.user.username,
                },
                target_id="nav-bar",
                namespace="nav",
            )

            def dashboard_view(request):
                return render_dashboard(
                    request,
                    "dashboard/content.html",
                    {"stats": get_stats()},
                    extra_swaps=Swap("partials/notifications.html", target_id="notif-badge"),
                )
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
