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
    """Renders a template and appends swap fragments on HTMX requests.

    This is the foundational HTMX-aware renderer. Unlike `render_nav`, it does
    no partial resolution or navigation state management. Use it for HTMX
    responses that need out-of-band swaps without navigation involvement.

    Args:
        request: The HTTP request object.
        template_name: Path to the main template.
        context: Optional template context.
        content_type: Optional response content type.
        status: Optional HTTP status code.
        using: Optional template engine.
        swaps: A single Swap, list, or None. Additional HTML fragments to
            append as out-of-band swaps.
        title: Optional page title. Overrides title context variable and
            injects a `<title>` element for HTMX requests.

    Returns:
        A TemplateResponse with swaps appended as post-render callbacks
        if the request is HTMX.

    Notes:
        - Adds "HX-Request" to Vary headers for proper caching.
        - Context from swaps is merged with main context (swap context wins).
        - Title injection is HTML-escaped.

    Example:
        .. code-block:: python

            def form_submit(request):
                form = MyForm(request.POST)
                if form.is_valid():
                    obj = form.save()
                    return render_with_swaps(
                        request,
                        "form/success.html",
                        {"form": form},
                        swaps=[
                            Swap("components/badge.html", context={"count": get_count()}),
                            Swap("components/notification.html", target_id="flash-messages"),
                        ],
                        title="Success!",
                    )
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

    Args:
        request: The HTTP request object.
        template_name: Path to the full template containing partial blocks.
        context: Optional template context.
        content_type: Optional response content type.
        status: Optional HTTP status code.
        using: Optional template engine.
        partial: Specifies which partial to render for HTMX requests.
            Can be a block name (`"#content"`), standalone path, callable, or
            dict mapping names to targets. Defaults to "#content".
        swaps: Additional out-of-band swaps to include.
        title: Optional page title. Overrides title context variable.

    Returns:
        A TemplateResponse with partial resolution and OOB swaps.

    Example:
        .. code-block:: python

            # Basic partial selection
            return render_nav(
                request,
                "project/detail.html",
                {"project": project},
                partial="#tab_content",
            )

            # Multiple partial targets with swaps
            return render_nav(
                request,
                "project/detail.html",
                {"project": project},
                partial={
                    "#tab_content": targeting("tab-content"),
                    "#main_content": targeting("main-content"),
                    "#content": True,  # fallback
                },
                swaps=[
                    Swap("partials/sidebar.html", target_id="sidebar"),
                    Swap("partials/notification.html", target_id="flash"),
                ],
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
