"""
Rendering shortcuts.

`render_with_swaps` is the htmx-aware counterpart to
django.shortcuts.render, for any HTMX view that wants to piggyback
out-of-band swaps — no navigation concept required. `render_nav` adds
PartialSpec-driven partial/block resolution on top, for views that
participate in this package's tab/nav-state model.
"""

from collections.abc import Mapping
from typing import Any

from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.utils.cache import patch_vary_headers
from django.utils.html import escape

from .partials import PartialSpec, _resolve_partial_name, _resolve_template_name
from .settings import _title_context_key
from .swaps import Swaps, _normalize_swaps
from .targeting import _is_htmx_request


def render_with_swaps(
    request: HttpRequest,
    template_name: str,
    context: Mapping[str, Any] | None = None,
    content_type: str | None = None,
    status: int | None = None,
    using: str | None = None,
    *,
    swaps: Swaps = None,
    title: str | None = None,
) -> TemplateResponse:
    """Renders a template as given and appends swap fragments on HTMX requests.

    Does no partial/block resolution and no active-navigation-region logic.
    Use this directly for HTMX responses that don't participate in this
    package's navigation system (e.g., a form POST that also refreshes a
    notification badge elsewhere via OOB).

    `render_nav` is the navigation-flavored version built on top of this.
    """
    is_htmx = _is_htmx_request(request)
    swap_list = _normalize_swaps(swaps)

    base_context: dict[str, Any] = {}
    for swap in swap_list:
        if swap.context:
            base_context.update(swap.context)
    page_context = {**base_context, **(context or {})}

    title_key = _title_context_key()
    page_context.setdefault(title_key, None)
    if title is not None:
        page_context[title_key] = title
    effective_title = page_context.get(title_key)

    response = TemplateResponse(
        request,
        template_name,
        page_context,
        content_type=content_type,
        status=status,
        using=using,
    )
    patch_vary_headers(response, ("HX-Request",))

    if is_htmx and (swap_list or effective_title):

        def append_swaps(response: TemplateResponse) -> TemplateResponse:
            for swap in swap_list:
                if not swap.applies_to(request):
                    continue
                html = swap.render(request, parent_context=page_context, using=using)
                response.content += html.encode(response.charset)
            if effective_title:
                response.content += f"<title>{escape(effective_title)}</title>".encode(
                    response.charset
                )
            return response

        response.add_post_render_callback(append_swaps)

    return response


def render_nav(
    request: HttpRequest,
    template_name: str,
    context: Mapping[str, Any] | None = None,
    content_type: str | None = None,
    status: int | None = None,
    using: str | None = None,
    *,
    partial: PartialSpec = "#content",
    swaps: Swaps = None,
    title: str | None = None,
) -> TemplateResponse:
    """Renders a Django template with HTMX partial resolution and OOB swaps.

    Navigation-flavored `render_with_swaps`: resolves which template-partials
    block or standalone template to render, and exposes `active_partial` in
    context for nav/tab highlighting.

    Example:
        .. code-block:: python

            return render_nav(
                request,
                "project/detail.html",
                {"project": project},
                partial={
                    "#tab_content": targeting("tab-content"),
                    "#main_content": targeting("main-content"),
                    "#content": True,
                },
                swaps=[Swap("partials/sidebar.html", target_id="sidebar")],
                title=project.name,
            )
    """
    is_htmx = _is_htmx_request(request)
    active_partial = _resolve_partial_name(partial, request)
    resolved_template = _resolve_template_name(template_name, active_partial, is_htmx)

    context = dict(context or {})
    context.setdefault("active_partial", active_partial)

    return render_with_swaps(
        request,
        resolved_template,
        context,
        content_type=content_type,
        status=status,
        using=using,
        swaps=swaps,
        title=title,
    )
