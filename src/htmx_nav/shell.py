"""
make_shell_renderer: a render_nav wrapper that always includes a fixed
list of navigational Swaps alongside whatever extra_swaps the caller
passes per-call.

Earlier versions took a single `shell_template` + `context_builder` and
built exactly one Swap internally. That collapsed every navigational
region into one fragment, which meant giving up what Swap already does
per-region for free: independent target_id, independent include_if for
conditional inclusion, and independent debug-swap highlighting (the
debug marker in swaps.py is emitted per Swap, keyed on that Swap's own
target_id — one shell Swap means one marker for the whole shell).

This version takes a `swaps` builder instead: a callable that returns
whatever Swap(s) should always accompany this shell for a given
request. Each returned Swap is a full Swap — its own template, context,
target_id, include_if — so per-region conditional rendering and
per-region debug highlighting both fall out for free, the same way they
would for any hand-written `render_nav(..., swaps=[...])` call.
make_shell_renderer's only remaining job is merging that fixed list
with per-call extra_swaps and forwarding to render_nav.
"""

from collections.abc import Callable, Mapping
from typing import Any, Protocol

from django.http import HttpRequest
from django.template.response import TemplateResponse

from .partials import PartialSpec
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
        partial: PartialSpec = "#content",
        **kwargs: Any,
    ) -> TemplateResponse: ...

    """
    Renders a template with a fixed set of navigational Swaps always
    included.

    Args:
        request: The HTTP request object.
        template_name: Path to the main content template.
        context: Optional context for the main template.
        extra_swaps: Additional, per-call Swaps included alongside the
            fixed shell Swaps.
        partial: Specifies the partial to render for HTMX requests.
        **kwargs: Additional arguments passed to `render_nav`.

    Returns:
        A TemplateResponse with the shell Swaps included.
    """


def make_shell_renderer(
    swaps: Callable[[HttpRequest], Swaps],
    *,
    partial: PartialSpec = "#content",
) -> ShellRenderer:
    """
    Creates a renderer that always includes a fixed set of Swaps.

    Args:
        swaps: Callable that returns the Swap(s) that should always
            accompany this shell for a given request — typically one
            Swap per navigational region, each with its own template,
            context, target_id, and include_if. Called once per render.
        partial: Default PartialSpec used unless overridden per-call.

    Returns:
        A `render_shell` function with the signature of `ShellRenderer`.

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
    default_partial: PartialSpec = partial

    def render_shell(
        request: HttpRequest,
        template_name: str,
        context: Mapping[str, Any] | None = None,
        *,
        extra_swaps: Swaps = None,
        partial: PartialSpec = default_partial,
        **kwargs: Any,
    ) -> TemplateResponse:
        shell_swaps = _normalize_swaps(swaps(request))
        return render_nav(
            request,
            template_name,
            context,
            partial=partial,
            swaps=[*shell_swaps, *_normalize_swaps(extra_swaps)],
            **kwargs,
        )

    return render_shell
