"""
Create ShellRenderers, a reusable wrapper around a render_nav.

Allows the definition of a shell (e.g. sidebar and breadcrumbs)
as the regions that need to always be synced in htmx requests
for that endpoint.
"""

from collections.abc import Callable, Mapping
from typing import Any, Protocol

from django.http import HttpRequest
from django.template.response import TemplateResponse

from .partials import PartialSpec
from .settings import _UNSET, _default_partial_spec
from .shortcuts import render_nav
from .swaps import Swaps, _normalize_swaps


class ShellRenderer(Protocol):
    """Callable signature for renderers produced by `make_shell_renderer`."""

    def __call__(
        self,
        request: HttpRequest,
        template_name: str,
        context: Mapping[str, Any] | None = None,
        *,
        extra_swaps: Swaps = None,
        partial: PartialSpec | object = _UNSET,
        **kwargs: Any,
    ) -> TemplateResponse:
        """Renders a template with recurring shell Swaps always included.

        Args:
            request: The HTTP request object.
            template_name: Path to the main content template.
            context: Optional context for the main template.
            extra_swaps: Additional per-call Swaps included alongside shell Swaps.
            partial: Specifies the partial to render for HTMX requests.
            **kwargs: Additional arguments passed to `render_nav`.

        Returns:
            A TemplateResponse with the shell Swaps included.
        """
        ...


def make_shell_renderer(
    swaps: Swaps | Callable[[HttpRequest], Swaps],
    *,
    partial: PartialSpec | object = _UNSET,
) -> ShellRenderer:
    """Creates a renderer that always includes a fixed set of Swaps.

    Args:
        swaps: Swaps included on each request, or a callable receiving
            request and returning Swaps.
        partial: Default PartialSpec used unless overridden per-call.
            Defaults to the `HTMX_NAV_DEFAULT_PARTIAL` setting (`"#content"`).

    Returns:
        A `render_shell` function matching the `ShellRenderer` protocol.

    Example:
        .. code-block:: python

            def build_shell_swaps(request):
                return [
                    Swap("nav/_sidebar.html", sidebar_context(request), target_id="sidebar"),
                    Swap("nav/_breadcrumbs.html", crumbs_context(request), target_id="breadcrumbs"),
                ]

            render_shell = make_shell_renderer(build_shell_swaps)

            def project_detail(request, pk):
                project = get_object_or_404(Project, pk=pk)
                return render_shell(request, "app/project_detail.html", {"project": project})
    """
    default_partial: PartialSpec = (
        _default_partial_spec() if partial is _UNSET else partial  # type: ignore[assignment]
    )

    def render_shell(
        request: HttpRequest,
        template_name: str,
        context: Mapping[str, Any] | None = None,
        *,
        extra_swaps: Swaps = None,
        partial: PartialSpec | object = _UNSET,
        **kwargs: Any,
    ) -> TemplateResponse:
        effective_partial = default_partial if partial is _UNSET else partial
        resolved = swaps(request) if callable(swaps) else swaps
        return render_nav(
            request,
            template_name,
            context,
            partial=effective_partial,
            swaps=[*_normalize_swaps(resolved), *_normalize_swaps(extra_swaps)],
            **kwargs,
        )

    return render_shell
